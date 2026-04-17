from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

WORKFLOW_INTEGRATION_SCHEMA_VERSION = "sage.workflow.product.integration.v1"

WorkflowIntegrationOperation = Literal[
    "workflow_import",
    "job_submit",
    "status_poll",
    "result_collect",
]
WorkflowExecutionTargetType = Literal["sage_executable", "endpoint_request"]
WorkflowJobStatus = Literal["accepted", "running", "completed", "failed", "cancelled"]
WorkflowSubmitMode = Literal["sync", "async"]

COMFY_FIRST_EXTENSION_POINT = "workflow_product.comfy_first"
LANGGRAPH_SECOND_EXTENSION_POINT = "workflow_product.langgraph_second"

_WORKFLOW_OPERATIONS = frozenset(
    {"workflow_import", "job_submit", "status_poll", "result_collect"}
)
_WORKFLOW_TARGET_TYPES = frozenset({"sage_executable", "endpoint_request"})
_WORKFLOW_JOB_STATUSES = frozenset({"accepted", "running", "completed", "failed", "cancelled"})
_WORKFLOW_SUBMIT_MODES = frozenset({"sync", "async"})


def _normalize_mapping(raw_value: Any, *, field_name: str) -> dict[str, Any]:
    if raw_value is None:
        return {}
    if not isinstance(raw_value, Mapping):
        raise TypeError(f"{field_name} must be a mapping when provided.")
    return dict(raw_value)


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


def _normalize_choice(raw_value: Any, *, field_name: str, allowed: Sequence[str]) -> str:
    normalized = _normalize_non_empty(raw_value, field_name=field_name)
    if normalized not in allowed:
        raise ValueError(f"{field_name} must be one of: {', '.join(sorted(set(allowed)))}.")
    return normalized


def _normalize_string_sequence(raw_value: Any, *, field_name: str) -> tuple[str, ...]:
    if raw_value is None:
        return ()
    if not isinstance(raw_value, Sequence) or isinstance(raw_value, (str, bytes)):
        raise TypeError(f"{field_name} must be a sequence when provided.")
    normalized: list[str] = []
    seen: set[str] = set()
    for item in raw_value:
        value = _normalize_non_empty(item, field_name=field_name)
        if value in seen:
            continue
        seen.add(value)
        normalized.append(value)
    return tuple(normalized)


def _normalize_choice_sequence(
    raw_value: Any,
    *,
    field_name: str,
    allowed: Sequence[str],
) -> tuple[str, ...]:
    values = _normalize_string_sequence(raw_value, field_name=field_name)
    for value in values:
        if value not in allowed:
            raise ValueError(f"{field_name} contains unsupported value: {value}.")
    return values


