"""Strict read-side boundary for observable inference v1 records."""

from __future__ import annotations

import re

from .core import _COUNTS, _LABELS, _SECRET, safe_label

_REQUIRED = {
    "schema_version",
    "event_id",
    "trace_id",
    "span_id",
    "producer_id",
    "clock_id",
    "sequence",
    "event_type",
    "wall_time_ns",
    "monotonic_ns",
}
_OPTIONAL = {
    "parent_span_id",
    "name",
    "kind",
    "status",
    "attributes",
    "decision_summary",
    "evidence_refs",
    "links",
}


def normalize_record(record, *, include_summaries=False):
    if (
        type(record) is not dict
        or set(record) - _REQUIRED - _OPTIONAL
        or not _REQUIRED <= set(record)
    ):
        raise ValueError("invalid trace envelope")
    if type(record["schema_version"]) is not int or record["schema_version"] != 1:
        raise ValueError("unsupported trace schema")
    result = {key: record[key] for key in _REQUIRED}
    for key, size in [("trace_id", 32), ("span_id", 16)]:
        value = record[key]
        if (
            type(value) is not str
            or not re.fullmatch(f"[0-9a-f]{{{size}}}", value)
            or int(value, 16) == 0
        ):
            raise ValueError("invalid trace identity")
    for key in ["event_id", "producer_id", "clock_id"]:
        if type(record[key]) is not str or safe_label(record[key], "") != record[key]:
            raise ValueError("invalid producer identity")
    for key in ["sequence", "wall_time_ns", "monotonic_ns"]:
        if type(record[key]) is not int or not 0 <= record[key] < 2**63:
            raise ValueError("invalid trace clock or sequence")
    if record["event_type"] not in {"span_start", "span_end", "span_event", "trace_end", "metrics"}:
        raise ValueError("unsupported trace event type")
    for key in ["name", "kind", "status"]:
        if key in record:
            result[key] = safe_label(record[key])
    if "parent_span_id" in record:
        parent = record["parent_span_id"]
        if type(parent) is not str or not re.fullmatch("[0-9a-f]{16}", parent):
            raise ValueError("invalid trace parent")
        result["parent_span_id"] = parent
    attrs = record.get("attributes", {})
    if type(attrs) is not dict or len(attrs) > 32:
        raise ValueError("invalid trace attributes")
    result["attributes"] = {}
    for key, value in attrs.items():
        if key in _COUNTS and type(value) is int and 0 <= value < 2**63:
            result["attributes"][key] = value
        elif key in _LABELS:
            result["attributes"][key] = safe_label(value)
    for key in ["evidence_refs", "links"]:
        values = record.get(key, [])
        if type(values) is not list or len(values) > 16:
            raise ValueError("invalid trace references")
        if key == "links":
            if any(type(v) is not str or not re.fullmatch("[0-9a-f]{16}", v) for v in values):
                raise ValueError("invalid dependency identity")
            result[key] = values
        else:
            result[key] = [safe_label(v) for v in values]
    summary = record.get("decision_summary")
    if (
        include_summaries
        and type(summary) is str
        and len(summary.encode()) <= 256
        and not _SECRET.search(summary)
    ):
        result["decision_summary"] = "".join(ch if ch.isprintable() else " " for ch in summary)
    return result
