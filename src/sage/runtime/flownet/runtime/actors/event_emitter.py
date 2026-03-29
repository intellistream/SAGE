from __future__ import annotations

import contextlib
import contextvars
from dataclasses import dataclass
from typing import Any, Literal

EMIT_ORDERING = "emit_order"
SEQ_ASC_ORDERING = "seq_asc"
SUPPORTED_TASK_EVENT_ORDERINGS = frozenset({EMIT_ORDERING, SEQ_ASC_ORDERING})


@dataclass(frozen=True)
class ActorEmittedEvent:
    """Actor event emitted via v1 public emit/publish interface."""

    mode: Literal["emit", "publish"]
    topic_uri: str
    event_group_id: str
    payload: Any = None
    tags: dict[str, str] | None = None
    seq: int | None = None


@dataclass(frozen=True)
class TaskEventPolicy:
    """Task-scoped actor event delivery policy."""

    ordering: Literal["emit_order", "seq_asc"] = EMIT_ORDERING


class ActorTaskEventBuffer:
    """Task-local actor event buffer; drained by runtime after task completion."""

    def __init__(self, *, policy: TaskEventPolicy) -> None:
        self._policy = policy
        self._events: list[ActorEmittedEvent] = []

    @property
    def policy(self) -> TaskEventPolicy:
        return self._policy

    def emit(
        self,
        *,
        topic_uri: str,
        event_group_id: str,
        payload: Any = None,
        tags: dict[str, str] | None = None,
        seq: int | None = None,
    ) -> None:
        self._events.append(
            ActorEmittedEvent(
                mode="emit",
                topic_uri=_normalize_non_empty(topic_uri, field_name="topic_uri"),
                event_group_id=_normalize_non_empty(
                    event_group_id,
                    field_name="event_group_id",
                ),
                payload=payload,
                tags=_normalize_tags(tags),
                seq=_normalize_seq(seq),
            )
        )

    def publish(
        self,
        *,
        topic_uri: str,
        event_group_id: str,
        payload: Any = None,
        tags: dict[str, str] | None = None,
        seq: int | None = None,
    ) -> None:
        self._events.append(
            ActorEmittedEvent(
                mode="publish",
                topic_uri=_normalize_non_empty(topic_uri, field_name="topic_uri"),
                event_group_id=_normalize_non_empty(
                    event_group_id,
                    field_name="event_group_id",
                ),
                payload=payload,
                tags=_normalize_tags(tags),
                seq=_normalize_seq(seq),
            )
        )

    def drain(self) -> tuple[ActorEmittedEvent, ...]:
        if not self._events:
            return ()
        events = list(self._events)
        self._events = []
        if self._policy.ordering == SEQ_ASC_ORDERING:
            indexed = list(enumerate(events))
            indexed.sort(key=_seq_asc_sort_key)
            return tuple(item[1] for item in indexed)
        return tuple(events)


_task_event_buffer_var: contextvars.ContextVar[ActorTaskEventBuffer | None] = (
    contextvars.ContextVar(
        "flownet_v1_actor_task_event_buffer",
        default=None,
    )
)


@contextlib.contextmanager
def actor_task_event_scope(*, policy: TaskEventPolicy | None = None):
    resolved_policy = policy or TaskEventPolicy()
    buffer = ActorTaskEventBuffer(policy=resolved_policy)
    token = _task_event_buffer_var.set(buffer)
    try:
        yield buffer
    finally:
        _task_event_buffer_var.reset(token)


def emit(
    topic_uri: str,
    event_group_id: str,
    payload: Any = None,
    tags: dict[str, str] | None = None,
    *,
    seq: int | None = None,
) -> None:
    buffer = _require_task_event_buffer()
    buffer.emit(
        topic_uri=topic_uri,
        event_group_id=event_group_id,
        payload=payload,
        tags=tags,
        seq=seq,
    )


def publish(
    topic_uri: str,
    event_group_id: str,
    payload: Any = None,
    tags: dict[str, str] | None = None,
    *,
    seq: int | None = None,
) -> None:
    buffer = _require_task_event_buffer()
    buffer.publish(
        topic_uri=topic_uri,
        event_group_id=event_group_id,
        payload=payload,
        tags=tags,
        seq=seq,
    )


def resolve_task_event_policy(task_policy: Any | None) -> TaskEventPolicy:
    if task_policy is None:
        return TaskEventPolicy()
    if not isinstance(task_policy, dict):
        raise TypeError("task_policy must be a dict when provided.")
    raw_ordering = str(task_policy.get("ordering") or EMIT_ORDERING).strip().lower()
    if raw_ordering not in SUPPORTED_TASK_EVENT_ORDERINGS:
        raise ValueError(f"unsupported_task_event_ordering:{raw_ordering}")
    return TaskEventPolicy(ordering=raw_ordering)


def _require_task_event_buffer() -> ActorTaskEventBuffer:
    buffer = _task_event_buffer_var.get()
    if buffer is None:
        raise RuntimeError("actor_emit_publish_outside_task_scope")
    return buffer


def _seq_asc_sort_key(item: tuple[int, ActorEmittedEvent]) -> tuple[int, int, int]:
    index, event = item
    seq = event.seq
    if seq is None:
        return (1, 0, index)
    return (0, int(seq), index)


def _normalize_non_empty(raw_value: Any, *, field_name: str) -> str:
    normalized = str(raw_value or "").strip()
    if not normalized:
        raise ValueError(f"{field_name} must be non-empty.")
    return normalized


def _normalize_tags(raw_tags: dict[str, str] | None) -> dict[str, str] | None:
    if raw_tags is None:
        return None
    if not isinstance(raw_tags, dict):
        raise TypeError("tags must be a dict when provided.")
    return {str(key): str(value) for key, value in raw_tags.items()}


def _normalize_seq(raw_seq: int | None) -> int | None:
    if raw_seq is None:
        return None
    seq = int(raw_seq)
    if seq < 0:
        raise ValueError("seq must be >= 0 when provided.")
    return seq


__all__ = [
    "EMIT_ORDERING",
    "SEQ_ASC_ORDERING",
    "SUPPORTED_TASK_EVENT_ORDERINGS",
    "ActorEmittedEvent",
    "TaskEventPolicy",
    "ActorTaskEventBuffer",
    "actor_task_event_scope",
    "emit",
    "publish",
    "resolve_task_event_policy",
]
