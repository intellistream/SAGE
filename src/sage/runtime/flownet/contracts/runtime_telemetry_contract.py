from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

RUNTIME_TELEMETRY_SCHEMA_VERSION = "flownet.runtime.telemetry.v1"


def normalize_runtime_stream_tracker_summary(payload: Any) -> dict[str, Any]:
    raw = dict(payload) if isinstance(payload, Mapping) else {}
    queue_rows = _normalize_queue_rows(raw.get("queues"))

    tracked_requests = _coerce_optional_non_negative_int(raw.get("tracked_requests"))
    if tracked_requests is None:
        tracked_requests = sum(int(row["tracked_requests"]) for row in queue_rows)

    completed_requests = _coerce_optional_non_negative_int(raw.get("completed_requests"))
    if completed_requests is None:
        completed_requests = sum(int(row["completed_requests"]) for row in queue_rows)

    active_requests = _coerce_optional_non_negative_int(raw.get("active_requests"))
    if active_requests is None:
        active_requests = sum(int(row["active_requests"]) for row in queue_rows)
    if active_requests is None:
        active_requests = max(0, tracked_requests - completed_requests)

    pending_event_chains = _coerce_optional_non_negative_int(raw.get("pending_event_chains"))
    if pending_event_chains is None:
        pending_event_chains = sum(int(row["pending_event_chains"]) for row in queue_rows)

    queue_delay_ms = _normalize_delay_ms(
        raw.get("queue_delay_ms"),
        fallback_rows=queue_rows,
    )

    return {
        "tracked_requests": tracked_requests,
        "completed_requests": completed_requests,
        "active_requests": active_requests,
        "pending_event_chains": pending_event_chains,
        "queue_delay_ms": queue_delay_ms,
        "queues": queue_rows,
    }


def normalize_runtime_scheduler_telemetry(payload: Any) -> dict[str, Any]:
    raw = dict(payload) if isinstance(payload, Mapping) else {}
    stream_tracker = normalize_runtime_stream_tracker_summary(raw.get("stream_tracker"))
    backends = _normalize_backend_summary(raw.get("backends"))
    workload_lanes = _normalize_workload_lane_summary(raw.get("workload_lanes"))
    queue = _normalize_queue_summary(
        raw.get("queue"),
        stream_tracker=stream_tracker,
        backends=backends,
        workload_lanes=workload_lanes,
        legacy_payload=raw,
    )

    return {
        "schema_version": _normalize_non_empty_string(
            raw.get("schema_version"),
            default=RUNTIME_TELEMETRY_SCHEMA_VERSION,
        ),
        "generated_at_ms": _coerce_non_negative_int(raw.get("generated_at_ms")),
        "source": _normalize_non_empty_string(
            raw.get("source"), default="flownet.runtime.node_control"
        ),
        "node": _normalize_node_summary(raw.get("node")),
        "queue": queue,
        "stream_tracker": stream_tracker,
        "backends": backends,
        "workload_lanes": workload_lanes,
        "scheduler_resource_fallback_rate": _normalize_fallback_summary(
            raw.get("scheduler_resource_fallback_rate"),
        ),
        "scheduler_spillover": _normalize_spillover_summary(raw.get("scheduler_spillover")),
        "transport": _normalize_mapping(raw.get("transport")),
    }


def summarize_runtime_scheduler_observability(payload: Any) -> dict[str, Any]:
    telemetry = normalize_runtime_scheduler_telemetry(payload)
    queue = telemetry["queue"]
    return {
        "queue": int(queue["depth"]),
        "pending": int(queue["pending"]),
        "running": int(queue["running"]),
        "inflight": int(queue["inflight"]),
        "queue_delay_ms": dict(queue["delay_ms"]),
        "fallback": dict(telemetry["scheduler_resource_fallback_rate"]),
        "spillover": dict(telemetry["scheduler_spillover"]),
    }


