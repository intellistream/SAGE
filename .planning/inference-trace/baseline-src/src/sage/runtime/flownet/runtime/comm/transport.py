from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, Protocol

from sage.runtime.flownet.runtime.comm.protocol import V1Envelope

V1TransportReceiver = Callable[[V1Envelope | dict[str, Any]], Any | Awaitable[Any]]


class V1TransportBackend(Protocol):
    """Transport backend contract used by V1CommHub."""

    def register_endpoint(
        self,
        *,
        address: str,
        receiver: V1TransportReceiver,
    ) -> None: ...

    def unregister_endpoint(self, *, address: str) -> bool: ...

    async def send(self, envelope_payload: V1Envelope | dict[str, Any]) -> None: ...

    def stats_snapshot(self) -> dict[str, Any]: ...


__all__ = [
    "V1TransportBackend",
    "V1TransportReceiver",
]
