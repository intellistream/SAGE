from __future__ import annotations

import json
import os
from collections.abc import Mapping
from threading import RLock
from typing import Any

from . import policy as serving_policy
from .contracts import (
    ImportedWorkflow,
    WorkflowImportRequest,
    WorkflowImportResponse,
    WorkflowIntegrationExtensionPoint,
    WorkflowJobResultCollectRequest,
    WorkflowJobResultCollectResponse,
    WorkflowJobStatusPollRequest,
    WorkflowJobStatusPollResponse,
    WorkflowJobSubmitRequest,
    WorkflowJobSubmitResponse,
    WorkflowProductAdapter,
    WorkflowProductAdapterDescriptor,
    WorkflowServingRequestContext,
    default_workflow_product_extension_points,
)


DEFAULT_WORKFLOW_POLICY_VARIANT_KIND = "baseline"
DEFAULT_WORKFLOW_POLICY_VARIANT_NAME = "vamos-slo-feasibility-controller"
DEFAULT_WORKFLOW_POLICY_EXECUTION_PRIORITY_MODE = "invert-vamos"


class WorkflowIntegrationRegistry:
    def __init__(
        self,
        *,
        extension_points: tuple[WorkflowIntegrationExtensionPoint, ...] | None = None,
        policy_variant_kind: str | None = None,
        policy_variant_name: str | None = None,
        execution_priority_mode: str = "off",
        policy_load_snapshot: Mapping[str, float | None] | None = None,
    ) -> None:
        resolved_extension_points = extension_points or default_workflow_product_extension_points()
        self._extension_points = {
            point.extension_point_id: point for point in resolved_extension_points
        }
        self._adapters_by_type: dict[str, WorkflowProductAdapter] = {}
        self._lock = RLock()
        self._policy_variant_kind = _normalize_optional_non_empty(policy_variant_kind)
        self._policy_variant_name = _normalize_optional_non_empty(policy_variant_name)
        self._execution_priority_mode = execution_priority_mode
        self._policy_load_snapshot = {
            "num_requests_running": _coerce_optional_float(
                (policy_load_snapshot or {}).get("num_requests_running")
            ),
            "num_requests_waiting": _coerce_optional_float(
                (policy_load_snapshot or {}).get("num_requests_waiting")
            ),
            "kv_cache_usage_perc": _coerce_optional_float(
                (policy_load_snapshot or {}).get("kv_cache_usage_perc")
            ),
        }
        if (self._policy_variant_kind is None) != (self._policy_variant_name is None):
            raise ValueError(
                "policy_variant_kind and policy_variant_name must be configured together."
            )
        if self._policy_variant_kind is not None and self._policy_variant_name is not None:
            serving_policy.validate_direct_endpoint_variant(
                {
                    "kind": self._policy_variant_kind,
                    "name": self._policy_variant_name,
                }
            )
        if execution_priority_mode not in serving_policy.EXECUTION_PRIORITY_MODES:
            raise ValueError(
                "execution_priority_mode must be one of: "
                + ", ".join(serving_policy.EXECUTION_PRIORITY_MODES)
            )

    def register_adapter(self, adapter: WorkflowProductAdapter) -> WorkflowProductAdapterDescriptor:
        descriptor = validate_workflow_product_adapter(adapter)
        unknown_extension_points = [
            point_id
            for point_id in descriptor.extension_points
            if point_id not in self._extension_points
        ]
        if unknown_extension_points:
            joined = ", ".join(sorted(unknown_extension_points))
            raise ValueError(f"unknown workflow integration extension points: {joined}")

        with self._lock:
            existing = self._adapters_by_type.get(descriptor.integration_type)
            if existing is not None and existing is not adapter:
                raise ValueError(
                    f"workflow integration type already registered: {descriptor.integration_type}"
                )
            self._adapters_by_type[descriptor.integration_type] = adapter
        return descriptor

    def unregister_adapter(self, integration_type: str) -> bool:
        normalized_integration_type = _normalize_non_empty(
            integration_type,
            field_name="integration_type",
        )
        with self._lock:
            return self._adapters_by_type.pop(normalized_integration_type, None) is not None

    def get_adapter(self, integration_type: str) -> WorkflowProductAdapter | None:
        normalized_integration_type = _normalize_non_empty(
            integration_type,
            field_name="integration_type",
        )
        with self._lock:
            return self._adapters_by_type.get(normalized_integration_type)

    def require_adapter(self, integration_type: str) -> WorkflowProductAdapter:
        adapter = self.get_adapter(integration_type)
        if adapter is None:
            raise KeyError(f"workflow integration adapter not registered: {integration_type}")
        return adapter

    def list_adapter_descriptors(self) -> tuple[WorkflowProductAdapterDescriptor, ...]:
        with self._lock:
            descriptors = tuple(
                sorted(
                    (
                        validate_workflow_product_adapter(adapter)
                        for adapter in self._adapters_by_type.values()
                    ),
                    key=lambda descriptor: descriptor.integration_type,
                )
            )
        return descriptors

    def snapshot(self) -> dict[str, Any]:
        descriptors = self.list_adapter_descriptors()
        claimed_by: dict[str, list[str]] = {point_id: [] for point_id in self._extension_points}
        for descriptor in descriptors:
            for point_id in descriptor.extension_points:
                claimed_by.setdefault(point_id, []).append(descriptor.integration_type)

        extension_point_rows: list[dict[str, Any]] = []
        for point in sorted(
            self._extension_points.values(),
            key=lambda value: (value.priority, value.extension_point_id),
        ):
            row = point.to_dict()
            row["claimed_by"] = sorted(claimed_by.get(point.extension_point_id, []))
            extension_point_rows.append(row)

        return {
            "registered_types": [descriptor.integration_type for descriptor in descriptors],
            "adapters": [descriptor.to_dict() for descriptor in descriptors],
            "extension_points": extension_point_rows,
        }

    def inspect(self) -> dict[str, Any]:
        return self.snapshot()

    def import_workflow(self, request: WorkflowImportRequest) -> WorkflowImportResponse:
        adapter = self.require_adapter(request.integration_type)
        response = adapter.import_workflow(request)
        _validate_adapter_response(
            request_integration_type=request.integration_type,
            request_id=request.request_id,
            response=response,
            response_type=WorkflowImportResponse,
        )
        return response

    def submit_job(self, request: WorkflowJobSubmitRequest) -> WorkflowJobSubmitResponse:
        adapter = self.require_adapter(request.integration_type)
        _validate_imported_workflow(
            request.imported_workflow, integration_type=request.integration_type
        )
        prepared_request = self._prepare_submit_request_with_policy(
            request,
            adapter=adapter,
        )
        response = adapter.submit_job(prepared_request)
        _validate_adapter_response(
            request_integration_type=request.integration_type,
            request_id=request.request_id,
            response=response,
            response_type=WorkflowJobSubmitResponse,
        )
        return response

    def _prepare_submit_request_with_policy(
        self,
        request: WorkflowJobSubmitRequest,
        *,
        adapter: WorkflowProductAdapter,
    ) -> WorkflowJobSubmitRequest:
        if self._policy_variant_kind is None or self._policy_variant_name is None:
            return request
        if request.serving_context is None:
            return request
        # Avoid applying registry-level shaping when adapter already embeds policy logic.
        if getattr(adapter, "_policy_variant_kind", None) is not None:
            return request

        base_context = dict(request.serving_context.to_dict())
        variant_policy = serving_policy.variant_policy_for(
            self._policy_variant_kind,
            self._policy_variant_name,
        )
        controller, source = serving_policy.resolve_deadline_class_max_tokens(
            type("_Args", (), {"deadline_class_max_tokens": None})(),
            variant_policy,
        )
        caps, cap_profile = serving_policy.deadline_class_max_tokens_for_request(
            variant_policy,
            controller,
            dict(self._policy_load_snapshot),
            event={"serving_context": base_context},
        )

        requested_max_tokens = base_context.get("max_tokens")
        effective_max_tokens = requested_max_tokens
        if requested_max_tokens is not None:
            requested, effective = serving_policy.effective_output_len(base_context, caps)
            base_context["max_tokens"] = effective
            requested_max_tokens = requested
            effective_max_tokens = effective

        mapped_priority = serving_policy.map_execution_priority(
            base_context,
            self._execution_priority_mode,
        )

        policy_decision = {
            "variant_kind": self._policy_variant_kind,
            "variant_name": self._policy_variant_name,
            "deadline_class_cap_source": source,
            "deadline_class_cap_profile": cap_profile,
            "deadline_class_max_tokens": caps,
            "execution_priority_mode": self._execution_priority_mode,
            "requested_max_tokens": requested_max_tokens,
            "effective_max_tokens": effective_max_tokens,
            "mapped_priority": mapped_priority,
            "applied_by": "registry",
        }
        metadata = dict(request.metadata)
        metadata["policy_decision"] = policy_decision
        return WorkflowJobSubmitRequest(
            integration_type=request.integration_type,
            imported_workflow=request.imported_workflow,
            input_payload=request.input_payload,
            submit_mode=request.submit_mode,
            request_id=request.request_id,
            metadata=metadata,
            serving_context=WorkflowServingRequestContext(**base_context),
        )

    def poll_status(self, request: WorkflowJobStatusPollRequest) -> WorkflowJobStatusPollResponse:
        adapter = self.require_adapter(request.integration_type)
        response = adapter.poll_status(request)
        _validate_adapter_response(
            request_integration_type=request.integration_type,
            request_id=request.request_id,
            response=response,
            response_type=WorkflowJobStatusPollResponse,
        )
        return response

    def collect_result(
        self,
        request: WorkflowJobResultCollectRequest,
    ) -> WorkflowJobResultCollectResponse:
        adapter = self.require_adapter(request.integration_type)
        response = adapter.collect_result(request)
        _validate_adapter_response(
            request_integration_type=request.integration_type,
            request_id=request.request_id,
            response=response,
            response_type=WorkflowJobResultCollectResponse,
        )
        return response