def _normalize_node_summary(payload: Any) -> dict[str, Any]:
    raw = dict(payload) if isinstance(payload, Mapping) else {}
    return {
        "node_id": _normalize_optional_non_empty(raw.get("node_id")),
        "node_address": _normalize_optional_non_empty(raw.get("node_address")),
        "local_address": _normalize_optional_non_empty(raw.get("local_address")),
        "runtime_loop_running": bool(raw.get("runtime_loop_running", False)),
        "user_loop_running": bool(raw.get("user_loop_running", False)),
        "actor_count": _coerce_non_negative_int(raw.get("actor_count")),
        "callback_count": _coerce_non_negative_int(raw.get("callback_count")),
        "topic_event_listener_count": _coerce_non_negative_int(
            raw.get("topic_event_listener_count")
        ),
        "backend_count": _coerce_non_negative_int(raw.get("backend_count")),
    }


def _normalize_queue_summary(
    payload: Any,
    *,
    stream_tracker: dict[str, Any],
    backends: dict[str, Any],
    workload_lanes: dict[str, Any],
    legacy_payload: Mapping[str, Any],
) -> dict[str, Any]:
    raw = dict(payload) if isinstance(payload, Mapping) else {}
    queue_rows = _normalize_queue_rows(raw.get("queues"))
    if not queue_rows:
        queue_rows = list(stream_tracker["queues"])

    tracked_requests = int(stream_tracker["tracked_requests"])
    completed_requests = int(stream_tracker["completed_requests"])
    active_requests = int(stream_tracker["active_requests"])

    pending = _coerce_optional_non_negative_int(raw.get("pending"))
    running = _coerce_optional_non_negative_int(raw.get("running"))
    inflight = _coerce_optional_non_negative_int(raw.get("inflight"))
    depth = _coerce_optional_non_negative_int(raw.get("depth"))

    legacy_pending = _derive_legacy_pending(legacy_payload)
    legacy_queue_depth = _derive_legacy_queue_depth(legacy_payload, fallback_pending=legacy_pending)
    legacy_running = _derive_legacy_running(legacy_payload, fallback_pending=legacy_pending)

    lane_running = int(workload_lanes["running"])
    lane_queued = int(workload_lanes["queued"])
    backend_pending = int(backends["queue_depth"])
    backend_running = int(backends["inflight"])
    has_runtime_shape = (
        bool(raw)
        or bool(queue_rows)
        or bool(backends["records"])
        or bool(workload_lanes["records"])
    )

    resolved_running = max(
        _or_zero(running),
        legacy_running,
        lane_running,
        backend_running,
    )
    resolved_pending = max(
        _or_zero(pending),
        legacy_pending,
        lane_queued,
        backend_pending,
        max(0, active_requests - resolved_running),
    )
    resolved_inflight = max(
        _or_zero(inflight),
        resolved_running,
        backend_running,
    )
    resolved_depth = max(
        _or_zero(depth),
        legacy_queue_depth,
        active_requests,
    )
    if has_runtime_shape:
        resolved_depth = max(
            resolved_depth,
            resolved_pending + resolved_running,
        )

    return {
        "depth": resolved_depth,
        "pending": resolved_pending,
        "running": resolved_running,
        "inflight": resolved_inflight,
        "tracked_requests": tracked_requests,
        "completed_requests": completed_requests,
        "active_requests": active_requests,
        "delay_ms": _normalize_delay_ms(raw.get("delay_ms"), fallback_rows=queue_rows),
        "queues": queue_rows,
    }


def _derive_legacy_pending(payload: Mapping[str, Any]) -> int:
    stream_tracker = normalize_runtime_stream_tracker_summary(payload.get("stream_tracker"))
    return int(stream_tracker["active_requests"])


def _derive_legacy_queue_depth(payload: Mapping[str, Any], *, fallback_pending: int) -> int:
    owner_fairness = _normalize_mapping(payload.get("scheduler_owner_fairness"))
    return max(
        fallback_pending,
        _coerce_non_negative_int(owner_fairness.get("active_reservations")),
    )


def _derive_legacy_running(payload: Mapping[str, Any], *, fallback_pending: int) -> int:
    autoscaling = _normalize_mapping(payload.get("scheduler_autoscaling"))
    stages = autoscaling.get("stages")
    if isinstance(stages, Mapping):
        running = 0
        for stage in stages.values():
            running += _coerce_non_negative_int(_normalize_mapping(stage).get("desired_workers"))
        if running > 0:
            return running
    return fallback_pending


