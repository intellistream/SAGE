from __future__ import annotations

import asyncio
import inspect
import socket
import socketserver
import threading
from collections.abc import Callable
from typing import Any

import cloudpickle

from sage.runtime.flownet.runtime.comm.loopback import InMemoryLoopbackTransport
from sage.runtime.flownet.runtime.comm.protocol import V1Envelope, coerce_envelope
from sage.runtime.flownet.runtime.comm.transport import V1TransportReceiver

_ALLOWED_TRANSPORT_MODES = frozenset(
    {
        "auto",
        "loopback",
        "loopback_prefer",
        "tcp",
    }
)


def build_v1_transport_backend(
    *,
    transport_mode: str = "loopback",
) -> InMemoryLoopbackTransport | V1SelectableTransportBackend:
    """Build a v1 transport backend from a normalized mode string."""

    normalized_mode = _normalize_transport_mode(transport_mode)
    if normalized_mode == "loopback":
        return InMemoryLoopbackTransport()
    return V1SelectableTransportBackend(transport_mode=normalized_mode)


class V1BackendSelector:
    """Resolve candidate backend order for one send operation."""

    def __init__(self, *, transport_mode: str = "auto") -> None:
        self._transport_mode = _normalize_transport_mode(transport_mode)

    @property
    def transport_mode(self) -> str:
        return self._transport_mode

    def resolve(
        self,
        *,
        target_address: str,
        loopback_has_endpoint: Callable[[str], bool],
    ) -> tuple[str, ...]:
        normalized_target = _normalize_non_empty(target_address, field_name="target_address")
        if self._transport_mode == "loopback":
            return ("loopback",)
        if self._transport_mode == "tcp":
            return ("tcp",)
        if self._transport_mode == "loopback_prefer":
            return ("loopback", "tcp")
        if loopback_has_endpoint(normalized_target):
            return ("loopback",)
        return ("tcp",)


class _ThreadingTcpServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True
    allow_reuse_address = True


class _FramedPacketHandler(socketserver.StreamRequestHandler):
    server: _ThreadingTcpServer

    def handle(self) -> None:
        backend = getattr(self.server, "backend", None)
        if not isinstance(backend, V1TcpSocketTransport):
            return

        while True:
            raw_size = self.rfile.read(4)
            if not raw_size:
                return
            if len(raw_size) != 4:
                backend._bump("receiver_errors")
                return
            payload_size = int.from_bytes(raw_size, "big")
            if payload_size <= 0:
                backend._bump("receiver_errors")
                return
            payload = self.rfile.read(payload_size)
            if len(payload) != payload_size:
                backend._bump("receiver_errors")
                return
            backend._handle_incoming_bytes(payload)


