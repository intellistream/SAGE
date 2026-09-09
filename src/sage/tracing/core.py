"""Fail-open, context-local tracing of observable work, never model reasoning."""

from __future__ import annotations

import contextvars
import functools
import hashlib
import hmac
import inspect
import json
import math
import queue
import re
import secrets
import threading
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager, nullcontext
from dataclasses import dataclass
from typing import Any, Protocol

SCHEMA_VERSION = 1
_LABEL = re.compile(r"[A-Za-z0-9_.:/-]{1,128}\Z")
_SECRET = re.compile(r"(?i)(bearer|sk-|api.?key|password|authorization|chain.of.thought|reasoning)")
_COUNTS = frozenset(
    {
        "attempt",
        "input_bytes",
        "output_bytes",
        "input_tokens",
        "output_tokens",
        "retrieved_count",
        "dropped_events",
    }
)
_LABELS = frozenset({"operation", "model", "provider", "error_type"})
_CURRENT: contextvars.ContextVar[Span | None] = contextvars.ContextVar(
    "sage_trace_span", default=None
)
_TRACER: contextvars.ContextVar[Tracer | None] = contextvars.ContextVar("sage_tracer", default=None)


class Exporter(Protocol):
    def export(self, record: bytes) -> None:
        """Receive one sanitized, size-bounded NDJSON record on a daemon worker."""


@dataclass(frozen=True)
class TraceConfig:
    sample_rate: float = 1.0
    queue_capacity: int = 1024
    max_record_bytes: int = 16 * 1024
    max_hash_bytes: int = 4096
    allow_summaries: bool = False
    summary_redactor: Callable[[str], str] | None = None

    def __post_init__(self):
        if not math.isfinite(self.sample_rate) or not 0 <= self.sample_rate <= 1:
            raise ValueError("sample_rate must be in [0, 1]")
        if not 1 <= self.queue_capacity <= 4096 or not 512 <= self.max_record_bytes <= 16384:
            raise ValueError("trace buffer/record bounds exceeded")
        if not 0 <= self.max_hash_bytes <= 65536:
            raise ValueError("max_hash_bytes must be in [0, 65536]")
        if self.allow_summaries and self.summary_redactor is None:
            raise ValueError("public summaries require an explicit summary_redactor")


def safe_label(value: Any, default: str = "redacted") -> str:
    if (
        type(value) is str
        and _LABEL.fullmatch(value)
        and not _SECRET.search(value)
        and "://" not in value
        and not value.startswith(("/", "\\", "."))
    ):
        return value
    return default


def bounded_value_bytes(value, limit):
    if type(value) is str:
        return value[:limit].encode("utf-8")[:limit]
    if type(value) is bytes:
        return value[:limit]
    if type(value) not in {dict, list, tuple, int, float, bool, type(None)}:
        return None
    parts = bytearray()
    pending = [value]
    visited = 0
    while pending and len(parts) < limit and visited < 64:
        item = pending.pop()
        visited += 1
        remaining = limit - len(parts)
        kind = type(item)
        if kind in {str, bytes}:
            parts.extend(bounded_value_bytes(item, remaining))
        elif kind in {list, tuple}:
            parts.extend(f"{kind.__name__}:{len(item)}:".encode()[:remaining])
            pending.extend(reversed(item[:16]))
        elif kind is dict:
            parts.extend(f"dict:{len(item)}:".encode()[:remaining])
            for index, (key, val) in enumerate(item.items()):
                if index >= 16:
                    break
                if type(key) is str and not _SECRET.search(key[:128]):
                    pending.extend([val, key])
        elif kind in {int, float, bool, type(None)}:
            if kind is int and item.bit_length() > 256:
                parts.extend(b"large-int"[:remaining])
            else:
                parts.extend(str(item).encode()[:remaining])
        else:
            parts.extend(b"opaque"[:remaining])
    return bytes(parts[:limit])


