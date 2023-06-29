import asyncio
import os as sos
import time

import aiofiles.os as aos
import pytest

from quickbolt.clients import AioRequests

pytestmark = pytest.mark.client


@pytest.fixture(scope="module")
def event_loop():
    pytest.root_dir = f"{sos.path.dirname(__file__)}/{__name__.split('.')[-1]}"
    pytest.headers = {}
    pytest.url = "https://jsonplaceholder.typicode.com/users/1"

    pytest.aio_requests = AioRequests(root_dir=pytest.root_dir, reuse=True)
    pytest.run_info_path = pytest.aio_requests.logging.run_info_path

    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.mark.asyncio
async def test_request(batch=None, delay=0, report=True, **kwargs):
    batch = batch or {"method": "get", "headers": pytest.headers, "url": pytest.url}
    response = await pytest.aio_requests.async_request(
        batch, delay=delay, report=report, **kwargs
    )

    assert response.get("duration")

    responses = response.get("responses")
    assert responses

    response_fields = [
        "description",
        "code_mismatch",
        "batch_number",
        "index",
        "method",
        "expected_code",
        "actual_code",
        "message",
        "url",
        "server_headers",
        "response_seconds",
        "delay_seconds",
        "utc_time",
        "headers",
    ]
    for field in response_fields:
        assert responses[0].get(field, "missing") != "missing"

    assert responses[0].get("actual_code") == "200"

    stream_path = kwargs.get("stream_path")
    if stream_path:
        assert await aos.path.exists(stream_path)
    else:
        assert responses[0].get("message")


@pytest.mark.asyncio
async def test_request_multiple():
    batch = [
        {"method": "get", "headers": pytest.headers, "url": pytest.url},
        {"method": "get", "headers": pytest.headers, "url": pytest.url},
    ]
    await test_request(batch)


@pytest.mark.asyncio
async def test_request_delay():
    start = time.perf_counter()
    await test_request(delay=2)
    stop = time.perf_counter() - start
    assert stop >= 2


@pytest.mark.asyncio
async def test_request_content_stream():
    stream_path = f"{pytest.run_info_path}/streamed_content.txt"
    await test_request(stream_path=stream_path)


@pytest.mark.asyncio
async def test_no_request_report():
    await pytest.aio_requests.logging.delete_run_info(pytest.root_dir)
    path = pytest.aio_requests.logging.log_file_path
    assert not await aos.path.exists(path)

    await test_request(report=False)
    assert not await aos.path.exists(pytest.aio_requests.csv_path)


@pytest.mark.asyncio
async def test_close_connection():
    await pytest.aio_requests.close()
    assert pytest.aio_requests.session is None
