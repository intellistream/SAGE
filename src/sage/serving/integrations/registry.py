from __future__ import annotations

from threading import RLock
from typing import Any

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
    default_workflow_product_extension_points,
)


class WorkflowIntegrationRegistry:
    def __init__(
        self,
        *,
        extension_points: tuple[WorkflowIntegrationExtensionPoint, ...] | None = None,
    ) -> None:
        resolved_extension_points = extension_points or default_workflow_product_extension_points()
        self._extension_points = {
            point.extension_point_id: point for point in resolved_extension_points
        }
        self._adapters_by_type: dict[str, WorkflowProductAdapter] = {}
        self._lock = RLock()

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
        response = adapter.submit_job(request)
        _validate_adapter_response(
            request_integration_type=request.integration_type,
            request_id=request.request_id,
            response=response,
            response_type=WorkflowJobSubmitResponse,
        )
        return response

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


__all__ = [
    "WorkflowIntegrationRegistry",
    "validate_workflow_product_adapter",
]
