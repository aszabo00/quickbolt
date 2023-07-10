import asyncio
import time
from copy import deepcopy
from datetime import datetime, timezone
from operator import itemgetter
from pathlib import Path
from typing import Any

import orjson
import pypeln as pl
from aiohttp import ClientSession, FormData, TCPConnector

import quickbolt.reporting.response_csv as rc
import quickbolt.utils.directory as dh
import quickbolt.utils.sync_async as sa
from quickbolt.logging import AsyncLogger


class AioRequests(object):
    """
    Code minifier for batching async aio requests.
    """

    session: None | ClientSession = None

    def __init__(self, root_dir: None | str = None, reuse: bool = False):
        """
        This is the constructor for AioRequests.

        Args:
            root_dir: A specified root directory.
            reuse: Whether to reuse an existing session or open and close one for each request.
        """
        self.logging = AsyncLogger(root_dir=root_dir)
        self.logger = self.logging.logger
        self.csv_path = self.logging.log_file_path.replace(".log", ".csv")

        self.reuse = reuse

        self.batch_number = 0
        self._return_history = []

    async def close(self):
        if self.session is not None:
            await self.session.close()
            self.session = None

    async def dict_as_form_data(self, **kwargs: Any) -> FormData:
        """
        This converts a dictionary into form data for posting.

        Args:
            kwargs: The dictionary to convert.

        Returns:
            data: The data to be used as the value of a data parameter.
        """
        content_types = {
            "ico": None,
            "jpeg": None,
            "jpg": None,
            "png": None,
        }

        await self.logger.info(f"Converting dictionary {kwargs}.")
        data = FormData()

        for key, value in kwargs.items():
            if "file" in key:
                if not isinstance(value, list):
                    value = [value]

                expanded_dirs = [await dh.expand_directory(v) for v in value]
                file_paths = [
                    file_path for sublist in expanded_dirs for file_path in sublist
                ]

                for file_path in file_paths:
                    path = Path(file_path)
                    extension = path.suffix[1:].lower()
                    data.add_field(
                        key,
                        path.open("rb"),
                        filename=path.name,
                        content_type=content_types.get(extension, "text/html"),
                    )
            else:
                data.add_field(key, value)

        await self.logger.info(f"Converted dictionary {kwargs} into {data}.")
        return data

    async def build_request_info(
        self, data: list[dict] | dict, delay: int | float = 0, **kwargs: Any
    ) -> list:
        """
        This builds the object for making requests.

        Args:
            data: The list of info needed to make the request eg [{'url': ..., 'method': 'get'}].
            delay: How long to delay between requests.
            **kwargs: The additional params eg headers or data etc. See
                https://docs.aiohttp.org/en/stable/client_reference.html for more details.

        Returns:
            list: The prepped data and kwargs e.g. [data, kwargs]
        """
        if not isinstance(data, list):
            data = [data]

        agg_delay = 0.0
        for i, d in enumerate(data):
            agg_delay += delay
            f_data = d.get("data")

            if f_data and not isinstance(f_data, FormData):
                f_data = await self.dict_as_form_data(**f_data)

            data[i] = {**d, "delay": round(agg_delay, 2), "index": i, "data": f_data}

        return [data, deepcopy(kwargs)]

    async def _request(self, session: ClientSession, data: dict, **kwargs: Any) -> dict:
        """
        This makes the individual requests.

        Args:
            session: The request making session object.
            data: The info needed to make the request eg {'url': ..., 'method': 'get'}.
            **kwargs: The additional params eg headers or data etc. See
                https://docs.aiohttp.org/en/stable/client_reference.html for more details.

        Returns:
            _return: The complete response of the request.
        """
        kwargs.update(data)

        description = kwargs.pop("description", None)
        code = kwargs.pop("code", None)
        method = kwargs.pop("method", "").lower()
        url = kwargs.pop("url", "")
        delay = kwargs.pop("delay", 0)
        stream_path = kwargs.pop("stream_path", "")
        index = kwargs.pop("index", 0)

        await self.logger.info(f"Making the request with {data}.")
        not delay or await asyncio.sleep(delay)

        t0 = datetime.utcnow().replace(tzinfo=timezone.utc)
        async with session.request(method, url, ssl=False, **kwargs) as response:
            t1 = datetime.utcnow().replace(tzinfo=timezone.utc)
            response_seconds = round((t1 - t0).total_seconds(), 2)

            if stream_path:
                with open(stream_path, "wb") as fd:
                    async for content in response.content.iter_chunked(1024):
                        fd.write(content)

            try:
                message = await response.json(loads=orjson.loads)
            except Exception:
                try:
                    message = await response.text()
                except Exception:
                    message = ""

            code_mismatch = ""
            if code and str(code).split("|")[0] != str(response.status):
                code_mismatch = "X"

            _return = {
                "description": description,
                "code_mismatch": code_mismatch,
                "batch_number": self.batch_number,
                "index": index + 1,
                "method": response.method.upper(),
                "expected_code": code,
                "actual_code": str(response.status),
                "message": message,
                "url": url,
                "server_headers": response.headers,
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
                https://docs.aiohttp.org/en/stable/client_reference.html for more details.

        Returns:
            responses: The responses of the batch.
        """
        try:
            if not self.session:
                conn = TCPConnector(limit=1000)
                self.session = ClientSession(connector=conn)

            return await pl.task.map(
                lambda d: self._request(self.session, d, **kwargs),
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
                https://docs.aiohttp.org/en/stable/client_reference.html for more details.

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
                https://docs.aiohttp.org/en/stable/client_reference.html for more details.

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