def _coerce_int(raw_value: Any, *, field_name: str) -> int:
    try:
        return int(raw_value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be an integer.") from exc


@dataclass(frozen=True)
class WorkflowIntegrationExtensionPoint:
    extension_point_id: str
    display_name: str
    priority: int
    description: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "extension_point_id",
            _normalize_non_empty(self.extension_point_id, field_name="extension_point_id"),
        )
        object.__setattr__(
            self,
            "display_name",
            _normalize_non_empty(self.display_name, field_name="display_name"),
        )
        priority = _coerce_int(self.priority, field_name="priority")
        if priority < 0:
            raise ValueError("priority must be >= 0.")
        object.__setattr__(self, "priority", priority)
        object.__setattr__(self, "description", _normalize_optional_non_empty(self.description))
        object.__setattr__(
            self,
            "metadata",
            _normalize_mapping(self.metadata, field_name="metadata"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "extension_point_id": self.extension_point_id,
            "display_name": self.display_name,
            "priority": self.priority,
            "description": self.description,
            "metadata": dict(self.metadata),
        }


_DEFAULT_EXTENSION_POINTS = (
    WorkflowIntegrationExtensionPoint(
        extension_point_id=COMFY_FIRST_EXTENSION_POINT,
        display_name="Comfy-first",
        priority=100,
        description="Reserved extension point for Comfy-class workflow product adapters.",
        metadata={"ecosystem": "ComfyUI", "recommended_order": "first"},
    ),
    WorkflowIntegrationExtensionPoint(
        extension_point_id=LANGGRAPH_SECOND_EXTENSION_POINT,
        display_name="LangGraph-second",
        priority=200,
        description="Reserved extension point for LangGraph-class workflow product adapters.",
        metadata={"ecosystem": "LangGraph", "recommended_order": "second"},
    ),
)


def default_workflow_product_extension_points() -> tuple[WorkflowIntegrationExtensionPoint, ...]:
    return _DEFAULT_EXTENSION_POINTS


@dataclass(frozen=True)
class WorkflowProductAdapterDescriptor:
    integration_type: str
    display_name: str
    description: str | None = None
    supported_targets: tuple[WorkflowExecutionTargetType, ...] = (
        "sage_executable",
        "endpoint_request",
    )
    operations: tuple[WorkflowIntegrationOperation, ...] = (
        "workflow_import",
        "job_submit",
        "status_poll",
        "result_collect",
    )
    extension_points: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "integration_type",
            _normalize_non_empty(self.integration_type, field_name="integration_type"),
        )
        object.__setattr__(
            self,
            "display_name",
            _normalize_non_empty(self.display_name, field_name="display_name"),
        )
        object.__setattr__(self, "description", _normalize_optional_non_empty(self.description))

        supported_targets = _normalize_choice_sequence(
            self.supported_targets,
            field_name="supported_targets",
            allowed=_WORKFLOW_TARGET_TYPES,
        )
        if not supported_targets:
            raise ValueError("supported_targets must contain at least one target type.")
        object.__setattr__(self, "supported_targets", supported_targets)

        operations = _normalize_choice_sequence(
            self.operations,
            field_name="operations",
            allowed=_WORKFLOW_OPERATIONS,
        )
        missing_operations = _WORKFLOW_OPERATIONS.difference(operations)
        if missing_operations:
            raise ValueError(
                "operations must include the four minimal workflow integration operations: "
                f"{', '.join(sorted(missing_operations))}."
            )
        object.__setattr__(self, "operations", operations)
        object.__setattr__(
            self,
            "extension_points",
            _normalize_string_sequence(self.extension_points, field_name="extension_points"),
        )
        object.__setattr__(
            self,
            "metadata",
            _normalize_mapping(self.metadata, field_name="metadata"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "integration_type": self.integration_type,
            "display_name": self.display_name,
            "description": self.description,
            "supported_targets": list(self.supported_targets),
            "operations": list(self.operations),
            "extension_points": list(self.extension_points),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class WorkflowIntegrationRequest:
    operation: WorkflowIntegrationOperation
    integration_type: str
    request_id: str
    payload: dict[str, Any]
    schema_version: str = WORKFLOW_INTEGRATION_SCHEMA_VERSION
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "operation",
            _normalize_choice(
                self.operation,
                field_name="operation",
                allowed=_WORKFLOW_OPERATIONS,
            ),
        )
        object.__setattr__(
            self,
            "integration_type",
            _normalize_non_empty(self.integration_type, field_name="integration_type"),
        )
        object.__setattr__(
            self,
            "request_id",
            _normalize_non_empty(self.request_id, field_name="request_id"),
        )
        object.__setattr__(
            self,
            "payload",
            _normalize_mapping(self.payload, field_name="payload"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _normalize_non_empty(self.schema_version, field_name="schema_version"),
        )
        object.__setattr__(
            self,
            "metadata",
            _normalize_mapping(self.metadata, field_name="metadata"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "operation": self.operation,
            "integration_type": self.integration_type,
            "request_id": self.request_id,
            "payload": dict(self.payload),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class WorkflowIntegrationResponse:
    operation: WorkflowIntegrationOperation
    integration_type: str
    request_id: str
    success: bool
    payload: dict[str, Any]
    schema_version: str = WORKFLOW_INTEGRATION_SCHEMA_VERSION
    error_code: str | None = None
    error_detail: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "operation",
            _normalize_choice(
                self.operation,
                field_name="operation",
                allowed=_WORKFLOW_OPERATIONS,
            ),
        )
        object.__setattr__(
            self,
            "integration_type",
            _normalize_non_empty(self.integration_type, field_name="integration_type"),
        )
        object.__setattr__(
            self,
            "request_id",
            _normalize_non_empty(self.request_id, field_name="request_id"),
        )
        object.__setattr__(
            self,
            "payload",
            _normalize_mapping(self.payload, field_name="payload"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _normalize_non_empty(self.schema_version, field_name="schema_version"),
        )
        object.__setattr__(self, "error_code", _normalize_optional_non_empty(self.error_code))
        object.__setattr__(
            self,
            "error_detail",
            _normalize_optional_non_empty(self.error_detail),
        )
        object.__setattr__(
            self,
            "metadata",
            _normalize_mapping(self.metadata, field_name="metadata"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "operation": self.operation,
            "integration_type": self.integration_type,
            "request_id": self.request_id,
            "success": bool(self.success),
            "payload": dict(self.payload),
            "error_code": self.error_code,
            "error_detail": self.error_detail,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class WorkflowExecutionTarget:
    target_type: WorkflowExecutionTargetType
    payload: dict[str, Any] = field(default_factory=dict)
    executable: Any | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "target_type",
            _normalize_choice(
                self.target_type,
                field_name="target_type",
                allowed=_WORKFLOW_TARGET_TYPES,
            ),
        )
        object.__setattr__(
            self,
            "payload",
            _normalize_mapping(self.payload, field_name="payload"),
        )
        object.__setattr__(
            self,
            "metadata",
            _normalize_mapping(self.metadata, field_name="metadata"),
        )
        if self.target_type == "sage_executable" and self.executable is None:
            raise ValueError("sage_executable target_type requires a non-None executable.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_type": self.target_type,
            "payload": dict(self.payload),
            "executable_type": type(self.executable).__name__ if self.executable is not None else None,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class ImportedWorkflow:
    workflow_id: str
    integration_type: str
    source_payload: dict[str, Any]
    normalized_workflow: dict[str, Any]
    execution_target: WorkflowExecutionTarget
    workflow_name: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "workflow_id",
            _normalize_non_empty(self.workflow_id, field_name="workflow_id"),
        )
        object.__setattr__(
            self,
            "integration_type",
            _normalize_non_empty(self.integration_type, field_name="integration_type"),
        )
        object.__setattr__(
            self,
            "source_payload",
            _normalize_mapping(self.source_payload, field_name="source_payload"),
        )
        object.__setattr__(
            self,
            "normalized_workflow",
            _normalize_mapping(self.normalized_workflow, field_name="normalized_workflow"),
        )
        if not isinstance(self.execution_target, WorkflowExecutionTarget):
            raise TypeError("execution_target must be a WorkflowExecutionTarget.")
        object.__setattr__(self, "workflow_name", _normalize_optional_non_empty(self.workflow_name))
        object.__setattr__(
            self,
            "metadata",
            _normalize_mapping(self.metadata, field_name="metadata"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "integration_type": self.integration_type,
            "workflow_name": self.workflow_name,
            "source_payload": dict(self.source_payload),
            "normalized_workflow": dict(self.normalized_workflow),
            "execution_target": self.execution_target.to_dict(),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class WorkflowImportRequest:
    integration_type: str
    workflow_payload: dict[str, Any]
    desired_target: WorkflowExecutionTargetType = "endpoint_request"
    request_id: str = "workflow-import"
    options: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "integration_type",
            _normalize_non_empty(self.integration_type, field_name="integration_type"),
        )
        object.__setattr__(
            self,
            "workflow_payload",
            _normalize_mapping(self.workflow_payload, field_name="workflow_payload"),
        )
        object.__setattr__(
            self,
            "desired_target",
            _normalize_choice(
                self.desired_target,
                field_name="desired_target",
                allowed=_WORKFLOW_TARGET_TYPES,
            ),
        )
        object.__setattr__(
            self,
            "request_id",
            _normalize_non_empty(self.request_id, field_name="request_id"),
        )
        object.__setattr__(
            self,
            "options",
            _normalize_mapping(self.options, field_name="options"),
        )
        object.__setattr__(
            self,
            "metadata",
            _normalize_mapping(self.metadata, field_name="metadata"),
        )

    def to_integration_request(self) -> WorkflowIntegrationRequest:
        return WorkflowIntegrationRequest(
            operation="workflow_import",
            integration_type=self.integration_type,
            request_id=self.request_id,
            payload={
                "workflow_payload": dict(self.workflow_payload),
                "desired_target": self.desired_target,
                "options": dict(self.options),
            },
            metadata=dict(self.metadata),
        )


@dataclass(frozen=True)
class WorkflowImportResponse:
    integration_type: str
    request_id: str
    imported_workflow: ImportedWorkflow
    warnings: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "integration_type",
            _normalize_non_empty(self.integration_type, field_name="integration_type"),
        )
        object.__setattr__(
            self,
            "request_id",
            _normalize_non_empty(self.request_id, field_name="request_id"),
        )
        if not isinstance(self.imported_workflow, ImportedWorkflow):
            raise TypeError("imported_workflow must be an ImportedWorkflow.")
        object.__setattr__(
            self,
            "warnings",
            _normalize_string_sequence(self.warnings, field_name="warnings"),
        )
        object.__setattr__(
            self,
            "metadata",
            _normalize_mapping(self.metadata, field_name="metadata"),
        )

    def to_integration_response(self) -> WorkflowIntegrationResponse:
        return WorkflowIntegrationResponse(
            operation="workflow_import",
            integration_type=self.integration_type,
            request_id=self.request_id,
            success=True,
            payload={
                "imported_workflow": self.imported_workflow.to_dict(),
                "warnings": list(self.warnings),
            },
            metadata=dict(self.metadata),
        )


@dataclass(frozen=True)
class WorkflowJobSubmitRequest:
    integration_type: str
    imported_workflow: ImportedWorkflow
    input_payload: Any = None
    submit_mode: WorkflowSubmitMode = "async"
    request_id: str = "workflow-submit"
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "integration_type",
            _normalize_non_empty(self.integration_type, field_name="integration_type"),
        )
        if not isinstance(self.imported_workflow, ImportedWorkflow):
            raise TypeError("imported_workflow must be an ImportedWorkflow.")
        object.__setattr__(
            self,
            "submit_mode",
            _normalize_choice(
                self.submit_mode,
                field_name="submit_mode",
                allowed=_WORKFLOW_SUBMIT_MODES,
            ),
        )
        object.__setattr__(
            self,
            "request_id",
            _normalize_non_empty(self.request_id, field_name="request_id"),
        )
        object.__setattr__(
            self,
            "metadata",
            _normalize_mapping(self.metadata, field_name="metadata"),
        )

    def to_integration_request(self) -> WorkflowIntegrationRequest:
        return WorkflowIntegrationRequest(
            operation="job_submit",
            integration_type=self.integration_type,
            request_id=self.request_id,
            payload={
                "imported_workflow": self.imported_workflow.to_dict(),
                "input_payload": self.input_payload,
                "submit_mode": self.submit_mode,
            },
            metadata=dict(self.metadata),
        )


@dataclass(frozen=True)
class WorkflowJobSubmitResponse:
    integration_type: str
    request_id: str
    job_id: str
    status: WorkflowJobStatus = "accepted"
    accepted: bool = True
    submit_payload: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "integration_type",
            _normalize_non_empty(self.integration_type, field_name="integration_type"),
        )
        object.__setattr__(
            self,
            "request_id",
            _normalize_non_empty(self.request_id, field_name="request_id"),
        )
        object.__setattr__(self, "job_id", _normalize_non_empty(self.job_id, field_name="job_id"))
        object.__setattr__(
            self,
            "status",
            _normalize_choice(self.status, field_name="status", allowed=_WORKFLOW_JOB_STATUSES),
        )
        object.__setattr__(
            self,
            "submit_payload",
            _normalize_mapping(self.submit_payload, field_name="submit_payload"),
        )
        object.__setattr__(
            self,
            "metadata",
            _normalize_mapping(self.metadata, field_name="metadata"),
        )

    def to_integration_response(self) -> WorkflowIntegrationResponse:
        return WorkflowIntegrationResponse(
            operation="job_submit",
            integration_type=self.integration_type,
            request_id=self.request_id,
            success=bool(self.accepted),
            payload={
                "job_id": self.job_id,
                "status": self.status,
                "accepted": bool(self.accepted),
                "submit_payload": dict(self.submit_payload),
            },
            metadata=dict(self.metadata),
        )


@dataclass(frozen=True)
class WorkflowJobStatusPollRequest:
    integration_type: str
    job_id: str
    request_id: str = "workflow-status-poll"
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "integration_type",
            _normalize_non_empty(self.integration_type, field_name="integration_type"),
        )
        object.__setattr__(self, "job_id", _normalize_non_empty(self.job_id, field_name="job_id"))
        object.__setattr__(
            self,
            "request_id",
            _normalize_non_empty(self.request_id, field_name="request_id"),
        )
        object.__setattr__(
            self,
            "metadata",
            _normalize_mapping(self.metadata, field_name="metadata"),
        )

    def to_integration_request(self) -> WorkflowIntegrationRequest:
        return WorkflowIntegrationRequest(
            operation="status_poll",
            integration_type=self.integration_type,
            request_id=self.request_id,
            payload={"job_id": self.job_id},
            metadata=dict(self.metadata),
        )


@dataclass(frozen=True)
class WorkflowJobStatusPollResponse:
    integration_type: str
    request_id: str
    job_id: str
    status: WorkflowJobStatus
    ready: bool
    result_available: bool
    progress: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "integration_type",
            _normalize_non_empty(self.integration_type, field_name="integration_type"),
        )
        object.__setattr__(
            self,
            "request_id",
            _normalize_non_empty(self.request_id, field_name="request_id"),
        )
        object.__setattr__(self, "job_id", _normalize_non_empty(self.job_id, field_name="job_id"))
        object.__setattr__(
            self,
            "status",
            _normalize_choice(self.status, field_name="status", allowed=_WORKFLOW_JOB_STATUSES),
        )
        progress = self.progress
        if progress is not None:
            try:
                progress = float(progress)
            except (TypeError, ValueError) as exc:
                raise ValueError("progress must be a float when provided.") from exc
            if progress < 0.0 or progress > 1.0:
                raise ValueError("progress must be between 0.0 and 1.0 when provided.")
        object.__setattr__(self, "progress", progress)
        object.__setattr__(
            self,
            "metadata",
            _normalize_mapping(self.metadata, field_name="metadata"),
        )

    def to_integration_response(self) -> WorkflowIntegrationResponse:
        return WorkflowIntegrationResponse(
            operation="status_poll",
            integration_type=self.integration_type,
            request_id=self.request_id,
            success=True,
            payload={
                "job_id": self.job_id,
                "status": self.status,
                "ready": bool(self.ready),
                "result_available": bool(self.result_available),
                "progress": self.progress,
            },
            metadata=dict(self.metadata),
        )


@dataclass(frozen=True)
class WorkflowJobResultCollectRequest:
    integration_type: str
    job_id: str
    request_id: str = "workflow-result-collect"
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "integration_type",
            _normalize_non_empty(self.integration_type, field_name="integration_type"),
        )
        object.__setattr__(self, "job_id", _normalize_non_empty(self.job_id, field_name="job_id"))
        object.__setattr__(
            self,
            "request_id",
            _normalize_non_empty(self.request_id, field_name="request_id"),
        )
        object.__setattr__(
            self,
            "metadata",
            _normalize_mapping(self.metadata, field_name="metadata"),
        )

    def to_integration_request(self) -> WorkflowIntegrationRequest:
        return WorkflowIntegrationRequest(
            operation="result_collect",
            integration_type=self.integration_type,
            request_id=self.request_id,
            payload={"job_id": self.job_id},
            metadata=dict(self.metadata),
        )


