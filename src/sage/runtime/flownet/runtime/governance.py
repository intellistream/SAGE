from __future__ import annotations

import time
from collections import deque
from collections.abc import Mapping, Sequence
from threading import RLock
from typing import Any

_DEFAULT_QUOTA_WINDOW_MS = 60_000
_AUDIT_MAXLEN = 2048


class GovernanceDeniedError(PermissionError):
    def __init__(
        self,
        *,
        error_prefix: str,
        reason_code: str,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        self.reason_code = _normalize_non_empty(reason_code, field_name="reason_code")
        self.details = dict(details or {})
        super().__init__(f"{error_prefix}:{self.reason_code}")


class GovernanceQuotaExceededError(RuntimeError):
    def __init__(
        self,
        *,
        error_prefix: str,
        reason_code: str = "quota_exceeded",
        details: Mapping[str, Any] | None = None,
    ) -> None:
        self.reason_code = _normalize_non_empty(reason_code, field_name="reason_code")
        self.details = dict(details or {})
        super().__init__(f"{error_prefix}:{self.reason_code}")


class RuntimeGovernanceManager:
    def __init__(self, *, audit_maxlen: int = _AUDIT_MAXLEN) -> None:
        self._lock = RLock()
        self._audit: deque[dict[str, Any]] = deque(maxlen=max(16, int(audit_maxlen)))
        self._windows: dict[str, deque[int]] = {}
        self._claim_to_scope: dict[str, str] = {}
        self._claims_by_scope: dict[str, set[str]] = {}
        self._reason_totals: dict[str, int] = {}
        self._stats: dict[str, Any] = {
            "admission_total": 0,
            "allow_total": 0,
            "deny_total": 0,
            "quota_hit_total": 0,
            "active_claims": 0,
            "endpoint_admission_total": 0,
            "shared_state_admission_total": 0,
            "last_reason_code": None,
        }

    def audit_snapshot(self) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(record) for record in self._audit]

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            stats = dict(self._stats)
            reason_totals = dict(self._reason_totals)
        return {
            "admission_total": int(stats.get("admission_total", 0)),
            "allow_total": int(stats.get("allow_total", 0)),
            "deny_total": int(stats.get("deny_total", 0)),
            "quota_hit_total": int(stats.get("quota_hit_total", 0)),
            "active_claims": int(stats.get("active_claims", 0)),
            "endpoint_admission_total": int(stats.get("endpoint_admission_total", 0)),
            "shared_state_admission_total": int(stats.get("shared_state_admission_total", 0)),
            "last_reason_code": _normalize_optional_non_empty(stats.get("last_reason_code")),
            "reason_totals": reason_totals,
            "audit_entries": len(self._audit),
        }

    def active_claim_count(self, *, scope: str | None = None) -> int:
        with self._lock:
            if scope is None:
                return len(self._claim_to_scope)
            return len(self._claims_by_scope.get(scope, set()))

    def start_claim(self, *, claim_key: str, scope: str) -> bool:
        normalized_claim_key = _normalize_non_empty(claim_key, field_name="claim_key")
        normalized_scope = _normalize_non_empty(scope, field_name="scope")
        with self._lock:
            existing_scope = self._claim_to_scope.get(normalized_claim_key)
            if existing_scope == normalized_scope:
                return False
            if existing_scope is not None:
                previous_scope_claims = self._claims_by_scope.get(existing_scope)
                if previous_scope_claims is not None:
                    previous_scope_claims.discard(normalized_claim_key)
                    if not previous_scope_claims:
                        self._claims_by_scope.pop(existing_scope, None)
            claims = self._claims_by_scope.setdefault(normalized_scope, set())
            claims.add(normalized_claim_key)
            self._claim_to_scope[normalized_claim_key] = normalized_scope
            self._stats["active_claims"] = len(self._claim_to_scope)
            return True

    def release_claim(self, claim_key: str) -> bool:
        normalized_claim_key = _normalize_non_empty(claim_key, field_name="claim_key")
        with self._lock:
            scope = self._claim_to_scope.pop(normalized_claim_key, None)
            if scope is None:
                return False
            claims = self._claims_by_scope.get(scope)
            if claims is not None:
                claims.discard(normalized_claim_key)
                if not claims:
                    self._claims_by_scope.pop(scope, None)
            self._stats["active_claims"] = len(self._claim_to_scope)
            return True

    def allow_window(
        self,
        *,
        scope: str,
        limit: int,
        window_ms: int,
        now_ms: int | None = None,
    ) -> tuple[bool, int]:
        normalized_scope = _normalize_non_empty(scope, field_name="scope")
        normalized_limit = _normalize_positive_int(limit, field_name="limit")
        normalized_window_ms = _normalize_positive_int(window_ms, field_name="window_ms")
        observed_at = _now_ms() if now_ms is None else int(now_ms)
        with self._lock:
            window = self._windows.setdefault(normalized_scope, deque())
            floor_ms = observed_at - normalized_window_ms
            while window and int(window[0]) < floor_ms:
                window.popleft()
            if len(window) >= normalized_limit:
                return False, len(window)
            window.append(observed_at)
            return True, len(window)

    def record_decision(
        self,
        *,
        resource_kind: str,
        resource_id: str,
        namespace: str,
        principal: str,
        tenant: str | None,
        allowed: bool,
        reason_code: str,
        resource_name: str | None = None,
        operation: str | None = None,
        request_id: str | None = None,
        flow_instance_id: str | None = None,
        contract_id: str | None = None,
        claim_key: str | None = None,
        quota_name: str | None = None,
        quota_limit: int | None = None,
        quota_value: int | None = None,
        details: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        normalized_reason_code = _normalize_non_empty(reason_code, field_name="reason_code")
        record = {
            "at_ms": _now_ms(),
            "resource_kind": _normalize_non_empty(resource_kind, field_name="resource_kind"),
            "resource_id": _normalize_non_empty(resource_id, field_name="resource_id"),
            "resource_name": _normalize_optional_non_empty(resource_name),
            "operation": _normalize_optional_non_empty(operation),
            "namespace": _normalize_non_empty(namespace, field_name="namespace"),
            "principal": _normalize_non_empty(principal, field_name="principal"),
            "tenant": _normalize_optional_non_empty(tenant),
            "allowed": bool(allowed),
            "reason_code": normalized_reason_code,
            "request_id": _normalize_optional_non_empty(request_id),
            "flow_instance_id": _normalize_optional_non_empty(flow_instance_id),
            "contract_id": _normalize_optional_non_empty(contract_id),
            "claim_key": _normalize_optional_non_empty(claim_key),
            "quota_name": _normalize_optional_non_empty(quota_name),
            "quota_limit": (
                _normalize_positive_int(quota_limit, field_name="quota_limit")
                if quota_limit is not None
                else None
            ),
            "quota_value": (
                _normalize_non_negative_int(quota_value, field_name="quota_value")
                if quota_value is not None
                else None
            ),
            "details": dict(details or {}),
        }
        with self._lock:
            self._stats["admission_total"] = int(self._stats.get("admission_total", 0)) + 1
            if record["resource_kind"] == "endpoint":
                self._stats["endpoint_admission_total"] = (
                    int(self._stats.get("endpoint_admission_total", 0)) + 1
                )
            if record["resource_kind"] == "shared_state":
                self._stats["shared_state_admission_total"] = (
                    int(self._stats.get("shared_state_admission_total", 0)) + 1
                )
            if allowed:
                self._stats["allow_total"] = int(self._stats.get("allow_total", 0)) + 1
            else:
                self._stats["deny_total"] = int(self._stats.get("deny_total", 0)) + 1
                if normalized_reason_code == "quota_exceeded":
                    self._stats["quota_hit_total"] = int(self._stats.get("quota_hit_total", 0)) + 1
            self._stats["last_reason_code"] = normalized_reason_code
            self._reason_totals[normalized_reason_code] = (
                int(self._reason_totals.get(normalized_reason_code, 0)) + 1
            )
            self._audit.append(record)
        return record


def normalize_runtime_admission_policy(raw_value: Any) -> dict[str, Any]:
    raw = dict(raw_value) if isinstance(raw_value, Mapping) else {}
    quota_raw = raw.get("quota")
    quota = dict(quota_raw) if isinstance(quota_raw, Mapping) else {}
    return {
        "principal": _normalize_optional_non_empty(raw.get("principal")),
        "allowed_principals": _normalize_optional_str_list(raw.get("allowed_principals")),
        "tenant": _normalize_optional_non_empty(raw.get("tenant")),
        "allowed_tenants": _normalize_optional_str_list(raw.get("allowed_tenants")),
        "allowed_namespaces": _normalize_optional_str_list(raw.get("allowed_namespaces")),
        "quota": {
            "max_requests_per_window": _normalize_optional_positive_int(
                quota.get("max_requests_per_window")
            ),
            "window_ms": _normalize_optional_positive_int(quota.get("window_ms"))
            or _DEFAULT_QUOTA_WINDOW_MS,
            "max_concurrent": _normalize_optional_positive_int(quota.get("max_concurrent")),
            "max_concurrent_claims": _normalize_optional_positive_int(
                quota.get("max_concurrent_claims", quota.get("max_concurrent"))
            ),
        },
    }


def resolve_runtime_governance_identity(
    tags: Mapping[str, Any] | None,
    *,
    default_principal: str,
    default_tenant: str | None = None,
) -> dict[str, str | None]:
    normalized_tags = dict(tags or {})
    principal = _first_non_empty(
        normalized_tags.get("principal"),
        normalized_tags.get("x-sage-principal"),
        default_principal,
    )
    tenant = _first_non_empty(
        normalized_tags.get("tenant"),
        normalized_tags.get("x-sage-tenant"),
        default_tenant,
    )
    return {
        "principal": _normalize_non_empty(principal, field_name="principal"),
        "tenant": _normalize_optional_non_empty(tenant),
    }


def evaluate_runtime_admission_policy(
    policy: Mapping[str, Any] | None,
    *,
    principal: str,
    tenant: str | None,
    namespace: str,
) -> str:
    normalized_policy = normalize_runtime_admission_policy(policy)
    normalized_principal = _normalize_non_empty(principal, field_name="principal")
    normalized_namespace = _normalize_non_empty(namespace, field_name="namespace")
    normalized_tenant = _normalize_optional_non_empty(tenant)

    required_principal = normalized_policy.get("principal")
    if required_principal is not None and normalized_principal != required_principal:
        return "principal_mismatch"

    allowed_principals = list(normalized_policy.get("allowed_principals") or ())
    if allowed_principals and normalized_principal not in allowed_principals:
        return "principal_forbidden"

    required_tenant = normalized_policy.get("tenant")
    if required_tenant is not None and normalized_tenant != required_tenant:
        return "tenant_mismatch"

    allowed_tenants = list(normalized_policy.get("allowed_tenants") or ())
    if allowed_tenants and normalized_tenant not in allowed_tenants:
        return "tenant_forbidden"

    allowed_namespaces = list(normalized_policy.get("allowed_namespaces") or ())
    if allowed_namespaces and not _namespace_allowed(normalized_namespace, allowed_namespaces):
        return "namespace_forbidden"

    return "ok"


def _namespace_allowed(namespace: str, allowed_namespaces: Sequence[str]) -> bool:
    normalized_namespace = _normalize_non_empty(namespace, field_name="namespace")
    for raw_pattern in allowed_namespaces:
        pattern = _normalize_optional_non_empty(raw_pattern)
        if pattern is None:
            continue
        if pattern == "*":
            return True
        if pattern.endswith(".*"):
            prefix = pattern[:-2]
            if normalized_namespace == prefix or normalized_namespace.startswith(f"{prefix}."):
                return True
            continue
        if normalized_namespace == pattern:
            return True
    return False


def _first_non_empty(*values: Any) -> str | None:
    for value in values:
        normalized = _normalize_optional_non_empty(value)
        if normalized is not None:
            return normalized
    return None


def _normalize_optional_str_list(raw_value: Any) -> list[str]:
    if raw_value is None:
        return []
    if isinstance(raw_value, str):
        normalized = _normalize_optional_non_empty(raw_value)
        return [normalized] if normalized is not None else []
    if not isinstance(raw_value, Sequence) or isinstance(raw_value, (bytes, bytearray)):
        raise TypeError("admission policy list fields must be a string or sequence of strings.")
    normalized: list[str] = []
    seen: set[str] = set()
    for item in raw_value:
        value = _normalize_optional_non_empty(item)
        if value is None or value in seen:
            continue
        seen.add(value)
        normalized.append(value)
    return normalized


def _normalize_optional_positive_int(raw_value: Any) -> int | None:
    if raw_value is None:
        return None
    return _normalize_positive_int(raw_value, field_name="value")


def _normalize_positive_int(raw_value: Any, *, field_name: str) -> int:
    try:
        normalized = int(raw_value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a positive integer.") from exc
    if normalized <= 0:
        raise ValueError(f"{field_name} must be a positive integer.")
    return normalized


def _normalize_non_negative_int(raw_value: Any, *, field_name: str) -> int:
    try:
        normalized = int(raw_value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a non-negative integer.") from exc
    if normalized < 0:
        raise ValueError(f"{field_name} must be a non-negative integer.")
    return normalized


def _normalize_non_empty(raw_value: Any, *, field_name: str) -> str:
    normalized = str(raw_value or "").strip()
    if not normalized:
        raise ValueError(f"{field_name} must be non-empty.")
    return normalized


def _normalize_optional_non_empty(raw_value: Any) -> str | None:
    if raw_value is None:
        return None
    normalized = str(raw_value).strip()
    if not normalized:
        return None
    return normalized


def _now_ms() -> int:
    return int(time.time() * 1000)


__all__ = [
    "GovernanceDeniedError",
    "GovernanceQuotaExceededError",
    "RuntimeGovernanceManager",
    "evaluate_runtime_admission_policy",
    "normalize_runtime_admission_policy",
    "resolve_runtime_governance_identity",
]