class Span:
    def __init__(self, tracer, name, kind, *, parent=None, links=(), attributes=None, enabled=True):
        self.tracer = tracer
        self.enabled = enabled
        self.trace_id = parent.trace_id if parent else secrets.token_hex(16)
        self.span_id = secrets.token_hex(8)
        self.parent_span_id = parent.span_id if parent else None
        self.name = safe_label(name)
        self.kind = (
            kind if kind in {"pipeline", "model", "retrieval", "tool", "data", "step"} else "step"
        )
        if type(links) not in {list, tuple}:
            raise TypeError("trace links must be a bounded sequence")
        self.links = [
            value
            for value in links[:16]
            if type(value) is str and re.fullmatch(r"[0-9a-f]{16}", value) and int(value, 16)
        ]
        if attributes is not None and type(attributes) is not dict:
            raise TypeError("trace attributes must be a dictionary")
        self.attributes = {
            key: attributes[key]
            for key in _LABELS | _COUNTS
            if attributes is not None and key in attributes
        }
        self.evidence_refs: list[str] = []
        self.decision_summary: str | None = None
        self.status = "ok"
        self._ended = False
        self._lock = threading.Lock()
        self.started_ns = time.monotonic_ns()
        if enabled:
            tracer._emit(self, "span_start")

    def annotate(self, **attributes):
        if self.enabled:
            self.attributes.update({k: v for k, v in attributes.items() if k in _LABELS | _COUNTS})
        return self

    def record_error(self, error: BaseException):
        if self.enabled:
            with self._lock:
                if self._ended:
                    return
                self.status = (
                    "cancelled"
                    if isinstance(error, (KeyboardInterrupt, GeneratorExit))
                    or type(error).__name__ == "CancelledError"
                    else "error"
                )
                self.attributes["error_type"] = type(error).__name__

    def summarize(self, value: Any, *, output=False):
        """HMAC a bounded builtin-value representation; never repr custom objects."""
        if not self.enabled:
            return
        try:
            prefix = "output" if output else "input"
            raw = bounded_value_bytes(value, self.tracer.config.max_hash_bytes)
            if raw is None:
                return
            if type(value) is bytes:
                self.annotate(**{prefix + "_bytes": len(value)})
            elif type(value) is str and len(value) < self.tracer.config.max_hash_bytes:
                if len(raw) < self.tracer.config.max_hash_bytes:
                    self.annotate(**{prefix + "_bytes": len(raw)})
            self.evidence(prefix + "-type-" + type(value).__name__)
            digest = hmac.new(self.tracer._hash_key, raw, hashlib.sha256).hexdigest()
            self.evidence(prefix + "-prefix-hmac-" + digest)
        except Exception:
            self.tracer._increment("instrumentation_errors")

    def evidence(self, reference: str):
        if self.enabled and len(self.evidence_refs) < 16:
            self.evidence_refs.append(safe_label(reference))

    def endpoint(self, endpoint: str):
        if self.enabled and type(endpoint) is str:
            try:
                # Endpoint bodies/URLs/auth/query strings never enter the wire contract.
                digest = hmac.new(
                    self.tracer._hash_key, endpoint[:4096].encode(), hashlib.sha256
                ).hexdigest()
                self.evidence("endpoint-hmac-" + digest)
            except Exception:
                self.tracer._increment("instrumentation_errors")

    def summary(self, text: str):
        if self.enabled and self.tracer.config.allow_summaries:
            try:
                redacted = self.tracer.config.summary_redactor(text[:1024])
                if type(redacted) is str:
                    redacted = redacted[:1024]
                if type(redacted) is str and not _SECRET.search(redacted):
                    self.decision_summary = (
                        "".join(ch if ch.isprintable() else " " for ch in redacted)
                        .encode()[:256]
                        .decode(errors="ignore")
                    )
            except Exception:
                self.tracer._increment("instrumentation_errors")

    @contextmanager
    def activate(self):
        token = _CURRENT.set(self)
        try:
            yield self
        finally:
            _CURRENT.reset(token)

    def __enter__(self):
        self._activation = self.activate()
        self._activation.__enter__()
        return self

    def __exit__(self, exc_type, exc, tb):
        try:
            if exc is not None:
                self.record_error(exc)
            self.end()
        finally:
            self._activation.__exit__(exc_type, exc, tb)

    def end(self, status=None):
        with self._lock:
            if self._ended:
                return
            if type(status) is str and status in {"ok", "error", "cancelled"}:
                self.status = status
            self._ended = True
        if not self.enabled:
            return
        self.tracer._emit(self, "span_end")
        if self.parent_span_id is None:
            self.tracer._emit(
                self,
                "metrics",
                attributes={"dropped_events": self.tracer.stats()["dropped_events"]},
            )
            self.tracer._emit(self, "trace_end")


