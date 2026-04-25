from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from threading import RLock
from typing import Any

from .contracts import (
    ImportedWorkflow,
    WorkflowExecutionTarget,
    WorkflowImportRequest,
    WorkflowImportResponse,
    WorkflowJobResultCollectRequest,
    WorkflowJobResultCollectResponse,
    WorkflowJobStatusPollRequest,
    WorkflowJobStatusPollResponse,
    WorkflowJobSubmitRequest,
    WorkflowJobSubmitResponse,
    WorkflowProductAdapterDescriptor,
)


def _serving_context_payload(request: WorkflowImportRequest | WorkflowJobSubmitRequest) -> dict[str, Any] | None:
    serving_context = getattr(request, "serving_context", None)
    if serving_context is None:
        return None
    if callable(getattr(serving_context, "to_dict", None)):
        return dict(serving_context.to_dict())
    return None


@dataclass(frozen=True)
class MockSageExecutable:
    executable_id: str
    workflow_id: str
    workflow_name: str | None
    normalized_workflow: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)

    def describe(self) -> dict[str, Any]:
        return {
            "executable_id": self.executable_id,
            "workflow_id": self.workflow_id,
            "workflow_name": self.workflow_name,
            "normalized_workflow": dict(self.normalized_workflow),
            "metadata": dict(self.metadata),
        }


