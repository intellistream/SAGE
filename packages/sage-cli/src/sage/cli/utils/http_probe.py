"""Best-effort HTTP probing helpers for CLI commands."""

from __future__ import annotations

from typing import Any

import httpx


def http_get_ok(url: str, *, timeout: float = 2.0) -> bool:
    """Return True when an HTTP GET responds with status code 200."""
    try:
        response = httpx.get(url, timeout=timeout)
        return response.status_code == 200
    except Exception:
        return False


def http_get_json(url: str, *, timeout: float = 5.0) -> dict[str, Any] | None:
    """Return parsed JSON dict for HTTP 200 response, else ``None``."""
    try:
        response = httpx.get(url, timeout=timeout)
        if response.status_code != 200:
            return None
        data = response.json()
    except Exception:
        return None

    if isinstance(data, dict):
        return data
    return None
