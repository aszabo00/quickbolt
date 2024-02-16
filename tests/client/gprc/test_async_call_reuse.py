from os import setsid
from pathlib import Path
from socket import create_connection
from subprocess import PIPE, Popen
from time import perf_counter, sleep

import pytest
from aiofiles.ospath import exists as aexists

import quickbolt.reporting.response_csv as rc
from quickbolt.clients.aio_grpc import AioGPRC
from tests.client.gprc.servers import helloworld_pb2, helloworld_pb2_grpc

pytestmark = pytest.mark.client

path = Path(__file__)
parent = path.joinpath(*path.parts[:-1])
root_dir = str(parent / path.stem)
host = "localhost"
port = 50051
_options = {
    "secure": False,
    "address": f"{host}:{port}",
    "stub": helloworld_pb2_grpc.GreeterStub,
    "method": "SayHello",
    "method_args": helloworld_pb2.HelloRequest(name="Quickbolt"),
}

# # to compile the proto file
# python -m grpc_tools.protoc -I. --python_out=. --pyi_out=. --grpc_python_out=. helloworld.proto


def is_server_online(host, port, timeout=1):
    try:
        with create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


@pytest.fixture(scope="module", autouse=True)
def setup_teardown():
    process = Popen(
        'export PYTHONPATH="/workspaces/quickbolt":$PYTHONPATH && \
            python async_greeter_server.py',
        stdout=PIPE,
        stderr=PIPE,
        shell=True,
        cwd=f"{parent}/servers",
        preexec_fn=setsid,
    )

    while True:
        if is_server_online(host, port):
            break
        sleep(0.25)

    yield

    process.kill()


async def test_call(
    options=None,
    delay=0,
    report=True,
    full_scrub_fields=None,
    delete=True,
    actual_code="OK",
):
    pytest.aio_grpc = AioGPRC(root_dir, True)
    pytest.run_info_path = pytest.aio_grpc.logging.run_info_path

    options = options or _options
    response = await pytest.aio_grpc.call(options, delay, report, full_scrub_fields)

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
        "address",
        "server_headers",
        "response_seconds",
        "delay_seconds",
        "utc_time",
        "headers",
    ]

    for field in response_fields:
        for response in responses:
            assert response.get(field, "missing") != "missing"

    assert responses[0].get("actual_code") == actual_code

    if delete:
        await pytest.aio_grpc.logging.delete_run_info(root_dir)
        path = pytest.aio_grpc.logging.log_file_path
        assert not await aexists(path)

    return response


async def test_call_multiple():
    options = [_options] * 2
    await test_call(options)


async def test_call_delay():
    start = perf_counter()
    await test_call(delay=2)
    stop = perf_counter() - start
    assert stop >= 2


async def test_call_report():
    await test_call(report=False)
    assert not await aexists(pytest.aio_grpc.csv_path)


async def test_call_report_full_scrub_fields():
    full_scrub_fields = ["message"]
    await test_call(full_scrub_fields=full_scrub_fields, delete=False)
    expected_message = {"message": '{\n  "greeting": "Hello, Quickbolt!"\n}'}

    scrubbed_csv_path = pytest.aio_grpc.csv_path.replace(".csv", "_scrubbed.csv")
    scrubbed_dict = await rc.csv_to_dict(scrubbed_csv_path)
    assert scrubbed_dict[0]["MESSAGE"] == expected_message

    await pytest.aio_grpc.logging.delete_run_info(root_dir)
    path = pytest.aio_grpc.logging.log_file_path
    assert not await aexists(path)


async def test_close_channel():
    await pytest.aio_grpc.close()
    assert pytest.aio_grpc.channel is None
