from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_vamos_launcher_contract_runner_renders_launch_plan(tmp_path: Path) -> None:
    coordination_root = tmp_path / "vamos"
    (coordination_root / "manifests" / "experiments").mkdir(parents=True)
    (coordination_root / "results" / "tables").mkdir(parents=True)
    (coordination_root / "results" / "replays").mkdir(parents=True)

    contract_path = coordination_root / "results" / "tables" / "launcher-contract.json"
    contract = {
        "contract_kind": "benchmark-carrier-launcher-contract",
        "systems": {
            "control_plane_repo": "SAGE",
            "coordination_repo": "VAMOS",
            "execution_plane_repo": "vllm-hust",
        },
        "variant_launch_specs": [
            {
                "kind": "baseline",
                "name": "fifo",
                "results_namespace": "baseline/fifo",
                "run_id": "burst-overload-baseline-fifo-seed42",
                "required_captured_metadata": ["run_id", "seed", "sage_commit"],
                "command_template": {
                    "argv": [
                        "<benchmark-carrier-entrypoint>",
                        "--experiment-manifest",
                        "manifests/experiments/scenario.yaml",
                        "--run-plan",
                        "results/tables/run-plan.json",
                        "--workload-replay",
                        "results/replays/workload.ndjson",
                        "--variant-kind",
                        "baseline",
                        "--variant-name",
                        "fifo",
                        "--summary-output",
                        "results/summaries/burst-overload/baseline/fifo.json",
                        "--trace-output",
                        "results/traces/burst-overload/baseline/fifo.ndjson",
                        "--raw-log-output",
                        "results/raw-logs/burst-overload/baseline/fifo.ndjson",
                        "--seed",
                        "42",
                    ]
                },
            },
            {
                "kind": "ablation",
                "name": "no-profiling",
                "results_namespace": "ablation/no-profiling",
                "run_id": "burst-overload-ablation-no-profiling-seed42",
                "required_captured_metadata": ["run_id", "seed", "sage_commit"],
                "command_template": {
                    "argv": [
                        "<benchmark-carrier-entrypoint>",
                        "--experiment-manifest",
                        "manifests/experiments/scenario.yaml",
                        "--run-plan",
                        "results/tables/run-plan.json",
                        "--workload-replay",
                        "results/replays/workload.ndjson",
                        "--variant-kind",
                        "ablation",
                        "--variant-name",
                        "no-profiling",
                        "--summary-output",
                        "results/summaries/burst-overload/ablation/no-profiling.json",
                        "--trace-output",
                        "results/traces/burst-overload/ablation/no-profiling.ndjson",
                        "--raw-log-output",
                        "results/raw-logs/burst-overload/ablation/no-profiling.ndjson",
                        "--seed",
                        "42",
                    ]
                },
            },
        ],
    }
    contract_path.write_text(json.dumps(contract), encoding="utf-8")

    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "tools" / "scripts" / "run_vamos_launcher_contract.py"
    plan_output = tmp_path / "launch-plan.json"
    benchmark_carrier_root = tmp_path / "carrier"
    benchmark_carrier_root.mkdir()

    result = subprocess.run(
        [
            sys.executable,
            str(script_path),
            "--contract",
            str(contract_path),
            "--carrier-entrypoint",
            "python -m carrier.run",
            "--benchmark-carrier-root",
            str(benchmark_carrier_root),
            "--plan-output",
            str(plan_output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    plan = json.loads(plan_output.read_text(encoding="utf-8"))
    assert plan["variant_count"] == 2

    first = plan["variants"][0]
    assert first["command"]["argv"][:3] == ["python", "-m", "carrier.run"]
    assert first["command"]["cwd"] == str(benchmark_carrier_root.resolve())
    assert first["run_id"] == "burst-overload-baseline-fifo-seed42"
    assert first["outputs"]["summary"] == str(
        coordination_root / "results" / "summaries" / "burst-overload" / "baseline" / "fifo.json"
    )
    assert first["outputs"]["metadata"].endswith("fifo.run-metadata.json")
    assert first["metadata"]["run_id"] == "burst-overload-baseline-fifo-seed42"
    assert first["metadata"]["seed"] == 42
    assert first["execution"]["status"] == "planned"


def test_vamos_launcher_contract_runner_rewrites_metadata_into_output_root(tmp_path: Path) -> None:
    coordination_root = tmp_path / "vamos"
    (coordination_root / "manifests" / "experiments").mkdir(parents=True)
    (coordination_root / "results" / "tables").mkdir(parents=True)
    (coordination_root / "results" / "replays").mkdir(parents=True)

    contract_path = coordination_root / "results" / "tables" / "launcher-contract.json"
    contract_path.write_text(
        json.dumps(
            {
                "contract_kind": "benchmark-carrier-launcher-contract",
                "systems": {
                    "control_plane_repo": "SAGE",
                    "coordination_repo": "VAMOS",
                    "execution_plane_repo": "vllm-hust",
                },
                "variant_launch_specs": [
                    {
                        "kind": "baseline",
                        "name": "fifo",
                        "results_namespace": "baseline/fifo",
                        "run_id": "burst-overload-baseline-fifo-seed42",
                        "required_captured_metadata": ["run_id", "seed", "sage_commit"],
                        "command_template": {
                            "argv": [
                                "<benchmark-carrier-entrypoint>",
                                "--experiment-manifest",
                                "manifests/experiments/scenario.yaml",
                                "--run-plan",
                                "results/tables/run-plan.json",
                                "--workload-replay",
                                "results/replays/workload.ndjson",
                                "--variant-kind",
                                "baseline",
                                "--variant-name",
                                "fifo",
                                "--summary-output",
                                "results/summaries/burst-overload/baseline/fifo.json",
                                "--trace-output",
                                "results/traces/burst-overload/baseline/fifo.ndjson",
                                "--raw-log-output",
                                "results/raw-logs/burst-overload/baseline/fifo.ndjson",
                                "--seed",
                                "42",
                            ]
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    output_root = tmp_path / "sandbox"
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "tools" / "scripts" / "run_vamos_launcher_contract.py"
    plan_output = tmp_path / "launch-plan.json"
    benchmark_carrier_root = tmp_path / "carrier"
    benchmark_carrier_root.mkdir()

    result = subprocess.run(
        [
            sys.executable,
            str(script_path),
            "--contract",
            str(contract_path),
            "--carrier-entrypoint",
            f"python -m carrier.run --output-root {output_root}",
            "--benchmark-carrier-root",
            str(benchmark_carrier_root),
            "--plan-output",
            str(plan_output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    plan = json.loads(plan_output.read_text(encoding="utf-8"))
    first = plan["variants"][0]
    assert first["run_id"] == "burst-overload-baseline-fifo-seed42"
    assert first["metadata"]["run_id"] == "burst-overload-baseline-fifo-seed42"
    assert first["outputs"]["metadata"] == str(
        output_root
        / "results"
        / "summaries"
        / "burst-overload"
        / "baseline"
        / "fifo.run-metadata.json"
    )
