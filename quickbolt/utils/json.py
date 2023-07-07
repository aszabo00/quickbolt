import re
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


def squash_leading_zeros(text: str) -> str:
    """
    This removes leading zeros e.g. by squashing them.

    Args:
        text: The text to squash the zeros from.

    Returns:
        no_leading_zeros_text: The leading zeros free text.
    """
    marked_text = re.sub(r'"(.*?)"', r"\g<0>QUOTEMARKED", text)
    marked_text_lines = marked_text.split("\n")

    for i, line in enumerate(marked_text_lines):
        split_line = line.split(":")
        value = split_line[-1]
        digits = re.findall(r'"?[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"?', value)

        if "QUOTEMARKED" not in value and digits:
            digits = digits[0]
            if digits.isdigit() and len(digits) > 1:
                new_value = re.sub(r"\b0+(?=\d)", "", digits)
                new_line = line.replace(digits, new_value)
                marked_text_lines[i] = new_line

    return "\n".join(marked_text_lines).replace("QUOTEMARKED", "")


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
    exceptions = [orjson.JSONDecodeError, TypeError] + other_exceptions

    try:
        no_leading_zeros_text = squash_leading_zeros(text)
        return orjson.loads(no_leading_zeros_text)
    except tuple(exceptions):
        if not safe:
            raise
        return text
