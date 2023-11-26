import asyncio
import json
import os
import time

import pytest

import quickbolt.reporting.response_csv as rc
from quickbolt.clients import AioRequests

pytestmark = pytest.mark.client

root_dir = f"{os.path.dirname(__file__)}/{__name__.split('.')[-1]}"
headers = {}
url = "https://jsonplaceholder.typicode.com/users/1"
post_url = "https://jsonplaceholder.typicode.com/posts"


def test_request(
    batch=None, delay=0, report=True, full_scrub_fields=None, delete=True, **kwargs
):
    pytest.aio_requests = AioRequests(root_dir=root_dir)
    pytest.run_info_path = pytest.aio_requests.logging.run_info_path

    batch = batch or {"method": "get", "headers": headers, "url": url}
    response = pytest.aio_requests.request(
        batch, delay=delay, report=report, full_scrub_fields=full_scrub_fields, **kwargs
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
        assert os.path.exists(stream_path)
    else:
        assert responses[0].get("message")

    if delete:
        asyncio.run(pytest.aio_requests.logging.delete_run_info(root_dir))
        path = pytest.aio_requests.logging.log_file_path
        assert not os.path.exists(path)


def test_post_string_request():
    pytest.aio_requests = AioRequests(root_dir=root_dir)
    pytest.run_info_path = pytest.aio_requests.logging.run_info_path
    payload = {
        "title": "test title",
        "body": "test body message",
    }

    response = pytest.aio_requests.request(
        {
            "url": post_url,
            "method": "post",
            "headers": {"Content-Type": "application/json"},
            "data": json.dumps(payload),
        }
    )["responses"][0]

    assert response["message"]["title"] == payload["title"]
    assert response["message"]["body"] == payload["body"]


def test_request_multiple():
    batch = [
        {"method": "get", "headers": headers, "url": url},
        {"method": "get", "headers": headers, "url": url},
    ]
    test_request(batch)


def test_request_delay():
    start = time.perf_counter()
    test_request(delay=2)
    stop = time.perf_counter() - start
    assert stop >= 2


def test_request_content_stream():
    stream_path = f"{pytest.run_info_path}/streamed_content.txt"
    test_request(stream_path=stream_path)


def test_request_report():
    test_request(report=False)
    assert not os.path.exists(pytest.aio_requests.csv_path)


def test_request_report_full_scrub_fields():
    full_scrub_fields = ["message"]
    test_request(full_scrub_fields=full_scrub_fields, delete=False)
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

    scrubbed_csv_path = pytest.aio_requests.csv_path.replace(".csv", "_scrubbed.csv")
    scrubbed_dict = asyncio.run(rc.csv_to_dict(scrubbed_csv_path))
    assert scrubbed_dict[0]["MESSAGE"] == expected_message

    asyncio.run(pytest.aio_requests.logging.delete_run_info(root_dir))
    path = pytest.aio_requests.logging.log_file_path
    assert not os.path.exists(path)
