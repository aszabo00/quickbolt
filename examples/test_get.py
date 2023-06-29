import asyncio

import pytest

from tests.pytest.tests.examples.some_pytest_base import SomePytestBase

pytestmark = pytest.mark.core_pytest_base


class TestGetExample(SomePytestBase):
    purge_run_info = True

    headers = {}
    url = "https://jsonplaceholder.typicode.com/users/1"

    @pytest.fixture(scope="class")
    def event_loop(request):
        loop = asyncio.new_event_loop()

        yield loop

        loop.close()

    def test_check_imported_data(self):
        expected_data = {"key1": "value1", "key2": {"key1": "value1"}}
        data = self.credentials_data["credentials"]["data"]
        assert data == expected_data

        data = self.tests_data["data"]["data"]
        assert data == expected_data

    @pytest.mark.asyncio
    async def test_get_example_request(self):
        batch = {"method": "get", "headers": self.headers, "url": self.url}
        await self.aio_requests.async_request(batch)
