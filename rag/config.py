"""Shared, bounded model configuration for Gemini-backed components."""

from __future__ import annotations

import os
from collections.abc import Mapping

DEFAULT_GEMINI_MODEL = "gemini-3.5-flash-lite"


def get_gemini_client_options(
    env: Mapping[str, str] | None = None,
) -> dict[str, int | float]:
    """Return fail-fast provider limits; never allow unbounded waits or retry storms."""
    values = env if env is not None else os.environ
    try:
        timeout = float(values.get("GEMINI_TIMEOUT_SECONDS", "20"))
        retries = int(values.get("GEMINI_MAX_RETRIES", "2"))
    except ValueError as error:
        raise RuntimeError("Gemini timeout and retry settings must be numeric") from error
    if not 1 <= timeout <= 120:
        raise RuntimeError("GEMINI_TIMEOUT_SECONDS must be between 1 and 120")
    if not 0 <= retries <= 5:
        raise RuntimeError("GEMINI_MAX_RETRIES must be between 0 and 5")
    return {"timeout": timeout, "max_retries": retries}
