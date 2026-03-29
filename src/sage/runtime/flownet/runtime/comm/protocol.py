from __future__ import annotations

import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

V1_SCHEMA_VERSION = "v1"

PLANE_RPC = "rpc"
PLANE_DATA = "data"
PLANE_CONTROL = "control"
PLANE_GOSSIP = "gossip"

SUPPORTED_PLANES = frozenset(
    {
        PLANE_RPC,
        PLANE_DATA,
        PLANE_CONTROL,
        PLANE_GOSSIP,
    }
)

OP_RPC_ACTOR_CALL = "actor.call"
OP_RPC_ACTOR_CALL_RESULT = "actor.call_result"
OP_RPC_FLOW_PROGRAM_PULL = "flow_program.pull"
OP_RPC_FLOW_PROGRAM_PULL_RESULT = "flow_program.pull_result"

OP_DATA_TOPIC_EVENT_FORWARD = "topic.event_forward"

OP_CONTROL_TOPIC_EVENT_CHAIN_DONE_FORWARD = "topic.event_chain_done_forward"
OP_CONTROL_TOPIC_PRODUCER_DONE_FORWARD = "topic.producer_done_forward"
OP_CONTROL_TOPIC_REQUEST_OUTCOME_FORWARD = "topic.request_outcome_forward"
OP_CONTROL_TOPIC_REQUEST_DONE_NOTIFY = "topic.request_done_notify"
OP_CONTROL_NODE_CALL = "node.control.call"
OP_CONTROL_NODE_RESULT = "node.control.result"

OP_GOSSIP_CV_DELTA_PUSH = "cv.delta.push"
OP_GOSSIP_CV_DELTA_PULL = "cv.delta.pull"
OP_GOSSIP_CV_DELTA_ACK = "cv.delta.ack"
OP_GOSSIP_CV_SNAPSHOT = "cv.snapshot"

SUPPORTED_OPS_BY_PLANE: dict[str, frozenset[str]] = {
    PLANE_RPC: frozenset(
        {
            OP_RPC_ACTOR_CALL,
            OP_RPC_ACTOR_CALL_RESULT,
            OP_RPC_FLOW_PROGRAM_PULL,
            OP_RPC_FLOW_PROGRAM_PULL_RESULT,
        }
    ),
    PLANE_DATA: frozenset(
        {
            OP_DATA_TOPIC_EVENT_FORWARD,
        }
    ),
    PLANE_CONTROL: frozenset(
        {
            OP_CONTROL_TOPIC_EVENT_CHAIN_DONE_FORWARD,
            OP_CONTROL_TOPIC_PRODUCER_DONE_FORWARD,
            OP_CONTROL_TOPIC_REQUEST_OUTCOME_FORWARD,
            OP_CONTROL_TOPIC_REQUEST_DONE_NOTIFY,
            OP_CONTROL_NODE_CALL,
            OP_CONTROL_NODE_RESULT,
        }
    ),
    PLANE_GOSSIP: frozenset(
        {
            OP_GOSSIP_CV_DELTA_PUSH,
            OP_GOSSIP_CV_DELTA_PULL,
            OP_GOSSIP_CV_DELTA_ACK,
            OP_GOSSIP_CV_SNAPSHOT,
        }
    ),
}


@dataclass(frozen=True)
class V1Envelope:
    schema_version: str
    plane: str
    op: str
    msg_id: str
    source_address: str
    target_address: str
    expects_reply: bool = False
    request_ref_id: str | None = None
    body: Any = None
    meta: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        payload = {
            "schema_version": self.schema_version,
            "plane": self.plane,
            "op": self.op,
            "msg_id": self.msg_id,
            "source_address": self.source_address,
            "target_address": self.target_address,
            "expects_reply": bool(self.expects_reply),
            "body": self.body,
            "meta": dict(self.meta),
        }
        if self.request_ref_id is not None:
            payload["request_ref_id"] = self.request_ref_id
        return payload


