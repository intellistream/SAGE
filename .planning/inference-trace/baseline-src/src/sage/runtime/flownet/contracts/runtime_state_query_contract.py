from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def build_runtime_state_query_request(
    namespace: str,
    *,
    prefix: str,
    principal: str,
    roles: list[str] | tuple[str, ...] | set[str] | str | None = None,
    allowed_namespaces: list[str] | tuple[str, ...] | set[str] | str | None = None,
    permissions: list[str] | tuple[str, ...] | set[str] | str | None = None,
    limit: int | None = None,
    cursor: int | str | None = None,
    include_values: bool = True,
    reveal_values: bool = False,
) -> dict[str, Any]:
    return {
        "namespace": _normalize_non_empty_string(namespace, field_name="namespace"),
        "prefix": _normalize_non_empty_string(prefix, field_name="prefix"),
        "principal": _normalize_non_empty_string(principal, field_name="principal"),
        "roles": roles,
        "allowed_namespaces": allowed_namespaces,
        "permissions": permissions,
        "limit": limit,
        "cursor": cursor,
        "include_values": bool(include_values),
        "reveal_values": bool(reveal_values),
    }


def normalize_runtime_state_query_response(payload: Any) -> Any:
    if not isinstance(payload, Mapping):
        return payload
    normalized = dict(payload)
    items = normalized.get("items")
    if isinstance(items, tuple):
        normalized["items"] = list(items)
    return normalized


def _normalize_non_empty_string(raw_value: Any, *, field_name: str) -> str:
    normalized = str(raw_value or "").strip()
    if not normalized:
        raise ValueError(f"{field_name} must be a non-empty string.")
    return normalized


__all__ = [
    "build_runtime_state_query_request",
    "normalize_runtime_state_query_response",
]
