from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from sage.runtime.flownet.runtime.flowengine.cursor_models import (
    FLOW_STACK_FRAME_KIND_FLATMAP_CONTINUATION,
    FLOW_STACK_FRAME_KIND_LOOP_SCOPE,
    FLOW_STACK_FRAME_KIND_PROCESS_RETURN,
    EventCursor,
    FlowProgramRef,
    FlowStackFrame,
    TopicRef,
)

_CURSOR_KEYS = frozenset(
    {
        "event_group_id",
        "event_chain_id",
        "flow_program_ref",
        "pc_node_id",
        "flow_stack",
        "payload",
        "tags",
        "seq",
        "origin_topic_ref",
        "convergence_topic_ref",
        "convergence_topic_epoch",
        "meta",
    }
)
_FLOW_PROGRAM_REF_KEYS = frozenset({"program_uri", "program_rev"})
_TOPIC_REF_KEYS = frozenset({"topic_uri", "coordinator_address"})
_FRAME_REQUIRED_KEYS = frozenset(
    {
        "resume_flow_program_ref",
        "resume_pc_node_ids",
        "caller_event_chain_id",
        "callsite_pc_node_id",
        "frame_meta",
    }
)
_FRAME_OPTIONAL_KEYS = frozenset({"frame_kind"})
_FRAME_ALLOWED_KINDS = frozenset(
    {
        FLOW_STACK_FRAME_KIND_PROCESS_RETURN,
        FLOW_STACK_FRAME_KIND_LOOP_SCOPE,
        FLOW_STACK_FRAME_KIND_FLATMAP_CONTINUATION,
    }
)


class EventCursorDecodeError(ValueError):
    """Raised when incoming cursor payload violates canonical schema."""


def decode_event_cursor(raw: Mapping[str, Any]) -> EventCursor:
    mapping = _require_mapping(raw, field_name="event_cursor")
    _assert_exact_keys(mapping, _CURSOR_KEYS, field_name="event_cursor")

    return EventCursor(
        event_group_id=_require_non_empty_str(
            mapping["event_group_id"], field_name="event_group_id"
        ),
        event_chain_id=_require_non_empty_str(
            mapping["event_chain_id"], field_name="event_chain_id"
        ),
        flow_program_ref=_decode_flow_program_ref(mapping["flow_program_ref"]),
        pc_node_id=_require_non_empty_str(mapping["pc_node_id"], field_name="pc_node_id"),
        flow_stack=_decode_flow_stack(mapping["flow_stack"]),
        payload=mapping["payload"],
        tags=_decode_string_dict(mapping["tags"], field_name="tags"),
        seq=_decode_seq(mapping["seq"]),
        origin_topic_ref=_decode_topic_ref(
            mapping["origin_topic_ref"], field_name="origin_topic_ref"
        ),
        convergence_topic_ref=_decode_topic_ref(
            mapping["convergence_topic_ref"],
            field_name="convergence_topic_ref",
        ),
        convergence_topic_epoch=_require_non_negative_int(
            mapping["convergence_topic_epoch"],
            field_name="convergence_topic_epoch",
        ),
        meta=_decode_meta(mapping["meta"], field_name="meta"),
    )


def encode_event_cursor(cursor: EventCursor) -> dict[str, Any]:
    return {
        "event_group_id": cursor.event_group_id,
        "event_chain_id": cursor.event_chain_id,
        "flow_program_ref": {
            "program_uri": cursor.flow_program_ref.program_uri,
            "program_rev": cursor.flow_program_ref.program_rev,
        },
        "pc_node_id": cursor.pc_node_id,
        "flow_stack": [
            {
                "resume_flow_program_ref": {
                    "program_uri": frame.resume_flow_program_ref.program_uri,
                    "program_rev": frame.resume_flow_program_ref.program_rev,
                },
                "resume_pc_node_ids": list(frame.resume_pc_node_ids),
                "caller_event_chain_id": frame.caller_event_chain_id,
                "callsite_pc_node_id": frame.callsite_pc_node_id,
                "frame_meta": dict(frame.frame_meta),
                "frame_kind": frame.frame_kind,
            }
            for frame in cursor.flow_stack
        ],
        "payload": cursor.payload,
        "tags": dict(cursor.tags),
        "seq": cursor.seq,
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
    }


