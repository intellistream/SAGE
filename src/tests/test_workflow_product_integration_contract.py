from __future__ import annotations

from sage.serving import (
    COMFY_FIRST_EXTENSION_POINT,
    LANGGRAPH_SECOND_EXTENSION_POINT,
    MockWorkflowProductAdapter,
    WorkflowImportRequest,
    WorkflowIntegrationRegistry,
    WorkflowJobResultCollectRequest,
    WorkflowJobStatusPollRequest,
    WorkflowJobSubmitRequest,
)


def _build_external_workflow_payload() -> dict[str, object]:
    return {
        "workflow_id": "external-demo-1",
        "name": "demo-external-workflow",
        "source_format": "external.mock.graph.v1",
        "nodes": [
            {"id": "load", "type": "loader", "config": {"source": "prompt"}},
            {"id": "run", "type": "inference", "config": {"model": "demo"}},
        ],
        "edges": [{"source": "load", "target": "run"}],
    }


def test_registry_snapshot_lists_registered_workflow_product_types() -> None:
    registry = WorkflowIntegrationRegistry()
    comfy_adapter = MockWorkflowProductAdapter(
        integration_type="workflow.mock.comfy",
        display_name="Mock Comfy Adapter",
        extension_points=(COMFY_FIRST_EXTENSION_POINT,),
    )
    langgraph_adapter = MockWorkflowProductAdapter(
        integration_type="workflow.mock.langgraph",
        display_name="Mock LangGraph Adapter",
        extension_points=(LANGGRAPH_SECOND_EXTENSION_POINT,),
    )

    registry.register_adapter(comfy_adapter)
    registry.register_adapter(langgraph_adapter)

    snapshot = registry.snapshot()

    assert snapshot["registered_types"] == [
        "workflow.mock.comfy",
        "workflow.mock.langgraph",
    ]
    extension_points = {
        row["extension_point_id"]: row["claimed_by"] for row in snapshot["extension_points"]
    }
    assert extension_points[COMFY_FIRST_EXTENSION_POINT] == ["workflow.mock.comfy"]
    assert extension_points[LANGGRAPH_SECOND_EXTENSION_POINT] == ["workflow.mock.langgraph"]


def test_mock_adapter_can_import_and_submit_endpoint_request_flow() -> None:
    registry = WorkflowIntegrationRegistry()
    adapter = MockWorkflowProductAdapter(
        integration_type="workflow.mock.comfy",
        display_name="Mock Comfy Adapter",
        extension_points=(COMFY_FIRST_EXTENSION_POINT,),
    )
    registry.register_adapter(adapter)

    import_request = WorkflowImportRequest(
        integration_type="workflow.mock.comfy",
        request_id="import-endpoint-request",
        workflow_payload=_build_external_workflow_payload(),
        desired_target="endpoint_request",
    )
    import_envelope = import_request.to_integration_request()

    imported = registry.import_workflow(import_request)
    submit_request = WorkflowJobSubmitRequest(
        integration_type="workflow.mock.comfy",
        request_id="submit-endpoint-request",
        imported_workflow=imported.imported_workflow,
        input_payload={"prompt": "hello"},
    )
    submit_response = registry.submit_job(submit_request)
    poll_response = registry.poll_status(
        WorkflowJobStatusPollRequest(
            integration_type="workflow.mock.comfy",
            request_id="poll-endpoint-request",
            job_id=submit_response.job_id,
        )
    )
    result_response = registry.collect_result(
        WorkflowJobResultCollectRequest(
            integration_type="workflow.mock.comfy",
            request_id="collect-endpoint-request",
            job_id=submit_response.job_id,
        )
    )

    assert import_envelope.operation == "workflow_import"
    assert imported.imported_workflow.execution_target.target_type == "endpoint_request"
    assert submit_response.submit_payload["submit_via"] == "endpoint_request"
    assert poll_response.status == "completed"
    assert result_response.status == "completed"
    assert result_response.result["target_type"] == "endpoint_request"
    assert result_response.result["submit_payload"]["body"]["input"] == {"prompt": "hello"}


def test_mock_adapter_can_import_to_sage_executable_target() -> None:
    registry = WorkflowIntegrationRegistry()
    adapter = MockWorkflowProductAdapter(
        integration_type="workflow.mock.langgraph",
        display_name="Mock LangGraph Adapter",
        extension_points=(LANGGRAPH_SECOND_EXTENSION_POINT,),
    )
    registry.register_adapter(adapter)

    imported = registry.import_workflow(
        WorkflowImportRequest(
            integration_type="workflow.mock.langgraph",
            request_id="import-sage-executable",
            workflow_payload=_build_external_workflow_payload(),
            desired_target="sage_executable",
        )
    )
    executable = imported.imported_workflow.execution_target.executable
    submit_response = registry.submit_job(
        WorkflowJobSubmitRequest(
            integration_type="workflow.mock.langgraph",
            request_id="submit-sage-executable",
            imported_workflow=imported.imported_workflow,
            input_payload={"question": "status?"},
        )
    )
    result_response = registry.collect_result(
        WorkflowJobResultCollectRequest(
            integration_type="workflow.mock.langgraph",
            request_id="collect-sage-executable",
            job_id=submit_response.job_id,
        )
    )

    assert imported.imported_workflow.execution_target.target_type == "sage_executable"
    assert executable is not None
    assert type(executable).__name__ == "MockSageExecutable"
    assert submit_response.submit_payload["submit_via"] == "sage_executable"
    assert result_response.result["target_type"] == "sage_executable"
    assert result_response.result["submit_payload"]["input"] == {"question": "status?"}