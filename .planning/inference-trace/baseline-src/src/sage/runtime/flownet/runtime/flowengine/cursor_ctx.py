from __future__ import annotations

import contextlib
import contextvars
from typing import Any

from sage.runtime.flownet.runtime.flowengine.cursor_models import EventCursor

_event_cursor_var: contextvars.ContextVar[EventCursor | None] = contextvars.ContextVar(
    "flownet_v1_active_cursor_ctx",
    default=None,
)


@contextlib.contextmanager
def bind_event_cursor(cursor: EventCursor):
    token = _event_cursor_var.set(cursor)
    try:
        yield cursor
    finally:
        _event_cursor_var.reset(token)


def current_event_cursor() -> EventCursor | None:
    return _event_cursor_var.get()


def require_event_cursor() -> EventCursor:
    cursor = current_event_cursor()
    if cursor is None:
        raise RuntimeError("flownet_v1_event_cursor_not_bound")
    return cursor


def current_event_meta() -> dict[str, Any] | None:
    cursor = current_event_cursor()
    if cursor is None:
        return None
    return {
        "event_group_id": cursor.event_group_id,
        "event_chain_id": cursor.event_chain_id,
        "pc_node_id": cursor.pc_node_id,
        "flow_program_ref": {
            "program_uri": cursor.flow_program_ref.program_uri,
            "program_rev": cursor.flow_program_ref.program_rev,
        },
        "origin_topic_ref": {
            "topic_uri": cursor.origin_topic_ref.topic_uri,
            "coordinator_address": cursor.origin_topic_ref.coordinator_address,
        },
        "convergence_topic_ref": {
            "topic_uri": cursor.convergence_topic_ref.topic_uri,
            "coordinator_address": cursor.convergence_topic_ref.coordinator_address,
        },
        "convergence_topic_epoch": cursor.convergence_topic_epoch,
        "meta": dict(cursor.meta),
        "tags": dict(cursor.tags),
        "seq": cursor.seq,
    }


__all__ = [
    "bind_event_cursor",
    "current_event_cursor",
    "require_event_cursor",
    "current_event_meta",
]