class V1TcpSocketTransport:
    """TCP transport backend using length-prefixed cloudpickle frames."""

    def __init__(
        self,
        *,
        connect_timeout_seconds: float = 3.0,
        io_timeout_seconds: float = 3.0,
    ) -> None:
        self._connect_timeout_seconds = max(0.1, float(connect_timeout_seconds))
        self._io_timeout_seconds = max(0.1, float(io_timeout_seconds))

        self._lock = threading.Lock()
        self._local_address: str | None = None
        self._receiver: V1TransportReceiver | None = None
        self._server: _ThreadingTcpServer | None = None
        self._server_thread: threading.Thread | None = None
        self._stats: dict[str, int] = {
            "send_total": 0,
            "send_tcp_total": 0,
            "send_dropped": 0,
            "recv_total": 0,
            "recv_dropped": 0,
            "receiver_errors": 0,
        }

    def register_endpoint(self, *, address: str, receiver: V1TransportReceiver) -> None:
        if not callable(receiver):
            raise TypeError("receiver must be callable.")
        normalized_address = _normalize_non_empty(address, field_name="address")
        host, port = _split_host_port(normalized_address)

        with self._lock:
            if self._receiver is not None:
                raise ValueError("tcp_endpoint_already_registered")

        server = _ThreadingTcpServer((host, port), _FramedPacketHandler)
        thread = threading.Thread(
            target=server.serve_forever,
            daemon=True,
            name=f"flownet-v1-tcp-server-{host}:{port}",
        )
        server.backend = self

        try:
            thread.start()
        except Exception:
            server.server_close()
            raise

        with self._lock:
            self._local_address = normalized_address
            self._receiver = receiver
            self._server = server
            self._server_thread = thread

    def unregister_endpoint(self, *, address: str) -> bool:
        normalized_address = _normalize_non_empty(address, field_name="address")

        server: _ThreadingTcpServer | None = None
        thread: threading.Thread | None = None
        with self._lock:
            if self._local_address != normalized_address:
                return False
            self._local_address = None
            self._receiver = None
            server = self._server
            thread = self._server_thread
            self._server = None
            self._server_thread = None

        if server is not None:
            server.shutdown()
            server.server_close()
        if thread is not None:
            thread.join(timeout=1.0)
        return True

    async def send(self, envelope_payload: V1Envelope | dict[str, Any]) -> None:
        envelope = coerce_envelope(envelope_payload)
        await asyncio.to_thread(self._send_blocking, envelope.target_address, envelope)

    def stats_snapshot(self) -> dict[str, Any]:
        with self._lock:
            send_total = int(self._stats.get("send_total", 0))
            send_dropped = int(self._stats.get("send_dropped", 0))
            receiver_errors = int(self._stats.get("receiver_errors", 0))
            recv_total = int(self._stats.get("recv_total", 0))
            recv_dropped = int(self._stats.get("recv_dropped", 0))
        fallback_total = send_dropped + receiver_errors + recv_dropped
        return {
            "transport_mode": "tcp",
            "source": "flownet.runtime.transport.tcp",
            "send_total": send_total,
            "send_tcp_total": send_total,
            "send_uds_total": 0,
            "send_shm_total": 0,
            "send_dropped": send_dropped,
            "recv_total": recv_total,
            "recv_dropped": recv_dropped,
            "receiver_errors": receiver_errors,
            "fallback_total": fallback_total,
            "fallback_uds_to_tcp_total": 0,
            "fallback_shm_to_uds_total": 0,
            "fallback_shm_to_tcp_total": 0,
            "backend_select_counts": {
                "tcp": send_total,
                "uds": 0,
                "shm": 0,
            },
            "backend_error_counts": {
                "tcp": send_dropped + receiver_errors,
                "uds": 0,
                "shm": 0,
            },
            "fallback_rates": {
                "per_send": (float(fallback_total) / float(send_total)) if send_total > 0 else 0.0,
                "per_select": (float(fallback_total) / float(send_total))
                if send_total > 0
                else 0.0,
            },
            "backend_type": type(self).__name__,
        }

    def _send_blocking(self, target_address: str, envelope: V1Envelope) -> None:
        host, port = _split_host_port(target_address)
        payload = cloudpickle.dumps(envelope)
        framed_payload = len(payload).to_bytes(4, "big") + payload
        try:
            with socket.create_connection(
                (host, port),
                timeout=self._connect_timeout_seconds,
            ) as sock:
                sock.settimeout(self._io_timeout_seconds)
                sock.sendall(framed_payload)
        except Exception as exc:
            self._bump("send_dropped")
            raise RuntimeError(f"tcp_send_failed:{target_address}:{exc}") from exc

        self._bump("send_total")
        self._bump("send_tcp_total")

    def _handle_incoming_bytes(self, payload: bytes) -> None:
        try:
            envelope_payload = cloudpickle.loads(payload)
            envelope = coerce_envelope(envelope_payload)
        except Exception:
            self._bump("receiver_errors")
            return

        receiver = self._resolve_receiver()
        if receiver is None:
            self._bump("recv_dropped")
            return

        self._bump("recv_total")
        try:
            result = receiver(envelope)
            if inspect.isawaitable(result):
                asyncio.run(self._run_receiver(result))
        except Exception:
            self._bump("receiver_errors")

    async def _run_receiver(self, awaitable: Any) -> None:
        try:
            await awaitable
        except Exception:
            self._bump("receiver_errors")

    def _resolve_receiver(self) -> V1TransportReceiver | None:
        with self._lock:
            return self._receiver

    def _bump(self, key: str) -> None:
        with self._lock:
            self._stats[key] = int(self._stats.get(key, 0)) + 1