def _decode_flow_stack(raw: Any) -> tuple[FlowStackFrame, ...]:
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes, bytearray)):
        raise EventCursorDecodeError("flow_stack must be a sequence.")
    frames: list[FlowStackFrame] = []
    for index, item in enumerate(raw):
        frame_mapping = _require_mapping(item, field_name=f"flow_stack[{index}]")
        _assert_required_and_allowed_keys(
            frame_mapping,
            required_keys=_FRAME_REQUIRED_KEYS,
            optional_keys=_FRAME_OPTIONAL_KEYS,
            field_name=f"flow_stack[{index}]",
        )
        resume_nodes_raw = frame_mapping["resume_pc_node_ids"]
        if not isinstance(resume_nodes_raw, Sequence) or isinstance(
            resume_nodes_raw,
            (str, bytes, bytearray),
        ):
            raise EventCursorDecodeError(
                f"flow_stack[{index}].resume_pc_node_ids must be a sequence."
            )
        resume_pc_node_ids = tuple(
            _require_non_empty_str(
                node_id,
                field_name=f"flow_stack[{index}].resume_pc_node_ids[{node_index}]",
            )
            for node_index, node_id in enumerate(resume_nodes_raw)
        )
        if not resume_pc_node_ids:
            raise EventCursorDecodeError(
                f"flow_stack[{index}].resume_pc_node_ids must not be empty."
            )
        frame_kind = _decode_frame_kind(
            frame_mapping.get("frame_kind", FLOW_STACK_FRAME_KIND_PROCESS_RETURN),
            field_name=f"flow_stack[{index}].frame_kind",
        )

        frames.append(
            FlowStackFrame(
                resume_flow_program_ref=_decode_flow_program_ref(
                    frame_mapping["resume_flow_program_ref"],
                    field_name=f"flow_stack[{index}].resume_flow_program_ref",
                ),
                resume_pc_node_ids=resume_pc_node_ids,
                caller_event_chain_id=_require_non_empty_str(
                    frame_mapping["caller_event_chain_id"],
                    field_name=f"flow_stack[{index}].caller_event_chain_id",
                ),
                callsite_pc_node_id=_require_non_empty_str(
                    frame_mapping["callsite_pc_node_id"],
                    field_name=f"flow_stack[{index}].callsite_pc_node_id",
                ),
                frame_meta=_decode_meta(
                    frame_mapping["frame_meta"],
                    field_name=f"flow_stack[{index}].frame_meta",
                ),
                frame_kind=frame_kind,
            )
        )
    return tuple(frames)


def _decode_flow_program_ref(
    raw: Any,
    *,
    field_name: str = "flow_program_ref",
) -> FlowProgramRef:
    mapping = _require_mapping(raw, field_name=field_name)
    _assert_exact_keys(mapping, _FLOW_PROGRAM_REF_KEYS, field_name=field_name)
    return FlowProgramRef(
        program_uri=_require_non_empty_str(
            mapping["program_uri"], field_name=f"{field_name}.program_uri"
        ),
        program_rev=_require_non_empty_str(
            mapping["program_rev"], field_name=f"{field_name}.program_rev"
        ),
    )


def _decode_topic_ref(raw: Any, *, field_name: str) -> TopicRef:
    mapping = _require_mapping(raw, field_name=field_name)
    _assert_exact_keys(mapping, _TOPIC_REF_KEYS, field_name=field_name)
    return TopicRef(
        topic_uri=_require_non_empty_str(
            mapping["topic_uri"], field_name=f"{field_name}.topic_uri"
        ),
        coordinator_address=_require_non_empty_str(
            mapping["coordinator_address"],
            field_name=f"{field_name}.coordinator_address",
        ),
    )


