import asyncio
import os as sos
from datetime import datetime

import aiofiles.os as aos
import pytest

import quickbolt.utils.directory as dh
from quickbolt.logging import AsyncLogger

pytestmark = pytest.mark.logging


@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


async def create_logging(by_time=False):
    root_dir = sos.path.dirname(__file__) + "/custom_root"

    logging = AsyncLogger(root_dir=root_dir, by_time=by_time)
    logger = logging.logger
    await logger.info("This is an example log message.")

    path = logging.log_file_path
    assert await aos.path.exists(path)

    run_info_path = logging.run_info_path
    expanded_dir = await dh.expand_directory(run_info_path)
    files = [
        "/".join(e.split("/")[-2:]) if e.split("/")[-1] else e.split("/")[-2]
        for e in expanded_dir
    ]
    expected_files = [
        "run_info",
        "run_info/run_logs",
        "run_logs/logging",
        "logging/fail",
        "logging/pass",
        "pass/async_logger.log",
    ]

    if not by_time:
        assert files == expected_files
    else:
        assert files != expected_files
        assert datetime.now().strftime("%Y-%m-%d_%H:") in str(files)

    await logging.delete_run_info(root_dir)
    assert not await aos.path.exists(path)


@pytest.mark.asyncio
async def test_logging_custom_root():
    await create_logging()


@pytest.mark.asyncio
async def test_logging_by_time():
    await create_logging(by_time=True)


@pytest.mark.asyncio
async def test_logging_custom_root_by_time_():
    await create_logging(by_time=True)