class _NoopSpan:
    enabled = False
    trace_id = span_id = parent_span_id = None
    status = "ok"
    started_ns = 0

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def activate(self):
        return self

    def end(self, *args, **kwargs):
        pass

    def annotate(self, **kwargs):
        return self

    def record_error(self, *args):
        pass

    def summarize(self, *args, **kwargs):
        pass

    def summary(self, *args):
        pass

    def endpoint(self, *args):
        pass

    def evidence(self, *args):
        pass


NOOP_SPAN = _NoopSpan()


class _NoopTracer:
    enabled = False

    def start_span(self, *args, **kwargs):
        return NOOP_SPAN

    span = start_span


NOOP_TRACER = _NoopTracer()


class Tracer:
    enabled = True

    def __init__(self, exporter: Exporter, config: TraceConfig | None = None):
        self.config = config or TraceConfig()
        self.exporter = exporter
        self.producer_id = secrets.token_hex(16)
        self.clock_id = secrets.token_hex(16)
        self._hash_key = secrets.token_bytes(32)
        self._queue = queue.Queue(maxsize=self.config.queue_capacity)
        self._lock = threading.Lock()
        self._counts = {
            "accepted_events": 0,
            "exported_events": 0,
            "dropped_events": 0,
            "export_errors": 0,
            "instrumentation_errors": 0,
        }
        self._sequence = 0
        self._closed = threading.Event()
        self._worker = threading.Thread(target=self._drain, name="sage-trace-export", daemon=True)
        self._worker.start()

    def _increment(self, key):
        with self._lock:
            self._counts[key] += 1

    def stats(self):
        with self._lock:
            return {**self._counts, "queue_depth": self._queue.qsize()}

    def start_span(self, name, *, kind="step", links=(), attributes=None):
        try:
            parent = _CURRENT.get()
            enabled = (
                parent.enabled
                if parent is not None
                else secrets.randbelow(1_000_000) < self.config.sample_rate * 1_000_000
            )
            return Span(
                self, name, kind, parent=parent, links=links, attributes=attributes, enabled=enabled
            )

        except Exception:
            self._increment("instrumentation_errors")
            return NOOP_SPAN

    span = start_span

    def _emit(self, span, event_type, *, attributes=None):
        try:
            attrs = {}
            for key, value in (span.attributes if attributes is None else attributes).items():
                if key in _COUNTS and type(value) is int and 0 <= value < 2**63:
                    attrs[key] = value
                elif key in _LABELS:
                    attrs[key] = safe_label(value)
            with self._lock:
                sequence = self._sequence
                self._sequence += 1
            record = {
                "schema_version": 1,
                "event_id": secrets.token_hex(16),
                "trace_id": span.trace_id,
                "span_id": span.span_id,
                "producer_id": self.producer_id,
                "clock_id": self.clock_id,
                "sequence": sequence,
                "event_type": event_type,
                "wall_time_ns": time.time_ns(),
                "monotonic_ns": time.monotonic_ns(),
                "name": span.name,
                "kind": span.kind,
                "attributes": attrs,
            }
            if span.parent_span_id:
                record["parent_span_id"] = span.parent_span_id
            if span.links:
                record["links"] = span.links
            if event_type in {"span_end", "trace_end"}:
                record["status"] = span.status
            if span.evidence_refs:
                record["evidence_refs"] = span.evidence_refs[:16]
            if span.decision_summary is not None:
                record["decision_summary"] = span.decision_summary
            encoded = (json.dumps(record, separators=(",", ":"), ensure_ascii=True) + "\n").encode()
            if len(encoded) > self.config.max_record_bytes:
                self._increment("dropped_events")
                return
            with self._lock:
                if self._closed.is_set():
                    self._counts["dropped_events"] += 1
                    return
                try:
                    self._queue.put_nowait(encoded)
                    self._counts["accepted_events"] += 1
                except queue.Full:
                    self._counts["dropped_events"] += 1
        except Exception:
            self._increment("instrumentation_errors")

    def _drain(self):
        while not self._closed.is_set() or not self._queue.empty():
            try:
                record = self._queue.get(timeout=0.05)
            except queue.Empty:
                continue
            try:
                self.exporter.export(record)
                self._increment("exported_events")
            except Exception:
                self._increment("export_errors")
                self._increment("dropped_events")
            finally:
                self._queue.task_done()

    def close(self, timeout=1.0):
        with self._lock:
            self._closed.set()
        self._worker.join(timeout=max(0, timeout))
        return not self._worker.is_alive()

    def flush(self, timeout=1.0):
        deadline = time.monotonic() + timeout
        while self._queue.unfinished_tasks and time.monotonic() < deadline:
            time.sleep(0.001)
        return self._queue.unfinished_tasks == 0


