from __future__ import annotations

import pytest

from sage.serving import (
    COMFY_FIRST_EXTENSION_POINT,
    LANGGRAPH_SECOND_EXTENSION_POINT,
    MockWorkflowProductAdapter,
    WorkflowImportRequest,
    WorkflowIntegrationRegistry,
    WorkflowJobResultCollectRequest,
    WorkflowJobStatusPollRequest,
    WorkflowJobSubmitRequest,
    WorkflowServingRequestContext,
    build_workflow_integration_registry_from_env,
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


def test_workflow_import_request_to_envelope_carries_serving_context() -> None:
    request = WorkflowImportRequest(
        integration_type="workflow.mock.comfy",
        request_id="vamos-import-request",
        workflow_payload=_build_external_workflow_payload(),
        desired_target="endpoint_request",
        serving_context=WorkflowServingRequestContext(
            tenant_id="tenant-a",
            model_id="meta-llama/Llama-3.1-8B-Instruct",
            prefix_cache_key="tenant-a:incident-summary:v1",
            prompt_len=512,
            max_tokens=128,
            priority=100,
            deadline_class="interactive-high",
            target_ttft_ms=300.0,
            target_e2e_ms=1500.0,
            accelerator_affinity="gpu",
            cost_class="gold",
            streaming=True,
            trace_tags={"phase": "phase-1", "workload": "interactive"},
        ),
    )

    envelope = request.to_integration_request()

    assert envelope.serving_context is not None
    assert envelope.serving_context.tenant_id == "tenant-a"
    assert envelope.serving_context.model_id == "meta-llama/Llama-3.1-8B-Instruct"
    assert envelope.serving_context.prefix_cache_key == "tenant-a:incident-summary:v1"
    assert envelope.serving_context.prompt_len == 512
    assert envelope.serving_context.target_ttft_ms == 300.0
    assert envelope.to_dict()["serving_context"]["trace_tags"] == {
        "phase": "phase-1",
        "workload": "interactive",
    }


def test_workflow_job_submit_request_normalizes_mapping_serving_context() -> None:
    registry = WorkflowIntegrationRegistry()
    adapter = MockWorkflowProductAdapter(
        integration_type="workflow.mock.comfy",
        display_name="Mock Comfy Adapter",
        extension_points=(COMFY_FIRST_EXTENSION_POINT,),
    )
    registry.register_adapter(adapter)
    imported = registry.import_workflow(
        WorkflowImportRequest(
            integration_type="workflow.mock.comfy",
            request_id="submit-serving-context-import",
            workflow_payload=_build_external_workflow_payload(),
        )
    )

    submit_request = WorkflowJobSubmitRequest(
        integration_type="workflow.mock.comfy",
        request_id="submit-serving-context",
        imported_workflow=imported.imported_workflow,
        input_payload={"prompt": "hello"},
        serving_context={
            "tenant_id": "tenant-b",
            "model_id": "Qwen/Qwen2.5-7B-Instruct",
            "prefix_cache_key": "tenant-b:comparative-report:v1",
            "prompt_len": "256",
            "max_tokens": "64",
            "priority": "20",
            "deadline_class": "batch-standard",
            "target_ttft_ms": "1200",
            "target_e2e_ms": "10000",
            "accelerator_affinity": "gpu",
            "cost_class": "standard",
            "streaming": False,
            "trace_tags": {"suite": "contract", "case": "submit"},
        },
    )

    envelope = submit_request.to_integration_request()

    assert envelope.serving_context is not None
    assert envelope.serving_context.prompt_len == 256
    assert envelope.serving_context.max_tokens == 64
    assert envelope.serving_context.priority == 20
    assert envelope.serving_context.prefix_cache_key == "tenant-b:comparative-report:v1"
    assert envelope.serving_context.streaming is False
    assert envelope.serving_context.trace_tags == {"suite": "contract", "case": "submit"}


def test_serving_context_rejects_negative_latency_target() -> None:
    with pytest.raises(ValueError, match="target_ttft_ms"):
        WorkflowServingRequestContext(target_ttft_ms=-1)


def test_registry_import_preserves_serving_context_in_imported_workflow_metadata() -> None:
    registry = WorkflowIntegrationRegistry()
    adapter = MockWorkflowProductAdapter(
        integration_type="workflow.mock.comfy",
        display_name="Mock Comfy Adapter",
        extension_points=(COMFY_FIRST_EXTENSION_POINT,),
    )
    registry.register_adapter(adapter)

    imported = registry.import_workflow(
        WorkflowImportRequest(
            integration_type="workflow.mock.comfy",
            request_id="import-serving-context-registry",
            workflow_payload=_build_external_workflow_payload(),
            serving_context={
                "tenant_id": "tenant-a",
                "model_id": "meta-llama/Llama-3.1-8B-Instruct",
                "prefix_cache_key": "tenant-a:incident-summary:v1",
                "priority": 100,
                "deadline_class": "interactive-high",
                "streaming": True,
                "trace_tags": {"path": "import"},
            },
        )
    )

    assert imported.imported_workflow.metadata["serving_context"] == {
        "tenant_id": "tenant-a",
        "model_id": "meta-llama/Llama-3.1-8B-Instruct",
        "prefix_cache_key": "tenant-a:incident-summary:v1",
        "prompt_len": None,
        "max_tokens": None,
        "priority": 100,
        "deadline_class": "interactive-high",
        "target_ttft_ms": None,
        "target_e2e_ms": None,
        "accelerator_affinity": None,
        "cost_class": None,
        "streaming": True,
        "trace_tags": {"path": "import"},
    }


def test_registry_submit_surfaces_serving_context_for_adapter_consumers() -> None:
    registry = WorkflowIntegrationRegistry()
    adapter = MockWorkflowProductAdapter(
        integration_type="workflow.mock.comfy",
        display_name="Mock Comfy Adapter",
        extension_points=(COMFY_FIRST_EXTENSION_POINT,),
    )
    registry.register_adapter(adapter)
    imported = registry.import_workflow(
        WorkflowImportRequest(
            integration_type="workflow.mock.comfy",
            request_id="submit-serving-context-registry-import",
            workflow_payload=_build_external_workflow_payload(),
        )
    )

    submit_response = registry.submit_job(
        WorkflowJobSubmitRequest(
            integration_type="workflow.mock.comfy",
            request_id="submit-serving-context-registry",
            imported_workflow=imported.imported_workflow,
            input_payload={"prompt": "hello"},
            serving_context={
                "tenant_id": "tenant-b",
                "model_id": "Qwen/Qwen2.5-7B-Instruct",
                "prefix_cache_key": "tenant-b:comparative-report:v1",
                "prompt_len": 256,
                "max_tokens": 64,
                "priority": 20,
                "deadline_class": "batch-standard",
                "target_ttft_ms": 1200,
                "target_e2e_ms": 10000,
                "accelerator_affinity": "gpu",
                "cost_class": "standard",
                "streaming": False,
                "trace_tags": {"path": "submit"},
            },
        )
    )
    result_response = registry.collect_result(
        WorkflowJobResultCollectRequest(
            integration_type="workflow.mock.comfy",
            request_id="collect-serving-context-registry",
            job_id=submit_response.job_id,
        )
    )

    assert (
        submit_response.submit_payload["serving_context"]["model_id"] == "Qwen/Qwen2.5-7B-Instruct"
    )
    assert (
        submit_response.submit_payload["serving_context"]["prefix_cache_key"]
        == "tenant-b:comparative-report:v1"
    )
    assert submit_response.metadata["serving_context"]["tenant_id"] == "tenant-b"
    assert result_response.result["serving_context"]["trace_tags"] == {"path": "submit"}


def test_registry_supports_two_slo_classes_and_multi_model_routing_contexts() -> None:
    registry = WorkflowIntegrationRegistry()
    adapter = MockWorkflowProductAdapter(
        integration_type="workflow.mock.comfy",
        display_name="Mock Comfy Adapter",
        extension_points=(COMFY_FIRST_EXTENSION_POINT,),
    )
    registry.register_adapter(adapter)

    interactive_import = registry.import_workflow(
        WorkflowImportRequest(
            integration_type="workflow.mock.comfy",
            request_id="interactive-import",
            workflow_payload=_build_external_workflow_payload(),
            serving_context={
                "tenant_id": "tenant-a",
                "model_id": "meta-llama/Llama-3.1-8B-Instruct",
                "prefix_cache_key": "shared:interactive:v1",
                "priority": 100,
                "deadline_class": "interactive-high",
                "target_ttft_ms": 300,
                "target_e2e_ms": 1500,
                "accelerator_affinity": "gpu",
                "cost_class": "gold",
                "streaming": True,
                "trace_tags": {"class": "interactive"},
            },
        )
    )
    batch_import = registry.import_workflow(
        WorkflowImportRequest(
            integration_type="workflow.mock.comfy",
            request_id="batch-import",
            workflow_payload=_build_external_workflow_payload(),
            serving_context={
                "tenant_id": "tenant-b",
                "model_id": "Qwen/Qwen2.5-7B-Instruct",
                "prefix_cache_key": "shared:batch:v1",
                "priority": 20,
                "deadline_class": "batch-standard",
                "target_ttft_ms": 1200,
                "target_e2e_ms": 10000,
                "accelerator_affinity": "gpu",
                "cost_class": "standard",
                "streaming": False,
                "trace_tags": {"class": "batch"},
            },
        )
    )

    interactive_submit = registry.submit_job(
        WorkflowJobSubmitRequest(
            integration_type="workflow.mock.comfy",
            request_id="interactive-submit",
            imported_workflow=interactive_import.imported_workflow,
            input_payload={"prompt": "short question"},
            serving_context=interactive_import.imported_workflow.metadata["serving_context"],
        )
    )
    batch_submit = registry.submit_job(
        WorkflowJobSubmitRequest(
            integration_type="workflow.mock.comfy",
            request_id="batch-submit",
            imported_workflow=batch_import.imported_workflow,
            input_payload={"prompt": "long batch prompt"},
            serving_context=batch_import.imported_workflow.metadata["serving_context"],
        )
    )

    assert (
        interactive_submit.submit_payload["serving_context"]["deadline_class"] == "interactive-high"
    )
    assert (
        interactive_submit.submit_payload["serving_context"]["model_id"]
        == "meta-llama/Llama-3.1-8B-Instruct"
    )
    assert (
        interactive_submit.submit_payload["serving_context"]["prefix_cache_key"]
        == "shared:interactive:v1"
    )
    assert batch_submit.submit_payload["serving_context"]["deadline_class"] == "batch-standard"
    assert batch_submit.submit_payload["serving_context"]["model_id"] == "Qwen/Qwen2.5-7B-Instruct"
    assert batch_submit.submit_payload["serving_context"]["prefix_cache_key"] == "shared:batch:v1"


def test_mock_adapter_policy_hook_shapes_serving_context_for_endpoint_submit() -> None:
    registry = WorkflowIntegrationRegistry()
    adapter = MockWorkflowProductAdapter(
        integration_type="workflow.mock.comfy",
        display_name="Mock Comfy Adapter",
        extension_points=(COMFY_FIRST_EXTENSION_POINT,),
        policy_variant_kind="baseline",
        policy_variant_name="vamos-slo-feasibility-controller",
        execution_priority_mode="invert-vamos",
        policy_load_snapshot={
            "num_requests_running": 3.0,
            "num_requests_waiting": 1.0,
            "kv_cache_usage_perc": 0.08,
        },
    )
    registry.register_adapter(adapter)

    imported = registry.import_workflow(
        WorkflowImportRequest(
            integration_type="workflow.mock.comfy",
            request_id="policy-hook-import",
            workflow_payload=_build_external_workflow_payload(),
        )
    )

    submit_response = registry.submit_job(
        WorkflowJobSubmitRequest(
            integration_type="workflow.mock.comfy",
            request_id="policy-hook-submit",
            imported_workflow=imported.imported_workflow,
            input_payload={"prompt": "hello"},
            serving_context={
                "tenant_id": "tenant-a",
                "model_id": "meta-llama/Llama-3.1-8B-Instruct",
                "prefix_cache_key": "tenant-a:incident-summary:v1",
                "prompt_len": 256,
                "max_tokens": 128,
                "priority": 100,
                "deadline_class": "interactive-high",
                "target_ttft_ms": 300,
                "target_e2e_ms": 1500,
                "streaming": True,
            },
        )
    )

    shaped = submit_response.submit_payload["serving_context"]
    decision = submit_response.submit_payload["policy_decision"]
    assert shaped["max_tokens"] == 16
    assert shaped["priority"] == -100
    assert decision["variant_name"] == "vamos-slo-feasibility-controller"
    assert decision["requested_max_tokens"] == 128
    assert decision["effective_max_tokens"] == 16
    assert decision["deadline_class_cap_profile"] == "static"


def test_mock_adapter_policy_hook_is_opt_in_and_default_submit_is_unchanged() -> None:
    registry = WorkflowIntegrationRegistry()
    adapter = MockWorkflowProductAdapter(
        integration_type="workflow.mock.comfy",
        display_name="Mock Comfy Adapter",
        extension_points=(COMFY_FIRST_EXTENSION_POINT,),
    )
    registry.register_adapter(adapter)

    imported = registry.import_workflow(
        WorkflowImportRequest(
            integration_type="workflow.mock.comfy",
            request_id="policy-hook-default-import",
            workflow_payload=_build_external_workflow_payload(),
        )
    )

    submit_response = registry.submit_job(
        WorkflowJobSubmitRequest(
            integration_type="workflow.mock.comfy",
            request_id="policy-hook-default-submit",
            imported_workflow=imported.imported_workflow,
            input_payload={"prompt": "hello"},
            serving_context={
                "model_id": "meta-llama/Llama-3.1-8B-Instruct",
                "max_tokens": 128,
                "priority": 100,
                "deadline_class": "interactive-high",
            },
        )
    )

    shaped = submit_response.submit_payload["serving_context"]
    assert shaped["max_tokens"] == 128
    assert shaped["priority"] == 100
    assert "policy_decision" not in submit_response.submit_payload


def test_registry_policy_hook_shapes_submit_request_for_plain_adapter() -> None:
    registry = WorkflowIntegrationRegistry(
        policy_variant_kind="baseline",
        policy_variant_name="vamos-slo-feasibility-controller",
        execution_priority_mode="invert-vamos",
        policy_load_snapshot={
            "num_requests_running": 3.0,
            "num_requests_waiting": 1.0,
            "kv_cache_usage_perc": 0.08,
        },
    )
    adapter = MockWorkflowProductAdapter(
        integration_type="workflow.mock.comfy",
        display_name="Mock Comfy Adapter",
        extension_points=(COMFY_FIRST_EXTENSION_POINT,),
    )
    registry.register_adapter(adapter)
    imported = registry.import_workflow(
        WorkflowImportRequest(
            integration_type="workflow.mock.comfy",
            request_id="registry-policy-import",
            workflow_payload=_build_external_workflow_payload(),
        )
    )

    submit_response = registry.submit_job(
        WorkflowJobSubmitRequest(
            integration_type="workflow.mock.comfy",
            request_id="registry-policy-submit",
            imported_workflow=imported.imported_workflow,
            input_payload={"prompt": "hello"},
            serving_context={
                "model_id": "meta-llama/Llama-3.1-8B-Instruct",
                "max_tokens": 128,
                "priority": 100,
                "deadline_class": "interactive-high",
                "target_e2e_ms": 1500,
            },
        )
    )

    shaped = submit_response.submit_payload["serving_context"]
    assert shaped["max_tokens"] == 16
    assert shaped["priority"] == 100
    assert submit_response.metadata["policy_decision"]["applied_by"] == "registry"
    assert submit_response.metadata["policy_decision"]["effective_max_tokens"] == 16
    assert submit_response.metadata["policy_decision"]["mapped_priority"] == -100


def test_registry_policy_hook_skips_adapter_with_builtin_policy() -> None:
    registry = WorkflowIntegrationRegistry(
        policy_variant_kind="baseline",
        policy_variant_name="vamos-slo-feasibility-controller",
        execution_priority_mode="invert-vamos",
        policy_load_snapshot={
            "num_requests_running": 3.0,
            "num_requests_waiting": 1.0,
            "kv_cache_usage_perc": 0.08,
        },
    )
    adapter = MockWorkflowProductAdapter(
        integration_type="workflow.mock.comfy",
        display_name="Mock Comfy Adapter",
        extension_points=(COMFY_FIRST_EXTENSION_POINT,),
        policy_variant_kind="baseline",
        policy_variant_name="vamos-slo-feasibility-controller",
        execution_priority_mode="invert-vamos",
        policy_load_snapshot={
            "num_requests_running": 3.0,
            "num_requests_waiting": 1.0,
            "kv_cache_usage_perc": 0.08,
        },
    )
    registry.register_adapter(adapter)
    imported = registry.import_workflow(
        WorkflowImportRequest(
            integration_type="workflow.mock.comfy",
            request_id="registry-policy-skip-import",
            workflow_payload=_build_external_workflow_payload(),
        )
    )

    submit_response = registry.submit_job(
        WorkflowJobSubmitRequest(
            integration_type="workflow.mock.comfy",
            request_id="registry-policy-skip-submit",
            imported_workflow=imported.imported_workflow,
            input_payload={"prompt": "hello"},
            serving_context={
                "model_id": "meta-llama/Llama-3.1-8B-Instruct",
                "max_tokens": 128,
                "priority": 100,
                "deadline_class": "interactive-high",
                "target_e2e_ms": 1500,
            },
        )
    )

    assert submit_response.metadata.get("policy_decision") is None
    assert submit_response.submit_payload["policy_decision"]["variant_name"] == "vamos-slo-feasibility-controller"


def test_build_registry_from_env_applies_policy_config() -> None:
    registry = build_workflow_integration_registry_from_env(
        env={
            "SAGE_WORKFLOW_POLICY_VARIANT_KIND": "baseline",
            "SAGE_WORKFLOW_POLICY_VARIANT_NAME": "vamos-slo-feasibility-controller",
            "SAGE_WORKFLOW_POLICY_EXECUTION_PRIORITY_MODE": "invert-vamos",
            "SAGE_WORKFLOW_POLICY_LOAD_SNAPSHOT_JSON": "{\"num_requests_running\": 2, \"num_requests_waiting\": 1, \"kv_cache_usage_perc\": 0.06}",
        }
    )
    adapter = MockWorkflowProductAdapter(
        integration_type="workflow.mock.comfy",
        display_name="Mock Comfy Adapter",
        extension_points=(COMFY_FIRST_EXTENSION_POINT,),
    )
    registry.register_adapter(adapter)
    imported = registry.import_workflow(
        WorkflowImportRequest(
            integration_type="workflow.mock.comfy",
            request_id="env-policy-import",
            workflow_payload=_build_external_workflow_payload(),
        )
    )
    submit_response = registry.submit_job(
        WorkflowJobSubmitRequest(
            integration_type="workflow.mock.comfy",
            request_id="env-policy-submit",
            imported_workflow=imported.imported_workflow,
            input_payload={"prompt": "hello"},
            serving_context={
                "model_id": "meta-llama/Llama-3.1-8B-Instruct",
                "max_tokens": 128,
                "priority": 100,
                "deadline_class": "interactive-high",
                "target_e2e_ms": 1500,
            },
        )
    )

    assert submit_response.submit_payload["serving_context"]["max_tokens"] == 16
    assert submit_response.metadata["policy_decision"]["mapped_priority"] == -100
    assert submit_response.metadata["policy_decision"]["applied_by"] == "registry"


def test_build_registry_from_env_direct_metrics_override_json() -> None:
    registry = build_workflow_integration_registry_from_env(
        env={
            "SAGE_WORKFLOW_POLICY_VARIANT_KIND": "ablation",
            "SAGE_WORKFLOW_POLICY_VARIANT_NAME": "adaptive-controller",
            "SAGE_WORKFLOW_POLICY_LOAD_SNAPSHOT_JSON": "{\"num_requests_running\": 0, \"num_requests_waiting\": 0, \"kv_cache_usage_perc\": 0.0}",
            "SAGE_WORKFLOW_POLICY_NUM_REQUESTS_RUNNING": "3",
            "SAGE_WORKFLOW_POLICY_NUM_REQUESTS_WAITING": "1",
            "SAGE_WORKFLOW_POLICY_KV_CACHE_USAGE_PERC": "0.06",
        }
    )
    adapter = MockWorkflowProductAdapter(
        integration_type="workflow.mock.comfy",
        display_name="Mock Comfy Adapter",
        extension_points=(COMFY_FIRST_EXTENSION_POINT,),
    )
    registry.register_adapter(adapter)
    imported = registry.import_workflow(
        WorkflowImportRequest(
            integration_type="workflow.mock.comfy",
            request_id="env-override-import",
            workflow_payload=_build_external_workflow_payload(),
        )
    )
    submit_response = registry.submit_job(
        WorkflowJobSubmitRequest(
            integration_type="workflow.mock.comfy",
            request_id="env-override-submit",
            imported_workflow=imported.imported_workflow,
            input_payload={"prompt": "hello"},
            serving_context={
                "model_id": "meta-llama/Llama-3.1-8B-Instruct",
                "max_tokens": 512,
                "priority": 100,
                "deadline_class": "interactive-high",
                "target_e2e_ms": 1500,
            },
        )
    )

    assert submit_response.submit_payload["serving_context"]["max_tokens"] == 256
    assert submit_response.metadata["policy_decision"]["deadline_class_cap_profile"] == "overload"


def test_build_registry_from_env_defaults_enable_policy() -> None:
    registry = build_workflow_integration_registry_from_env(env={})
    adapter = MockWorkflowProductAdapter(
        integration_type="workflow.mock.comfy",
        display_name="Mock Comfy Adapter",
        extension_points=(COMFY_FIRST_EXTENSION_POINT,),
    )
    registry.register_adapter(adapter)
    imported = registry.import_workflow(
        WorkflowImportRequest(
            integration_type="workflow.mock.comfy",
            request_id="env-defaults-import",
            workflow_payload=_build_external_workflow_payload(),
        )
    )
    submit_response = registry.submit_job(
        WorkflowJobSubmitRequest(
            integration_type="workflow.mock.comfy",
            request_id="env-defaults-submit",
            imported_workflow=imported.imported_workflow,
            input_payload={"prompt": "hello"},
            serving_context={
                "model_id": "meta-llama/Llama-3.1-8B-Instruct",
                "max_tokens": 128,
                "priority": 100,
                "deadline_class": "interactive-high",
                "target_e2e_ms": 1500,
            },
        )
    )

    assert submit_response.submit_payload["serving_context"]["max_tokens"] == 16
    assert submit_response.metadata["policy_decision"]["variant_kind"] == "baseline"
    assert (
        submit_response.metadata["policy_decision"]["variant_name"]
        == "vamos-slo-feasibility-controller"
    )
    assert submit_response.metadata["policy_decision"]["execution_priority_mode"] == "invert-vamos"
