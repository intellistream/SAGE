from __future__ import annotations

import asyncio
import inspect
from collections.abc import Awaitable
from threading import Lock
from typing import Any

from sage.runtime.flownet.runtime.comm.protocol import V1Envelope, coerce_envelope
from sage.runtime.flownet.runtime.comm.transport import V1TransportReceiver


class InMemoryLoopbackTransport:
    """
    In-memory transport used by v1 unit tests.

    Delivery is best-effort asynchronous for awaitable receivers so request timeouts
    can be tested without blocking sender-side send().
    """

    def __init__(self) -> None:
        self._receivers: dict[str, V1TransportReceiver] = {}
        self._lock = Lock()
        self._inflight_tasks: set[asyncio.Task[Any]] = set()
        self._stats: dict[str, int] = {
            "send_total": 0,
            "send_dropped": 0,
            "receiver_errors": 0,
        }

    def register_endpoint(self, *, address: str, receiver: V1TransportReceiver) -> None:
        if not callable(receiver):
            raise TypeError("receiver must be callable.")
        normalized_address = _normalize_non_empty(address, field_name="address")
        with self._lock:
            if normalized_address in self._receivers:
                raise ValueError(f"endpoint_already_registered:{normalized_address}")
            self._receivers[normalized_address] = receiver

    def unregister_endpoint(self, *, address: str) -> bool:
        normalized_address = _normalize_non_empty(address, field_name="address")
        with self._lock:
            return self._receivers.pop(normalized_address, None) is not None

    def has_endpoint(self, *, address: str) -> bool:
        normalized_address = _normalize_non_empty(address, field_name="address")
        with self._lock:
            return normalized_address in self._receivers

    async def send(self, envelope_payload: V1Envelope | dict[str, Any]) -> None:
        envelope = coerce_envelope(envelope_payload)
        receiver = self._resolve_receiver(envelope.target_address)
        self._bump("send_total")
        if receiver is None:
            self._bump("send_dropped")
            raise RuntimeError(f"loopback_target_not_found:{envelope.target_address}")

        try:
            result = receiver(envelope)
        except Exception:
            self._bump("receiver_errors")
            raise

        if inspect.isawaitable(result):
            task = asyncio.create_task(self._run_receiver(result))
            self._track_task(task)

    async def flush(self) -> None:
        while True:
            with self._lock:
                self._inflight_tasks = {task for task in self._inflight_tasks if not task.done()}
                tasks = list(self._inflight_tasks)
            if not tasks:
                return
            await asyncio.gather(*tasks, return_exceptions=True)
            await asyncio.sleep(0)

    def stats_snapshot(self) -> dict[str, int]:
        with self._lock:
            raw = dict(self._stats)
        send_total = int(raw.get("send_total", 0))
        fallback_total = int(raw.get("send_dropped", 0)) + int(raw.get("receiver_errors", 0))
        return {
            "transport_mode": "loopback",
            "source": "flownet.runtime.loopback",
            "send_total": send_total,
            "send_loopback_total": send_total,
            # Keep tcp alias for existing benchmark compatibility.
            "send_tcp_total": send_total,
            "send_uds_total": 0,
            "send_shm_total": 0,
            "send_dropped": int(raw.get("send_dropped", 0)),
            "receiver_errors": int(raw.get("receiver_errors", 0)),
            "fallback_total": fallback_total,
            "fallback_uds_to_tcp_total": 0,
            "fallback_shm_to_uds_total": 0,
            "fallback_shm_to_tcp_total": 0,
            "fallback_rates": {
                "per_send": (float(fallback_total) / float(send_total)) if send_total > 0 else 0.0,
                "per_select": (float(fallback_total) / float(send_total))
                if send_total > 0
                else 0.0,
            },
            "backend_select_counts": {
                "loopback": send_total,
                "tcp": send_total,
                "uds": 0,
                "shm": 0,
            },
            "backend_error_counts": {
                "loopback": int(raw.get("receiver_errors", 0)),
                "tcp": 0,
                "uds": 0,
                "shm": 0,
            },
            "backend_type": type(self).__name__,
            "loopback_raw_stats": raw,
        }

    def _resolve_receiver(self, address: str) -> V1TransportReceiver | None:
        with self._lock:
            return self._receivers.get(address)

    async def _run_receiver(self, awaitable: Awaitable[Any]) -> None:
        try:
            await awaitable
        except Exception:
            self._bump("receiver_errors")

    def _track_task(self, task: asyncio.Task[Any]) -> None:
        with self._lock:
            self._inflight_tasks.add(task)
        task.add_done_callback(self._on_task_done)

    def _on_task_done(self, task: asyncio.Task[Any]) -> None:
        with self._lock:
            self._inflight_tasks.discard(task)

    def _bump(self, key: str) -> None:
        with self._lock:
            self._stats[key] = int(self._stats.get(key, 0)) + 1


def _normalize_non_empty(value: Any, *, field_name: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError(f"{field_name} must be non-empty.")
    return normalized


__all__ = [
    "InMemoryLoopbackTransport",
    "V1TransportReceiver",
]
