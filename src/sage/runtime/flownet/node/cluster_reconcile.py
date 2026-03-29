from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any


def merge_observed_cluster_views(
    snapshots: Iterable[Mapping[str, Any]],
) -> list[dict[str, str]]:
    merged: dict[str, dict[str, str]] = {}
    for snapshot in snapshots:
        raw_nodes = snapshot.get("nodes")
        if not isinstance(raw_nodes, list):
            continue
        for raw_node in raw_nodes:
            if not isinstance(raw_node, Mapping):
                continue
            node_id = str(raw_node.get("node_id") or "").strip()
            if not node_id:
                continue
            health = str(raw_node.get("health") or "").strip().lower() or "unknown"
            address = str(raw_node.get("address") or "").strip()
            next_row = {
                "node_id": node_id,
                "health": health,
                "address": address,
            }
            previous = merged.get(node_id)
            if previous is None or _health_rank(health) >= _health_rank(previous["health"]):
                merged[node_id] = next_row
    return [merged[node_id] for node_id in sorted(merged)]


def compute_cluster_drift(
    *,
    desired_node_ids: Iterable[str],
    observed_nodes: Iterable[Mapping[str, Any]],
) -> dict[str, list[str]]:
    desired = {
        str(node_id or "").strip() for node_id in desired_node_ids if str(node_id or "").strip()
    }
    observed_ids: set[str] = set()
    offline: set[str] = set()
    for row in observed_nodes:
        node_id = str(row.get("node_id") or "").strip()
        if not node_id:
            continue
        observed_ids.add(node_id)
        health = str(row.get("health") or "").strip().lower()
        if health != "healthy":
            offline.add(node_id)
    return {
        "missing": sorted(desired.difference(observed_ids)),
        "extra": sorted(observed_ids.difference(desired)),
        "offline": sorted(offline),
    }


def build_reconcile_actions(
    *,
    drift: Mapping[str, Any],
    apply: bool,
) -> list[dict[str, str]]:
    mode = "apply" if apply else "report"
    actions: list[dict[str, str]] = []
    for node_id in sorted(_string_list(drift.get("missing"))):
        actions.append(
            {
                "action": "join",
                "node_id": node_id,
                "mode": mode,
            }
        )
    for node_id in sorted(_string_list(drift.get("offline"))):
        actions.append(
            {
                "action": "restart",
                "node_id": node_id,
                "mode": mode,
            }
        )
    for node_id in sorted(_string_list(drift.get("extra"))):
        actions.append(
            {
                "action": "leave",
                "node_id": node_id,
                "leave_mode": "hard",
                "mode": mode,
            }
        )
    return actions


def _string_list(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for item in raw:
        token = str(item or "").strip()
        if not token:
            continue
        out.append(token)
    return out


def _health_rank(health: str) -> int:
    normalized = str(health or "").strip().lower()
    if normalized == "healthy":
        return 3
    if normalized == "degraded":
        return 2
    if normalized == "offline":
        return 1
    return 0