def _normalize_backend_summary(payload: Any) -> dict[str, Any]:
    raw = dict(payload) if isinstance(payload, Mapping) else {}
    records = _normalize_backend_records(raw.get("records"))
    if (
        not records
        and isinstance(payload, Sequence)
        and not isinstance(payload, (str, bytes, bytearray))
    ):
        records = _normalize_backend_records(payload)

    queue_depth = _coerce_optional_non_negative_int(raw.get("queue_depth"))
    if queue_depth is None:
        queue_depth = sum(int(record["queue_depth"]) for record in records)

    inflight = _coerce_optional_non_negative_int(raw.get("inflight"))
    if inflight is None:
        inflight = sum(int(record["inflight"]) for record in records)

    healthy = _coerce_optional_non_negative_int(raw.get("healthy"))
    if healthy is None:
        healthy = sum(1 for record in records if bool(record["healthy"]))

    schedulable = _coerce_optional_non_negative_int(raw.get("schedulable"))
    if schedulable is None:
        schedulable = sum(1 for record in records if bool(record["schedulable"]))

    return {
        "records": records,
        "backend_count": len(records),
        "healthy": healthy,
        "schedulable": schedulable,
        "queue_depth": queue_depth,
        "inflight": inflight,
    }


def _normalize_backend_records(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, Sequence) or isinstance(payload, (str, bytes, bytearray)):
        return []
    rows: list[dict[str, Any]] = []
    for item in payload:
        if not isinstance(item, Mapping):
            continue
        raw = dict(item)
        metrics = _normalize_mapping(raw.get("metrics"))
        row = {
            "backend_id": _normalize_non_empty_string(raw.get("backend_id"), default=""),
            "node_id": _normalize_optional_non_empty(raw.get("node_id")),
            "node_address": _normalize_optional_non_empty(raw.get("node_address")),
            "healthy": bool(metrics.get("healthy", raw.get("healthy", False))),
            "schedulable": bool(metrics.get("schedulable", raw.get("schedulable", False))),
            "queue_depth": _coerce_non_negative_int(metrics.get("queue_depth")),
            "queue_capacity": _coerce_non_negative_int(metrics.get("queue_capacity")),
            "inflight": _coerce_non_negative_int(metrics.get("inflight")),
            "epoch": _coerce_optional_non_negative_int(metrics.get("epoch")),
            "tags": _normalize_mapping(raw.get("tags")),
            "capabilities": _normalize_mapping(raw.get("capabilities")),
            "metadata": _normalize_mapping(raw.get("metadata")),
        }
        rows.append(row)
    rows.sort(key=lambda item: (str(item["backend_id"]), str(item["node_address"] or "")))
    return rows


def _normalize_workload_lane_summary(payload: Any) -> dict[str, Any]:
    raw = dict(payload) if isinstance(payload, Mapping) else {}
    records = _normalize_workload_lane_records(raw.get("records"))

    pending = _coerce_optional_non_negative_int(raw.get("pending"))
    if pending is None:
        pending = sum(int(record["pending"]) for record in records)

    running = _coerce_optional_non_negative_int(raw.get("running"))
    if running is None:
        running = sum(int(record["running"]) for record in records)

    queued = _coerce_optional_non_negative_int(raw.get("queued"))
    if queued is None:
        queued = sum(int(record["queued"]) for record in records)

    return {
        "records": records,
        "lane_count": len(records),
        "pending": pending,
        "running": running,
        "queued": queued,
    }


def _normalize_workload_lane_records(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, Sequence) or isinstance(payload, (str, bytes, bytearray)):
        return []
    rows: list[dict[str, Any]] = []
    for item in payload:
        if not isinstance(item, Mapping):
            continue
        raw = dict(item)
        row = {
            "lane": _normalize_non_empty_string(raw.get("lane"), default="default_cpu"),
            "actor_count": _coerce_non_negative_int(raw.get("actor_count")),
            "pending": _coerce_non_negative_int(raw.get("pending")),
            "running": _coerce_non_negative_int(raw.get("running")),
            "queued": _coerce_non_negative_int(raw.get("queued")),
            "worker_capacity": _coerce_optional_non_negative_int(raw.get("worker_capacity")),
        }
        rows.append(row)
    rows.sort(key=lambda item: str(item["lane"]))
    return rows


