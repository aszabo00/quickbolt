import asyncio
import os

import pytest

from quickbolt.logging import AsyncLogger
from quickbolt.validations import Validations

pytestmark = pytest.mark.validations


@pytest.fixture(scope="module")
def event_loop():
    pytest.root_dir = os.path.dirname(__file__)
    pytest.validations = Validations(root_dir=pytest.root_dir)

    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.mark.asyncio
async def test_validate_references():
    validations = Validations(root_dir=pytest.root_dir)
    actual_path = f"{pytest.root_dir}/get_example_scrubbed.csv"
    mismatches = await validations.validate_references(actual_path)
    assert not mismatches
    await validations.logging.delete_run_info()


@pytest.mark.asyncio
async def test_validate_references_mismatch(safe=True):
    validations = Validations(root_dir=pytest.root_dir)
    actual_path = f"{pytest.root_dir}/get_example_scrubbed_mismatch.csv"
    mismatches = await validations.validate_references(actual_path, safe=safe)

    assert mismatches
    assert mismatches[0]

    fields = [
        "values",
        "skipped_keys",
        "unscrubbed_refs",
        "actual_refs",
        "expected_refs",
    ]
    assert all(field in mismatches[0] for field in fields)

    expected_mismatches = [{"key": "ACTUAL_CODE", "d1": "404", "d2": "999"}]
    assert mismatches[0]["values"] == expected_mismatches

    await validations.logging.delete_run_info()


@pytest.mark.asyncio
async def test_validate_references_mismatch_not_safe():
    try:
        await test_validate_references_mismatch(safe=False)
        raise AssertionError
    except Exception as e:
        if isinstance(e, AssertionError):
            assert False
    await Validations(root_dir=pytest.root_dir).logging.delete_run_info()


@pytest.mark.asyncio
async def test_fail_no_debug():
    validations = Validations(root_dir=pytest.root_dir)
    log_file_path = validations.logging.log_file_path

    try:
        await validations.fail("Error message")
    except:
        log_generator = AsyncLogger(root_dir=pytest.root_dir).read_log_file(
            log_file_path
        )
        logs = [line async for line in log_generator]
        logs = "".join(logs)
        assert "Error message" in logs
        assert "Debugging the raise.\n" not in logs

    await validations.logging.delete_run_info()


@pytest.mark.asyncio
async def test_fail_debug():
    validations = Validations(root_dir=pytest.root_dir, debug=True)
    log_file_path = validations.logging.log_file_path
    await validations.fail("Error message")

    log_generator = AsyncLogger(root_dir=pytest.root_dir).read_log_file(log_file_path)
    logs = [line async for line in log_generator]
    logs = "".join(logs)
    assert "Error message" in logs
    assert "Debugging the raise.\n" in logs

    await validations.logging.delete_run_info()