def build_workflow_integration_registry_from_env(
    *,
    extension_points: tuple[WorkflowIntegrationExtensionPoint, ...] | None = None,
    env: Mapping[str, str] | None = None,
) -> WorkflowIntegrationRegistry:
    env_map: Mapping[str, str] = env if env is not None else os.environ

    variant_kind = _normalize_optional_non_empty(
        env_map.get("SAGE_WORKFLOW_POLICY_VARIANT_KIND")
    ) or DEFAULT_WORKFLOW_POLICY_VARIANT_KIND
    variant_name = _normalize_optional_non_empty(
        env_map.get("SAGE_WORKFLOW_POLICY_VARIANT_NAME")
    ) or DEFAULT_WORKFLOW_POLICY_VARIANT_NAME
    execution_priority_mode = (
        _normalize_optional_non_empty(env_map.get("SAGE_WORKFLOW_POLICY_EXECUTION_PRIORITY_MODE"))
        or DEFAULT_WORKFLOW_POLICY_EXECUTION_PRIORITY_MODE
    )

    snapshot = _parse_policy_load_snapshot_from_env(env_map)

    return WorkflowIntegrationRegistry(
        extension_points=extension_points,
        policy_variant_kind=variant_kind,
        policy_variant_name=variant_name,
        execution_priority_mode=execution_priority_mode,
        policy_load_snapshot=snapshot,
    )


