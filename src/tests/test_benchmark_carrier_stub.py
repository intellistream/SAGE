from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_benchmark_carrier_stub_emits_schema_complete_summary(tmp_path: Path) -> None:
    coordination_root = tmp_path / "vamos"
    (coordination_root / "results" / "tables").mkdir(parents=True)
    (coordination_root / "results" / "replays").mkdir(parents=True)
    (coordination_root / "manifests" / "experiments").mkdir(parents=True)
    experiment_manifest = coordination_root / "manifests" / "experiments" / "scenario.yaml"
    experiment_manifest.write_text("name: synthetic\n", encoding="utf-8")

    run_plan_path = coordination_root / "results" / "tables" / "run-plan.json"
    run_plan_path.write_text(
        json.dumps(
            {
                "systems": {
                    "control_plane_repo": "SAGE",
                    "coordination_repo": "VAMOS",
                    "execution_plane_repo": "vllm-hust",
                },
                "experiment": {"name": "burst-overload-baseline-matrix"},
                "metrics": {
                    "latency": ["ttft_p50_ms", "ttft_p95_ms", "e2e_p95_ms"],
                    "capacity": ["throughput_rps", "running_requests", "waiting_requests"],
                    "memory": ["kv_cache_usage_perc", "free_vram_bytes", "reserved_vram_bytes"],
                    "reliability": [
                        "slo_violation_rate",
                        "spillover_rate",
                        "reject_rate",
                        "delayed_request_rate",
                    ],
                },
                "variants": [{"kind": "baseline", "name": "fifo"}],
            }
        ),
        encoding="utf-8",
    )

    replay_path = coordination_root / "results" / "replays" / "workload.ndjson"
    replay_rows = [
        {
            "request_id": "interactive-high-0001",
            "metadata": {"phase": "steady-state", "scheduled_at_s": 0.0},
            "serving_context": {
                "deadline_class": "interactive-high",
                "priority": 100,
                "model_id": "meta-llama/Llama-3.1-8B-Instruct",
                "target_ttft_ms": 250,
                "target_e2e_ms": 1200,
                "trace_tags": {"phase": "steady-state"},
            },
        },
        {
            "request_id": "batch-standard-0002",
            "metadata": {"phase": "overload-burst", "scheduled_at_s": 1.0},
            "serving_context": {
                "deadline_class": "batch-standard",
                "priority": 20,
                "model_id": "Qwen/Qwen2.5-7B-Instruct",
                "target_ttft_ms": 2000,
                "target_e2e_ms": 20000,
                "trace_tags": {"phase": "overload-burst"},
            },
        },
    ]
    replay_path.write_text(
        "\n".join(json.dumps(row) for row in replay_rows) + "\n",
        encoding="utf-8",
    )

    output_root = tmp_path / "carrier-output"
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "tools" / "benchmark_carrier" / "main.py"

    result = subprocess.run(
        [
            sys.executable,
            str(script_path),
            "--experiment-manifest",
            str(experiment_manifest),
            "--run-plan",
            str(run_plan_path),
            "--workload-replay",
            str(replay_path),
            "--variant-kind",
            "baseline",
            "--variant-name",
            "fifo",
            "--summary-output",
            str(
                coordination_root
                / "results"
                / "summaries"
                / "burst-overload"
                / "baseline"
                / "fifo.json"
            ),
            "--trace-output",
            str(
                coordination_root
                / "results"
                / "traces"
                / "burst-overload"
                / "baseline"
                / "fifo.ndjson"
            ),
            "--raw-log-output",
            str(
                coordination_root
                / "results"
                / "raw-logs"
                / "burst-overload"
                / "baseline"
                / "fifo.ndjson"
            ),
            "--seed",
            "42",
            "--output-root",
            str(output_root),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    summary_path = (
        output_root / "results" / "summaries" / "burst-overload" / "baseline" / "fifo.json"
    )
    trace_path = output_root / "results" / "traces" / "burst-overload" / "baseline" / "fifo.ndjson"
    raw_log_path = (
        output_root / "results" / "raw-logs" / "burst-overload" / "baseline" / "fifo.ndjson"
    )
    assert summary_path.exists()
    assert trace_path.exists()
    assert raw_log_path.exists()

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["kind"] == "baseline"
    assert summary["variant"] == "fifo"
    assert summary["carrier_mode"] == "synthetic-contract-validation"
    assert set(summary["metrics"]) == {
        "ttft_p50_ms",
        "ttft_p95_ms",
        "e2e_p95_ms",
        "throughput_rps",
        "running_requests",
        "waiting_requests",
        "kv_cache_usage_perc",
        "free_vram_bytes",
        "reserved_vram_bytes",
        "slo_violation_rate",
        "spillover_rate",
        "reject_rate",
        "delayed_request_rate",
    }
