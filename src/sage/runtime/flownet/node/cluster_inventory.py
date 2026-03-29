from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sage.runtime.flownet.client import resolve_seed_addresses

try:
    import yaml
except Exception:  # pragma: no cover - dependency is optional at import time
    yaml = None


_BUILTIN_RESOURCE_KEYS = {"cpu", "memory_mb", "gpu", "gpu_mem_mb"}
_SUPPORTED_SEED_STRATEGIES = {"full-mesh"}


def normalize_resource_meta_key(resource_key: str) -> str:
    key = str(resource_key or "").strip()
    if not key:
        raise ValueError("resource key cannot be empty")
    if key in _BUILTIN_RESOURCE_KEYS:
        return key
    if key.startswith("res_"):
        return key
    return f"res_{key}"


def normalize_resource_metadata(raw_resources: Mapping[str, Any] | None) -> dict[str, str]:
    if raw_resources is None:
        return {}
    if not isinstance(raw_resources, Mapping):
        raise ValueError("resources must be mapping/object when provided")
    result: dict[str, str] = {}
    for key, value in raw_resources.items():
        normalized_key = normalize_resource_meta_key(str(key))
        normalized_value = _sanitize_meta_value(value)
        if not normalized_value:
            raise ValueError(f"resource value cannot be empty for key={key!r}")
        result[normalized_key] = normalized_value
    return result


def resolve_cluster_inventory(
    *,
    inventory_path: str | None = None,
    seed_strategy: str = "full-mesh",
    require_ssh_target: bool = False,
) -> dict[str, Any]:
    normalized_seed_strategy = _normalize_seed_strategy(seed_strategy)
    inventory_path = str(inventory_path or "").strip()
    if not inventory_path:
        raise ValueError("inventory input missing: set inventory_path")

    source = {"kind": "yaml", "path": str(Path(inventory_path).expanduser().resolve())}
    nodes, ssh_defaults = _parse_nodes_from_yaml(
        path=inventory_path,
        require_ssh_target=require_ssh_target,
    )

    if not nodes:
        raise ValueError("inventory.nodes must be non-empty")

    _assert_unique_nodes(nodes)
    bind_addresses = [str(node["bind_address"]) for node in nodes]

    resolved_nodes: list[dict[str, Any]] = []
    for idx, node in enumerate(nodes):
        explicit_seeds = tuple(str(item) for item in (node.get("seed_addresses") or ()))
        if explicit_seeds:
            resolved_seeds = list(explicit_seeds)
            seed_source = "explicit"
        else:
            if normalized_seed_strategy != "full-mesh":
                raise ValueError(f"unsupported seed strategy: {normalized_seed_strategy!r}")
            resolved_seeds = list(bind_addresses)
            seed_source = "derived_full_mesh"
        resolved_nodes.append(
            {
                "index": idx,
                "node_id": str(node["node_id"]),
                "ssh_target": str(node.get("ssh_target") or ""),
                "ssh_user": str(node.get("ssh_user") or ""),
                "ssh_identity_file": str(node.get("ssh_identity_file") or ""),
                "bind_address": str(node["bind_address"]),
                "seed_addresses": resolved_seeds,
                "seed_source": seed_source,
                "resource_metadata": dict(node.get("resource_metadata") or {}),
                "metadata": dict(node.get("metadata") or {}),
            }
        )

    return {
        "schema_version": "flownet.cluster.inventory.v1",
        "source": source,
        "seed_strategy": normalized_seed_strategy,
        "node_count": len(resolved_nodes),
        "bind_addresses": bind_addresses,
        "ssh": dict(ssh_defaults),
        "nodes": resolved_nodes,
    }