def validate_workflow_product_adapter(
    adapter: WorkflowProductAdapter,
) -> WorkflowProductAdapterDescriptor:
    descriptor = getattr(adapter, "descriptor", None)
    if not isinstance(descriptor, WorkflowProductAdapterDescriptor):
        raise TypeError("workflow integration adapter must expose a descriptor.")
    for method_name in (
        "import_workflow",
        "submit_job",
        "poll_status",
        "collect_result",
    ):
        if not callable(getattr(adapter, method_name, None)):
            raise TypeError(f"workflow integration adapter must provide {method_name}(...).")
    return descriptor


def _validate_adapter_response(
    *,
    request_integration_type: str,
    request_id: str,
    response: Any,
    response_type: type,
) -> None:
    if not isinstance(response, response_type):
        raise TypeError(
            f"adapter returned {type(response).__name__}; expected {response_type.__name__}."
        )
    if response.integration_type != request_integration_type:
        raise ValueError(
            "adapter response integration_type mismatch: "
            f"expected={request_integration_type}, actual={response.integration_type}"
        )
    if response.request_id != request_id:
        raise ValueError(
            f"adapter response request_id mismatch: expected={request_id}, actual={response.request_id}"
        )


def _validate_imported_workflow(
    imported_workflow: ImportedWorkflow, *, integration_type: str
) -> None:
    if imported_workflow.integration_type != integration_type:
        raise ValueError(
            "imported_workflow integration_type mismatch: "
            f"expected={integration_type}, actual={imported_workflow.integration_type}"
        )


