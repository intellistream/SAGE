"""Shared helpers for CLI runtime command implementations."""

from __future__ import annotations

import json
from importlib.util import find_spec
from pathlib import Path
from typing import Any


def module_available(module_name: str) -> bool:
    """Return whether an importable Python module exists."""
    return find_spec(module_name) is not None


def load_structured_config(config_path: Path) -> dict[str, Any]:
    """Load a JSON/YAML config file and return a dict.

    Raises:
        ValueError: If file content is not a mapping object.
    """
    if config_path.suffix in (".yaml", ".yml"):
        import yaml  # type: ignore[import-untyped]

        data = yaml.safe_load(config_path.read_text())
    else:
        data = json.loads(config_path.read_text())

    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError("配置文件根节点必须是对象")
    return data