@dataclass(frozen=True)
class WorkflowJobResultCollectResponse:
    integration_type: str
    request_id: str
    job_id: str
    status: WorkflowJobStatus
    result: Any = None
    artifacts: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "integration_type",
            _normalize_non_empty(self.integration_type, field_name="integration_type"),
        )
        object.__setattr__(
            self,
            "request_id",
            _normalize_non_empty(self.request_id, field_name="request_id"),
        )
        object.__setattr__(self, "job_id", _normalize_non_empty(self.job_id, field_name="job_id"))
        object.__setattr__(
            self,
            "status",
            _normalize_choice(self.status, field_name="status", allowed=_WORKFLOW_JOB_STATUSES),
        )
        object.__setattr__(
            self,
            "artifacts",
            _normalize_mapping(self.artifacts, field_name="artifacts"),
        )
        object.__setattr__(
            self,
            "metadata",
            _normalize_mapping(self.metadata, field_name="metadata"),
        )

    def to_integration_response(self) -> WorkflowIntegrationResponse:
        return WorkflowIntegrationResponse(
            operation="result_collect",
            integration_type=self.integration_type,
            request_id=self.request_id,
            success=self.status == "completed",
            payload={
                "job_id": self.job_id,
                "status": self.status,
                "result": self.result,
                "artifacts": dict(self.artifacts),
            },
            metadata=dict(self.metadata),
        )


