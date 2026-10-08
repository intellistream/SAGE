from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import yaml
except Exception:  # pragma: no cover - optional dependency during import
    yaml = None

_DEFAULT_CLUSTER_PORT = 18787
_DEFAULT_LOCAL_RUNTIME_ENTRY = "127.0.0.1:18787"


@dataclass(frozen=True)
class ResolvedClusterContext:
    resolved_entry_node: str | None
    resolved_by: str
    cluster_name: str | None
    transport_mode: str | None
    timeouts: dict[str, float | None] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    resolved_inventory: str | None = None


def resolve_cluster_context(
    *,
    mode: str = "connect",
    entry_node: str | None = None,
    node_address: str | None = None,
    inventory: str | None = None,
    cluster: str | None = None,
    env: Mapping[str, str] | None = None,
    config_path: str | Path | None = None,
    clusters_dir: str | Path | None = None,
    default_local_entry_node: str = _DEFAULT_LOCAL_RUNTIME_ENTRY,
    transport_mode: str | None = None,
    connect_timeout: float | None = None,
) -> ResolvedClusterContext:
    normalized_mode = _normalize_mode(mode)
    normalized_timeout = _normalize_optional_non_negative_float(
        connect_timeout,
        field_name="connect_timeout",
    )
    normalized_transport_mode = _normalize_optional_non_empty(transport_mode)
    explicit_entry = _normalize_optional_address(
        entry_node if entry_node is not None else node_address,
        field_name="entry_node",
    )
    explicit_inventory = _normalize_optional_inventory(inventory)

    if normalized_mode == "local_runtime":
        resolved_entry = explicit_entry or _normalize_address(
            default_local_entry_node,
            field_name="default_local_entry_node",
        )
        return ResolvedClusterContext(
            resolved_entry_node=resolved_entry,
            resolved_by="local_runtime",
            cluster_name=None,
            transport_mode=normalized_transport_mode,
            timeouts={"connect_timeout": normalized_timeout},
            metadata={"mode": "local_runtime"},
            resolved_inventory=None,
        )

    if explicit_entry is not None or explicit_inventory is not None:
        return ResolvedClusterContext(
            resolved_entry_node=explicit_entry,
            resolved_by="arg",
            cluster_name=None,
            transport_mode=normalized_transport_mode,
            timeouts={"connect_timeout": normalized_timeout},
            metadata={},
            resolved_inventory=explicit_inventory,
        )

    runtime_env = os.environ if env is None else env
    cluster_name = _normalize_optional_non_empty(cluster)
    resolved_by = "cluster"
    if cluster_name is None:
        cluster_name = _normalize_optional_non_empty(runtime_env.get("FLOWNET_CLUSTER"))
        resolved_by = "env"
    if cluster_name is None:
        cluster_name = _read_default_cluster_name(config_path=config_path)
        resolved_by = "default"
    if cluster_name is None:
        raise RuntimeError(
            "cluster_target_unresolved:"
            " provide entry_node=... or cluster=..., or set FLOWNET_CLUSTER / ~/.flownet/config.yaml",
        )

    payload, profile_path = _load_cluster_profile(
        cluster_name=cluster_name,
        clusters_dir=clusters_dir,
    )
    entry_payload = _resolve_profile_entry_node(payload)
    resolved_inventory = _resolve_profile_inventory(payload, profile_path)
    if entry_payload is None and resolved_inventory is None:
        raise RuntimeError(
            "cluster_context_invalid:"
            f" cluster profile missing entry_node/inventory: cluster={cluster_name}"
            f" path={profile_path}",
        )
    return ResolvedClusterContext(
        resolved_entry_node=entry_payload["entry_node"] if entry_payload is not None else None,
        resolved_by=resolved_by,
        cluster_name=cluster_name,
        transport_mode=normalized_transport_mode,
        timeouts={"connect_timeout": normalized_timeout},
        metadata={
            "profile_path": str(profile_path),
            "selected_node_id": (
                entry_payload.get("selected_node_id") if entry_payload is not None else None
            ),
        },
        resolved_inventory=resolved_inventory,
    )


def _normalize_mode(raw_mode: str) -> str:
    token = _normalize_optional_non_empty(raw_mode) or "connect"
    lowered = token.lower()
    if lowered in {"connect", "remote"}:
        return "connect"
    if lowered in {"local_runtime", "local_backend", "local"}:
        return "local_runtime"
    raise ValueError("mode must be one of: connect, local_runtime, local_backend, local.")


