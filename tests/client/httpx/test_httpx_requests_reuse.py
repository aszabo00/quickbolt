import os as sos
import time

import aiofiles.os as aos
import pytest

import quickbolt.reporting.response_csv as rc
from quickbolt.clients import HttpxRequests

pytestmark = pytest.mark.client


@pytest.fixture(scope="module", autouse=True)
def default_values():
    pytest.root_dir = f"{sos.path.dirname(__file__)}/{__name__.split('.')[-1]}"
    pytest.headers = {}
    pytest.url = "https://jsonplaceholder.typicode.com/users/1"


async def test_request(
    batch=None, delay=0, report=True, full_scrub_fields=None, **kwargs
):
    pytest.httpx_requests = HttpxRequests(root_dir=pytest.root_dir, reuse=True)
    pytest.run_info_path = pytest.httpx_requests.logging.run_info_path

    batch = batch or {"method": "get", "headers": pytest.headers, "url": pytest.url}
    response = await pytest.httpx_requests.async_request(
        batch, delay=delay, report=report, full_scrub_fields=full_scrub_fields, **kwargs
    )

    assert response.get("duration") is not None

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
    assert responses[0].get("message")

    assert pytest.httpx_requests.client is not None

    stream_path = kwargs.get("stream_path")
    if stream_path:
        assert await aos.path.exists(stream_path)


async def test_request_multiple():
    batch = [
        {"method": "get", "headers": pytest.headers, "url": pytest.url},
        {"method": "get", "headers": pytest.headers, "url": pytest.url},
    ]
    await test_request(batch)


async def test_request_delay():
    start = time.perf_counter()
    await test_request(delay=2)
    stop = time.perf_counter() - start
    assert stop >= 2


async def test_request_content_stream():
    stream_path = f"{pytest.run_info_path}/streamed_content.txt"
    await test_request(stream_path=stream_path)


async def test_request_report_full_scrub_fields():
    full_scrub_fields = ["message"]
    await test_request(full_scrub_fields=full_scrub_fields)
    expected_message = {
        "id": "0000000",
        "name": "0000000000000",
        "username": "0000",
        "email": "00000000000000000",
        "address": {
            "street": "00000000000",
            "suite": "00000000",
            "city": "00000000000",
            "zipcode": "0000000000",
            "geo": {"lat": "00000000", "lng": "0000000"},
        },
        "phone": "000000000000000000000",
        "website": "0000000000000",
        "company": {
            "name": "000000000000000",
            "catchPhrase": "00000000000000000000000000000000000000",
            "bs": "000000000000000000000000000",
        },
    }

    scrubbed_csv_path = pytest.httpx_requests.csv_path.replace(".csv", "_scrubbed.csv")
    scrubbed_dict = await rc.csv_to_dict(scrubbed_csv_path)
    assert scrubbed_dict[-1]["MESSAGE"] == expected_message


async def test_no_request_report():
    await pytest.httpx_requests.logging.delete_run_info(pytest.root_dir)
    path = pytest.httpx_requests.logging.log_file_path
    assert not await aos.path.exists(path)

    await test_request(report=False)
    assert not await aos.path.exists(pytest.httpx_requests.csv_path)


async def test_close_connection():
    try:
        await pytest.httpx_requests.close()
        assert pytest.httpx_requests.client is None
    except:
        if not pytest.httpx_requests.client.is_closed:
            raise Exception("The client not closed.")