def _normalize_non_empty(value: Any, *, field_name: str) -> str:
    normalized = str(value or "").strip()
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


def _coerce_optional_float(raw_value: Any) -> float | None:
    if raw_value is None:
        return None
    return float(raw_value)


def _parse_policy_load_snapshot_from_env(env_map: Mapping[str, str]) -> dict[str, float | None]:
    snapshot: dict[str, float | None] = {
        "num_requests_running": None,
        "num_requests_waiting": None,
        "kv_cache_usage_perc": None,
    }

    raw_json = _normalize_optional_non_empty(env_map.get("SAGE_WORKFLOW_POLICY_LOAD_SNAPSHOT_JSON"))
    if raw_json is not None:
        try:
            payload = json.loads(raw_json)
        except json.JSONDecodeError as exc:
            raise ValueError("SAGE_WORKFLOW_POLICY_LOAD_SNAPSHOT_JSON must be valid JSON") from exc
        if not isinstance(payload, Mapping):
            raise ValueError("SAGE_WORKFLOW_POLICY_LOAD_SNAPSHOT_JSON must decode to an object")
        snapshot["num_requests_running"] = _coerce_optional_float(
            payload.get("num_requests_running")
        )
        snapshot["num_requests_waiting"] = _coerce_optional_float(
            payload.get("num_requests_waiting")
        )
        snapshot["kv_cache_usage_perc"] = _coerce_optional_float(
            payload.get("kv_cache_usage_perc")
        )

    direct_running = _normalize_optional_non_empty(
        env_map.get("SAGE_WORKFLOW_POLICY_NUM_REQUESTS_RUNNING")
    )
    if direct_running is not None:
        snapshot["num_requests_running"] = float(direct_running)

    direct_waiting = _normalize_optional_non_empty(
        env_map.get("SAGE_WORKFLOW_POLICY_NUM_REQUESTS_WAITING")
    )
    if direct_waiting is not None:
        snapshot["num_requests_waiting"] = float(direct_waiting)

    direct_kv = _normalize_optional_non_empty(env_map.get("SAGE_WORKFLOW_POLICY_KV_CACHE_USAGE_PERC"))
    if direct_kv is not None:
        snapshot["kv_cache_usage_perc"] = float(direct_kv)

    return snapshot


__all__ = [
    "build_workflow_integration_registry_from_env",
    "WorkflowIntegrationRegistry",
    "validate_workflow_product_adapter",
]