@contextmanager
def use_tracer(tracer: Tracer) -> Iterator[Tracer]:
    token = _TRACER.set(tracer)
    # Isolate roots when switching tracers inside another trace.
    span_token = _CURRENT.set(None)
    try:
        yield tracer
    finally:
        _CURRENT.reset(span_token)
        _TRACER.reset(token)


def get_tracer():
    return _TRACER.get() or NOOP_TRACER


def current_span():
    return _CURRENT.get() or NOOP_SPAN


def traced(name, *, kind="step", input_index=None, operation=None):
    def decorate(function):
        if inspect.iscoroutinefunction(function):

            @functools.wraps(function)
            async def run_async(*args, **kwargs):
                tracer = get_tracer()
                if not tracer.enabled:
                    return await function(*args, **kwargs)
                with tracer.span(
                    name, kind=kind, attributes={"operation": operation} if operation else None
                ) as span:
                    if input_index is not None and len(args) > input_index:
                        span.summarize(args[input_index])
                    result = await function(*args, **kwargs)
                    span.summarize(result, output=True)
                    return result

            return run_async

        @functools.wraps(function)
        def run(*args, **kwargs):
            tracer = get_tracer()
            if not tracer.enabled:
                return function(*args, **kwargs)
            with tracer.span(
                name, kind=kind, attributes={"operation": operation} if operation else None
            ) as span:
                if input_index is not None and len(args) > input_index:
                    span.summarize(args[input_index])
                result = function(*args, **kwargs)
                span.summarize(result, output=True)
                return result

        return run

    return decorate


def submit_traced(executor, function, *args, **kwargs):
    tracer = get_tracer()
    if not tracer.enabled:
        return executor.submit(function, *args, **kwargs)
    root = tracer.start_span("sage.runtime.call") if _CURRENT.get() is None else None
    with root.activate() if root is not None else nullcontext():
        context = contextvars.copy_context()
        queued = tracer.start_span("sage.runtime.queue", kind="step")

    def run():
        queued.end()
        try:
            with tracer.span("sage.runtime.execute", kind="step", links=[queued.span_id]):
                return function(*args, **kwargs)
        except BaseException as exc:
            if root is not None:
                root.record_error(exc)
            raise
        finally:
            if root is not None:
                root.end()

    def cancelled(future):
        if future.cancelled():
            queued.end("cancelled")
            if root is not None:
                root.end("cancelled")

    try:
        future = executor.submit(context.run, run)
    except BaseException as exc:
        queued.record_error(exc)
        queued.end()
        if root is not None:
            root.record_error(exc)
            root.end()
        raise
    future.add_done_callback(cancelled)
    return future


def inject_context() -> dict[str, Any]:
    """Transport IDs and sampling only. Callers explicitly attach this to their RPC contract."""
    span = _CURRENT.get()
    if span is None:
        return {}
    return {
        "schema_version": 1,
        "trace_id": span.trace_id,
        "span_id": span.span_id,
        "sampled": bool(span.enabled),
    }


@contextmanager
def use_trace_context(carrier):
    """Bind a validated remote parent without claiming clock synchronization."""
    if type(carrier) is not dict or set(carrier) != {
        "schema_version",
        "trace_id",
        "span_id",
        "sampled",
    }:
        raise ValueError("invalid trace context carrier")
    if (
        type(carrier["schema_version"]) is not int
        or carrier["schema_version"] != 1
        or type(carrier["sampled"]) is not bool
    ):
        raise ValueError("unsupported trace context carrier")
    for key, size in [("trace_id", 32), ("span_id", 16)]:
        value = carrier[key]
        if (
            type(value) is not str
            or not re.fullmatch(f"[0-9a-f]{{{size}}}", value)
            or int(value, 16) == 0
        ):
            raise ValueError("invalid trace context identity")
    parent = _NoopSpan()
    parent.trace_id, parent.span_id, parent.enabled = (
        carrier["trace_id"],
        carrier["span_id"],
        carrier["sampled"],
    )
    token = _CURRENT.set(parent)
    try:
        yield
    finally:
        _CURRENT.reset(token)