class MockWorkflowProductAdapter:
    def __init__(
        self,
        *,
        integration_type: str = "workflow.mock",
        display_name: str = "Mock Workflow Product Adapter",
        description: str | None = None,
        extension_points: Sequence[str] = (),
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        self.descriptor = WorkflowProductAdapterDescriptor(
            integration_type=integration_type,
            display_name=display_name,
            description=description,
            extension_points=tuple(extension_points),
            metadata=dict(metadata or {}),
        )
        self._lock = RLock()
        self._workflow_counter = 0
        self._job_counter = 0
        self._imported_workflows: dict[str, ImportedWorkflow] = {}
        self._jobs: dict[str, dict[str, Any]] = {}

    def import_workflow(self, request: WorkflowImportRequest) -> WorkflowImportResponse:
        self._require_supported_target(request.desired_target)
        source_payload = dict(request.workflow_payload)
        normalized_workflow = _normalize_external_workflow(source_payload)
        workflow_name = _normalize_optional_non_empty(source_payload.get("name"))
        serving_context = _serving_context_payload(request)

        with self._lock:
            self._workflow_counter += 1
            workflow_id = _normalize_optional_non_empty(source_payload.get("workflow_id"))
            if workflow_id is None:
                workflow_id = f"{self.descriptor.integration_type}:workflow:{self._workflow_counter}"

        if request.desired_target == "sage_executable":
            executable = MockSageExecutable(
                executable_id=f"mock-exec:{workflow_id}",
                workflow_id=workflow_id,
                workflow_name=workflow_name,
                normalized_workflow=normalized_workflow,
                metadata={
                    "adapter": self.descriptor.integration_type,
                    **({"serving_context": serving_context} if serving_context is not None else {}),
                },
            )
            execution_target = WorkflowExecutionTarget(
                target_type="sage_executable",
                executable=executable,
                payload={
                    "execution_kind": "mock_sage_executable",
                    "workflow_id": workflow_id,
                    **({"serving_context": serving_context} if serving_context is not None else {}),
                },
                metadata={
                    "adapter": self.descriptor.integration_type,
                    **({"serving_context": serving_context} if serving_context is not None else {}),
                },
            )
        else:
            execution_target = WorkflowExecutionTarget(
                target_type="endpoint_request",
                payload={
                    "endpoint": "sage://workflow-products/submit",
                    "method": "POST",
                    "body": {
                        "workflow_id": workflow_id,
                        "integration_type": self.descriptor.integration_type,
                        "workflow_name": workflow_name,
                        **({"serving_context": serving_context} if serving_context is not None else {}),
                    },
                },
                metadata={
                    "adapter": self.descriptor.integration_type,
                    **({"serving_context": serving_context} if serving_context is not None else {}),
                },
            )

        imported_workflow = ImportedWorkflow(
            workflow_id=workflow_id,
            integration_type=self.descriptor.integration_type,
            workflow_name=workflow_name,
            source_payload=source_payload,
            normalized_workflow=normalized_workflow,
            execution_target=execution_target,
            metadata={
                "adapter": self.descriptor.integration_type,
                "node_count": len(normalized_workflow.get("nodes", [])),
                **({"serving_context": serving_context} if serving_context is not None else {}),
            },
        )
        with self._lock:
            self._imported_workflows[workflow_id] = imported_workflow
        return WorkflowImportResponse(
            integration_type=self.descriptor.integration_type,
            request_id=request.request_id,
            imported_workflow=imported_workflow,
            metadata={"adapter": self.descriptor.display_name},
        )

    def submit_job(self, request: WorkflowJobSubmitRequest) -> WorkflowJobSubmitResponse:
        imported_workflow = request.imported_workflow
        if imported_workflow.integration_type != self.descriptor.integration_type:
            raise ValueError("imported workflow does not belong to this adapter.")

        serving_context = _serving_context_payload(request)
        submit_payload = self._build_submit_payload(
            imported_workflow,
            request.input_payload,
            serving_context=serving_context,
        )

        with self._lock:
            self._job_counter += 1
            job_id = f"{self.descriptor.integration_type}:job:{self._job_counter}"
            self._jobs[job_id] = {
                "status": "accepted",
                "poll_count": 0,
                "result": {
                    "job_id": job_id,
                    "workflow_id": imported_workflow.workflow_id,
                    "workflow_name": imported_workflow.workflow_name,
                    "integration_type": self.descriptor.integration_type,
                    "target_type": imported_workflow.execution_target.target_type,
                    "normalized_workflow": dict(imported_workflow.normalized_workflow),
                    "submitted_input": request.input_payload,
                    "submit_payload": submit_payload,
                    **({"serving_context": serving_context} if serving_context is not None else {}),
                },
            }

        return WorkflowJobSubmitResponse(
            integration_type=self.descriptor.integration_type,
            request_id=request.request_id,
            job_id=job_id,
            status="accepted",
            accepted=True,
            submit_payload=submit_payload,
            metadata={
                "submit_mode": request.submit_mode,
                **({"serving_context": serving_context} if serving_context is not None else {}),
            },
        )

    def poll_status(
        self,
        request: WorkflowJobStatusPollRequest,
    ) -> WorkflowJobStatusPollResponse:
        with self._lock:
            job = self._require_job(request.job_id)
            job["poll_count"] = int(job.get("poll_count", 0)) + 1
            if job["status"] in {"accepted", "running"}:
                job["status"] = "completed"
            status = str(job["status"])

        return WorkflowJobStatusPollResponse(
            integration_type=self.descriptor.integration_type,
            request_id=request.request_id,
            job_id=request.job_id,
            status=status,
            ready=status == "completed",
            result_available=status == "completed",
            progress=1.0 if status == "completed" else 0.5,
            metadata={"adapter": self.descriptor.display_name},
        )

    def collect_result(
        self,
        request: WorkflowJobResultCollectRequest,
    ) -> WorkflowJobResultCollectResponse:
        with self._lock:
            job = self._require_job(request.job_id)
            if job["status"] in {"accepted", "running"}:
                job["status"] = "completed"
            status = str(job["status"])
            result = job.get("result")
            poll_count = int(job.get("poll_count", 0))

        return WorkflowJobResultCollectResponse(
            integration_type=self.descriptor.integration_type,
            request_id=request.request_id,
            job_id=request.job_id,
            status=status,
            result=result,
            artifacts={"poll_count": poll_count},
            metadata={"adapter": self.descriptor.display_name},
        )

    def _require_supported_target(self, target_type: str) -> None:
        if target_type not in self.descriptor.supported_targets:
            raise ValueError(
                f"unsupported target_type for adapter {self.descriptor.integration_type}: {target_type}"
            )

    def _build_submit_payload(
        self,
        imported_workflow: ImportedWorkflow,
        input_payload: Any,
        *,
        serving_context: dict[str, Any] | None,
    ) -> dict[str, Any]:
        execution_target = imported_workflow.execution_target
        if execution_target.target_type == "sage_executable":
            executable = execution_target.executable
            described = (
                executable.describe()
                if callable(getattr(executable, "describe", None))
                else {"executable_type": type(executable).__name__}
            )
            return {
                "submit_via": "sage_executable",
                "workflow_id": imported_workflow.workflow_id,
                "input": input_payload,
                "executable": described,
                **({"serving_context": serving_context} if serving_context is not None else {}),
            }

        endpoint_request = dict(execution_target.payload)
        endpoint_body = _normalize_mapping(endpoint_request.get("body"))
        endpoint_body["input"] = input_payload
        endpoint_request["body"] = endpoint_body
        endpoint_request["submit_via"] = "endpoint_request"
        endpoint_request["workflow_id"] = imported_workflow.workflow_id
        if serving_context is not None:
            endpoint_request["serving_context"] = serving_context
        return endpoint_request

    def _require_job(self, job_id: str) -> dict[str, Any]:
        job = self._jobs.get(job_id)
        if job is None:
            raise KeyError(f"mock workflow job not found: {job_id}")
        return job


def _normalize_external_workflow(payload: Mapping[str, Any]) -> dict[str, Any]:
    raw_nodes = payload.get("nodes")
    if not isinstance(raw_nodes, Sequence) or isinstance(raw_nodes, (str, bytes)):
        raise TypeError("workflow_payload.nodes must be a sequence.")

    normalized_nodes: list[dict[str, Any]] = []
    for index, raw_node in enumerate(raw_nodes, start=1):
        if not isinstance(raw_node, Mapping):
            raise TypeError("workflow_payload.nodes entries must be mappings.")
        node_id = _normalize_optional_non_empty(raw_node.get("id")) or f"node-{index}"
        node_type = _normalize_optional_non_empty(raw_node.get("type")) or "operation"
        normalized_nodes.append(
            {
                "id": node_id,
                "type": node_type,
                "config": _normalize_mapping(raw_node.get("config")),
            }
        )

    normalized_edges: list[dict[str, str]] = []
    raw_edges = payload.get("edges")
    if raw_edges is not None:
        if not isinstance(raw_edges, Sequence) or isinstance(raw_edges, (str, bytes)):
            raise TypeError("workflow_payload.edges must be a sequence when provided.")
        for raw_edge in raw_edges:
            if not isinstance(raw_edge, Mapping):
                raise TypeError("workflow_payload.edges entries must be mappings.")
            source = _normalize_non_empty(raw_edge.get("source"), field_name="edge.source")
            target = _normalize_non_empty(raw_edge.get("target"), field_name="edge.target")
            normalized_edges.append({"source": source, "target": target})

    return {
        "nodes": normalized_nodes,
        "edges": normalized_edges,
        "source_format": _normalize_optional_non_empty(payload.get("source_format"))
        or "external.workflow.v1",
    }


def _normalize_mapping(raw_value: Any) -> dict[str, Any]:
    if raw_value is None:
        return {}
    if not isinstance(raw_value, Mapping):
        raise TypeError("value must be a mapping when provided.")
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


__all__ = [
    "MockSageExecutable",
    "MockWorkflowProductAdapter",
]