class WorkflowProductAdapter(Protocol):
    descriptor: WorkflowProductAdapterDescriptor

    def import_workflow(self, request: WorkflowImportRequest) -> WorkflowImportResponse: ...

    def submit_job(self, request: WorkflowJobSubmitRequest) -> WorkflowJobSubmitResponse: ...

    def poll_status(
        self,
        request: WorkflowJobStatusPollRequest,
    ) -> WorkflowJobStatusPollResponse: ...

    def collect_result(
        self,
        request: WorkflowJobResultCollectRequest,
    ) -> WorkflowJobResultCollectResponse: ...


__all__ = [
    "COMFY_FIRST_EXTENSION_POINT",
    "ImportedWorkflow",
    "LANGGRAPH_SECOND_EXTENSION_POINT",
    "WORKFLOW_INTEGRATION_SCHEMA_VERSION",
    "WorkflowExecutionTarget",
    "WorkflowExecutionTargetType",
    "WorkflowImportRequest",
    "WorkflowImportResponse",
    "WorkflowIntegrationExtensionPoint",
    "WorkflowIntegrationOperation",
    "WorkflowIntegrationRequest",
    "WorkflowIntegrationResponse",
    "WorkflowJobResultCollectRequest",
    "WorkflowJobResultCollectResponse",
    "WorkflowJobStatus",
    "WorkflowJobStatusPollRequest",
    "WorkflowJobStatusPollResponse",
    "WorkflowJobSubmitRequest",
    "WorkflowJobSubmitResponse",
    "WorkflowProductAdapter",
    "WorkflowProductAdapterDescriptor",
    "WorkflowSubmitMode",
    "default_workflow_product_extension_points",
]