class V1SelectableTransportBackend:
    """
    Transport hub with backend selector + fallback counters.

    Supports loopback and tcp in v1. UDS/SHM counters are kept for schema
    compatibility and remain zero in this slice.
    """

    def __init__(
        self,
        *,
        transport_mode: str = "auto",
        selector: V1BackendSelector | None = None,
        loopback_backend: InMemoryLoopbackTransport | None = None,
        tcp_backend: V1TcpSocketTransport | None = None,
    ) -> None:
        normalized_mode = _normalize_transport_mode(transport_mode)
        self._selector = selector or V1BackendSelector(transport_mode=normalized_mode)
        self._loopback = loopback_backend or InMemoryLoopbackTransport()
        self._tcp = tcp_backend or V1TcpSocketTransport()
        self._lock = threading.Lock()
        self._stats: dict[str, Any] = {
            "send_loopback_total": 0,
            "send_tcp_total": 0,
            "send_uds_total": 0,
            "send_shm_total": 0,
            "fallback_total": 0,
            "fallback_loopback_to_tcp_total": 0,
            "fallback_uds_to_tcp_total": 0,
            "fallback_shm_to_uds_total": 0,
            "fallback_shm_to_tcp_total": 0,
            "backend_select_counts": {
                "loopback": 0,
                "tcp": 0,
                "uds": 0,
                "shm": 0,
            },
            "backend_error_counts": {
                "loopback": 0,
                "tcp": 0,
                "uds": 0,
                "shm": 0,
            },
        }

    def register_endpoint(self, *, address: str, receiver: V1TransportReceiver) -> None:
        self._loopback.register_endpoint(address=address, receiver=receiver)
        try:
            self._tcp.register_endpoint(address=address, receiver=receiver)
        except Exception:
            self._loopback.unregister_endpoint(address=address)
            raise

    def unregister_endpoint(self, *, address: str) -> bool:
        loopback_removed = self._loopback.unregister_endpoint(address=address)
        tcp_removed = self._tcp.unregister_endpoint(address=address)
        return bool(loopback_removed or tcp_removed)

    async def send(self, envelope_payload: V1Envelope | dict[str, Any]) -> None:
        envelope = coerce_envelope(envelope_payload)
        backend_order = self._selector.resolve(
            target_address=envelope.target_address,
            loopback_has_endpoint=self._loopback_has_endpoint,
        )
        last_exc: Exception | None = None

        for index, backend in enumerate(backend_order):
            next_backend = backend_order[index + 1] if index + 1 < len(backend_order) else None
            self._increment_backend_counter("backend_select_counts", backend)
            try:
                await self._send_with_backend(backend=backend, envelope=envelope)
            except Exception as exc:
                last_exc = exc
                self._increment_backend_counter("backend_error_counts", backend)
                if next_backend is not None:
                    self._record_fallback(backend=backend, next_backend=next_backend)
                continue

            self._record_send(backend)
            return

        if last_exc is not None:
            raise last_exc
        raise RuntimeError(f"transport_backend_unavailable:{envelope.target_address}")

    async def flush(self) -> None:
        await self._loopback.flush()

    def stats_snapshot(self) -> dict[str, Any]:
        loopback_raw = self._loopback.stats_snapshot()
        tcp_raw = self._tcp.stats_snapshot()

        with self._lock:
            send_loopback_total = int(self._stats.get("send_loopback_total", 0))
            send_tcp_total = int(self._stats.get("send_tcp_total", 0))
            send_uds_total = int(self._stats.get("send_uds_total", 0))
            send_shm_total = int(self._stats.get("send_shm_total", 0))
            fallback_total = int(self._stats.get("fallback_total", 0))
            fallback_loopback_to_tcp_total = int(
                self._stats.get("fallback_loopback_to_tcp_total", 0)
            )
            fallback_uds_to_tcp_total = int(self._stats.get("fallback_uds_to_tcp_total", 0))
            fallback_shm_to_uds_total = int(self._stats.get("fallback_shm_to_uds_total", 0))
            fallback_shm_to_tcp_total = int(self._stats.get("fallback_shm_to_tcp_total", 0))
            backend_select_counts = dict(self._stats.get("backend_select_counts", {}))
            backend_error_counts = dict(self._stats.get("backend_error_counts", {}))

        send_total = send_loopback_total + send_tcp_total + send_uds_total + send_shm_total
        total_select = sum(
            int(backend_select_counts.get(name, 0)) for name in ("loopback", "tcp", "uds", "shm")
        )

        source = "flownet.runtime.transport.auto"
        if self._selector.transport_mode == "loopback":
            source = "flownet.runtime.loopback"
        elif self._selector.transport_mode == "tcp":
            source = "flownet.runtime.transport.tcp"
        elif self._selector.transport_mode == "loopback_prefer":
            source = "flownet.runtime.transport.loopback_prefer"

        send_dropped = _safe_int(loopback_raw.get("send_dropped")) + _safe_int(
            tcp_raw.get("send_dropped")
        )
        receiver_errors = _safe_int(loopback_raw.get("receiver_errors")) + _safe_int(
            tcp_raw.get("receiver_errors")
        )

        return {
            "transport_mode": self._selector.transport_mode,
            "source": source,
            "send_total": send_total,
            "send_loopback_total": send_loopback_total,
            "send_tcp_total": send_tcp_total,
            "send_uds_total": send_uds_total,
            "send_shm_total": send_shm_total,
            "send_dropped": send_dropped,
            "receiver_errors": receiver_errors,
            "fallback_total": fallback_total,
            "fallback_loopback_to_tcp_total": fallback_loopback_to_tcp_total,
            "fallback_uds_to_tcp_total": fallback_uds_to_tcp_total,
            "fallback_shm_to_uds_total": fallback_shm_to_uds_total,
            "fallback_shm_to_tcp_total": fallback_shm_to_tcp_total,
            "backend_select_counts": {
                "loopback": int(backend_select_counts.get("loopback", 0)),
                "tcp": int(backend_select_counts.get("tcp", 0)),
                "uds": int(backend_select_counts.get("uds", 0)),
                "shm": int(backend_select_counts.get("shm", 0)),
            },
            "backend_error_counts": {
                "loopback": int(backend_error_counts.get("loopback", 0)),
                "tcp": int(backend_error_counts.get("tcp", 0)),
                "uds": int(backend_error_counts.get("uds", 0)),
                "shm": int(backend_error_counts.get("shm", 0)),
            },
            "fallback_rates": {
                "per_send": (float(fallback_total) / float(send_total)) if send_total > 0 else 0.0,
                "per_select": (float(fallback_total) / float(total_select))
                if total_select > 0
                else 0.0,
                "uds_to_tcp_per_uds_select": (
                    float(fallback_uds_to_tcp_total)
                    / float(int(backend_select_counts.get("uds", 0)))
                )
                if int(backend_select_counts.get("uds", 0)) > 0
                else 0.0,
                "shm_to_uds_per_shm_select": (
                    float(fallback_shm_to_uds_total)
                    / float(int(backend_select_counts.get("shm", 0)))
                )
                if int(backend_select_counts.get("shm", 0)) > 0
                else 0.0,
                "shm_to_tcp_per_shm_select": (
                    float(fallback_shm_to_tcp_total)
                    / float(int(backend_select_counts.get("shm", 0)))
                )
                if int(backend_select_counts.get("shm", 0)) > 0
                else 0.0,
            },
            "backend_type": type(self).__name__,
            "loopback_raw_stats": loopback_raw,
            "tcp_raw_stats": tcp_raw,
        }

    async def _send_with_backend(self, *, backend: str, envelope: V1Envelope) -> None:
        if backend == "loopback":
            await self._loopback.send(envelope)
            return
        if backend == "tcp":
            await self._tcp.send(envelope)
            return
        raise RuntimeError(f"unsupported_transport_backend:{backend}")

    def _loopback_has_endpoint(self, address: str) -> bool:
        return self._loopback.has_endpoint(address=address)

    def _record_send(self, backend: str) -> None:
        key = f"send_{backend}_total"
        with self._lock:
            if key not in self._stats:
                self._stats[key] = 0
            self._stats[key] = int(self._stats.get(key, 0)) + 1

    def _increment_backend_counter(self, metric: str, backend: str) -> None:
        with self._lock:
            counters = self._stats.get(metric)
            if not isinstance(counters, dict):
                counters = {}
                self._stats[metric] = counters
            counters[backend] = int(counters.get(backend, 0)) + 1

    def _record_fallback(self, *, backend: str, next_backend: str) -> None:
        with self._lock:
            self._stats["fallback_total"] = int(self._stats.get("fallback_total", 0)) + 1
            if backend == "loopback" and next_backend == "tcp":
                self._stats["fallback_loopback_to_tcp_total"] = (
                    int(self._stats.get("fallback_loopback_to_tcp_total", 0)) + 1
                )
            elif backend == "uds" and next_backend == "tcp":
                self._stats["fallback_uds_to_tcp_total"] = (
                    int(self._stats.get("fallback_uds_to_tcp_total", 0)) + 1
                )
            elif backend == "shm" and next_backend == "uds":
                self._stats["fallback_shm_to_uds_total"] = (
                    int(self._stats.get("fallback_shm_to_uds_total", 0)) + 1
                )
            elif backend == "shm" and next_backend == "tcp":
                self._stats["fallback_shm_to_tcp_total"] = (
                    int(self._stats.get("fallback_shm_to_tcp_total", 0)) + 1
                )


def _normalize_non_empty(value: Any, *, field_name: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError(f"{field_name} must be non-empty.")
    return normalized


def _split_host_port(address: str) -> tuple[str, int]:
    host, raw_port = str(address or "").strip().rsplit(":", 1)
    normalized_host = _normalize_non_empty(host, field_name="host")
    port = int(raw_port)
    if port <= 0 or port > 65535:
        raise ValueError("port must be in 1..65535")
    return normalized_host, port


def _normalize_transport_mode(value: str) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {"", "loopback_only", "memory"}:
        normalized = "loopback"
    if normalized in {"tcp_only", "network"}:
        normalized = "tcp"
    if normalized not in _ALLOWED_TRANSPORT_MODES:
        supported = ", ".join(sorted(_ALLOWED_TRANSPORT_MODES))
        raise ValueError(f"transport_mode must be one of: {supported}.")
    return normalized


def _safe_int(value: Any) -> int:
    try:
        normalized = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, normalized)


__all__ = [
    "V1BackendSelector",
    "V1SelectableTransportBackend",
    "V1TcpSocketTransport",
    "build_v1_transport_backend",
]
