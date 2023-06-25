import asyncio
import os as sos
from pathlib import Path

import aiofiles.os as aos
import pytest

import quickbolt.utils.directory as dh

pytestmark = pytest.mark.utils


@pytest.fixture(scope="module")
def event_loop():
    pytest.base_path = sos.path.dirname(__file__)
    pytest.test_dict = {
        "str1": "value1",
        "int1": 2,
        "list1": ["str1", "str2"],
        "list2": [0, 1],
    }

    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.mark.asyncio
async def test_safe_mkdirs():
    path = pytest.base_path + "/test_dir"
    await dh.safe_mkdirs(path)
    assert await aos.path.exists(path)

    await aos.rmdir(path)
    assert not await aos.path.exists(path)


@pytest.mark.asyncio
async def test_safe_mkdirs_sync():
    path = pytest.base_path + "/test_dir"
    dh.safe_mkdirs_sync(path)
    assert await aos.path.exists(path)

    await aos.rmdir(path)
    assert not await aos.path.exists(path)


@pytest.mark.asyncio
async def test_make_json():
    path = pytest.base_path + "/test.json"
    await dh.make_json(pytest.test_dict, path)
    assert await aos.path.exists(path)

    await aos.remove(path)
    assert not await aos.path.exists(path)


@pytest.mark.asyncio
async def test_make_json_append():
    path = pytest.base_path + "/test_append.json"
    await dh.make_json(pytest.test_dict, path)
    assert await aos.path.exists(path)

    extra_dict = {"new_key": "new_value"}
    await dh.make_json(extra_dict, path, append=True)
    assert await aos.path.exists(path)

    appended_dict = await dh.load_json(path)
    assert appended_dict == {**pytest.test_dict, **extra_dict}

    await aos.remove(path)


@pytest.mark.asyncio
async def test_make_json_ascii():
    path = pytest.base_path + "/test_ascii.json"
    await dh.make_json(pytest.test_dict, path, ensure_ascii=True)
    assert await aos.path.exists(path)

    await aos.remove(path)
    assert not await aos.path.exists(path)


@pytest.mark.asyncio
async def test_load_json():
    path = pytest.base_path + "/test_load.json"
    await dh.make_json(pytest.test_dict, path)
    assert await aos.path.exists(path)

    loaded_dict = await dh.load_json(path)
    assert loaded_dict == pytest.test_dict

    await aos.remove(path)
    assert not await aos.path.exists(path)


def test_find_reference_in_list_directory():
    references = [
        "/foo/apple.txt",
        "/foo/bar",
        "/foo/bar/orange.txt",
        "/foo/bar/py/peach.txt",
    ]
    reference = dh.find_reference_in_list("peach.txt", references)
    assert reference == references[-1]


def test_find_reference_in_list_file():
    references = [
        "/foo/apple.txt",
        "/foo/bar",
        "/foo/bar/orange.txt",
        "/foo/bar/py/peach.txt",
    ]
    reference = dh.find_reference_in_list("bar", references)
    assert reference == references[1]


def test_get_root_dir():
    root_dir = dh.get_root_dir()
    expected_root_dir = "/".join(__file__.split("/")[:-4])
    assert root_dir == expected_root_dir


def test_get_root_dir_root_checks():
    root_dir = dh.get_root_dir(root_checks=["bad_check"])
    expected_root_dir = "/".join(__file__.split("/")[:-4])
    assert root_dir == expected_root_dir


def test_get_src_app_dir():
    app_dir = dh.get_src_app_dir()
    expected_dir = f"{dh.get_root_dir()}/tests/utils/directory"
    assert app_dir == expected_dir


@pytest.mark.asyncio
async def test_expand_directory():
    expanded_dir = await dh.expand_directory(pytest.base_path)
    expanded_dir = [Path(e) for e in expanded_dir if "__pycache__" not in e]
    actual_files = [e.name for e in expanded_dir]
    expected_files = ["directory", "__init__.py", "test_directory_utils.py"]
    assert actual_files == expected_files
