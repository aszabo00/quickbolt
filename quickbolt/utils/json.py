from typing import Any

import orjson


def ensure_serializable(data: Any) -> Any:
    """
    This ensures data is serializable.

    Args:
        data: Any data to serialize.

    Returns:
        data: The serializable data.
    """
    try:
        orjson.dumps(data)
        return data
    except:
        return str(data)


def serialize(data: Any, other_exceptions: Any = None, safe=False) -> str:
    """
    This converts data to json.

    Args:
        data: The data to convert.
        other_exceptions: Other exceptions to catch.
        safe: Whether to rase on an exception.

    Returns:
        data: The converted data.
    """
    other_exceptions = other_exceptions or []
    if not isinstance(other_exceptions, list):
        other_exceptions = [other_exceptions]
    exceptions = [orjson.JSONEncodeError] + other_exceptions

    try:
        return orjson.dumps(
            data, option=orjson.OPT_INDENT_2 | orjson.OPT_NON_STR_KEYS
        ).decode()
    except tuple(exceptions):
        if not safe:
            raise
        return data


def deserialize(text: str | bytes, other_exceptions: Any = None, safe=False) -> Any:
    """
    This converts json to its pythonic object.

    Args:
        text: The string to convert.
        other_exceptions: Other exceptions to catch.
        safe: Whether to rase on an exception.

    Returns:
        data: The converted text or original text.
    """
    other_exceptions = other_exceptions or []
    if not isinstance(other_exceptions, list):
        other_exceptions = [other_exceptions]
    exceptions = [orjson.JSONDecodeError] + other_exceptions

    try:
        return orjson.loads(text)
    except tuple(exceptions):
        if not safe:
            raise
        return text
