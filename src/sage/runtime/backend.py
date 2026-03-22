"""Runtime backend acquisition helpers for the main-repo runtime surface."""

from __future__ import annotations

from typing import Any

from .flutty_backend import get_flutty_adapter


def get_runtime_backend() -> Any:
    """Return the process-global Flutty runtime adapter.

    The distributed backend remains optional. When callers need cluster-backed
    execution they should go through this helper rather than importing Flutty
    internals directly.
    """
    return get_flutty_adapter()


__all__ = ["get_runtime_backend"]
