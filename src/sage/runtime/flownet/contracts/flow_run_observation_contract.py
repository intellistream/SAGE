from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def normalize_flow_run_read_item(item: Any) -> dict[str, Any] | None:
    if item is None:
        return None
    if isinstance(item, dict) and "kind" in item:
        return dict(item)

    item_type_name = item.__class__.__name__
    request_id = getattr(item, "request_id", None)
    request_ref_id = getattr(item, "request_ref_id", None) or request_id

    if item_type_name == "RunOutputDone":
        result = {
            "kind": "done",
            "request_id": request_id,
            "request_ref_id": request_ref_id,
            "final_seq": getattr(item, "final_seq", None),
            "reason": getattr(item, "reason", None),
        }
        expected_total_events = getattr(item, "expected_total_events", None)
        if expected_total_events is not None:
            result["expected_total_events"] = expected_total_events
        request_done = getattr(item, "request_done", None)
        if request_done is not None:
            result["request_done"] = bool(request_done)
        status = getattr(item, "status", None)
        if isinstance(status, str) and status.strip():
            result["status"] = status.strip()
        subscriber_done = getattr(item, "subscriber_done", None)
        if subscriber_done is not None:
            result["subscriber_done"] = bool(subscriber_done)
        return result
    if item_type_name == "RunOutputError":
        return {
            "kind": "error",
            "request_id": request_id,
            "request_ref_id": request_ref_id,
            "error_type": getattr(item, "error_type", None),
            "message": getattr(item, "message", None),
            "traceback_text": getattr(item, "traceback_text", None),
            "event": getattr(item, "event", None),
        }
    if item_type_name == "RunOutputGap":
        return {
            "kind": "gap",
            "request_id": request_id,
            "request_ref_id": request_ref_id,
            "seq": getattr(item, "seq", None),
            "reason": getattr(item, "reason", None),
        }
    return {"kind": "data", "value": item}


def normalize_request_status_payload(
    status: Any,
    *,
    fallback_request_id: str,
) -> Any:
    if not isinstance(status, dict):
        return status
    normalized = dict(status)
    request_ref_id = str(
        normalized.get("request_ref_id") or normalized.get("request_id") or fallback_request_id
    )
    normalized.setdefault("request_id", request_ref_id)
    normalized.setdefault("request_ref_id", request_ref_id)
    return normalized


def _coerce_non_negative_int(value: Any) -> int | None:
    try:
        normalized = int(value)
    except (TypeError, ValueError):
        return None
    if normalized < 0:
        return None
    return normalized


def _derive_request_status_value(
    *,
    status_value: Any,
    request_done: bool,
    producer_done: bool,
    event_chain_pending: int,
    run_status: Any = None,
) -> str:
    normalized_status = str(status_value or "").strip().lower()
    if normalized_status:
        return normalized_status
    if request_done:
        normalized_run_status = str(run_status or "").strip().lower()
        if normalized_run_status in {"failed", "cancelled", "timed_out"}:
            return normalized_run_status
        return "completed"
    if producer_done and event_chain_pending > 0:
        return "quiescing"
    return "running"


def normalize_flow_run_request_delivery_status(
    status: Any,
    *,
    fallback_request_id: str,
    run_status: Any = None,
) -> dict[str, Any]:
    normalized = dict(status) if isinstance(status, Mapping) else {}
    request_ref_id = str(
        normalized.get("request_ref_id") or normalized.get("request_id") or fallback_request_id
    )
    pending = normalized.get("event_chain_pending")
    if pending is None:
        pending = normalized.get("pending")
    try:
        event_chain_pending = max(0, int(pending))
    except (TypeError, ValueError):
        event_chain_pending = 0
    producer_done = bool(
        normalized.get("producer_done")
        if "producer_done" in normalized
        else normalized.get("done_marked", False)
    )
    request_done = bool(
        normalized.get("request_done")
        if "request_done" in normalized
        else normalized.get("completed", False)
    )
    final_seq = _coerce_non_negative_int(normalized.get("final_seq"))
    if final_seq is None:
        final_seq = _coerce_non_negative_int(normalized.get("source_final_seq"))
    expected_total_events = _coerce_non_negative_int(normalized.get("expected_total_events"))
    if expected_total_events is None:
        expected_total_events = final_seq
    status_value = _derive_request_status_value(
        status_value=normalized.get("status"),
        request_done=request_done,
        producer_done=producer_done,
        event_chain_pending=event_chain_pending,
        run_status=run_status,
    )
    normalized.setdefault("request_id", request_ref_id)
    normalized.setdefault("request_ref_id", request_ref_id)
    normalized.setdefault("pending", event_chain_pending)
    normalized.setdefault("event_chain_pending", event_chain_pending)
    normalized.setdefault("event_chain_done", event_chain_pending == 0)
    normalized.setdefault("done_marked", producer_done)
    normalized.setdefault("producer_done", producer_done)
    normalized.setdefault("completed", request_done)
    normalized.setdefault("request_done", request_done)
    normalized.setdefault("status", status_value)
    if final_seq is not None:
        normalized.setdefault("final_seq", final_seq)
    if expected_total_events is not None:
        normalized.setdefault("expected_total_events", expected_total_events)
    return normalized


__all__ = [
    "normalize_flow_run_read_item",
    "normalize_request_status_payload",
    "normalize_flow_run_request_delivery_status",
]
