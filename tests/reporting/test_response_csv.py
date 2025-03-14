import asyncio
import os as sos
from random import randint
from shutil import copy

import aiofiles.os as aos
import pytest

import quickbolt.reporting.response_csv as rc
import quickbolt.utils.json as jh

pytestmark = pytest.mark.reporting


@pytest.fixture(scope="module", autouse=True)
def default_vaults():
    pytest.csv_dir = f"{sos.path.dirname(__file__)}/validations"
    pytest.csv_path = f"{pytest.csv_dir}/response_csv.csv"

    pytest.test_field = {"field": "Test12345"}
    pytest.response = {
        "duration": 4.58,
        "responses": [
            {
                "description": None,
                "code_mismatch": "",
                "batch_number": 1,
                "index": 1,
                "method": "GET",
                "expected_code": None,
                "actual_code": "200",
                "message": {
                    "args": {},
                    "headers": {
                        "Accept": "*/*",
                        "Accept-Encoding": "gzip, deflate",
                        "Host": "httpbin.org",
                        "User-Agent": "Python/3.11 aiohttp/3.8.4",
                        "X-Amzn-Trace-Id": "Root=1-6493e2fa-24520f204c55802545a3fdfc",
                    },
                    "origin": "70.80.147.182",
                    "url": "https://httpbin.org/get",
                },
                "url": "https://httpbin.org/get",
                "server_headers": {
                    "Date": "Thu, 22 Jun 2023 05:58:22 GMT",
                    "Content-Type": "application/json",
                    "Content-Length": "310",
                    "Connection": "keep-alive",
                    "Server": "gunicorn/19.9.0",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Credentials": "true",
                },
                "utc_time": "2023-06-22T05:58:22.882526+00:00",
                "headers": {},
                "kwargs": {},
                "body": None,
                "response_seconds": 4.57,
                "delay_seconds": 0.0,
            }
        ],
    }


async def test_read_csv():
    response_csv = await rc.read_csv(pytest.csv_path)
    assert response_csv
    assert len(response_csv) == 2


def test_scrub():
    data = {"new_field": "Test12345"}
    data_message = jh.serialize(data)
    scrubbed_data_message = rc.scrub(data_message)
    scrubbed_data = jh.deserialize(scrubbed_data_message)
    assert scrubbed_data["new_field"] == "000000000"


def test_scrub_leading_zeros():
    data = {"leading_zeros": 10000}
    data_message = jh.serialize(data)
    scrubbed_data_message = rc.scrub(data_message)

    assert scrubbed_data_message == '{\n  "leading_zeros": "00000 <int>"\n}'
    assert jh.deserialize(scrubbed_data_message) == {"leading_zeros": "00000 <int>"}


def test_scrub_data():
    data = {
        "actual_code": "200",
        "headers": pytest.test_field,
        "body": pytest.test_field,
        "message": pytest.test_field,
    }
    scrubbed_data = rc.scrub_data(data)
    expected_scrubbed_data = {
        "actual_code": "200",
        "headers": {"field": "000000000"},
        "body": {"field": "000000000"},
        "message": {"field": "000000000"},
    }
    assert scrubbed_data == expected_scrubbed_data


def test_scrub_full_fields():
    full_scrub_fields = ["headers", "kwargs"]
    data = {
        "actual_code": "200",
        "headers": {
            "field1": "Bearer 987644r8g789sd78d9s7f9s-qasdfvbn-97saaa7df9s-7s9s79f89s7f8s-89sf98sd79f87s9",
            "field2": "Bearer 788887y8g789sd78d9s7f9s-qasdfvbn-97saaa7df9s-7s9s79f89s7f8s-89sf98sd79f87s9",
        },
        "body": pytest.test_field,
        "message": pytest.test_field,
        "kwargs": {"field": "87787-5343-some_data-2322"},
    }
    scrubbed_data = rc.scrub_data(data, full_scrub_fields)
    expected_scrubbed_data = {
        "actual_code": "200",
        "headers": {
            "field1": "0000000000000000000000000000000000000000000000000000000000000000000000000000000000",
            "field2": "0000000000000000000000000000000000000000000000000000000000000000000000000000000000",
        },
        "body": {"field": "000000000"},
        "message": {"field": "000000000"},
        "kwargs": {"field": "0000000000000000000000000"},
    }
    assert scrubbed_data == expected_scrubbed_data


