"""Read-only, bounded live/finished timeline data for CLI and UI consumers."""

from __future__ import annotations

import json
from pathlib import Path

from .schema import normalize_record


def read_events(source, *, max_bytes=64 * 1024**2, max_events=100_000, include_summaries=False):
    source = Path(source)
    paths = sorted(source.glob("trace-*.ndjson")) if source.is_dir() else [source]
    events = []
    seen = {}
    lifecycle = set()
    consumed = 0
    for path in paths:
        try:
            stream = path.open("rb")
        except FileNotFoundError:
            if source.is_dir():
                continue  # A concurrent spool purge removed this segment.
            raise
        with stream:
            while line := stream.readline(16385):
                consumed += len(line)
                if consumed > max_bytes or len(line) > 16384:
                    raise ValueError("trace read budget exceeded")
                if not line.endswith(b"\n"):
                    break  # Concurrent writer's partial last record remains pending.
                record = normalize_record(json.loads(line), include_summaries=include_summaries)
                key = record["trace_id"], record["event_id"]
                if key in seen and seen[key] != record:
                    raise ValueError("conflicting trace event identity")
                if key not in seen:
                    kind = record["event_type"]
                    lifecycle_key = None
                    if kind in {"span_start", "span_end"}:
                        lifecycle_key = record["trace_id"], record["span_id"], kind
                    elif kind == "trace_end":
                        lifecycle_key = record["trace_id"], kind
                    if lifecycle_key is not None:
                        if lifecycle_key in lifecycle:
                            raise ValueError("conflicting trace lifecycle")
                        lifecycle.add(lifecycle_key)
                    seen[key] = record
                    events.append(record)
                if len(events) > max_events:
                    raise ValueError("trace event budget exceeded")
    return events


def timeline(events, trace_id=None):
    traces = {}
    for event in events:
        key = event["trace_id"]
        if trace_id and key != trace_id:
            continue
        trace = traces.setdefault(
            key, {"trace_id": key, "spans": {}, "receipt": None, "producer_drops": {}}
        )
        kind = event["event_type"]
        if kind == "trace_end":
            trace["receipt"] = event
        elif kind == "metrics":
            producer = event["producer_id"]
            trace["producer_drops"][producer] = max(
                trace["producer_drops"].get(producer, 0),
                event.get("attributes", {}).get("dropped_events", 0),
            )
        elif kind in {"span_start", "span_end"}:
            trace["spans"].setdefault(event["span_id"], {})[kind] = event
    result = []
    for trace in traces.values():
        spans = []
        for span_id, pair in trace["spans"].items():
            start, end = pair.get("span_start"), pair.get("span_end")
            identity = start or end
            comparable = (
                start
                and end
                and (start["producer_id"], start["clock_id"])
                == (end["producer_id"], end["clock_id"])
            )
            duration = end["monotonic_ns"] - start["monotonic_ns"] if comparable else None
            spans.append(
                {
                    "span_id": span_id,
                    "parent_span_id": identity.get("parent_span_id"),
                    "name": identity.get("name"),
                    "kind": identity.get("kind"),
                    "clock_id": identity["clock_id"],
                    "producer_id": identity["producer_id"],
                    "start_ns": start["monotonic_ns"] if start else None,
                    "wall_time_ns": identity["wall_time_ns"],
                    "end_ns": end["monotonic_ns"] if end else None,
                    "duration_ns": duration if duration is not None and duration >= 0 else None,
                    "status": end.get("status", "ok") if end else "running",
                    "complete": bool(comparable and duration >= 0),
                    "attributes": (end or start).get("attributes", {}),
                    "evidence_refs": (end or start).get("evidence_refs", []),
                    "decision_summary": (end or start).get("decision_summary"),
                    "links": identity.get("links", []),
                }
            )
        spans.sort(key=lambda span: (span["clock_id"], span["start_ns"] or 0))
        receipt = trace["receipt"]
        root_observed = receipt is not None and any(
            span["span_id"] == receipt["span_id"]
            and span["parent_span_id"] is None
            and span["complete"]
            for span in spans
        )
        complete = root_observed and all(span["complete"] for span in spans)
        dropped = sum(trace["producer_drops"].values())
        result.append(
            {
                "trace_id": trace["trace_id"],
                "state": "finished_observed" if complete else "live_or_incomplete",
                "dropped_events": dropped,
                "spans": spans,
                "critical_path": longest_observed_path(spans, dropped=dropped),
            }
        )
    return {"schema_version": 1, "traces": result}


def longest_observed_path(spans, *, dropped=0):
    """Bounded DAG traversal of explicit, observed completion-before-start links."""
    from collections import deque

    by_id = {span["span_id"]: span for span in spans}
    reasons = {"producer_does_not_attest_all_dependencies"}
    if dropped:
        reasons.add("dropped_events")
    if any(not span["complete"] for span in spans):
        reasons.add("incomplete_spans")
    scoped = {span["parent_span_id"] for span in spans if span["parent_span_id"]}
    if scoped - by_id.keys():
        reasons.add("missing_parent")
    nodes = {key: span for key, span in by_id.items() if span["complete"]}
    outgoing = {key: set() for key in nodes}
    indegree = {key: 0 for key in nodes}
    for key, span in nodes.items():
        for previous_id in set(span["links"]):
            previous = by_id.get(previous_id)
            if previous is None:
                reasons.add("missing_dependency")
                continue
            if (previous["producer_id"], previous["clock_id"]) != (
                span["producer_id"],
                span["clock_id"],
            ):
                reasons.add("uncalibrated_clock_domains")
                continue
            if previous_id not in nodes:
                continue
            if previous["end_ns"] > span["start_ns"]:
                reasons.add("noncausal_dependency")
                continue
            outgoing[previous_id].add(key)
            indegree[key] += 1
    ready = deque(key for key, count in indegree.items() if count == 0)
    cost = {key: span["duration_ns"] for key, span in nodes.items()}
    predecessor = {}
    visited = set()
    while ready:
        key = ready.popleft()
        visited.add(key)
        for successor in outgoing[key]:
            candidate = cost[key] + nodes[successor]["duration_ns"]
            if candidate > cost[successor]:
                cost[successor] = candidate
                predecessor[successor] = key
            indegree[successor] -= 1
            if indegree[successor] == 0:
                ready.append(successor)
    if len(visited) != len(nodes):
        reasons.add("dependency_cycle")
    leaf_candidates = visited - scoped
    last = max(leaf_candidates, key=lambda key: (cost[key], key), default=None)
    path = []
    key = last
    while key is not None:
        path.append(key)
        key = predecessor.get(key)
    return {
        "basis": "longest_observed_dependency_path",
        "dependency_completeness": "partial",
        "duration_ns": cost[last] if last is not None else 0,
        "span_ids": list(reversed(path)),
        "limitations": sorted(reasons),
    }
