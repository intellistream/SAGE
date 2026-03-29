from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from sage.runtime.flownet.client.cluster_context import resolve_cluster_context


def resolve_cluster_target(
    *,
    entry_node: str | None = None,
    inventory: str | None = None,
    cluster: str | None = None,
    env: Mapping[str, str] | None = None,
    config_path: str | Path | None = None,
    clusters_dir: str | Path | None = None,
) -> dict[str, str]:
    try:
        resolved = resolve_cluster_context(
            mode="connect",
            entry_node=entry_node,
            inventory=inventory,
            cluster=cluster,
            env=env,
            config_path=config_path,
            clusters_dir=clusters_dir,
        )
    except RuntimeError as exc:
        message = str(exc)
        if message.startswith("cluster_target_unresolved:"):
            raise ValueError(
                "cluster target unresolved: " + message.split(":", 1)[1].strip()
            ) from exc
        if message.startswith("cluster_context_invalid:"):
            if "missing entry_node/inventory" in message:
                raise ValueError(
                    "cluster target unresolved: profile/config/env must define entry_node or inventory",
                ) from exc
            raise ValueError(
                "cluster context invalid: " + message.split(":", 1)[1].strip()
            ) from exc
        raise

    source_map = {
        "arg": "cli",
        "cluster": "cluster_flag",
        "env": "env",
        "default": "config",
        "local_runtime": "local_runtime",
    }
    source = source_map.get(resolved.resolved_by, resolved.resolved_by)
    return {
        "source": source,
        "entry_node": str(resolved.resolved_entry_node or ""),
        "inventory": str(resolved.resolved_inventory or ""),
        "cluster": str(resolved.cluster_name or ""),
    }


__all__ = ["resolve_cluster_target"]
