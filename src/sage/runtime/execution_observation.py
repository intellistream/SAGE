"""Request-scoped, content-free native execution observations.

These events describe execution, not application durability or external effects.
Sinks may persist/forward events but must not execute workflows. Sink failures
fail explicitly; they are never fabricated as successful operator completions.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import asdict, dataclass
from threading import Lock
from uuid import uuid4

from sage.runtime.cancellation import RequestCancelledError

_observer: ContextVar[ExecutionObserver | None] = ContextVar("sage_execution_observer", default=None)
_parent: ContextVar[str | None] = ContextVar("sage_execution_parent", default=None)
_wave: ContextVar[tuple[str, int] | None] = ContextVar("sage_execution_wave", default=None)
_delivering: ContextVar[ExecutionObserver | None] = ContextVar("sage_execution_delivery", default=None)


class ExecutionObservationError(RuntimeError):
    """The execution observation port failed; no secret-bearing sink error text."""


def execution_is_observed():
    return _observer.get() is not None


@dataclass(frozen=True)
class ExecutionNodeRef:
    program_uri: str
    program_rev: str
    node_id: str


@dataclass(frozen=True)
class ExecutionEvent:
    version: int
    event_id: str
    sequence: int
    trace_id: str
    execution_id: str
    parent_execution_id: str | None
    request_id: str
    program_uri: str
    program_rev: str
    node_id: str
    operator_type: str
    operator_key: str | None
    upstream_node_ids: tuple[str, ...]
    downstream_node_ids: tuple[str, ...]
    next_nodes: tuple[ExecutionNodeRef, ...]
    wave_id: str | None
    wave_size: int
    state: str
    timestamp_ns: int
    duration_ns: int | None
    resolution: str | None

    def to_dict(self):
        return asdict(self)


class ExecutionObserver:
    """One serialized observation port, safe across copied request contexts.

    IDs/labels must be non-secret registry identifiers, never prompts or tokens.
    Events do not contain operator inputs, outputs, tags, exception messages or
    transport addresses. Wave membership describes scheduling, not measured
    temporal overlap. A terminal operator event does not acknowledge a database
    commit or complete all background work.
    """

    def __init__(self, sink: Callable[[ExecutionEvent], None], *, trace_id: str | None = None):
        if not callable(sink):
            raise TypeError("execution_observation_sink_required")
        self.trace_id = trace_id if trace_id is not None else uuid4().hex
        if not isinstance(self.trace_id, str) or not self.trace_id or self.trace_id != self.trace_id.strip():
            raise ValueError("invalid_execution_trace_id")
        self._sink = sink
        self._identity = uuid4().hex
        self._sequence = 0
        self._lock = Lock()

    @classmethod
    def journaled(cls, journal, *, stream_id: str, trace_id: str | None = None):
        """Persist metadata through the existing EventJournal, not a new store.

        The caller owns stream authorization and must keep it open until observed
        operators drain. A closed/failing journal is an explicit sink error.
        """
        from sage.runtime.event_journal import EventJournal

        if not isinstance(journal, EventJournal):
            raise TypeError("execution_event_journal_required")
        if not isinstance(stream_id, str) or not stream_id or stream_id != stream_id.strip():
            raise ValueError("invalid_execution_stream_id")

        def persist(event):
            journal.append(stream_id, event_id=event.event_id,
                payload={"type": "execution-event", "event": event.to_dict()})

        return cls(persist, trace_id=stream_id if trace_id is None else trace_id)

    @contextmanager
    def bind(self):
        observer_token = _observer.set(self)
        parent_token = _parent.set(None)
        wave_token = _wave.set(None)
        try:
            yield self
        finally:
            _wave.reset(wave_token)
            _parent.reset(parent_token)
            _observer.reset(observer_token)

    def _emit(self, fields):
        if _delivering.get() is not None:
            raise ExecutionObservationError("execution_observer_reentrant_delivery")
        with self._lock:
            self._sequence += 1
            event = ExecutionEvent(version=1, event_id=f"{self._identity}:{self._sequence}",
                sequence=self._sequence, trace_id=self.trace_id, timestamp_ns=time.time_ns(), **fields)
            token = _delivering.set(self)
            try:
                self._sink(event)
            except BaseException as error:
                raise ExecutionObservationError("execution_observation_delivery_failed") from error
            finally:
                _delivering.reset(token)


@contextmanager
def execution_wave(size):
    if _observer.get() is None:
        yield
        return
    token = _wave.set((uuid4().hex, size))
    try:
        yield
    finally:
        _wave.reset(token)


class _ExecutionSpan:
    def __init__(self):
        self.state = "completed"
        self.resolution = None
        self.next_nodes = ()

    def resolve(self, result):
        operator_type = result.operator_type
        self.next_nodes = tuple(ExecutionNodeRef(cursor.flow_program_ref.program_uri,
            cursor.flow_program_ref.program_rev, cursor.pc_node_id) for cursor in result.next_cursors)
        if operator_type == "exception/fallback":
            self.state, self.resolution = "recovered", "fallback"
        elif operator_type in {"exception/drop", "exception/abort"}:
            self.state, self.resolution = "failed", operator_type.split("/")[1]

    def failed_resolution(self, action):
        if action in {"drop", "abort"}:
            self.resolution = action


@contextmanager
def observe_operator(cursor, transformation):
    observer = _observer.get()
    span = _ExecutionSpan()
    if observer is None:
        yield span
        return
    wave = _wave.get()
    execution_id = uuid4().hex
    fields = dict(execution_id=execution_id, parent_execution_id=_parent.get(),
        request_id=cursor.event_group_id, program_uri=cursor.flow_program_ref.program_uri,
        program_rev=cursor.flow_program_ref.program_rev, node_id=cursor.pc_node_id,
        operator_type=str(getattr(transformation, "type", "unknown")),
        operator_key=getattr(transformation, "operator_key", None),
        upstream_node_ids=tuple(item.trans_id for item in getattr(transformation, "upstreams", ())),
        downstream_node_ids=tuple(item.trans_id for item in getattr(transformation, "downstreams", ())),
        wave_id=wave[0] if wave else None, wave_size=wave[1] if wave else 1)
    observer._emit({**fields, "state": "started", "duration_ns": None, "resolution": None,
                    "next_nodes": ()})
    parent_token = _parent.set(execution_id)
    started = time.monotonic_ns()
    try:
        yield span
    except BaseException as error:
        state = "cancelled" if isinstance(error, (RequestCancelledError, asyncio.CancelledError)) else "failed"
        observer._emit({**fields, "state": state, "duration_ns": time.monotonic_ns() - started,
                        "resolution": span.resolution, "next_nodes": ()})
        raise
    else:
        observer._emit({**fields, "state": span.state, "duration_ns": time.monotonic_ns() - started,
                        "resolution": span.resolution, "next_nodes": span.next_nodes})
    finally:
        _parent.reset(parent_token)