def _normalize_fallback_summary(payload: Any) -> dict[str, Any]:
    raw = dict(payload) if isinstance(payload, Mapping) else {}
    fallback_count = _coerce_non_negative_int(raw.get("fallback_count"))
    total = _coerce_non_negative_int(raw.get("total"))
    rate = _coerce_optional_non_negative_float(raw.get("rate"))
    if rate is None:
        rate = (float(fallback_count) / float(total)) if total > 0 else 0.0
    return {
        "fallback_count": fallback_count,
        "total": total,
        "rate": rate,
    }


def _normalize_spillover_summary(payload: Any) -> dict[str, Any]:
    raw = dict(payload) if isinstance(payload, Mapping) else {}
    return {
        "decision_count": _coerce_non_negative_int(raw.get("decision_count")),
        "remote_used_count": _coerce_non_negative_int(raw.get("remote_used_count")),
        "remote_blocked_count": _coerce_non_negative_int(raw.get("remote_blocked_count")),
        "active_claims": _coerce_non_negative_int(raw.get("active_claims")),
    }


def _normalize_queue_rows(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, Sequence) or isinstance(payload, (str, bytes, bytearray)):
        return []
    rows: list[dict[str, Any]] = []
    for item in payload:
        if not isinstance(item, Mapping):
            continue
        raw = dict(item)
        topic_uri = _normalize_non_empty_string(raw.get("topic_uri"), default="")
        epoch = _coerce_non_negative_int(raw.get("epoch"))
        queue_id = _normalize_optional_non_empty(raw.get("queue_id"))
        if queue_id is None and topic_uri:
            queue_id = f"{topic_uri}@{epoch}"
        row = {
            "queue_id": queue_id or "",
            "topic_uri": topic_uri,
            "epoch": epoch,
            "tracked_requests": _coerce_non_negative_int(raw.get("tracked_requests")),
            "completed_requests": _coerce_non_negative_int(raw.get("completed_requests")),
            "active_requests": _coerce_non_negative_int(raw.get("active_requests")),
            "pending_event_chains": _coerce_non_negative_int(raw.get("pending_event_chains")),
            "queue_delay_ms": _coerce_optional_non_negative_float(
                raw.get("queue_delay_ms", raw.get("delay_ms"))
            ),
        }
        rows.append(row)
    rows.sort(key=lambda item: (str(item["topic_uri"]), int(item["epoch"]), str(item["queue_id"])))
    return rows


def _normalize_delay_ms(
    payload: Any, *, fallback_rows: Sequence[Mapping[str, Any]]
) -> dict[str, float]:
    raw = dict(payload) if isinstance(payload, Mapping) else {}
    avg = _coerce_optional_non_negative_float(raw.get("avg"))
    max_delay = _coerce_optional_non_negative_float(raw.get("max"))
    if avg is None or max_delay is None:
        samples = [
            float(delay)
            for delay in (
                _coerce_optional_non_negative_float(row.get("queue_delay_ms"))
                for row in fallback_rows
            )
            if delay is not None
        ]
        if avg is None:
            avg = (sum(samples) / float(len(samples))) if samples else 0.0
        if max_delay is None:
            max_delay = max(samples) if samples else 0.0
    return {
        "avg": round(avg, 3),
        "max": round(max_delay, 3),
    }


def _normalize_mapping(payload: Any) -> dict[str, Any]:
    return dict(payload) if isinstance(payload, Mapping) else {}


def _normalize_non_empty_string(value: Any, *, default: str) -> str:
    normalized = str(value or "").strip()
    if normalized:
        return normalized
    return str(default)


def _normalize_optional_non_empty(value: Any) -> str | None:
    normalized = str(value or "").strip()
    if not normalized:
        return None
    return normalized


def _coerce_non_negative_int(value: Any) -> int:
    try:
        normalized = int(value)
    except (TypeError, ValueError):
        return 0
    if normalized < 0:
        return 0
    return normalized


def _coerce_optional_non_negative_int(value: Any) -> int | None:
    if value is None:
        return None
    return _coerce_non_negative_int(value)


def _coerce_optional_non_negative_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        normalized = float(value)
    except (TypeError, ValueError):
        return None
    if normalized < 0.0:
        return None
    return normalized


def _or_zero(value: int | None) -> int:
    return 0 if value is None else int(value)


__all__ = [
    "RUNTIME_TELEMETRY_SCHEMA_VERSION",
    "normalize_runtime_scheduler_telemetry",
    "normalize_runtime_stream_tracker_summary",
    "summarize_runtime_scheduler_observability",
]
