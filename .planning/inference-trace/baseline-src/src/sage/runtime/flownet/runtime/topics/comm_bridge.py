from __future__ import annotations

from typing import Any

from sage.runtime.flownet.runtime.comm import (
    OP_CONTROL_TOPIC_EVENT_CHAIN_DONE_FORWARD,
    OP_CONTROL_TOPIC_PRODUCER_DONE_FORWARD,
    OP_CONTROL_TOPIC_REQUEST_DONE_NOTIFY,
    OP_CONTROL_TOPIC_REQUEST_OUTCOME_FORWARD,
    OP_DATA_TOPIC_EVENT_FORWARD,
    PLANE_CONTROL,
    PLANE_DATA,
    V1CommHub,
    V1Envelope,
)
from sage.runtime.flownet.runtime.topics.topic_api import TopicAPI

_TOPIC_FORWARD_MODE_TO_WIRE: dict[str, tuple[str, str, str]] = {
    "forward_topic_event": (PLANE_DATA, OP_DATA_TOPIC_EVENT_FORWARD, "coordinator_address"),
    "forward_event_chain_done": (
        PLANE_CONTROL,
        OP_CONTROL_TOPIC_EVENT_CHAIN_DONE_FORWARD,
        "coordinator_address",
    ),
    "forward_producer_done": (
        PLANE_CONTROL,
        OP_CONTROL_TOPIC_PRODUCER_DONE_FORWARD,
        "coordinator_address",
    ),
    "forward_request_outcome": (
        PLANE_CONTROL,
        OP_CONTROL_TOPIC_REQUEST_OUTCOME_FORWARD,
        "coordinator_address",
    ),
    "request_done_notify": (
        PLANE_CONTROL,
        OP_CONTROL_TOPIC_REQUEST_DONE_NOTIFY,
        "subscriber_address",
    ),
}


def register_topic_forward_handlers(*, topic_api: TopicAPI, comm_hub: V1CommHub) -> None:
    """Register owner-side handlers for topic forward ops."""

    def _handle_event_forward(envelope) -> dict[str, Any]:
        intent = _coerce_topic_intent(envelope.body, expected_mode="forward_topic_event")
        return topic_api.apply_forward_intent(intent)

    def _handle_event_chain_done_forward(envelope) -> dict[str, Any]:
        intent = _coerce_topic_intent(envelope.body, expected_mode="forward_event_chain_done")
        return topic_api.apply_forward_intent(intent)

    def _handle_producer_done_forward(envelope) -> dict[str, Any]:
        intent = _coerce_topic_intent(envelope.body, expected_mode="forward_producer_done")
        return topic_api.apply_forward_intent(intent)

    def _handle_request_outcome_forward(envelope) -> dict[str, Any]:
        intent = _coerce_topic_intent(envelope.body, expected_mode="forward_request_outcome")
        return topic_api.apply_forward_intent(intent)

    def _handle_request_done_notify(envelope) -> dict[str, Any]:
        intent = _coerce_topic_intent(envelope.body, expected_mode="request_done_notify")
        return topic_api.apply_forward_intent(intent)

    comm_hub.protocol_router.register_handler(
        plane=PLANE_DATA,
        op=OP_DATA_TOPIC_EVENT_FORWARD,
        handler=_handle_event_forward,
    )
    comm_hub.protocol_router.register_handler(
        plane=PLANE_CONTROL,
        op=OP_CONTROL_TOPIC_EVENT_CHAIN_DONE_FORWARD,
        handler=_handle_event_chain_done_forward,
    )
    comm_hub.protocol_router.register_handler(
        plane=PLANE_CONTROL,
        op=OP_CONTROL_TOPIC_PRODUCER_DONE_FORWARD,
        handler=_handle_producer_done_forward,
    )
    comm_hub.protocol_router.register_handler(
        plane=PLANE_CONTROL,
        op=OP_CONTROL_TOPIC_REQUEST_OUTCOME_FORWARD,
        handler=_handle_request_outcome_forward,
    )
    comm_hub.protocol_router.register_handler(
        plane=PLANE_CONTROL,
        op=OP_CONTROL_TOPIC_REQUEST_DONE_NOTIFY,
        handler=_handle_request_done_notify,
    )


async def send_topic_forward_intent_via_comm(
    *,
    comm_hub: V1CommHub,
    intent: dict[str, Any],
) -> V1Envelope:
    """Send topic forward intent through V1CommHub as one-way data/control traffic."""

    if not isinstance(intent, dict):
        raise TypeError("intent must be a dict.")
    mode = _normalize_non_empty(intent.get("mode"), field_name="mode")
    if mode == "local":
        raise ValueError("local result does not require remote forwarding.")
    wire = _TOPIC_FORWARD_MODE_TO_WIRE.get(mode)
    if wire is None:
        raise ValueError(f"unsupported_topic_forward_mode:{mode}")
    plane, op, target_field = wire
    target_address = _normalize_non_empty(
        intent.get(target_field),
        field_name=target_field,
    )
    event_group_id = _resolve_event_group_id_from_intent(intent)
    request_ref_id = _normalize_non_empty(
        event_group_id,
        field_name="request_ref_id",
    )
    return await comm_hub.send(
        plane=plane,
        op=op,
        target_address=target_address,
        request_ref_id=request_ref_id,
        body=dict(intent),
    )


def _coerce_topic_intent(body: Any, *, expected_mode: str) -> dict[str, Any]:
    if not isinstance(body, dict):
        raise TypeError("topic forward body must be a dict.")
    intent = dict(body)
    mode = _normalize_non_empty(intent.get("mode"), field_name="mode")
    if mode != expected_mode:
        raise ValueError(f"topic_forward_mode_mismatch: expected={expected_mode}, actual={mode}")
    return intent


def _resolve_event_group_id_from_intent(intent: dict[str, Any]) -> str:
    if "request_ref_id" in intent:
        raise ValueError("request_ref_id is not allowed for v1 topic intents.")
    return _normalize_non_empty(
        intent.get("event_group_id"),
        field_name="event_group_id",
    )


def _normalize_non_empty(value: Any, *, field_name: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError(f"{field_name} must be non-empty.")
    return normalized


__all__ = [
    "register_topic_forward_handlers",
    "send_topic_forward_intent_via_comm",
]