def make_envelope(
    *,
    plane: str,
    op: str,
    source_address: str,
    target_address: str,
    expects_reply: bool = False,
    request_ref_id: str | None = None,
    body: Any = None,
    meta: Mapping[str, Any] | None = None,
    msg_id: str | None = None,
    schema_version: str = V1_SCHEMA_VERSION,
) -> V1Envelope:
    envelope = V1Envelope(
        schema_version=_normalize_non_empty(schema_version, field_name="schema_version"),
        plane=_normalize_plane(plane),
        op=_normalize_non_empty(op, field_name="op"),
        msg_id=_normalize_non_empty(msg_id or uuid.uuid4().hex, field_name="msg_id"),
        source_address=_normalize_non_empty(source_address, field_name="source_address"),
        target_address=_normalize_non_empty(target_address, field_name="target_address"),
        expects_reply=bool(expects_reply),
        request_ref_id=_normalize_optional_non_empty(request_ref_id),
        body=body,
        meta=dict(meta or {}),
    )
    validate_envelope(envelope)
    return envelope


def coerce_envelope(payload: V1Envelope | Mapping[str, Any]) -> V1Envelope:
    if isinstance(payload, V1Envelope):
        validate_envelope(payload)
        return payload
    if not isinstance(payload, Mapping):
        raise TypeError("envelope payload must be V1Envelope or mapping.")

    request_ref_id = payload.get("request_ref_id")
    raw_meta = payload.get("meta")
    if raw_meta is None:
        meta = {}
    elif isinstance(raw_meta, Mapping):
        meta = dict(raw_meta)
    else:
        raise TypeError("envelope.meta must be a mapping when provided.")

    envelope = V1Envelope(
        schema_version=_normalize_non_empty(
            payload.get("schema_version"), field_name="schema_version"
        ),
        plane=_normalize_plane(payload.get("plane")),
        op=_normalize_non_empty(payload.get("op"), field_name="op"),
        msg_id=_normalize_non_empty(payload.get("msg_id"), field_name="msg_id"),
        source_address=_normalize_non_empty(
            payload.get("source_address"),
            field_name="source_address",
        ),
        target_address=_normalize_non_empty(
            payload.get("target_address"),
            field_name="target_address",
        ),
        expects_reply=bool(payload.get("expects_reply", False)),
        request_ref_id=_normalize_optional_non_empty(request_ref_id),
        body=payload.get("body"),
        meta=meta,
    )
    validate_envelope(envelope)
    return envelope


def validate_envelope(envelope: V1Envelope) -> None:
    if envelope.schema_version != V1_SCHEMA_VERSION:
        raise ValueError(
            f"unsupported_schema_version:{envelope.schema_version}",
        )
    if envelope.plane not in SUPPORTED_PLANES:
        raise ValueError(f"unsupported_plane:{envelope.plane}")
    allowed_ops = SUPPORTED_OPS_BY_PLANE.get(envelope.plane, frozenset())
    if envelope.op not in allowed_ops:
        raise ValueError(
            f"unsupported_op_for_plane:{envelope.plane}:{envelope.op}",
        )
    _validate_topic_op_contract(envelope)
    _validate_flow_program_pull_op_contract(envelope)


