from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


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
    assert row["f1"] == 1.0
    assert row["support_evidence_recall"] == 0.875
    assert row["accepted_edit_count"] == 2
    assert row["fallback_count"] == 1
    assert row["invalid_action_count"] == 3
    assert row["invalid_schema_count"] == 1
    assert row["estimated_total_tokens"] == 507
    assert row["reduce_duration_ms"] == 321.5
    assert row["model_latency_ms"] == 319.25
    assert row["failure_taxonomy"] == {
        "missed": {"wrong_root": 2},
        "false_positive": {"over_merged_incidents": 1},
    }
    assert (tmp_path / "case_seed_summary.csv").is_file()