def _decode_seq(raw: Any) -> int | None:
    if raw is None:
        return None
    return _require_non_negative_int(raw, field_name="seq")


def _decode_meta(raw: Any, *, field_name: str) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise EventCursorDecodeError(f"{field_name} must be a mapping.")
    resolved: dict[str, Any] = {}
    for key, value in raw.items():
        if not isinstance(key, str) or not key.strip():
            raise EventCursorDecodeError(f"{field_name} keys must be non-empty strings.")
        resolved[key] = value
    return resolved


def _decode_string_dict(raw: Any, *, field_name: str) -> dict[str, str]:
    if not isinstance(raw, Mapping):
        raise EventCursorDecodeError(f"{field_name} must be a mapping.")
    resolved: dict[str, str] = {}
    for key, value in raw.items():
        if not isinstance(key, str) or not key.strip():
            raise EventCursorDecodeError(f"{field_name} keys must be non-empty strings.")
        if not isinstance(value, str):
            raise EventCursorDecodeError(f"{field_name}[{key!r}] must be a string.")
        resolved[key] = value
    return resolved


def _assert_exact_keys(
    mapping: Mapping[str, Any],
    expected_keys: frozenset[str],
    *,
    field_name: str,
) -> None:
    keys = set(mapping.keys())
    unknown = sorted(key for key in keys - expected_keys)
    if unknown:
        raise EventCursorDecodeError(f"{field_name} contains unknown keys: {unknown}")
    missing = sorted(key for key in expected_keys - keys)
    if missing:
        raise EventCursorDecodeError(f"{field_name} is missing required keys: {missing}")


def _assert_required_and_allowed_keys(
    mapping: Mapping[str, Any],
    *,
    required_keys: frozenset[str],
    optional_keys: frozenset[str],
    field_name: str,
) -> None:
    keys = set(mapping.keys())
    allowed_keys = required_keys | optional_keys
    unknown = sorted(key for key in keys - allowed_keys)
    if unknown:
        raise EventCursorDecodeError(f"{field_name} contains unknown keys: {unknown}")
    missing = sorted(key for key in required_keys - keys)
    if missing:
        raise EventCursorDecodeError(f"{field_name} is missing required keys: {missing}")


def _decode_frame_kind(raw: Any, *, field_name: str) -> str:
    if not isinstance(raw, str):
        raise EventCursorDecodeError(f"{field_name} must be a string.")
    frame_kind = raw.strip()
    if not frame_kind:
        raise EventCursorDecodeError(f"{field_name} must not be empty.")
    if frame_kind not in _FRAME_ALLOWED_KINDS:
        allowed = ", ".join(sorted(_FRAME_ALLOWED_KINDS))
        raise EventCursorDecodeError(
            f"{field_name} must be one of: {allowed}.",
        )
    return frame_kind


def _require_mapping(raw: Any, *, field_name: str) -> Mapping[str, Any]:
    if not isinstance(raw, Mapping):
        raise EventCursorDecodeError(f"{field_name} must be a mapping.")
    return raw


def _require_non_empty_str(raw: Any, *, field_name: str) -> str:
    if not isinstance(raw, str):
        raise EventCursorDecodeError(f"{field_name} must be a string.")
    resolved = raw.strip()
    if not resolved:
        raise EventCursorDecodeError(f"{field_name} must not be empty.")
    return resolved


def _require_non_negative_int(raw: Any, *, field_name: str) -> int:
    if isinstance(raw, bool):
        raise EventCursorDecodeError(f"{field_name} must be an integer.")
    if isinstance(raw, int):
        resolved = raw
    elif isinstance(raw, str):
        try:
            resolved = int(raw)
        except ValueError as exc:
            raise EventCursorDecodeError(f"{field_name} must be an integer.") from exc
    else:
        raise EventCursorDecodeError(f"{field_name} must be an integer.")
    if resolved < 0:
        raise EventCursorDecodeError(f"{field_name} must be >= 0.")
    return resolved


__all__ = [
    "EventCursorDecodeError",
    "decode_event_cursor",
    "encode_event_cursor",
]