def _validate_topic_op_contract(envelope: V1Envelope) -> None:
    if envelope.op == OP_DATA_TOPIC_EVENT_FORWARD:
        _validate_topic_forward_body(envelope, expected_mode="forward_topic_event")
        return
    if envelope.op == OP_CONTROL_TOPIC_EVENT_CHAIN_DONE_FORWARD:
        body = _validate_topic_forward_body(
            envelope,
            expected_mode="forward_event_chain_done",
        )
        if "delta" not in body:
            raise ValueError("topic_forward_delta_missing")
        int(body["delta"])
        return
    if envelope.op == OP_CONTROL_TOPIC_PRODUCER_DONE_FORWARD:
        body = _validate_topic_forward_body(
            envelope,
            expected_mode="forward_producer_done",
        )
        if "final_seq" in body and body["final_seq"] is not None:
            _normalize_non_negative_int(body["final_seq"], field_name="final_seq")
        if "expected_total_events" in body and body["expected_total_events"] is not None:
            _normalize_non_negative_int(
                body["expected_total_events"],
                field_name="expected_total_events",
            )
        return
    if envelope.op == OP_CONTROL_TOPIC_REQUEST_OUTCOME_FORWARD:
        body = _validate_topic_forward_body(
            envelope,
            expected_mode="forward_request_outcome",
        )
        _normalize_non_empty(body.get("outcome_status"), field_name="outcome_status")
        for field_name in (
            "outcome_error_type",
            "outcome_error_message",
            "outcome_error_stage",
        ):
            if field_name in body and body[field_name] is not None:
                _normalize_non_empty(body[field_name], field_name=field_name)
        if "outcome_metadata" in body and body["outcome_metadata"] is not None:
            if not isinstance(body["outcome_metadata"], Mapping):
                raise TypeError("outcome_metadata must be a mapping when provided.")
        return
    if envelope.op == OP_CONTROL_TOPIC_REQUEST_DONE_NOTIFY:
        body = _validate_topic_notify_body(
            envelope,
            expected_mode="request_done_notify",
        )
        _normalize_non_empty(body.get("status"), field_name="status")
        _normalize_non_empty(body.get("subscriber_id"), field_name="subscriber_id")
        if "final_seq" in body and body["final_seq"] is not None:
            _normalize_non_negative_int(body["final_seq"], field_name="final_seq")
        if "expected_total_events" not in body:
            raise ValueError("request_done_expected_total_events_missing")
        _normalize_non_negative_int(
            body.get("expected_total_events"),
            field_name="expected_total_events",
        )
        return


def _validate_flow_program_pull_op_contract(envelope: V1Envelope) -> None:
    if envelope.op == OP_RPC_FLOW_PROGRAM_PULL:
        _validate_flow_program_pull_body(
            envelope,
            expected_mode="flow_program_pull",
            require_found=False,
        )
        return
    if envelope.op == OP_RPC_FLOW_PROGRAM_PULL_RESULT:
        body = _validate_flow_program_pull_body(
            envelope,
            expected_mode="flow_program_pull_result",
            require_found=True,
        )
        found = bool(body["found"])
        if found and "flow_program" not in body:
            raise ValueError("flow_program_pull_result_missing_flow_program")
        return


def _validate_flow_program_pull_body(
    envelope: V1Envelope,
    *,
    expected_mode: str,
    require_found: bool,
) -> Mapping[str, Any]:
    if not isinstance(envelope.body, Mapping):
        raise TypeError("flow_program_pull_body must be a mapping.")
    body = envelope.body
    mode = _normalize_non_empty(body.get("mode"), field_name="mode")
    if mode != expected_mode:
        raise ValueError(
            f"flow_program_pull_mode_mismatch:{expected_mode}:{mode}",
        )
    if "flow_program_ref" not in body:
        raise ValueError("flow_program_pull_ref_missing")
    _validate_flow_program_ref_mapping(body.get("flow_program_ref"))
    if require_found:
        if "found" not in body:
            raise ValueError("flow_program_pull_result_found_missing")
        bool(body["found"])
    return body


def _validate_flow_program_ref_mapping(raw: Any) -> None:
    if not isinstance(raw, Mapping):
        raise TypeError("flow_program_ref must be a mapping.")
    _normalize_non_empty(raw.get("program_uri"), field_name="flow_program_ref.program_uri")
    _normalize_non_empty(raw.get("program_rev"), field_name="flow_program_ref.program_rev")


