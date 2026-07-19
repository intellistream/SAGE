from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from tools.benchmark_carrier.summarize_semantic_merge_budget_sweep import summarize
from tools.benchmark_carrier.summarize_semantic_merge_stability import (
    _paired_comparisons,
)


def test_matrix_manifest_infers_conda_environment_from_interpreter(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    script = repo_root / "tools" / "benchmark_carrier" / "run_semantic_merge_matrix.py"
    output_root = tmp_path / "matrix-output"
    environment = dict(os.environ)
    environment.pop("CONDA_DEFAULT_ENV", None)
    environment["PYTHONPATH"] = str(repo_root / "src")

    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--seeds",
            "7",
            "--reducers",
            "hybrid-hint",
            "--scenarios",
            "ambiguous-overmerge",
            "--output-root",
            str(output_root),
            "--run-id",
            "manifest-env-test",
        ],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )

    assert result.returncode == 0, result.stderr
    manifest = json.loads(
        (output_root / "manifest-env-test" / "manifest.json").read_text(encoding="utf-8")
    )
    expected = Path(sys.prefix).name if Path(sys.prefix).parent.name == "envs" else ""
    assert manifest["conda_env"] == expected


def test_matrix_repeated_samples_have_distinct_artifacts(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    script = repo_root / "tools" / "benchmark_carrier" / "run_semantic_merge_matrix.py"
    output_root = tmp_path / "matrix-output"
    environment = {**os.environ, "PYTHONPATH": str(repo_root / "src")}

    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--seeds",
            "7",
            "--samples",
            "3",
            "--reducers",
            "hybrid-hint",
            "--scenarios",
            "single-service",
            "--output-root",
            str(output_root),
            "--run-id",
            "repeated-test",
        ],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )

    assert result.returncode == 0, result.stderr
    outdir = output_root / "repeated-test"
    rows = json.loads((outdir / "summary.json").read_text(encoding="utf-8"))
    assert [row["sample_id"] for row in rows] == [1, 2, 3]
    assert len(list(outdir.glob("single-service_seed7_hybrid_hint_sample*.json"))) == 3
    manifest = json.loads((outdir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["samples"] == 3

    stability = repo_root / "tools" / "benchmark_carrier" / "summarize_semantic_merge_stability.py"
    summary = subprocess.run(
        [sys.executable, str(stability), str(outdir)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert summary.returncode == 0, summary.stderr
    payload = json.loads(
        (output_root / "stability_summary.json").read_text(encoding="utf-8")
    )
    assert payload["evidence_label"] == "derived-artifact"
    assert payload["samples_per_case"] == 3
    assert payload["by_reducer"]["hybrid-hint"]["samples"] == 3
    assert payload["by_reducer"]["hybrid-hint"]["f1_stdev"] == 0.0
    assert payload["by_reducer"]["hybrid-hint"]["within_case_f1_stdev_max"] == 0.0
    assert payload["by_reducer"]["hybrid-hint"]["action_exact_agreement_min"] == 1.0
    assert payload["by_reducer"]["hybrid-hint"]["model_call_runs"] == 0
    assert payload["by_reducer"]["hybrid-hint"]["called_latency_ms_median"] is None


def test_paired_bootstrap_uses_case_seed_means_as_units() -> None:
    records = []
    for scenario, seed, target, baseline in (
        ("a", 7, 0.9, 0.7),
        ("a", 11, 0.8, 0.7),
        ("b", 7, 0.6, 0.7),
        ("b", 11, 0.7, 0.7),
    ):
        records.extend(
            [
                {
                    "scenario": scenario,
                    "seed": seed,
                    "reducer": "llm-pairwise-action-validated",
                    "f1_mean": target,
                    "samples": 5,
                },
                {
                    "scenario": scenario,
                    "seed": seed,
                    "reducer": "hybrid-hint",
                    "f1_mean": baseline,
                    "samples": 5,
                },
            ]
        )

    comparison = _paired_comparisons(records)[0]
    assert comparison["unit_count"] == 4
    assert comparison["repeated_rows_are_not_independent_units"] is True
    assert comparison["f1_delta_mean"] == 0.05
    assert comparison["wins_ties_losses"] == {"wins": 2, "ties": 1, "losses": 1}
    assert comparison["by_scenario_f1_delta"] == {"a": 0.15, "b": -0.05}
    assert comparison["family_cluster_count"] == 2
    assert comparison["family_cluster_definition"] == (
        "scenario_family_with_seed_rows_preserved"
    )
    low, high = comparison["f1_delta_family_clustered_bootstrap_95ci"]
    assert low <= comparison["f1_delta_mean"] <= high


def test_summary_emits_submission_facing_case_seed_rows(tmp_path: Path) -> None:
    matrix_dir = tmp_path / "matrix"
    matrix_dir.mkdir()
    (matrix_dir / "manifest.json").write_text(
        json.dumps(
            {
                "evidence_label": "real-online",
                "workload_source": {
                    "kind": "repo-local",
                    "path": "src/sage/workloads/semantic_merge_analysis.py",
                },
            }
        ),
        encoding="utf-8",
    )
    summary_row = {
        "scenario": "ambiguous-disconnected-merge",
        "seed": 11,
        "reducer": "llm-pairwise-action-validated",
        "precision": 1.0,
        "recall": 1.0,
        "f1": 1.0,
        "support_evidence_recall": 0.875,
    }
    (matrix_dir / "summary.json").write_text(json.dumps([summary_row]), encoding="utf-8")
    raw_report = {
        **summary_row,
        "reduce_duration_ms": 321.5,
        "cost_accounting": {
            "accepted_edit_count": 2,
            "fallback_count": 1,
            "invalid_action_count": 3,
            "json_valid": True,
            "schema_valid": False,
            "estimated_total_tokens": 507,
            "provider_total_tokens": 123,
            "token_measurement_source": "provider-usage",
            "latency_ms": 319.25,
            "validator_reject_reason": "affected_service_mismatch",
        },
        "missed_incidents": [
            {"failure_type": "wrong_root"},
            {"failure_type": "wrong_root"},
        ],
        "false_positive_incidents": [{"failure_type": "over_merged_incidents"}],
    }
    raw_path = matrix_dir / "ambiguous-disconnected-merge_seed11_llm_pairwise_action_validated.json"
    raw_path.write_text(json.dumps(raw_report), encoding="utf-8")
    (matrix_dir / "aggregate.json").write_text(
        json.dumps(
            {
                "by_reducer": {
                    "llm-pairwise-action-validated": {
                        "precision": {"mean": 1.0},
                        "recall": {"mean": 1.0},
                        "f1": {"mean": 1.0},
                        "evidence_coverage": {"mean": 1.0},
                        "root_evidence_coverage": {"mean": 1.0},
                        "support_evidence_recall": {"mean": 0.875},
                        "reduce_duration_ms": {"mean": 321.5},
                        "detected_incident_count": {"mean": 4.0},
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    repo_root = Path(__file__).resolve().parents[2]
    script = (
        repo_root / "tools" / "benchmark_carrier" / "summarize_semantic_merge_llm_comparison.py"
    )
    result = subprocess.run(
        [sys.executable, str(script), str(matrix_dir)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    case_rows = json.loads((tmp_path / "case_seed_summary.json").read_text(encoding="utf-8"))
    assert len(case_rows) == 1
    row = case_rows[0]
    assert row["evidence_label"] == "real-online"
    assert row["scenario"] == "ambiguous-disconnected-merge"
    assert row["seed"] == 11
    assert row["sample_id"] == 1
    assert row["f1"] == 1.0
    assert row["support_evidence_recall"] == 0.875
    assert row["accepted_edit_count"] == 2
    assert row["fallback_count"] == 1
    assert row["invalid_action_count"] == 3
    assert row["invalid_schema_count"] == 1
    assert row["estimated_total_tokens"] == 507
    assert row["provider_total_tokens"] == 123
    assert row["total_tokens"] == 123
    assert row["token_measurement_source"] == "provider-usage"
    assert row["reduce_duration_ms"] == 321.5
    assert row["model_latency_ms"] == 319.25
    assert row["failure_taxonomy"] == {
        "missed": {"wrong_root": 2},
        "false_positive": {"over_merged_incidents": 1},
    }
    assert (tmp_path / "case_seed_summary.csv").is_file()


def test_budget_summary_retains_quality_gate_outcome(tmp_path: Path) -> None:
    run = tmp_path / "candidates-4"
    run.mkdir()
    (run / "run_metadata.json").write_text(
        json.dumps(
            {
                "evidence_label": "real-online",
                "run_id": "budget-4",
                "git": {"commit": "a" * 40},
                "endpoint": {"model": "model-a"},
                "llm_reducer": {"max_candidates": 4},
                "workload": {"samples": 5},
            }
        ),
        encoding="utf-8",
    )
    comparison = {
        "reducer": "llm-pairwise-action-validated",
        "f1_mean": 0.7,
        "support_evidence_recall_mean": 0.7,
        "reduce_ms_mean": 1.0,
        "estimated_tokens_mean": 2.0,
        "total_tokens_mean": 3.0,
        "provider_tokens_observed_runs": 1,
        "fallback_count_mean": 0.0,
        "invalid_action_count_mean": 0.0,
        "invalid_schema_runs": 0,
    }
    (run / "comparison_summary.json").write_text(
        json.dumps([comparison]), encoding="utf-8"
    )
    (run / "stability_summary.json").write_text(
        json.dumps({"by_reducer": {comparison["reducer"]: {}}}), encoding="utf-8"
    )
    (run / "artifact_gate.json").write_text(
        json.dumps({"status": "FAIL", "failures": ["below baseline"]}),
        encoding="utf-8",
    )

    result = summarize([run])

    assert result["sources"][0]["artifact_gate_status"] == "FAIL"
    assert result["sources"][0]["artifact_gate_failures"] == ["below baseline"]
    assert result["curve"][0]["artifact_gate_status"] == "FAIL"
