from __future__ import annotations

import importlib
import importlib.util
import json
import socket
import sys
import threading
import time
from pathlib import Path

import pytest

pytest.importorskip("langchain")
pytest.importorskip("langchain_text_splitters")

SHARED_WORKLOAD_SRC = Path(__file__).resolve().parents[3] / "llm-serving-workloads" / "src"
if SHARED_WORKLOAD_SRC.exists() and str(SHARED_WORKLOAD_SRC) not in sys.path:
    sys.path.insert(0, str(SHARED_WORKLOAD_SRC))

pytest.importorskip("llm_serving_workloads")

SCRIPT_PATH = (
    Path(__file__).resolve().parents[2] / "evaluation" / "run_langchain_sage_rag_experiment.py"
)
SPEC = importlib.util.spec_from_file_location(
    "evaluation.run_langchain_sage_rag_experiment", SCRIPT_PATH
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
runner_module = importlib.import_module("evaluation.langchain_rag.runner")
create_langchain_rpc_worker_server = importlib.import_module(
    "evaluation.langchain_rag.rpc"
).create_langchain_rpc_worker_server


def test_shared_workload_comparison_writes_separated_batch_outputs(tmp_path: Path) -> None:
    batch_dir = MODULE.run_shared_workload_comparison(
        output_root=tmp_path,
        workload_names=("rag-followup",),
        variant_names=("full_rag", "retrieval_only"),
        max_requests_per_workload=4,
        top_k=2,
        seed=7,
    )

    manifest = json.loads((batch_dir / "manifest.json").read_text(encoding="utf-8"))
    matrix = json.loads(
        (batch_dir / "comparison" / "workload_variant_matrix.json").read_text(encoding="utf-8")
    )
    by_variant = json.loads(
        (batch_dir / "comparison" / "by_variant.json").read_text(encoding="utf-8")
    )
    stage_latency = json.loads(
        (batch_dir / "comparison" / "stage_latency_by_variant.json").read_text(encoding="utf-8")
    )
    fairness_audit = json.loads(
        (batch_dir / "comparison" / "fairness_audit.json").read_text(encoding="utf-8")
    )
    run_dir = batch_dir / "runs" / "rag-followup" / "full_rag"
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    runtime_metrics = json.loads((run_dir / "runtime_metrics.json").read_text(encoding="utf-8"))
    source_stage = json.loads(
        (run_dir / "stage_metrics" / "source.json").read_text(encoding="utf-8")
    )
    retrieval_stage = json.loads(
        (run_dir / "stage_metrics" / "retrieval.json").read_text(encoding="utf-8")
    )

    assert manifest["status"] == "completed"
    assert manifest["frameworks"] == ["sage"]
    assert manifest["run_count"] == 2
    assert manifest["langchain_native_parallelism"] == 1
    assert manifest["generation_parallelism"] == 1
    assert manifest["retrieval_index_backend"] == "faiss_offline"
    assert manifest["variant_execution_policy"] == "deterministic_rotation_by_workload_and_seed"
    assert set(manifest["workload_variant_orders"]["rag-followup"]) == {
        "full_rag",
        "retrieval_only",
    }
    assert len(manifest["completed_runs"]) == 2
    assert manifest["comparison_files"]["fairness_audit"].endswith("comparison/fairness_audit.json")
    assert manifest["fairness_notes"]
    assert len(matrix["rows"]) == 2
    assert summary["query_count"] == 4
    assert summary["throughput_qps"] > 0
    assert runtime_metrics["status"] == "completed"
    assert any(stage["avg_queue_wait_ms"] is not None for stage in runtime_metrics["stages"])
    assert summary["stage_latency_ms"]["source"]["source_load_ms"] >= 0
    assert summary["stage_latency_ms"]["retrieval"]["document_count"] > 0
    assert source_stage["queries"]
    assert retrieval_stage["summary"]["retrieved_count_avg"] >= 0
    assert by_variant["variants"][0]["aggregate_method"] == "micro_by_query_count"
    assert stage_latency["aggregate_method"] == "micro_by_query_count"
    assert fairness_audit["variant_aggregate_method"] == "micro_by_query_count"
    assert fairness_audit["framework_parallelism_policy"]["langchain_native_parallelism"] == 1
    assert fairness_audit["retrieval_index_policy"]["backend"] == "faiss_offline"
    assert fairness_audit["generation_backend_policy"]["mixed_backends_allowed"] is False
    assert fairness_audit["workloads"][0]["execution_order_matches_matrix"] is True
    assert matrix["rows"][0]["framework_name"] == "sage"


def test_shared_workload_comparison_applies_fixed_source_rate(tmp_path: Path) -> None:
    batch_dir = MODULE.run_shared_workload_comparison(
        output_root=tmp_path,
        workload_names=("memory-write-then-reuse",),
        variant_names=("direct_generation",),
        max_requests_per_workload=4,
        seed=7,
        source_request_rate_qps=10.0,
    )

    manifest = json.loads((batch_dir / "manifest.json").read_text(encoding="utf-8"))
    run_dir = batch_dir / "runs" / "memory-write-then-reuse" / "direct_generation"
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    source_stage = json.loads(
        (run_dir / "stage_metrics" / "source.json").read_text(encoding="utf-8")
    )

    assert manifest["source_request_rate_qps"] == 10.0
    assert summary["stage_latency_ms"]["source"]["target_request_rate_qps"] == 10.0
    assert summary["stage_latency_ms"]["source"]["source_emission_span_ms"] >= 200.0
    assert summary["stage_latency_ms"]["source"]["achieved_request_rate_qps"] > 5.0
    assert source_stage["queries"][0]["pacing_sleep_ms"] >= 0.0


def test_shared_workload_comparison_supports_framework_comparison(tmp_path: Path) -> None:
    batch_dir = MODULE.run_shared_workload_comparison(
        output_root=tmp_path,
        framework_names=("langchain_native", "sage"),
        workload_names=("rag-followup",),
        variant_names=("direct_generation",),
        max_requests_per_workload=2,
        seed=7,
    )

    manifest = json.loads((batch_dir / "manifest.json").read_text(encoding="utf-8"))
    matrix = json.loads(
        (batch_dir / "comparison" / "workload_variant_matrix.json").read_text(encoding="utf-8")
    )
    by_variant = json.loads(
        (batch_dir / "comparison" / "by_variant.json").read_text(encoding="utf-8")
    )

    framework_names = {row["framework_name"] for row in matrix["rows"]}
    by_variant_frameworks = {row["framework_name"] for row in by_variant["variants"]}

    assert manifest["frameworks"] == ["langchain_native", "sage"]
    assert framework_names == {"langchain_native", "sage"}
    assert by_variant_frameworks == {"langchain_native", "sage"}
    assert len(manifest["completed_runs"]) == 2


def test_shared_workload_comparison_supports_flownet_sage_runtime(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter_calls: list[tuple[str, object | None]] = []

    class _FakeAdapter:
        def start(self, config=None) -> None:
            adapter_calls.append(("start", dict(config or {})))

        def stop(self) -> None:
            adapter_calls.append(("stop", None))

    monkeypatch.setattr(runner_module, "FlowNetEnvironment", runner_module.LocalEnvironment)
    monkeypatch.setattr(
        runner_module,
        "get_flownet_adapter",
        lambda auto_start=False: _FakeAdapter(),
    )

    batch_dir = MODULE.run_shared_workload_comparison(
        output_root=tmp_path,
        framework_names=("sage",),
        workload_names=("rag-followup",),
        variant_names=("direct_generation",),
        max_requests_per_workload=2,
        seed=7,
        sage_runtime_platform="flownet",
        flownet_session_mode="connect",
        flownet_entry_node="sage-node-1:19001",
        flownet_cluster="cluster8",
        flownet_connect_timeout=5.0,
    )

    manifest = json.loads((batch_dir / "manifest.json").read_text(encoding="utf-8"))
    fairness_audit = json.loads(
        (batch_dir / "comparison" / "fairness_audit.json").read_text(encoding="utf-8")
    )

    assert manifest["sage_runtime_platform"] == "flownet"
    assert manifest["flownet_session_mode"] == "connect"
    assert fairness_audit["runtime_environment_policy"] == {
        "sage_runtime_platform": "flownet",
        "flownet_session_mode": "connect",
        "flownet_entry_node": "sage-node-1:19001",
        "flownet_cluster": "cluster8",
    }
    assert adapter_calls[0] == ("stop", None)
    assert adapter_calls[1] == (
        "start",
        {
            "mode": "connect",
            "owner": "langchain-rag-benchmark",
            "entry_node": "sage-node-1:19001",
            "cluster": "cluster8",
            "connect_timeout": 5.0,
        },
    )
    assert adapter_calls[-1] == ("stop", None)


def test_shared_workload_comparison_supports_langchain_native_parallelism(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    counters = {"in_flight": 0, "max_in_flight": 0}
    counter_lock = threading.Lock()
    original_execute = runner_module.LangChainGenerationStage.execute

    def instrumented_execute(self, item):
        with counter_lock:
            counters["in_flight"] += 1
            counters["max_in_flight"] = max(counters["max_in_flight"], counters["in_flight"])
        try:
            time.sleep(0.05)
            return original_execute(self, item)
        finally:
            with counter_lock:
                counters["in_flight"] -= 1

    monkeypatch.setattr(
        runner_module.LangChainGenerationStage,
        "execute",
        instrumented_execute,
    )

    batch_dir = MODULE.run_shared_workload_comparison(
        output_root=tmp_path,
        framework_names=("langchain_native",),
        workload_names=("rag-followup",),
        variant_names=("direct_generation",),
        max_requests_per_workload=4,
        seed=7,
        langchain_native_parallelism=2,
    )

    manifest = json.loads((batch_dir / "manifest.json").read_text(encoding="utf-8"))

    assert manifest["langchain_native_parallelism"] == 2
    assert manifest["retrieval_index_backend"] == "faiss_offline"
    assert counters["max_in_flight"] >= 2


def test_shared_workload_comparison_parallel_langchain_retrieval_builds_index(
    tmp_path: Path,
) -> None:
    batch_dir = MODULE.run_shared_workload_comparison(
        output_root=tmp_path,
        framework_names=("langchain_native",),
        workload_names=("rag-followup",),
        variant_names=("retrieval_only",),
        max_requests_per_workload=4,
        seed=7,
        langchain_native_parallelism=2,
    )

    run_dir = batch_dir / "runs" / "rag-followup" / "langchain_native" / "retrieval_only"
    index_dir = run_dir / "retrieval_index"
    retrieval_stage = json.loads(
        (run_dir / "stage_metrics" / "retrieval.json").read_text(encoding="utf-8")
    )

    assert (index_dir / "index.faiss").exists()
    assert (index_dir / "records.json").exists()
    assert retrieval_stage["summary"]["chunk_count"] > 0
    assert retrieval_stage["summary"]["index_build_ms"] > 0.0
    assert all(query["retrieved_count"] > 0 for query in retrieval_stage["queries"])


def test_shared_workload_comparison_supports_langchain_rpc(tmp_path: Path) -> None:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        rpc_port = probe.getsockname()[1]

    server = create_langchain_rpc_worker_server(
        host="127.0.0.1",
        port=rpc_port,
        node_id="rpc-node-1",
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        batch_dir = MODULE.run_shared_workload_comparison(
            output_root=tmp_path,
            framework_names=("langchain_rpc",),
            workload_names=("rag-followup",),
            variant_names=("direct_generation",),
            max_requests_per_workload=4,
            seed=7,
            langchain_rpc_endpoints=(f"127.0.0.1:{rpc_port}",),
            langchain_rpc_parallelism=2,
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2.0)

    manifest = json.loads((batch_dir / "manifest.json").read_text(encoding="utf-8"))
    fairness_audit = json.loads(
        (batch_dir / "comparison" / "fairness_audit.json").read_text(encoding="utf-8")
    )
    run_dir = batch_dir / "runs" / "rag-followup" / "langchain_rpc" / "direct_generation"
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    query_results = json.loads((run_dir / "query_results.json").read_text(encoding="utf-8"))

    assert manifest["frameworks"] == ["langchain_rpc"]
    assert manifest["langchain_rpc_parallelism"] == 2
    assert manifest["langchain_rpc_endpoints"] == [f"127.0.0.1:{rpc_port}"]
    assert fairness_audit["framework_parallelism_policy"]["langchain_rpc_parallelism"] == 2
    assert fairness_audit["framework_parallelism_policy"]["langchain_rpc_endpoint_count"] == 1
    assert summary["query_count"] == 4
    assert summary["throughput_qps"] > 0
    assert all(result["rpc_node_id"] == "rpc-node-1" for result in query_results["results"])


def test_shared_workload_comparison_records_rotated_variant_orders(tmp_path: Path) -> None:
    batch_dir = MODULE.run_shared_workload_comparison(
        output_root=tmp_path,
        workload_names=("session-affine-multi-turn", "long-context-doc-analysis"),
        variant_names=("full_rag", "retrieval_only", "direct_generation"),
        max_requests_per_workload=1,
        seed=7,
    )

    manifest = json.loads((batch_dir / "manifest.json").read_text(encoding="utf-8"))
    matrix = json.loads(
        (batch_dir / "comparison" / "workload_variant_matrix.json").read_text(encoding="utf-8")
    )
    fairness_audit = json.loads(
        (batch_dir / "comparison" / "fairness_audit.json").read_text(encoding="utf-8")
    )

    expected_orders = {
        "session-affine-multi-turn": ["retrieval_only", "direct_generation", "full_rag"],
        "long-context-doc-analysis": ["direct_generation", "full_rag", "retrieval_only"],
    }
    rows = matrix["rows"]
    for workload_name, expected_order in expected_orders.items():
        assert manifest["workload_variant_orders"][workload_name] == expected_order
        observed_order = [
            row["variant_name"] for row in rows if row["workload_name"] == workload_name
        ]
        assert observed_order == expected_order

    audit_orders = {
        item["workload_name"]: item["variant_execution_order"]
        for item in fairness_audit["workloads"]
    }
    assert audit_orders == expected_orders


def test_shared_workload_comparison_keeps_batches_separate(tmp_path: Path) -> None:
    batch_a = MODULE.run_shared_workload_comparison(
        output_root=tmp_path,
        workload_names=("memory-write-then-reuse",),
        variant_names=("direct_generation",),
        max_requests_per_workload=2,
        seed=7,
    )
    batch_b = MODULE.run_shared_workload_comparison(
        output_root=tmp_path,
        workload_names=("memory-write-then-reuse",),
        variant_names=("direct_generation",),
        max_requests_per_workload=2,
        seed=7,
    )

    assert batch_a != batch_b
    assert batch_a.exists()
    assert batch_b.exists()
    assert batch_a.name != batch_b.name
