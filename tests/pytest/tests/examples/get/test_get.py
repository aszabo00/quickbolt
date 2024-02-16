from pathlib import Path

import pytest

from tests.client.gprc.servers import helloworld_pb2, helloworld_pb2_grpc
from tests.pytest.tests.examples.some_pytest_base import SomePytestBase

pytestmark = pytest.mark.core_pytest_base


class TestGetExample(SomePytestBase):
    file_path = Path(__file__)
    root_dir = str(Path().joinpath(*file_path.parts[:-4]))
    purge_run_info = True

    headers = {}
    url = "https://jsonplaceholder.typicode.com/users/1"

    def test_check_imported_data(self):
        expected_data = {"key1": "value1", "key2": {"key1": "value1"}}
        data = self.credentials_data["credentials"]["data"]
        assert data == expected_data

        data = self.tests_data["data"]["data"]
        assert data == expected_data

    async def test_get_example_request(self):
        batch = {"method": "get", "headers": self.headers, "url": self.url}
        await self.aio_requests.async_request(batch)

    async def test_get_example_call(self):
        options = {
            "secure": False,
            "address": "localhost:50051",
            "stub": helloworld_pb2_grpc.GreeterStub,
            "method": "SayHello",
            "method_args": helloworld_pb2.HelloRequest(name="Quickbolt"),
        }
        await self.aio_grpc.call(options)
