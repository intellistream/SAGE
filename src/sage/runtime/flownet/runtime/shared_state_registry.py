from __future__ import annotations

import time
from dataclasses import dataclass, field, replace
from threading import RLock
from typing import Any

from sage.runtime.flownet.contracts.recovery_contract import (
    RecoveryStatusSummary,
    build_initial_recovery_summary,
    build_recovery_failure_summary,
    build_recovery_success_summary,
    normalize_recovery_status_summary,
    require_checkpoint_restore_support,
    restore_checkpoint_state,
    snapshot_checkpoint_state,
)
from sage.runtime.flownet.contracts.shared_state_contract import (
    SharedStateBindingSpec,
    SharedStateServiceDescriptor,
    normalize_shared_state_binding_spec,
    normalize_shared_state_service_descriptor,
)
from sage.runtime.flownet.runtime.governance import (
    GovernanceDeniedError,
    GovernanceQuotaExceededError,
    RuntimeGovernanceManager,
    evaluate_runtime_admission_policy,
    normalize_runtime_admission_policy,
)


@dataclass(frozen=True)
class SharedStateServiceRecord:
    descriptor: SharedStateServiceDescriptor
    service_object: Any
    declaration: Any | None = None
    source_kind: str = "service"
    service_uri: str | None = None
    source_instance_id: str | None = None
    factory: Any | None = None
    factory_args: tuple[Any, ...] = ()
    factory_kwargs: dict[str, Any] = field(default_factory=dict)
    recovery_summary: RecoveryStatusSummary = field(default_factory=build_initial_recovery_summary)
    service_revision: int = 1
    created_at_epoch_ms: int = field(default_factory=lambda: int(time.time() * 1000))

    @property
    def contract_id(self) -> str:
        return self.descriptor.contract_id

    def snapshot(self) -> dict[str, Any]:
        return {
            "contract_id": self.descriptor.contract_id,
            "service_name": self.descriptor.service_name,
            "namespace": self.descriptor.namespace,
            "owner": self.descriptor.owner,
            "visibility": self.descriptor.visibility,
            "reuse_policy": self.descriptor.reuse_policy,
            "recovery_policy": self.descriptor.recovery_policy,
            "binding_metadata": dict(self.descriptor.binding_metadata),
            "service_uri": self.service_uri,
            "source_kind": self.source_kind,
            "source_instance_id": self.source_instance_id,
            "created_at_epoch_ms": int(self.created_at_epoch_ms),
            "service_revision": int(self.service_revision),
            "recovery_summary": self.recovery_summary.to_dict(),
            "object_type": type(self.service_object).__name__,
        }