async def test_csv_to_dict_path():
    response_dict = await rc.csv_to_dict(pytest.csv_path)
    assert response_dict
    assert isinstance(response_dict[0], dict)


async def test_csv_to_dict_data():
    response_csv = await rc.read_csv(pytest.csv_path)
    response_dict = await rc.csv_to_dict(response_csv)
    assert response_dict
    assert isinstance(response_dict[0], dict)


async def test_csv_to_dict_path_scrub_data():
    response_csv = await rc.read_csv(pytest.csv_path)
    response_csv[1][11] = pytest.test_field
    response_dict = await rc.csv_to_dict(response_csv, scrub=True)

    assert response_dict
    assert isinstance(response_dict[0], dict)
    assert response_dict[0]["HEADERS"] == {"field": "000000000"}


async def test_csv_to_dict_path_scrub_data_full_fields():
    full_scrub_fields = ["headers", "message"]
    response_csv = await rc.read_csv(pytest.csv_path)
    response_csv[1][11] = pytest.test_field
    response_dict = await rc.csv_to_dict(
        response_csv, scrub=True, full_scrub_fields=full_scrub_fields
    )

    assert response_dict
    assert isinstance(response_dict[0], dict)
    assert response_dict[0]["HEADERS"] == {"field": "000000000"}
    assert response_dict[0]["MESSAGE"] == {
        "args": 0,
        "headers": {
            "Accept": "000",
            "Accept-Encoding": "0000000000000",
            "Host": "00000000000",
            "User-Agent": "0000000000000000000000000",
            "X-Amzn-Trace-Id": "0000000000000000000000000000000000000000",
        },
        "origin": "0000000000000",
        "url": "00000000000000000000000",
    }


async def test_create_csv_report(scrub=False, delete=True):
    async def check_creation(path, delete):
        assert await aos.path.exists(path)
        response_csv = await rc.read_csv(path)
        response_dict = await rc.csv_to_dict(response_csv)
        assert response_dict
        not delete or await aos.remove(path)

    pytest.response["responses"][0]["headers"] = pytest.test_field

    randoms = "".join(str(randint(0, 9)) for _ in range(10))
    csv_copy = pytest.csv_path.replace(".csv", f"_{randoms}.csv")
    await asyncio.to_thread(copy, pytest.csv_path, csv_copy)

    await rc.create_csv_report(csv_copy, pytest.response, scrub=scrub)

    csv_scrubbed_copy = ""
    if scrub:
        csv_scrubbed_copy = csv_copy.replace(".csv", "_scrubbed.csv")
        await check_creation(csv_scrubbed_copy, delete)

    await check_creation(csv_copy, delete)

    return [csv_copy, csv_scrubbed_copy]


async def test_create_csv_report_scrub():
    await test_create_csv_report(scrub=True)


async def test_add_rows_to_csv_report(delete=True):
    csv_copy, _ = await test_create_csv_report(delete=False)
    response_csv = await rc.read_csv(csv_copy)
    await rc.add_rows_to_csv_report(csv_copy, [response_csv[1]])

    response_csv = await rc.read_csv(csv_copy)
    assert len(response_csv) == 4
    assert response_csv[1] == response_csv[3]

    not delete or await aos.remove(csv_copy)
    return csv_copy


async def test_delete_last_n_rows_from_csv_report():
    csv_copy, _ = await test_create_csv_report(delete=False)
    await rc.delete_last_n_rows_from_csv_report(csv_copy, 2)

    response_csv = await rc.read_csv(csv_copy)
    assert len(response_csv) == 2
    await aos.remove(csv_copy)


async def test_add_column_to_csv_report():
    csv_copy, _ = await test_create_csv_report(delete=False)
    await rc.add_column_to_csv_report(
        csv_copy, ["New Column Value0", "New Column Value1", "New Column Value2"]
    )

    response_csv = await rc.read_csv(csv_copy)
    assert response_csv[0][-1] == "New Column Value0"
    assert response_csv[1][-1] == "New Column Value1"
    assert response_csv[2][-1] == "New Column Value2"
    await aos.remove(csv_copy)
