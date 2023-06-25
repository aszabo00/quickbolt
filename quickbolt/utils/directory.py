import json
import os as sos
from glob import iglob
from pathlib import Path

import aiofiles.os as aos
from aiofiles import open as aopen

import quickbolt.utils.json as jh


async def safe_mkdirs(path: str):
    """
    This makes new directories if needed.

    Args:
        path: The full path of the would be directory.
    """
    if not await aos.path.exists(path):
        await aos.makedirs(path, exist_ok=True)


def safe_mkdirs_sync(path: str):
    """
    This makes new directories if needed.

    Args:
        path: The full path of the would be directory.
    """
    if not sos.path.exists(path):
        sos.makedirs(path, exist_ok=True)


async def make_json(
    content: dict, path: str, append: bool = False, ensure_ascii: bool = False
):
    """
    This writes a dictionary to a json file.

    Args:
        content: The content to write.
        path: The path to write to.
        append: Whether to append data to an existing json.
        ensure_ascii: Whether to contain ASCII characters.
    """
    if append and await aos.path.exists(path):
        stored_json = await load_json(path)
        content = {**stored_json, **content}

    parent = Path(path).parent
    await safe_mkdirs(parent)

    if not ensure_ascii:
        data = jh.serialize(content)
    else:
        data = json.dumps(content, indent=2, ensure_ascii=ensure_ascii)

    async with aopen(path, "w") as f:
        await f.write(data)


async def load_json(path: str) -> dict:
    """
    This reads and loads json into python from a file.

    Args:
        path: The path to read from.

    Returns:
        data: The json data.
    """
    if not await aos.path.exists(path):
        return {}

    async with aopen(path) as f:
        read = await f.read()
        return jh.deserialize(read)


def find_reference_in_list(name: str, references: list) -> str:
    """
    This finds the matching reference (file path) in a list of references.

    Args:
        name: The name of the file to look for.
        references: The list of references to look through for a match.

    Returns:
        reference: The matching reference from the list.
    """
    return next((ref for ref in references if ref.endswith("/" + name)), 0)


def get_root_dir(root_checks: None | list[str] = None) -> str:
    """
    This gets the root directory by looking for ['.lock', 'tests', 'Pipfile', 'Poetry'].

    Args:
        root_checks: The things to check for to identify the project's root directory.

    Returns:
        root_dir: The root dir of the project.
    """
    root_checks = root_checks or []

    default_checks = [
        ".git",
        "pytest.ini",
        "poetry.lock",
        "Pipfile.lock",
        "pyproject.toml",
        "Pipfile",
    ]
    root_checks.extend(default_checks)

    cwd = Path.cwd()
    for path in [cwd] + list(cwd.parents):
        if any(Path(path, root).exists() for root in root_checks):
            return str(path)

    return None


def get_src_app_dir(root_dir: None | str = None) -> str:
    """
    This finds which src app directory (app, map, ..) we're automating against.

    Args:
        root_dir: The root directory.

    Returns:
        app: The src app/project folder path in use.
    """
    root_dir = root_dir or get_root_dir()
    calling_test = sos.environ.get("PYTEST_CURRENT_TEST", "")
    calling_test = calling_test.split("::")[0]
    calling_test_name = Path(calling_test).name

    root_path = Path(root_dir)
    file_path = next(
        (f for f in root_path.rglob("*") if f.name == calling_test_name), None
    )

    return str(file_path.parent)


async def expand_directory(path: str) -> list:
    """
    This expands a directory into a list of its files absolute paths.

    Args:
        path: The path of the directory to traverse.

    Returns:
        files: The list of files in a directory.
    """
    files = [path]
    if await aos.path.isdir(path):
        files = [
            f
            for f in iglob(f"{path}//**", recursive=True)
            if "ds_store" not in f.lower()
        ]
    return files
