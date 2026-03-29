from __future__ import annotations

import threading
from collections.abc import Mapping
from typing import Any

from .contracts import BackendContainer, BackendContainerPlugin


class BackendContainerRegistry:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._plugins_by_id: dict[str, BackendContainerPlugin] = {}
        self._containers_by_id: dict[str, BackendContainer] = {}
        self._container_tags_by_id: dict[str, dict[str, str]] = {}
        self._container_capabilities_by_id: dict[str, dict[str, Any]] = {}
        self._container_metadata_by_id: dict[str, dict[str, Any]] = {}

    def register_plugin(self, plugin: BackendContainerPlugin) -> None:
        plugin_id = _normalize_non_empty(getattr(plugin, "plugin_id", None), field_name="plugin_id")
        if not callable(getattr(plugin, "create_container", None)):
            raise TypeError("plugin must provide create_container(...).")
        with self._lock:
            self._plugins_by_id[plugin_id] = plugin

    def unregister_plugin(self, plugin_id: str) -> bool:
        normalized_plugin_id = _normalize_non_empty(plugin_id, field_name="plugin_id")
        with self._lock:
            return self._plugins_by_id.pop(normalized_plugin_id, None) is not None

    def get_plugin(self, plugin_id: str) -> BackendContainerPlugin | None:
        normalized_plugin_id = _normalize_non_empty(plugin_id, field_name="plugin_id")
        with self._lock:
            return self._plugins_by_id.get(normalized_plugin_id)

    def register_container(
        self,
        container: BackendContainer,
        *,
        tags: Mapping[str, str] | None = None,
        capabilities: Mapping[str, Any] | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        backend_id = _normalize_non_empty(
            getattr(container, "backend_id", None), field_name="backend_id"
        )
        if not callable(getattr(container, "metrics", None)):
            raise TypeError("container must provide metrics().")
        if not callable(getattr(container, "submit", None)):
            raise TypeError("container must provide submit(...).")
        if not callable(getattr(container, "poll", None)):
            raise TypeError("container must provide poll(...).")
        with self._lock:
            self._containers_by_id[backend_id] = container
            self._container_tags_by_id[backend_id] = _normalize_tags(tags)
            self._container_capabilities_by_id[backend_id] = dict(capabilities or {})
            self._container_metadata_by_id[backend_id] = dict(metadata or {})

    def unregister_container(self, backend_id: str) -> bool:
        normalized_backend_id = _normalize_non_empty(backend_id, field_name="backend_id")
        removed = False
        with self._lock:
            removed = self._containers_by_id.pop(normalized_backend_id, None) is not None
            self._container_tags_by_id.pop(normalized_backend_id, None)
            self._container_capabilities_by_id.pop(normalized_backend_id, None)
            self._container_metadata_by_id.pop(normalized_backend_id, None)
        return removed

    def get_container(self, backend_id: str) -> BackendContainer | None:
        normalized_backend_id = _normalize_non_empty(backend_id, field_name="backend_id")
        with self._lock:
            return self._containers_by_id.get(normalized_backend_id)

    def list_containers(
        self,
        *,
        include_metrics: bool = True,
    ) -> tuple[dict[str, Any], ...]:
        records: list[dict[str, Any]] = []
        with self._lock:
            items = tuple(sorted(self._containers_by_id.items(), key=lambda item: item[0]))
            tags_by_id = dict(self._container_tags_by_id)
            capabilities_by_id = dict(self._container_capabilities_by_id)
            metadata_by_id = dict(self._container_metadata_by_id)
        for backend_id, container in items:
            record: dict[str, Any] = {
                "backend_id": backend_id,
                "tags": dict(tags_by_id.get(backend_id, {})),
                "capabilities": dict(capabilities_by_id.get(backend_id, {})),
                "metadata": dict(metadata_by_id.get(backend_id, {})),
            }
            if include_metrics:
                try:
                    raw_metrics = container.metrics()
                except Exception as exc:
                    record["metrics_error"] = str(exc)
                    record["healthy"] = False
                else:
                    record["metrics"] = (
                        dict(raw_metrics) if isinstance(raw_metrics, Mapping) else {}
                    )
            records.append(record)
        return tuple(records)

    def find_containers(
        self,
        *,
        required_tags: Mapping[str, str] | None = None,
        include_metrics: bool = True,
    ) -> tuple[dict[str, Any], ...]:
        normalized_required_tags = _normalize_tags(required_tags)
        candidates: list[dict[str, Any]] = []
        for record in self.list_containers(include_metrics=include_metrics):
            tags = record.get("tags")
            if not isinstance(tags, Mapping):
                continue
            if not _tags_match(candidate_tags=tags, required_tags=normalized_required_tags):
                continue
            candidates.append(record)
        return tuple(candidates)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "plugins": tuple(sorted(self._plugins_by_id.keys())),
                "containers": tuple(sorted(self._containers_by_id.keys())),
            }


def _normalize_non_empty(value: Any, *, field_name: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError(f"{field_name} must be non-empty.")
    return normalized


def _normalize_tags(raw_tags: Mapping[str, Any] | None) -> dict[str, str]:
    normalized: dict[str, str] = {}
    if not isinstance(raw_tags, Mapping):
        return normalized
    for raw_key, raw_value in raw_tags.items():
        key = str(raw_key or "").strip()
        if not key:
            continue
        value = str(raw_value or "").strip()
        if not value:
            continue
        normalized[key] = value
    return normalized


def _tags_match(
    *,
    candidate_tags: Mapping[str, Any],
    required_tags: Mapping[str, str],
) -> bool:
    if not required_tags:
        return True
    for key, required_value in required_tags.items():
        actual = candidate_tags.get(key)
        if actual is None:
            return False
        if str(actual).strip() != required_value:
            return False
    return True


__all__ = [
    "BackendContainerRegistry",
]