def _read_default_cluster_name(*, config_path: str | Path | None) -> str | None:
    if yaml is None:
        raise RuntimeError(
            "cluster_context_invalid: PyYAML is required for cluster context resolution"
        )
    resolved_path = (
        Path(config_path).expanduser()
        if config_path is not None
        else Path("~/.flownet/config.yaml").expanduser()
    )
    if not resolved_path.exists():
        return None
    payload = yaml.safe_load(resolved_path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        return None
    direct = _normalize_optional_non_empty(
        payload.get("current_cluster") or payload.get("cluster"),
    )
    if direct is not None:
        return direct
    context = payload.get("context")
    if isinstance(context, Mapping):
        return _normalize_optional_non_empty(
            context.get("current_cluster") or context.get("cluster"),
        )
    return None


def _load_cluster_profile(
    *,
    cluster_name: str,
    clusters_dir: str | Path | None,
) -> tuple[Mapping[str, Any], Path]:
    if yaml is None:
        raise RuntimeError(
            "cluster_context_invalid: PyYAML is required for cluster context resolution"
        )
    base = (
        Path(clusters_dir).expanduser()
        if clusters_dir is not None
        else Path("~/.flownet/clusters").expanduser()
    )
    profile_path = base / f"{cluster_name}.yaml"
    if not profile_path.exists():
        raise RuntimeError(
            "cluster_context_invalid:"
            f" cluster profile not found: cluster={cluster_name} path={profile_path}",
        )
    payload = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise RuntimeError(
            f"cluster_context_invalid: cluster profile must be mapping/object: path={profile_path}",
        )
    return payload, profile_path


def _resolve_profile_entry_node(payload: Mapping[str, Any]) -> dict[str, str] | None:
    target = payload.get("target")
    target_mapping = target if isinstance(target, Mapping) else {}

    preferred_entry = _pick_text(payload, target_mapping, "preferred_entry")
    if preferred_entry is not None:
        return {
            "entry_node": _normalize_address(preferred_entry, field_name="preferred_entry"),
            "selected_node_id": "",
        }

    direct_entry = _pick_text(payload, target_mapping, "entry_node", "entry", "node_address")
    if direct_entry is not None:
        return {
            "entry_node": _normalize_address(direct_entry, field_name="entry_node"),
            "selected_node_id": "",
        }

    selected = _select_healthy_node(payload, target_mapping)
    if selected is None:
        return None
    return selected


def _resolve_profile_inventory(payload: Mapping[str, Any], profile_path: Path) -> str | None:
    target = payload.get("target")
    target_mapping = target if isinstance(target, Mapping) else {}
    raw_inventory = _pick_text(payload, target_mapping, "inventory", "inventory_path")
    if raw_inventory is None:
        return None
    candidate = Path(raw_inventory).expanduser()
    if not candidate.is_absolute():
        candidate = (profile_path.parent / candidate).resolve()
    return str(candidate)


def _select_healthy_node(
    payload: Mapping[str, Any],
    target: Mapping[str, Any],
) -> dict[str, str] | None:
    raw_nodes = payload.get("nodes")
    if not isinstance(raw_nodes, list):
        raw_nodes = target.get("nodes")
    if not isinstance(raw_nodes, list):
        return None

    candidates: list[tuple[str, str, str]] = []
    for item in raw_nodes:
        if not isinstance(item, Mapping):
            continue
        address = _pick_text(item, {}, "entry_node", "address", "node_address", "addr")
        if address is None:
            continue
        health = _normalize_optional_non_empty(item.get("health") or item.get("status"))
        if health is not None and health.lower() not in {"healthy", "ready", "online", "up"}:
            continue
        node_id = (
            _normalize_optional_non_empty(item.get("node_id") or item.get("id") or item.get("name"))
            or ""
        )
        normalized_address = _normalize_address(address, field_name="node_address")
        sort_key = node_id or normalized_address
        candidates.append((sort_key, normalized_address, node_id))

    if not candidates:
        return None
    candidates.sort(key=lambda item: (item[0], item[1]))
    _, address, node_id = candidates[0]
    return {"entry_node": address, "selected_node_id": node_id}


def _pick_text(
    payload: Mapping[str, Any],
    nested: Mapping[str, Any],
    *keys: str,
) -> str | None:
    for key in keys:
        value = payload.get(key)
        normalized = _normalize_optional_non_empty(value)
        if normalized is not None:
            return normalized
        value = nested.get(key)
        normalized = _normalize_optional_non_empty(value)
        if normalized is not None:
            return normalized
    return None


def _normalize_address(raw_value: Any, *, field_name: str) -> str:
    normalized = _normalize_optional_non_empty(raw_value)
    if normalized is None:
        raise ValueError(f"{field_name} must be non-empty.")
    if ":" in normalized:
        host, _, port_raw = normalized.rpartition(":")
        if not host.strip():
            raise ValueError(f"{field_name} host must be non-empty.")
        try:
            port = int(port_raw)
        except Exception as exc:
            raise ValueError(f"{field_name} port must be an integer.") from exc
        if port <= 0:
            raise ValueError(f"{field_name} port must be positive.")
        return f"{host}:{port}"
    return f"{normalized}:{_DEFAULT_CLUSTER_PORT}"


def _normalize_optional_address(raw_value: Any, *, field_name: str) -> str | None:
    normalized = _normalize_optional_non_empty(raw_value)
    if normalized is None:
        return None
    return _normalize_address(normalized, field_name=field_name)


def _normalize_optional_inventory(raw_value: Any) -> str | None:
    normalized = _normalize_optional_non_empty(raw_value)
    if normalized is None:
        return None
    return str(Path(normalized).expanduser().resolve())


def _normalize_optional_non_empty(raw_value: Any) -> str | None:
    if raw_value is None:
        return None
    normalized = str(raw_value).strip()
    return normalized or None


def _normalize_optional_non_negative_float(raw_value: Any, *, field_name: str) -> float | None:
    if raw_value is None:
        return None
    normalized = float(raw_value)
    if normalized < 0:
        raise ValueError(f"{field_name} must be >= 0 when provided.")
    return normalized


__all__ = [
    "ResolvedClusterContext",
    "resolve_cluster_context",
]
