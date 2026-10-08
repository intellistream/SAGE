from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from sage.runtime.flownet.runtime.flowengine.cursor_codec import encode_event_cursor
from sage.runtime.flownet.runtime.flowengine.cursor_models import EventCursor

DEFAULT_MAX_FLOW_STACK_DEPTH = 128
DEFAULT_MAX_CURSOR_BYTES = 65536


class EventCursorGuardError(ValueError):
    """Raised when cursor runtime guardrails are violated."""


def enforce_flow_stack_depth(
    cursor: EventCursor,
    *,
    max_depth: int = DEFAULT_MAX_FLOW_STACK_DEPTH,
) -> int:
    if max_depth < 0:
        raise ValueError("max_depth must be >= 0.")
    depth = len(cursor.flow_stack)
    if depth > max_depth:
        raise EventCursorGuardError(
            f"event_cursor_flow_stack_depth_exceeded: depth={depth}, max_depth={max_depth}",
        )
    return depth


def estimate_cursor_size_bytes(encoded_cursor: Mapping[str, Any]) -> int:
    try:
        encoded = json.dumps(
            encoded_cursor,
            separators=(",", ":"),
            ensure_ascii=False,
            sort_keys=True,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise EventCursorGuardError("event_cursor_not_json_serializable") from exc
    return len(encoded)


def enforce_cursor_size(
    encoded_cursor: Mapping[str, Any],
    *,
    max_bytes: int = DEFAULT_MAX_CURSOR_BYTES,
) -> int:
    if max_bytes < 0:
        raise ValueError("max_bytes must be >= 0.")
    size_bytes = estimate_cursor_size_bytes(encoded_cursor)
    if size_bytes > max_bytes:
        raise EventCursorGuardError(
            f"event_cursor_size_exceeded: size_bytes={size_bytes}, max_bytes={max_bytes}",
        )
    return size_bytes


def validate_event_cursor_guards(
    cursor: EventCursor,
    *,
    max_flow_stack_depth: int = DEFAULT_MAX_FLOW_STACK_DEPTH,
    max_cursor_bytes: int = DEFAULT_MAX_CURSOR_BYTES,
) -> int:
    enforce_flow_stack_depth(cursor, max_depth=max_flow_stack_depth)
    encoded = encode_event_cursor(cursor)
    return enforce_cursor_size(encoded, max_bytes=max_cursor_bytes)


__all__ = [
    "DEFAULT_MAX_FLOW_STACK_DEPTH",
    "DEFAULT_MAX_CURSOR_BYTES",
    "EventCursorGuardError",
    "enforce_flow_stack_depth",
    "estimate_cursor_size_bytes",
    "enforce_cursor_size",
    "validate_event_cursor_guards",
]
