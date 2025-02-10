from asyncio import sleep
from copy import copy, deepcopy
from datetime import datetime, timezone
from operator import itemgetter
from time import perf_counter

import pypeln as pl
from google.protobuf.json_format import MessageToDict
from grpc import ssl_channel_credentials
from grpc.aio import AioRpcError, Channel, insecure_channel, secure_channel

import quickbolt.reporting.response_csv as rc
import quickbolt.utils.sync_async as sa
from quickbolt.logging import AsyncLogger


class AioGPRC(object):
    """
    Code minifier for batching async grpc calls.
    """

    channel: None | Channel = None

    def __init__(self, root_dir: None | str = None, reuse: bool = False):
        """
        This is the constructor for AioGPRC.

        Args:
            root_dir: A specified root directory.
            reuse: Whether to reuse an existing channel.
        """
        self.logging = AsyncLogger(root_dir=root_dir)
        self.logger = self.logging.logger
        self.csv_path = self.logging.log_file_path.replace(".log", ".csv")

        self.reuse = reuse
        self.batch_number = 0
        self._return_history: list = []

    async def create_channel(
        self, address: str, options: dict, secure: bool = True
    ) -> Channel:
        """
        This creates an insecure channel to the server.

        Args:
            address: The address of the server to connect to.
            options: The options of the call.
            secure: Whether to use a secure or insecure channel.

        Returns:
            channel: The insecure channel to the server.
        """
        await self.logger.info(
            f"Creating the channel at {address} with options {options}."
        )

        ssl_creds = ssl_channel_credentials()
        _options = list(options.items())

        if not self.channel:
            self.channel = (
                secure_channel(address, ssl_creds, _options)
                if secure
                else insecure_channel(address, _options)
            )

        await self.logger.info(
            f"Created the channel at {address} with options {options}."
        )
        return self.channel

    async def close(self):
        """
        This closes the channel.
        """
        if self.channel is not None:
            await self.channel.close()
            self.channel = None

    async def _call(self, options: dict) -> dict:
        """
        This makes an async grpc call to the server.

        Args:
            options: The options of the call.

        Returns:
            response: The response of the call.
        """
        await self.logger.info(f"Making the call with the options {options}.")
        _options = deepcopy(options)

        description = _options.get("description", None)
        code = _options.get("code", None)
        delay = _options.get("delay", 0)
        index = _options.get("index", 0)

        secure = options.get("secure", True)
        address = _options.get("address", "")
        stub = _options.get("stub", None)
        method = _options.get("method", None)
        method_args = _options.get("method_args", None)
        headers = _options.get("headers", {})
        headers = list(headers.items())
        channel_options = _options.get("channel_options", {})
        actual_code = "OK"

        await self.create_channel(address, channel_options, secure=secure)
        stub_active = stub(self.channel)
        stub_method = getattr(stub_active, method)
        call = stub_method(method_args, metadata=headers)
        server_headers = await call.initial_metadata()
        server_headers = server_headers._metadata

        not delay or await sleep(delay)
        t0 = datetime.now(timezone.utc)
        try:
            response = await call
            t1 = datetime.now(timezone.utc)
            message = MessageToDict(response)
        except AioRpcError as e:
            t1 = datetime.now(timezone.utc)
            error_code = e.code()
            actual_code = error_code.name
            message = e.details()
        response_seconds = round((t1 - t0).total_seconds() * 1000, 2)

        code_mismatch = ""
        if code and actual_code not in code.split("|"):
            code_mismatch = "X"

        await self.logger.info(f"Made the call with the options {options}.")
        return {
            "description": description,
            "code_mismatch": code_mismatch,
            "batch_number": self.batch_number,
            "index": index + 1,
            "method": method,
            "expected_code": code,
            "actual_code": actual_code,
            "message": message,
            "address": address,
            "server_headers": dict(server_headers),
            "response_seconds": response_seconds,
            "delay_seconds": delay,
            "utc_time": t1.isoformat(),
            "headers": dict(headers),
            "kwargs": channel_options,
        }

    async def each_call(self, options: list[dict]) -> list:
        """
        The looping wrapper for _call.

        Args:
            options: The additional options of the call.

        Returns:
            responses: The responses of the calls (batch).
        """
        try:
            return await pl.task.map(
                lambda o: self._call(o), options, workers=len(options)
            )
        finally:
            self.reuse or await self.close()

    def update_options(self, options: list[dict], delay: int | float = 0) -> list:
        """
        This updates the call options with some internal fields.

        Args:
            options: The options of the call.
            delay: How long to delay between requests.

        Returns:
            options: The options with the included internal fields.
        """
        agg_delay = 0.0
        for i, o in enumerate(options):
            o["index"] = i
            agg_delay += delay
            o["delay"] = agg_delay
            options[i] = copy(o)
        return options

    async def call(
        self,
        options: list[dict] | dict,
        delay: int | float = 0,
        report: bool = True,
        full_scrub_fields: None | list = None,
    ) -> dict:
        """
        This is the user facing method for making an async gprc call.

        Args:
            options: The options of the call.
            delay: How long to delay between requests.
            report: Whether to create or update a report with the current responses.
            full_scrub_fields: The fields to do a full char scrub on.

        Returns:
            responses: The responses of the calls.
        """
        self.batch_number += 1
        if isinstance(options, dict):
            options = [options]
        options = self.update_options(options, delay)

        t0 = perf_counter()
        responses = await self.each_call(options)
        t1 = perf_counter()

        _return = {
            "duration": round(t1 - t0, 2),
            "responses": sorted(responses, key=itemgetter("index")),
        }
        self._return_history.append(_return)

        if _return["responses"]:
            not report or await rc.create_csv_report(
                self.csv_path, _return, scrub=True, full_scrub_fields=full_scrub_fields
            )

        await self.logger.info(f"Completed the call {_return}.")
        return _return

    @sa.force_sync
    async def call_sync(
        self,
        options: list[dict] | dict,
        delay: int | float = 0,
        report: bool = True,
        full_scrub_fields: None | list = None,
    ) -> dict:
        """
        This is the user facing method for making a sync gprc call.

        Args:
            options: The options of the call.
            delay: How long to delay between requests.
            report: Whether to create or update a report with the current responses.
            full_scrub_fields: The fields to do a full char scrub on.

        Returns:
            responses: The responses of the calls.
        """
        return await self.call(options, delay, report, full_scrub_fields)