def build_inventory_snapshot_payload(
    *,
    plan: Mapping[str, Any],
    source_env_file: str,
    source_inventory_yaml: str | None = None,
    source_legacy_nodes: str | None = None,
    coordinator_runtime: Mapping[str, Any],
) -> dict[str, Any]:
    nodes_raw = plan.get("nodes")
    if not isinstance(nodes_raw, list) or not nodes_raw:
        raise ValueError("plan.nodes must be non-empty list")

    nodes: list[dict[str, Any]] = []
    for item in nodes_raw:
        if not isinstance(item, Mapping):
            continue
        nodes.append(
            {
                "index": int(item.get("index", len(nodes))),
                "node_id": str(item.get("node_id") or ""),
                "ssh_target": str(item.get("ssh_target") or ""),
                "bind_address": str(item.get("bind_address") or ""),
                "seed_addresses": [str(v) for v in (item.get("seed_addresses") or [])],
                "seed_source": str(item.get("seed_source") or ""),
                "resource_metadata": dict(item.get("resource_metadata") or {}),
                "metadata": dict(item.get("metadata") or {}),
            }
        )

    digest_payload = {"nodes": nodes, "coordinator_runtime": dict(coordinator_runtime)}
    inventory_sha256 = hashlib.sha256(
        json.dumps(
            digest_payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()

    return {
        "schema_version": "flownet.phase2_cluster_inventory_snapshot.v1",
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "source_env_file": source_env_file,
        "source_inventory_yaml": source_inventory_yaml or None,
        "source_nodes_raw": source_legacy_nodes or "",
        "node_count": len(nodes),
        "nodes": nodes,
        "coordinator_runtime": dict(coordinator_runtime),
        "inventory_sha256": inventory_sha256,
        "plan_schema_version": str(plan.get("schema_version") or ""),
        "plan_source": dict(plan.get("source") or {}),
        "seed_strategy": str(plan.get("seed_strategy") or ""),
    }


def format_cluster_plan_text(plan: Mapping[str, Any]) -> str:
    source = plan.get("source") if isinstance(plan.get("source"), Mapping) else {}
    source_kind = str((source or {}).get("kind") or "unknown")
    source_path = str((source or {}).get("path") or "")
    lines: list[str] = [
        "[cluster-plan]",
        f"source_kind={source_kind}",
        f"source_path={source_path or '-'}",
        f"seed_strategy={plan.get('seed_strategy')}",
        f"node_count={plan.get('node_count')}",
        "ssh_default_user="
        + (
            str(((plan.get("ssh") or {}).get("user")) or "-")
            if isinstance(plan.get("ssh"), Mapping)
            else "-"
        ),
    ]
    nodes = plan.get("nodes")
    if isinstance(nodes, list):
        for item in nodes:
            if not isinstance(item, Mapping):
                continue
            seeds = ",".join(str(seed) for seed in (item.get("seed_addresses") or []))
            lines.append(
                "node="
                f"{item.get('node_id')}|"
                f"target={item.get('ssh_target') or '-'}|"
                f"ssh_user={item.get('ssh_user') or '-'}|"
                f"bind={item.get('bind_address')}|"
                f"seed_source={item.get('seed_source')}|"
                f"seeds={seeds}"
            )
    return "\n".join(lines)


def _normalize_seed_strategy(seed_strategy: str) -> str:
    normalized = str(seed_strategy or "").strip().lower()
    if not normalized:
        normalized = "full-mesh"
    if normalized not in _SUPPORTED_SEED_STRATEGIES:
        supported = ",".join(sorted(_SUPPORTED_SEED_STRATEGIES))
        raise ValueError(f"unsupported seed strategy: {seed_strategy!r}; supported={supported}")
    return normalized


def _parse_nodes_from_yaml(
    *,
    path: str,
    require_ssh_target: bool,
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    if yaml is None:
        raise RuntimeError("PyYAML is required for yaml inventory parsing")
    inventory_path = Path(path).expanduser()
    if not inventory_path.exists():
        raise FileNotFoundError(f"inventory yaml not found: {inventory_path}")
    payload = yaml.safe_load(inventory_path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError("inventory yaml must deserialize to mapping/object")
    cluster_raw = payload.get("cluster")
    cluster_mapping = cluster_raw if isinstance(cluster_raw, Mapping) else {}
    ssh_defaults = _parse_inventory_ssh_defaults(payload, cluster_mapping)

    nodes_raw = payload.get("nodes")
    if nodes_raw is None:
        nodes_raw = cluster_mapping.get("nodes")
    if not isinstance(nodes_raw, list) or not nodes_raw:
        raise ValueError("inventory.nodes must be non-empty list")

    nodes: list[dict[str, Any]] = []
    for idx, item in enumerate(nodes_raw):
        if not isinstance(item, Mapping):
            raise ValueError(f"inventory.nodes[{idx}] must be mapping/object")
        node_id = _pick_text(item, "node_id", "id", "name")
        bind_address = _pick_text(item, "bind_address", "bind", "address")
        ssh_target = _pick_text(item, "ssh_target", "ssh", "target", "host")
        if not node_id:
            raise ValueError(f"inventory.nodes[{idx}] missing node_id")
        if not bind_address:
            raise ValueError(f"inventory.nodes[{idx}] missing bind_address")
        if require_ssh_target and not ssh_target:
            raise ValueError(
                f"inventory.nodes[{idx}] missing ssh_target (required by this command)"
            )
        raw_resources = item.get("resources")
        if raw_resources is not None and not isinstance(raw_resources, Mapping):
            raise ValueError(f"inventory.nodes[{idx}].resources must be mapping/object")
        ssh_user = _pick_text(item, "ssh_user", "user")
        if not ssh_user:
            ssh_user = ssh_defaults.get("user", "")
        ssh_identity_file = _pick_text(
            item,
            "ssh_identity_file",
            "identity_file",
            "identity",
        )
        if not ssh_identity_file:
            ssh_identity_file = ssh_defaults.get("identity_file", "")
        node = {
            "node_id": node_id,
            "ssh_target": ssh_target,
            "ssh_user": ssh_user,
            "ssh_identity_file": ssh_identity_file,
            "bind_address": bind_address,
            "seed_addresses": _extract_seed_addresses(
                item.get("seeds", item.get("seed_addresses", item.get("seed_csv")))
            ),
            "resource_metadata": normalize_resource_metadata(
                raw_resources if isinstance(raw_resources, Mapping) else None
            ),
            "metadata": _normalize_metadata(item),
        }
        nodes.append(node)
    return nodes, ssh_defaults


def _pick_text(row: Mapping[str, Any], *keys: str) -> str:
    for key in keys:
        value = row.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def _parse_inventory_ssh_defaults(
    payload: Mapping[str, Any],
    cluster_mapping: Mapping[str, Any],
) -> dict[str, str]:
    ssh_mapping = payload.get("ssh")
    if not isinstance(ssh_mapping, Mapping):
        ssh_mapping = cluster_mapping.get("ssh")
    if not isinstance(ssh_mapping, Mapping):
        return {}
    return {
        "user": _pick_text(ssh_mapping, "user", "ssh_user"),
        "identity_file": _pick_text(
            ssh_mapping,
            "identity_file",
            "ssh_identity_file",
            "identity",
        ),
    }


def _extract_seed_addresses(raw: Any) -> tuple[str, ...]:
    if raw is None:
        return ()
    try:
        resolved = resolve_seed_addresses(raw)
    except Exception as exc:
        raise ValueError(f"invalid seed addresses: {raw!r}") from exc
    out: list[str] = []
    seen: set[str] = set()
    for item in resolved:
        token = str(item or "").strip()
        if not token or token in seen:
            continue
        seen.add(token)
        out.append(token)
    return tuple(out)


def _normalize_metadata(node: Mapping[str, Any]) -> dict[str, str]:
    metadata: dict[str, str] = {}
    raw_metadata = node.get("metadata")
    if isinstance(raw_metadata, Mapping):
        for raw_key, raw_value in raw_metadata.items():
            key = str(raw_key or "").strip()
            if not key:
                continue
            value = _sanitize_meta_value(raw_value)
            if not value:
                continue
            metadata[key] = value

    zone = _pick_text(node, "zone")
    region = _pick_text(node, "region")
    labels = node.get("labels")
    if isinstance(labels, Mapping):
        if not zone:
            zone = _pick_text(labels, "zone")
        if not region:
            region = _pick_text(labels, "region")
    if zone:
        metadata["zone"] = _sanitize_meta_value(zone)
    if region:
        metadata["region"] = _sanitize_meta_value(region)
    return metadata


def _sanitize_meta_value(value: Any) -> str:
    return str(value).strip().replace("|", "_").replace(",", "_")


def _assert_unique_nodes(nodes: list[dict[str, Any]]) -> None:
    seen_node_ids: set[str] = set()
    seen_bind_addresses: set[str] = set()
    for item in nodes:
        node_id = str(item["node_id"])
        bind_address = str(item["bind_address"])
        if node_id in seen_node_ids:
            raise ValueError(f"duplicate node_id: {node_id}")
        if bind_address in seen_bind_addresses:
            raise ValueError(f"duplicate bind_address: {bind_address}")
        seen_node_ids.add(node_id)
        seen_bind_addresses.add(bind_address)
