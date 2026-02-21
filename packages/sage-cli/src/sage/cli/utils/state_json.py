"""Helpers for reading/writing JSON state files used by CLI commands."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def save_json_state(path: Path, payload: dict[str, Any]) -> None:
    """Persist a JSON payload to disk, ensuring parent directory exists."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2))


def load_json_state(path: Path) -> dict[str, Any] | None:
    """Load a JSON payload from disk.

    Returns ``None`` if the file does not exist or cannot be decoded.
    """
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None

    if isinstance(data, dict):
        return data
    return None