def _validate_topic_forward_body(
    envelope: V1Envelope,
    *,
    expected_mode: str,
) -> Mapping[str, Any]:
    if not isinstance(envelope.body, Mapping):
        raise TypeError("topic_forward_body must be a mapping.")
    body = envelope.body
    mode = _normalize_non_empty(body.get("mode"), field_name="mode")
    if mode != expected_mode:
        raise ValueError(
            f"topic_forward_mode_mismatch:{expected_mode}:{mode}",
        )
    if "request_ref_id" in body:
        raise ValueError("request_ref_id is not allowed in v1 topic forward body.")
    event_group_id = _normalize_non_empty(
        body.get("event_group_id"),
        field_name="event_group_id",
    )
    _normalize_non_empty(body.get("topic_uri"), field_name="topic_uri")
    _normalize_non_negative_int(body.get("epoch"), field_name="epoch")
    envelope_request_ref_id = _normalize_non_empty(
        envelope.request_ref_id,
        field_name="request_ref_id",
    )
    if envelope_request_ref_id != event_group_id:
        raise ValueError(
            "topic_forward_request_ref_mismatch:"
            f" envelope_request_ref_id={envelope_request_ref_id},"
            f" event_group_id={event_group_id}",
        )
    return body


def _validate_topic_notify_body(
    envelope: V1Envelope,
    *,
    expected_mode: str,
) -> Mapping[str, Any]:
    if not isinstance(envelope.body, Mapping):
        raise TypeError("topic_notify_body must be a mapping.")
    body = envelope.body
    mode = _normalize_non_empty(body.get("mode"), field_name="mode")
    if mode != expected_mode:
        raise ValueError(
            f"topic_notify_mode_mismatch:{expected_mode}:{mode}",
        )
    if "request_ref_id" in body:
        raise ValueError("request_ref_id is not allowed in v1 topic notify body.")
    event_group_id = _normalize_non_empty(
        body.get("event_group_id"),
        field_name="event_group_id",
    )
    _normalize_non_empty(body.get("topic_uri"), field_name="topic_uri")
    _normalize_non_negative_int(body.get("epoch"), field_name="epoch")
    envelope_request_ref_id = _normalize_non_empty(
        envelope.request_ref_id,
        field_name="request_ref_id",
    )
    if envelope_request_ref_id != event_group_id:
        raise ValueError(
            "topic_notify_request_ref_mismatch:"
            f" envelope_request_ref_id={envelope_request_ref_id},"
            f" event_group_id={event_group_id}",
        )
    return body


def _normalize_plane(value: Any) -> str:
    normalized = _normalize_non_empty(value, field_name="plane").lower()
    return normalized


def _normalize_non_empty(value: Any, *, field_name: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError(f"{field_name} must be non-empty.")
    return normalized


def _normalize_optional_non_empty(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    if not normalized:
        return None
    return normalized


def _normalize_non_negative_int(value: Any, *, field_name: str) -> int:
    normalized = int(value)
    if normalized < 0:
        raise ValueError(f"{field_name} must be non-negative.")
    return normalized


__all__ = [
    "V1_SCHEMA_VERSION",
    "PLANE_RPC",
    "PLANE_DATA",
    "PLANE_CONTROL",
    "PLANE_GOSSIP",
    "SUPPORTED_PLANES",
    "OP_RPC_ACTOR_CALL",
    "OP_RPC_ACTOR_CALL_RESULT",
    "OP_RPC_FLOW_PROGRAM_PULL",
    "OP_RPC_FLOW_PROGRAM_PULL_RESULT",
    "OP_DATA_TOPIC_EVENT_FORWARD",
    "OP_CONTROL_TOPIC_EVENT_CHAIN_DONE_FORWARD",
    "OP_CONTROL_TOPIC_PRODUCER_DONE_FORWARD",
    "OP_CONTROL_TOPIC_REQUEST_OUTCOME_FORWARD",
    "OP_CONTROL_TOPIC_REQUEST_DONE_NOTIFY",
    "OP_CONTROL_NODE_CALL",
    "OP_CONTROL_NODE_RESULT",
    "OP_GOSSIP_CV_DELTA_PUSH",
    "OP_GOSSIP_CV_DELTA_PULL",
    "OP_GOSSIP_CV_DELTA_ACK",
    "OP_GOSSIP_CV_SNAPSHOT",
    "SUPPORTED_OPS_BY_PLANE",
    "V1Envelope",
    "make_envelope",
    "coerce_envelope",
    "validate_envelope",
]
