from __future__ import annotations

import threading
from collections.abc import Iterable
from typing import Any

from .contracts import CollectiveExecutor


class CollectiveExecutorRegistry:
    """
    Runtime collective executor registry.

    Resolution order:
    1. explicit `path_tag`
    2. backend `mode`
    3. `auto` mode fallback (`fast_channel` -> `topic_fallback`)
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._executors_by_mode: dict[str, CollectiveExecutor] = {}
        self._executors_by_path_tag: dict[str, CollectiveExecutor] = {}

    def register_executor(
        self,
        *,
        mode: str,
        executor: CollectiveExecutor,
        path_tags: Iterable[str] = (),
    ) -> None:
        normalized_mode = _normalize_mode(mode)
        if not callable(getattr(executor, "execute", None)):
            raise TypeError("executor must provide execute(request).")
        with self._lock:
            self._executors_by_mode[normalized_mode] = executor
            for raw_path_tag in tuple(path_tags):
                path_tag = _normalize_optional_path_tag(raw_path_tag)
                if path_tag is None:
                    continue
                self._executors_by_path_tag[path_tag] = executor

    def unregister_executor(
        self,
        *,
        mode: str | None = None,
        path_tag: str | None = None,
    ) -> bool:
        removed = False
        with self._lock:
            normalized_mode = _normalize_mode(mode) if mode is not None else None
            normalized_path_tag = (
                _normalize_optional_path_tag(path_tag) if path_tag is not None else None
            )
            if normalized_mode is not None:
                removed = self._executors_by_mode.pop(normalized_mode, None) is not None or removed
            if normalized_path_tag is not None:
                removed = (
                    self._executors_by_path_tag.pop(normalized_path_tag, None) is not None
                    or removed
                )
        return removed

    def resolve_executor(
        self,
        *,
        mode: str,
        path_tag: str | None = None,
    ) -> CollectiveExecutor | None:
        normalized_mode = _normalize_mode(mode)
        normalized_path_tag = _normalize_optional_path_tag(path_tag)
        with self._lock:
            if normalized_path_tag is not None:
                executor = self._executors_by_path_tag.get(normalized_path_tag)
                if executor is not None:
                    return executor

            if normalized_mode == "auto":
                return self._executors_by_mode.get("fast_channel") or self._executors_by_mode.get(
                    "topic_fallback"
                )
            return self._executors_by_mode.get(normalized_mode)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "modes": tuple(sorted(self._executors_by_mode.keys())),
                "path_tags": tuple(sorted(self._executors_by_path_tag.keys())),
            }


_DEFAULT_REGISTRY = CollectiveExecutorRegistry()
registry = _DEFAULT_REGISTRY


def get_default_registry() -> CollectiveExecutorRegistry:
    return _DEFAULT_REGISTRY


def get_registry() -> CollectiveExecutorRegistry:
    return _DEFAULT_REGISTRY


def _normalize_mode(raw_mode: str | None) -> str:
    mode = str(raw_mode or "").strip().lower()
    if not mode:
        raise ValueError("collective mode must be non-empty.")
    if mode not in {"auto", "topic_fallback", "fast_channel"}:
        raise ValueError(
            "collective mode must be one of: auto, topic_fallback, fast_channel.",
        )
    return mode


def _normalize_optional_path_tag(raw_path_tag: Any) -> str | None:
    if raw_path_tag is None:
        return None
    path_tag = str(raw_path_tag).strip()
    if not path_tag:
        raise ValueError("collective path_tag must be a non-empty string when provided.")
    return path_tag


__all__ = [
    "CollectiveExecutorRegistry",
    "registry",
    "get_default_registry",
    "get_registry",
]
