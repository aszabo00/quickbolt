import asyncio
import os as sos

import aiofiles.os as aos
import pytest

import quickbolt.utils.directory as dh
from quickbolt.clients import HttpxRequests

pytestmark = pytest.mark.client


@pytest.fixture(scope="module")
def event_loop():
    pytest.root_dir = f"{sos.path.dirname(__file__)}/{__name__.split('.')[-1]}"
    pytest.expected_form_data = """{'data': {'field1': 'value1'}, 'files': [('file', <_io.BufferedReader name='root_dir/tests/client/httpx/test_form_data_separation.py'>)]}"""
    pytest.expected_form_data = pytest.expected_form_data.replace(
        "root_dir", dh.get_root_dir()
    )

    pytest.httpx_requests = HttpxRequests(root_dir=pytest.root_dir)

    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.mark.asyncio
async def test_dict_as_form_data():
    form_data = await pytest.httpx_requests.separate_form_data(
        field1="value1", file=__file__
    )
    assert str(form_data) == pytest.expected_form_data


@pytest.mark.asyncio
async def test_dict_as_form_data_kwargs():
    body = {"field1": "value1", "file": __file__}
    form_data = await pytest.httpx_requests.separate_form_data(**body)
    assert str(form_data) == pytest.expected_form_data

    await pytest.httpx_requests.logging.delete_run_info(pytest.root_dir)
    path = pytest.httpx_requests.logging.log_file_path
    assert not await aos.path.exists(path)
