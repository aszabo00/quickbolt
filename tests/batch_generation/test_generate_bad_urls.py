import pytest

import quickbolt.batch_generation.batch_generation as bg

pytestmark = pytest.mark.batch_generation


def test_generate_bad_urls_semicolon():
    # using the ';' to denote the start of the path arguments.
    url = "https://httpbin.org;/houseId/1b/2c?param=value1&another_param=2"
    bad_urls = bg.generate_bad_urls(url)

    expected_urls = [
        "https://httpbin.org/aaaaaaa/1b/2c?param=value1&another_param=2",
        "https://httpbin.org/houseId/0a/2c?param=value1&another_param=2",
        "https://httpbin.org/houseId/1b/0a?param=value1&another_param=2",
        "https://httpbin.org/houseId/1b/2c?param=aaaaa0&another_param=2",
        "https://httpbin.org/houseId/1b/2c?param=value1&another_param=0",
        "https://httpbin.org/aaaaaaa/0a/0a?param=aaaaa0&another_param=0",
    ]
    assert bad_urls == expected_urls


def test_generate_bad_urls_semicolon_number():
    # using the ';' to denote the start of the path arguments.
    url = "https://httpbin.org;/houseId/1b/2?param=value1&another_param=2"
    bad_urls = bg.generate_bad_urls(url)

    expected_urls = [
        "https://httpbin.org/aaaaaaa/1b/2?param=value1&another_param=2",
        "https://httpbin.org/houseId/0a/2?param=value1&another_param=2",
        "https://httpbin.org/houseId/1b/0?param=value1&another_param=2",
        "https://httpbin.org/houseId/1b/2?param=aaaaa0&another_param=2",
        "https://httpbin.org/houseId/1b/2?param=value1&another_param=0",
        "https://httpbin.org/aaaaaaa/0a/0?param=aaaaa0&another_param=0",
    ]
    assert bad_urls == expected_urls


def test_generate_bad_urls_no_semicolon():
    url = "https://httpbin.org/houseId/1b/2c?param=value1&another_param=2"
    bad_urls = bg.generate_bad_urls(url)

    expected_urls = [
        "https://httpbin.org/aaaaaaa/1b/2c?param=value1&another_param=2",
        "https://httpbin.org/houseId/0a/2c?param=value1&another_param=2",
        "https://httpbin.org/houseId/1b/0a?param=value1&another_param=2",
        "https://httpbin.org/houseId/1b/2c?param=aaaaa0&another_param=2",
        "https://httpbin.org/houseId/1b/2c?param=value1&another_param=0",
        "https://httpbin.org/aaaaaaa/0a/0a?param=aaaaa0&another_param=0",
    ]
    assert bad_urls == expected_urls


def test_generate_bad_urls_no_semicolon_number():
    url = "https://httpbin.org/houseId/1b/2?param=value1&another_param=2"
    bad_urls = bg.generate_bad_urls(url)

    expected_urls = [
        "https://httpbin.org/aaaaaaa/1b/2?param=value1&another_param=2",
        "https://httpbin.org/houseId/0a/2?param=value1&another_param=2",
        "https://httpbin.org/houseId/1b/0?param=value1&another_param=2",
        "https://httpbin.org/houseId/1b/2?param=aaaaa0&another_param=2",
        "https://httpbin.org/houseId/1b/2?param=value1&another_param=0",
        "https://httpbin.org/aaaaaaa/0a/0?param=aaaaa0&another_param=0",
    ]
    assert bad_urls == expected_urls


def test_generate_bad_urls_no_corrupt_query_params():
    url = "https://httpbin.org/houseId/1b/2c?param=value1&another_param=2"
    bad_urls = bg.generate_bad_urls(url, corrupt_query_params=False)

    expected_urls = [
        "https://httpbin.org/aaaaaaa/1b/2c?param=value1&another_param=2",
        "https://httpbin.org/houseId/0a/2c?param=value1&another_param=2",
        "https://httpbin.org/houseId/1b/0a?param=value1&another_param=2",
        "https://httpbin.org/aaaaaaa/0a/0a?param=value1&another_param=2",
    ]
    assert bad_urls == expected_urls


def test_generate_bad_urls_semicolon_no_query():
    # using the ';' to denote the start of the path arguments.
    url = "https://httpbin.org;/houseId/1b/2c"
    bad_urls = bg.generate_bad_urls(url)

    expected_urls = [
        "https://httpbin.org/aaaaaaa/1b/2c",
        "https://httpbin.org/houseId/0a/2c",
        "https://httpbin.org/houseId/1b/0a",
        "https://httpbin.org/aaaaaaa/0a/0a",
    ]
    assert bad_urls == expected_urls


def test_generate_bad_urls_no_semicolon_no_query():
    url = "https://httpbin.org/houseId/1b/2c"
    bad_urls = bg.generate_bad_urls(url)

    expected_urls = [
        "https://httpbin.org/aaaaaaa/1b/2c",
        "https://httpbin.org/houseId/0a/2c",
        "https://httpbin.org/houseId/1b/0a",
        "https://httpbin.org/aaaaaaa/0a/0a",
    ]
    assert bad_urls == expected_urls
