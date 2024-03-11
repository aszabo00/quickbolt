import asyncio
import sys

import pytest
import uvloop


def pytest_addoption(parser):
    parser.addoption("--test-debug", action="store", default=False)


@pytest.fixture
def test_debug(request):
    return request.config.getoption("--test-debug").lower() == "true"


def pytest_configure(config):
    if sys.platform != "win32":
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())


@pytest.fixture(autouse=True, scope="module")
def event_loop():
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    yield loop
    loop.close()