class SharedStateServiceRegistry:
    def __init__(self) -> None:
        self._records: dict[str, SharedStateServiceRecord] = {}
        self._flow_claims: dict[str, set[str]] = {}
        self._governance_manager: RuntimeGovernanceManager | None = None
        self._lock = RLock()

    def set_governance_manager(self, governance_manager: RuntimeGovernanceManager | None) -> None:
        with self._lock:
            self._governance_manager = governance_manager

    def register_service(
        self,
        *,
        descriptor: SharedStateServiceDescriptor | dict[str, Any],
        service_object: Any,
        declaration: Any | None = None,
        source_kind: str = "service",
        service_uri: str | None = None,
        source_instance_id: str | None = None,
        factory: Any | None = None,
        factory_args: tuple[Any, ...] = (),
        factory_kwargs: dict[str, Any] | None = None,
        recovery_summary: RecoveryStatusSummary | dict[str, Any] | None = None,
    ) -> SharedStateServiceRecord:
        resolved_descriptor = normalize_shared_state_service_descriptor(descriptor)
        if service_object is None:
            raise TypeError("service_object must not be None.")
        resolved_source_kind = str(source_kind or "service").strip() or "service"
        resolved_service_uri = _normalize_optional_non_empty(service_uri)
        resolved_source_instance_id = _normalize_optional_non_empty(source_instance_id)
        resolved_factory_kwargs = _normalize_mapping(factory_kwargs, field_name="factory_kwargs")
        resolved_recovery_summary = normalize_recovery_status_summary(recovery_summary)

        with self._lock:
            if resolved_descriptor.contract_id in self._records:
                raise ValueError(
                    "shared_state_descriptor_already_registered:"
                    f"{resolved_descriptor.contract_id}"
                )
            record = SharedStateServiceRecord(
                descriptor=resolved_descriptor,
                service_object=service_object,
                declaration=declaration,
                source_kind=resolved_source_kind,
                service_uri=resolved_service_uri,
                source_instance_id=resolved_source_instance_id,
                factory=factory,
                factory_args=tuple(factory_args),
                factory_kwargs=resolved_factory_kwargs,
                recovery_summary=resolved_recovery_summary,
            )
            self._records[resolved_descriptor.contract_id] = record
            return record

    def recover_service(
        self,
        descriptor_or_contract_id: Any,
        *,
        reason: str = "manual_recovery",
    ) -> SharedStateServiceRecord:
        contract_id = self._resolve_contract_id(descriptor_or_contract_id)
        normalized_reason = _normalize_optional_non_empty(reason) or "manual_recovery"
        updated_at_epoch_ms = int(time.time() * 1000)

        with self._lock:
            record = self._records.get(contract_id)
            if record is None:
                raise ValueError(f"shared_state_descriptor_not_registered:{contract_id}")
            factory = record.factory
            if not callable(factory):
                raise RuntimeError(
                    f"shared_state_recovery_factory_missing:contract_id={contract_id}"
                )

            if record.descriptor.recovery_policy == "checkpoint_restore":
                checkpoint_details = {
                    "contract_id": contract_id,
                    "service_name": record.descriptor.service_name,
                }
                try:
                    require_checkpoint_restore_support(
                        record.service_object,
                        error_prefix="shared_state_checkpoint_restore_not_supported",
                        details=checkpoint_details,
                    )
                    snapshot = snapshot_checkpoint_state(record.service_object)
                    recovered_object = factory(*record.factory_args, **record.factory_kwargs)
                    require_checkpoint_restore_support(
                        recovered_object,
                        error_prefix="shared_state_checkpoint_restore_not_supported",
                        details=checkpoint_details,
                    )
                    restore_checkpoint_state(recovered_object, snapshot)
                except Exception as exc:
                    failure_summary = build_recovery_failure_summary(
                        action="checkpoint_restore",
                        error=exc,
                        updated_at_epoch_ms=updated_at_epoch_ms,
                        metadata={
                            "contract_id": contract_id,
                            "reason": normalized_reason,
                            "service_revision": int(record.service_revision),
                        },
                    )
                    failed_record = replace(record, recovery_summary=failure_summary)
                    self._records[contract_id] = failed_record
                    raise
                success_summary = build_recovery_success_summary(
                    action="checkpoint_restore",
                    updated_at_epoch_ms=updated_at_epoch_ms,
                    detail=normalized_reason,
                    metadata={
                        "contract_id": contract_id,
                        "service_revision": int(record.service_revision) + 1,
                    },
                )
            else:
                recovered_object = factory(*record.factory_args, **record.factory_kwargs)
                success_summary = build_recovery_success_summary(
                    action="restart",
                    updated_at_epoch_ms=updated_at_epoch_ms,
                    detail=normalized_reason,
                    metadata={
                        "contract_id": contract_id,
                        "policy": record.descriptor.recovery_policy,
                        "service_revision": int(record.service_revision) + 1,
                    },
                )

            updated_record = replace(
                record,
                service_object=recovered_object,
                recovery_summary=success_summary,
                service_revision=int(record.service_revision) + 1,
                created_at_epoch_ms=updated_at_epoch_ms,
            )
            self._records[contract_id] = updated_record
            return updated_record

    def unregister_service(self, descriptor_or_contract_id: Any) -> bool:
        contract_id = self._resolve_contract_id(descriptor_or_contract_id)
        with self._lock:
            removed = self._records.pop(contract_id, None)
            released_flow_ids = self._flow_claims.pop(contract_id, set())
            governance_manager = self._governance_manager
            for flow_instance_id in released_flow_ids:
                if governance_manager is None:
                    continue
                governance_manager.release_claim(
                    _shared_state_claim_key(contract_id=contract_id, flow_instance_id=flow_instance_id)
                )
        return removed is not None

    def resolve_binding(
        self,
        binding: SharedStateBindingSpec | dict[str, Any],
        *,
        consumer_kind: str,
        consumer_owner: str,
        consumer_namespace: str,
        consumer_tenant: str | None = None,
        consumer_instance_id: str | None = None,
        consumer_flow_instance_id: str | None = None,
    ) -> SharedStateServiceRecord:
        resolved_binding = normalize_shared_state_binding_spec(binding)
        resolved_consumer_kind = _normalize_non_empty(consumer_kind, field_name="consumer_kind")
        resolved_consumer_owner = _normalize_non_empty(consumer_owner, field_name="consumer_owner")
        resolved_consumer_namespace = _normalize_non_empty(
            consumer_namespace,
            field_name="consumer_namespace",
        )
        resolved_consumer_tenant = _normalize_optional_non_empty(consumer_tenant)
        resolved_consumer_instance_id = _normalize_optional_non_empty(consumer_instance_id)
        resolved_consumer_flow_instance_id = _normalize_optional_non_empty(consumer_flow_instance_id)

        with self._lock:
            record = self._records.get(resolved_binding.descriptor.contract_id)
            if record is None:
                raise ValueError(
                    "shared_state_descriptor_not_registered:"
                    f" alias={resolved_binding.alias}"
                    f" contract_id={resolved_binding.descriptor.contract_id}"
                )
            self._validate_visibility(
                record=record,
                consumer_owner=resolved_consumer_owner,
                consumer_namespace=resolved_consumer_namespace,
                consumer_tenant=resolved_consumer_tenant,
            )
            self._validate_admission_policy(
                record=record,
                consumer_owner=resolved_consumer_owner,
                consumer_namespace=resolved_consumer_namespace,
                consumer_tenant=resolved_consumer_tenant,
                consumer_instance_id=resolved_consumer_instance_id,
                consumer_flow_instance_id=resolved_consumer_flow_instance_id,
            )
            self._validate_reuse_policy(
                record=record,
                consumer_kind=resolved_consumer_kind,
                consumer_instance_id=resolved_consumer_instance_id,
                consumer_flow_instance_id=resolved_consumer_flow_instance_id,
            )
            claim_key = None
            if resolved_consumer_flow_instance_id is not None:
                claim_key = _shared_state_claim_key(
                    contract_id=record.contract_id,
                    flow_instance_id=resolved_consumer_flow_instance_id,
                )
                governance_manager = self._governance_manager
                if governance_manager is not None:
                    governance_manager.start_claim(
                        claim_key=claim_key,
                        scope=_shared_state_claim_scope(
                            contract_id=record.contract_id,
                            principal=resolved_consumer_owner,
                            tenant=resolved_consumer_tenant,
                        ),
                    )
            self._record_governance_decision_locked(
                record=record,
                consumer_owner=resolved_consumer_owner,
                consumer_namespace=resolved_consumer_namespace,
                consumer_tenant=resolved_consumer_tenant,
                allowed=True,
                reason_code="ok",
                consumer_instance_id=resolved_consumer_instance_id,
                consumer_flow_instance_id=resolved_consumer_flow_instance_id,
                claim_key=claim_key,
            )
            return record

    def resolve_contract(self, descriptor_or_contract_id: Any) -> SharedStateServiceRecord | None:
        contract_id = self._resolve_contract_id(descriptor_or_contract_id)
        with self._lock:
            return self._records.get(contract_id)

    def release_flow_instance_claims(self, flow_instance_id: str) -> None:
        resolved_flow_instance_id = _normalize_non_empty(flow_instance_id, field_name="flow_instance_id")
        with self._lock:
            empty_contract_ids: list[str] = []
            for contract_id, claimed_flow_ids in self._flow_claims.items():
                removed = resolved_flow_instance_id in claimed_flow_ids
                claimed_flow_ids.discard(resolved_flow_instance_id)
                if removed and self._governance_manager is not None:
                    self._governance_manager.release_claim(
                        _shared_state_claim_key(
                            contract_id=contract_id,
                            flow_instance_id=resolved_flow_instance_id,
                        )
                    )
                if not claimed_flow_ids:
                    empty_contract_ids.append(contract_id)
            for contract_id in empty_contract_ids:
                self._flow_claims.pop(contract_id, None)

    def list_records(self) -> list[SharedStateServiceRecord]:
        with self._lock:
            records = list(self._records.values())
        records.sort(key=lambda item: (item.descriptor.namespace, item.descriptor.service_name, item.contract_id))
        return records

    def observability_snapshot(self) -> list[dict[str, Any]]:
        return [record.snapshot() for record in self.list_records()]

    def _resolve_contract_id(self, descriptor_or_contract_id: Any) -> str:
        if isinstance(descriptor_or_contract_id, str):
            return _normalize_non_empty(descriptor_or_contract_id, field_name="contract_id")
        descriptor = normalize_shared_state_service_descriptor(descriptor_or_contract_id)
        return descriptor.contract_id

    def _validate_visibility(
        self,
        *,
        record: SharedStateServiceRecord,
        consumer_owner: str,
        consumer_namespace: str,
        consumer_tenant: str | None,
    ) -> None:
        visibility = record.descriptor.visibility
        if visibility == "public":
            return
        if visibility == "namespace":
            if consumer_namespace != record.descriptor.namespace:
                details = {
                    "visibility": visibility,
                    "expected_namespace": record.descriptor.namespace,
                    "observed_namespace": consumer_namespace,
                }
                self._record_governance_decision_locked(
                    record=record,
                    consumer_owner=consumer_owner,
                    consumer_namespace=consumer_namespace,
                    consumer_tenant=consumer_tenant,
                    allowed=False,
                    reason_code="namespace_forbidden",
                    details=details,
                )
                raise GovernanceDeniedError(
                    error_prefix="shared_state_descriptor_not_visible",
                    reason_code="namespace_forbidden",
                    details=details,
                )
            return
        if consumer_owner != record.descriptor.owner:
            details = {
                "visibility": visibility,
                "expected_principal": record.descriptor.owner,
                "observed_principal": consumer_owner,
            }
            self._record_governance_decision_locked(
                record=record,
                consumer_owner=consumer_owner,
                consumer_namespace=consumer_namespace,
                consumer_tenant=consumer_tenant,
                allowed=False,
                reason_code="principal_mismatch",
                details=details,
            )
            raise GovernanceDeniedError(
                error_prefix="shared_state_descriptor_not_visible",
                reason_code="principal_mismatch",
                details=details,
            )

    def _validate_admission_policy(
        self,
        *,
        record: SharedStateServiceRecord,
        consumer_owner: str,
        consumer_namespace: str,
        consumer_tenant: str | None,
        consumer_instance_id: str | None,
        consumer_flow_instance_id: str | None,
    ) -> None:
        policy = normalize_runtime_admission_policy(record.descriptor.admission_policy)
        reason_code = evaluate_runtime_admission_policy(
            policy,
            principal=consumer_owner,
            tenant=consumer_tenant,
            namespace=consumer_namespace,
        )
        if reason_code != "ok":
            details = {
                "admission_policy": dict(policy),
                "consumer_instance_id": consumer_instance_id,
                "consumer_flow_instance_id": consumer_flow_instance_id,
            }
            self._record_governance_decision_locked(
                record=record,
                consumer_owner=consumer_owner,
                consumer_namespace=consumer_namespace,
                consumer_tenant=consumer_tenant,
                allowed=False,
                reason_code=reason_code,
                consumer_instance_id=consumer_instance_id,
                consumer_flow_instance_id=consumer_flow_instance_id,
                details=details,
            )
            raise GovernanceDeniedError(
                error_prefix="shared_state_admission_denied",
                reason_code=reason_code,
                details=details,
            )

        quota = dict(policy.get("quota") or {})
        max_concurrent_claims = quota.get("max_concurrent_claims")
        if consumer_flow_instance_id is None or max_concurrent_claims is None:
            return
        claim_key = _shared_state_claim_key(
            contract_id=record.contract_id,
            flow_instance_id=consumer_flow_instance_id,
        )
        claim_scope = _shared_state_claim_scope(
            contract_id=record.contract_id,
            principal=consumer_owner,
            tenant=consumer_tenant,
        )
        governance_manager = self._governance_manager
        active_claims = len(self._flow_claims.get(record.contract_id, set()))
        if governance_manager is not None:
            if governance_manager.active_claim_count(scope=claim_scope) < active_claims:
                active_claims = governance_manager.active_claim_count(scope=claim_scope)
        if claim_key in _shared_state_active_claim_keys(record.contract_id, self._flow_claims):
            return
        if active_claims >= int(max_concurrent_claims):
            details = {
                "admission_policy": dict(policy),
                "consumer_instance_id": consumer_instance_id,
                "consumer_flow_instance_id": consumer_flow_instance_id,
            }
            self._record_governance_decision_locked(
                record=record,
                consumer_owner=consumer_owner,
                consumer_namespace=consumer_namespace,
                consumer_tenant=consumer_tenant,
                allowed=False,
                reason_code="quota_exceeded",
                consumer_instance_id=consumer_instance_id,
                consumer_flow_instance_id=consumer_flow_instance_id,
                claim_key=claim_key,
                quota_name="max_concurrent_claims",
                quota_limit=int(max_concurrent_claims),
                quota_value=active_claims,
                details=details,
            )
            raise GovernanceQuotaExceededError(
                error_prefix="shared_state_quota_exceeded",
                details=details,
            )

    def _validate_reuse_policy(
        self,
        *,
        record: SharedStateServiceRecord,
        consumer_kind: str,
        consumer_instance_id: str | None,
        consumer_flow_instance_id: str | None,
    ) -> None:
        if consumer_kind != "flow" or consumer_flow_instance_id is None:
            return
        claimed_flow_ids = self._flow_claims.setdefault(record.contract_id, set())
        if record.descriptor.reuse_policy == "cross_flow":
            claimed_flow_ids.add(consumer_flow_instance_id)
            return
        if claimed_flow_ids and consumer_flow_instance_id not in claimed_flow_ids:
            raise RuntimeError(
                "shared_state_cross_flow_reuse_not_allowed:"
                f" contract_id={record.contract_id}"
                f" consumer_instance_id={consumer_instance_id or ''}"
                f" consumer_flow_instance_id={consumer_flow_instance_id}"
            )
        claimed_flow_ids.add(consumer_flow_instance_id)

    def _record_governance_decision_locked(
        self,
        *,
        record: SharedStateServiceRecord,
        consumer_owner: str,
        consumer_namespace: str,
        consumer_tenant: str | None,
        allowed: bool,
        reason_code: str,
        consumer_instance_id: str | None = None,
        consumer_flow_instance_id: str | None = None,
        claim_key: str | None = None,
        quota_name: str | None = None,
        quota_limit: int | None = None,
        quota_value: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        governance_manager = self._governance_manager
        if governance_manager is None:
            return
        governance_manager.record_decision(
            resource_kind="shared_state",
            resource_id=record.contract_id,
            resource_name=record.descriptor.service_name,
            namespace=consumer_namespace,
            principal=consumer_owner,
            tenant=consumer_tenant,
            allowed=allowed,
            reason_code=reason_code,
            operation="resolve_binding",
            flow_instance_id=consumer_flow_instance_id,
            contract_id=record.contract_id,
            claim_key=claim_key,
            quota_name=quota_name,
            quota_limit=quota_limit,
            quota_value=quota_value,
            details={
                "consumer_instance_id": consumer_instance_id,
                **dict(details or {}),
            },
        )


def list_bound_shared_state_bindings() -> list[dict[str, Any]]:
    context = _require_actor_execution_context()
    return _extract_bound_binding_rows(getattr(context, "actor_config", None))


def resolve_bound_shared_state_service(alias: str | None = None) -> Any:
    runtime_host = _require_actor_runtime_host()
    registry = getattr(runtime_host, "shared_state_registry", None)
    if registry is None:
        raise RuntimeError("shared_state_registry_not_available")

    binding_rows = list_bound_shared_state_bindings()
    resolved_alias = _normalize_optional_non_empty(alias)
    if resolved_alias is None:
        if len(binding_rows) != 1:
            raise ValueError("shared_state_alias_required_for_ambiguous_binding_set")
        selected = binding_rows[0]
    else:
        selected = next(
            (row for row in binding_rows if _normalize_optional_non_empty(row.get("alias")) == resolved_alias),
            None,
        )
        if selected is None:
            raise ValueError(f"shared_state_alias_not_bound:{resolved_alias}")

    contract_id = _normalize_non_empty(selected.get("contract_id"), field_name="contract_id")
    record = registry.resolve_contract(contract_id)
    if record is None:
        raise ValueError(f"shared_state_descriptor_not_registered:{contract_id}")
    return record.service_object


def _extract_bound_binding_rows(actor_config: Any) -> list[dict[str, Any]]:
    if isinstance(actor_config, dict):
        raw_bindings = actor_config.get("shared_state_bindings")
    else:
        raw_bindings = getattr(actor_config, "shared_state_bindings", None)
    if not isinstance(raw_bindings, list):
        return []
    rows: list[dict[str, Any]] = []
    for raw_row in raw_bindings:
        if not isinstance(raw_row, dict):
            continue
        rows.append(dict(raw_row))
    return rows


def _require_actor_execution_context() -> Any:
    from sage.runtime.flownet.runtime.actors.execution_context import (
        require_actor_execution_context,
    )

    return require_actor_execution_context()


def _require_actor_runtime_host() -> Any:
    from sage.runtime.flownet.runtime.actors.execution_context import require_actor_runtime_host

    return require_actor_runtime_host()


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


def _normalize_mapping(raw_value: Any, *, field_name: str) -> dict[str, Any]:
    if raw_value is None:
        return {}
    if not isinstance(raw_value, dict):
        try:
            return dict(raw_value)
        except Exception as exc:
            raise TypeError(f"{field_name} must be a mapping when provided.") from exc
    return dict(raw_value)


def _shared_state_claim_key(*, contract_id: str, flow_instance_id: str) -> str:
    return f"{_normalize_non_empty(contract_id, field_name='contract_id')}::{_normalize_non_empty(flow_instance_id, field_name='flow_instance_id')}"


def _shared_state_claim_scope(*, contract_id: str, principal: str, tenant: str | None) -> str:
    normalized_tenant = _normalize_optional_non_empty(tenant) or "-"
    return (
        f"shared_state::{_normalize_non_empty(contract_id, field_name='contract_id')}::"
        f"{_normalize_non_empty(principal, field_name='principal')}::{normalized_tenant}"
    )


def _shared_state_active_claim_keys(
    contract_id: str,
    flow_claims: dict[str, set[str]],
) -> set[str]:
    return {
        _shared_state_claim_key(contract_id=contract_id, flow_instance_id=flow_instance_id)
        for flow_instance_id in flow_claims.get(contract_id, set())
    }


__all__ = [
    "list_bound_shared_state_bindings",
    "resolve_bound_shared_state_service",
    "SharedStateServiceRecord",
    "SharedStateServiceRegistry",
]