"""Fail-closed security configuration helpers."""

from __future__ import annotations

import os
from collections.abc import Mapping


LOCAL_ORIGINS = "http://127.0.0.1:8000,http://localhost:8000"


def get_required_secret_key(environ: Mapping[str, str] | None = None) -> str:
    values = environ if environ is not None else os.environ
    secret = values.get("SECRET_KEY", "").strip()
    if len(secret) < 32 or "change" in secret.lower() or "your-" in secret.lower():
        raise RuntimeError(
            "SECRET_KEY must be explicitly configured with at least 32 non-placeholder characters"
        )
    return secret


def get_allowed_origins(environ: Mapping[str, str] | None = None) -> list[str]:
    values = environ if environ is not None else os.environ
    configured = values.get("ALLOWED_ORIGINS", LOCAL_ORIGINS)
    origins = [origin.strip().rstrip("/") for origin in configured.split(",") if origin.strip()]
    if not origins:
        raise RuntimeError("ALLOWED_ORIGINS must contain at least one origin")
    if "*" in origins:
        raise RuntimeError("Wildcard CORS origins are not allowed")
    if any(not origin.startswith(("http://", "https://")) for origin in origins):
        raise RuntimeError("ALLOWED_ORIGINS entries must be absolute HTTP(S) origins")
    return origins
