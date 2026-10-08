"""Langfuse instrumentation that becomes a no-op when the SDK is not installed."""

from collections.abc import Callable
from functools import wraps
from typing import Any

try:
    from langfuse import observe as _observe
    from langfuse import get_client as _get_client
except ImportError:
    _observe = None
    _get_client = None


def observed(*, name: str, as_type: str = "span") -> Callable:
    if _observe is not None:
        return _observe(name=name, as_type=as_type)

    def decorator(function: Callable) -> Callable:
        @wraps(function)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return function(*args, **kwargs)
        return wrapper
    return decorator


def score_current_trace(name: str, value: Any, data_type: str | None = None) -> None:
    """Attach operational scores when Langfuse is configured; never break tutoring."""
    if _get_client is None:
        return
    try:
        _get_client().score_current_trace(name=name, value=value, data_type=data_type)
    except Exception:
        # Observability must not become an availability dependency.
        return
