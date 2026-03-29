from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol


class BackendContainer(Protocol):
    backend_id: str

    def metrics(self) -> Mapping[str, Any]: ...

    def heartbeat(self) -> Mapping[str, Any]: ...

    def submit(self, request: Mapping[str, Any]) -> Mapping[str, Any]: ...

    def poll(self, job_id: str) -> Mapping[str, Any] | None: ...

    def cancel(self, job_id: str, *, reason: str = "") -> bool: ...

    def ack(self, job_id: str) -> bool: ...


class BackendContainerPlugin(Protocol):
    plugin_id: str
    backend_type: str

    def capabilities(self) -> Mapping[str, Any]: ...

    def create_container(
        self,
        *,
        node_id: str,
        config: Mapping[str, Any],
    ) -> BackendContainer: ...


__all__ = [
    "BackendContainer",
    "BackendContainerPlugin",
]
