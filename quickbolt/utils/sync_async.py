import asyncio
from functools import wraps
from typing import Any, Callable, TypeVar

T = TypeVar("T")


def force_sync(fn: Callable) -> Callable:
    """
    This decorator allows an async function to be run
    outside an event loop from a sync function.
    """

    @wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        return asyncio.run(fn(*args, **kwargs))

    return wrapper
