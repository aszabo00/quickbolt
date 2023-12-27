import asyncio
from pathlib import Path

import pytest

import quickbolt.reporting.response_csv as rc
from quickbolt.clients import AioRequests
from quickbolt.pytest import CorePytestBase

pytestmark = pytest.mark.core_pytest_base


class TestGetExample:
    file_path = Path(__file__)
    root_dir = str(Path().joinpath(*file_path.parts[:-4]))
    purge_run_info = True

    headers = {}
    url = "https://jsonplaceholder.typicode.com/users/1"

    @pytest.fixture(scope="class")
    def event_loop(self):
        pytest.aio_requests = AioRequests(root_dir=self.root_dir)
        pytest.core_pytest_base = CorePytestBase()
        pytest.core_pytest_base.csv_path = pytest.aio_requests.csv_path
        pytest.core_pytest_base.root_dir = self.root_dir

        loop = asyncio.new_event_loop()

        yield loop

        loop.close()

    @pytest.mark.asyncio
    async def test_get_example_request(self):
        batch = {"method": "get", "headers": self.headers, "url": self.url}
        await pytest.aio_requests.async_request(batch)

        await pytest.core_pytest_base.validate_mismatches()

        error_dict = await rc.csv_to_dict(pytest.core_pytest_base.error_file_path)
        error_row = next((r for r in error_dict if "error_values" in str(r)), None)
        assert list(error_row.values())[1] == [
            {
                "key": "MESSAGE.phone",
                "d1": "0-000-000-0000 000000",
                "d2": "0-000-000-0000 000000notthephonenumber",
            }
        ]

        if self.purge_run_info:
            await pytest.core_pytest_base.purge_run_info_dirs()
