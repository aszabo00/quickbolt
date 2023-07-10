import asyncio
import time
from copy import deepcopy
from datetime import datetime, timezone
from operator import itemgetter
from typing import Any

import aiofiles.os as aos
import pypeln as pl
from httpx import AsyncClient

import quickbolt.reporting.response_csv as rc
import quickbolt.utils.json as jh
import quickbolt.utils.sync_async as sa
from quickbolt.logging import AsyncLogger


class HttpxRequests(object):
    """
    Code minifier for batching async httpx requests.
    """

    client: AsyncClient | None = None

    def __init__(
        self, root_dir: None | str = None, reuse: bool = False, **client_configs
    ):
        """
        This is the constructor for HttpxRequests.

        Args:
            root_dir: A specified root directory.
            reuse: Whether to reuse an existing client or open and close one for each request.
            client_configs: Additional configs are available here
                            https://github.com/encode/httpx/blob/5b06aea1d64f0815af6fe71da3ac725bed3ec09f/httpx/_client.py#L1291
                app: The Python web application to send requests to.
                base_url: The base url to use when calling into python web apps.
                transport: The transport class for sending requests over the network.
        """
        self.logging = AsyncLogger(root_dir=root_dir)
        self.logger = self.logging.logger
        self.csv_path = self.logging.log_file_path.replace(".log", ".csv")

        self.reuse = reuse
        self.client_configs = client_configs
        self.batch_number = 0
        self._return_history = []

    async def close(self):
        """
        This will close the httpx client connection.
        """
        if self.client:
            await self.client.aclose()
            self.client = None

    @staticmethod
    async def separate_form_data(**kwargs: Any) -> dict:
        """
        This separates out files and json from the data(multipart) object.

        Args:
            kwargs: A data object with containing both files and json.

        Returns:
            body: An object with separate fields for files and other json data.
        """
        body = {"data": {}}

        for key, value in kwargs.items():
            if "file" in key:
                if not isinstance(value, list):
                    value = [value]

                body["files"] = [
                    (key, open(f, "rb"))
                    if isinstance(f, str | bytes) and await aos.path.exists(f)
                    else f
                    for f in value
                ]
            else:
                body["data"][key] = value

        return body

    async def build_request_info(
        self, data: list[dict] | dict, delay: int | float = 0, **kwargs: Any
    ) -> list:
        """
        This builds the object for making requests.

        Args:
            data: The list of info needed to make the request eg [{'url': ..., 'method': 'get'}].
            delay: How long to delay between requests.
            **kwargs: The additional params eg headers or data etc. See
                https://github.com/encode/httpx/blob/5b06aea1d64f0815af6fe71da3ac725bed3ec09f/httpx/_client.py#L1481
                for more details.

        Returns:
            list: The prepped data and kwargs e.g. [data, kwargs]

        """
        if not isinstance(data, list):
            data = [data]

        agg_delay = 0
        for i, d in enumerate(data):
            agg_delay += delay
            f_data = d.pop("data", {})
            for field in ["file", "files"]:
                f_file = d.pop(field, None)
                if f_file:
                    f_data[field] = f_file

            d["delay"] = round(agg_delay, 2)
            d["index"] = i

            if f_data:
                body = f_data
                if any(isinstance(field, str | bytes) for field in ["file", "files"]):
                    body = await self.separate_form_data(**f_data)
                d.update(body)
            data[i] = d

            return [data, deepcopy(kwargs)]

    async def _request(self, client: AsyncClient, data: dict, **kwargs: Any) -> dict:
        """
        This makes the individual requests.

        Args:
            client: The request making client object.
            data: The info needed to make the request eg {'url': ..., 'method': 'get'}.
            **kwargs: The additional params eg headers or data etc. See
                https://github.com/encode/httpx/blob/5b06aea1d64f0815af6fe71da3ac725bed3ec09f/httpx/_client.py#L1481
                for more details.

        Returns:
            _return: The complete response of the request.
        """
        kwargs.update(data)

        description = kwargs.pop("description", None)
        code = kwargs.pop("code", None)
        method = kwargs.pop("method", "").upper()
        url = kwargs.pop("url", "")
        delay = kwargs.pop("delay", 0)
        stream_path = kwargs.pop("stream_path", "")
        index = kwargs.pop("index", 0)

        await self.logger.info(f"Making the request with {data}.")
        not delay or await asyncio.sleep(delay)

        t0 = datetime.utcnow().replace(tzinfo=timezone.utc)
        response = await client.request(method, url, **kwargs)

        t1 = datetime.utcnow().replace(tzinfo=timezone.utc)
        response_seconds = round((t1 - t0).total_seconds(), 2)

        if stream_path:
            with open(stream_path, "wb") as fd:
                async for content in response.aiter_bytes(1024):
                    fd.write(content)

        message = response.text
        try:
            message = jh.deserialize(message)
        except Exception:
            pass

        code_mismatch = ""
        if code and str(code).split("|")[0] != str(response.status_code):
            code_mismatch = "X"

        _return = {
            "description": description,
            "code_mismatch": code_mismatch,
            "batch_number": self.batch_number,
            "index": index + 1,
            "method": method,
            "expected_code": code,
            "actual_code": str(response.status_code),
            "message": message,
            "url": url,
            "server_headers": dict(response.headers),
            "response_seconds": response_seconds,
            "delay_seconds": delay,
            "utc_time": t1.isoformat(),
            "headers": kwargs.pop("headers", {}),
            "kwargs": kwargs,
        }

        if stream_path:
            _return["stream_path"] = stream_path

        await self.logger.info(f"Made the request with {data} \n returning {_return}.")

        return _return

    async def each_request(self, data: list[dict], **kwargs: Any) -> list:
        """
        The looping wrapper for _request.

        Args:
            data: The list of info needed to make the request eg [{'url': ..., 'method': 'get'}].
            **kwargs: The additional params eg headers or data etc. See
                https://github.com/encode/httpx/blob/5b06aea1d64f0815af6fe71da3ac725bed3ec09f/httpx/_client.py#L1291
                for more details.

        Returns:
            responses: The responses of the batch.
        """
        try:
            if not self.client:
                self.client = AsyncClient(timeout=300, **self.client_configs)

            return await pl.task.map(
                lambda d: self._request(self.client, d, **kwargs),
                data,
                workers=len(data),
            )
        finally:
            if not self.reuse:
                await self.close()

    @sa.force_sync
    async def request(
        self,
        data: list[dict] | dict,
        delay: int | float = 0,
        report: bool = True,
        full_scrub_fields: None | list = None,
        **kwargs: Any,
    ) -> dict:
        """
        The batch executor for the requests batch.

        Args:
            data: The list of info needed to make the request eg [{'url': ..., 'method': 'get'}].
            delay: How long to delay between requests.
            report: Whether to create or update a report with the current responses.
            full_scrub_fields: The fields to do a full char scrub on.
            **kwargs: The additional params eg headers or data etc. See
                https://github.com/encode/httpx/blob/5b06aea1d64f0815af6fe71da3ac725bed3ec09f/httpx/_client.py#L1481
                for more details.

        Returns:
            responses: The global response object eg {'duration': ..., 'responses': ...}.
        """
        return await self.async_request(
            data=data,
            delay=delay,
            report=report,
            full_scrub_fields=full_scrub_fields,
            **kwargs,
        )

    async def async_request(
        self,
        data: list[dict] | dict,
        delay: int | float = 0,
        report: bool = True,
        full_scrub_fields: None | list = None,
        **kwargs: Any,
    ) -> dict:
        """
        The batch executor for the async requests batch.

        Args:
            data: The list of info needed to make the request eg [{'url': ..., 'method': 'get'}].
            delay: How long to delay between requests.
            report: Whether to create or update a report with the current responses.
            full_scrub_fields: The fields to do a full char scrub on.
            **kwargs: The additional params eg headers or data etc. See
                https://github.com/encode/httpx/blob/5b06aea1d64f0815af6fe71da3ac725bed3ec09f/httpx/_client.py#L1481
                for more details.

        Returns:
            responses: The global response object eg {'duration': ..., 'responses': ...}.
        """
        self.batch_number += 1
        data, kwargs = await self.build_request_info(data, delay, **kwargs)

        t0 = time.perf_counter()
        responses = await self.each_request(data, **kwargs)
        t1 = time.perf_counter()

        _return = {
            "duration": round(t1 - t0, 2),
            "responses": sorted(responses, key=itemgetter("index")),
        }
        self._return_history.append(_return)
        await self.logger.info(f'The batch duration was {_return["duration"]} seconds.')

        if _return["responses"]:
            not report or await rc.create_csv_report(
                self.csv_path, _return, scrub=True, full_scrub_fields=full_scrub_fields
            )
        return _return
