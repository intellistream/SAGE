#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import statistics
from pathlib import Path
from typing import Any


def _mean_int(costs: list[dict[str, Any]], name: str) -> float:
    values = [int(cost.get(name, 0) or 0) for cost in costs]
    return round(statistics.fmean(values), 4) if values else 0.0


def _token_value(cost: dict[str, Any]) -> int:
    measured = cost.get("provider_total_tokens")
    return int(measured) if measured is not None else int(
        cost.get("estimated_total_tokens", 0) or 0
    )


def _count_false(costs: list[dict[str, Any]], name: str) -> int:
    return sum(1 for cost in costs if cost.get(name) is False)


def _count_values(costs: list[dict[str, Any]], name: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for cost in costs:
        value = cost.get(name)
        if value in (None, ""):
            continue
        key = str(value)
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def _failure_counts(report: dict[str, Any]) -> dict[str, dict[str, int]]:
    groups: dict[str, dict[str, int]] = {}
    for output_name, report_name in (
        ("missed", "missed_incidents"),
        ("false_positive", "false_positive_incidents"),
    ):
        counts: dict[str, int] = {}
        for item in report.get(report_name, []):
            failure_type = str(item.get("failure_type") or "unknown")
            counts[failure_type] = counts.get(failure_type, 0) + 1
        groups[output_name] = dict(sorted(counts.items()))
    return groups


def _load_manifest(matrix_dir: Path) -> dict[str, Any]:
    path = matrix_dir / "manifest.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _raw_report_path(matrix_dir: Path, summary: dict[str, Any]) -> Path:
    reducer = str(summary["reducer"])
    stem = f"{summary['scenario']}_seed{summary['seed']}_{reducer.replace('-', '_')}"
    sample_path = matrix_dir / f"{stem}_sample{int(summary.get('sample_id', 1))}.json"
    if sample_path.exists():
        return sample_path
    return matrix_dir / f"{stem}.json"


def summarize_cases(matrix_dir: Path) -> list[dict[str, Any]]:
    """Build the submission-facing per-case/per-seed evidence table."""
    summary_rows = json.loads((matrix_dir / "summary.json").read_text(encoding="utf-8"))
    manifest = _load_manifest(matrix_dir)
    evidence_label = manifest.get("evidence_label", "unknown")
    workload_source = manifest.get("workload_source", {})
    rows: list[dict[str, Any]] = []
    for summary in summary_rows:
        reducer = str(summary["reducer"])
        raw_path = _raw_report_path(matrix_dir, summary)
        report = json.loads(raw_path.read_text(encoding="utf-8"))
        cost = report.get("cost_accounting", {}) or {}
        metadata = (report.get("reducer_trace") or {}).get("metadata") or {}
        contract = metadata.get("contract_trace") or {}
        request_trace = metadata.get("request_trace") or []
        schema_valid = cost.get("schema_valid")
        json_valid = cost.get("json_valid")
        rows.append(
            {
                "evidence_label": evidence_label,
                "workload_source": workload_source,
                "scenario": summary["scenario"],
                "seed": int(summary["seed"]),
                "sample_id": int(summary.get("sample_id", 1)),
                "reducer": reducer,
                "precision": float(summary["precision"]),
                "recall": float(summary["recall"]),
                "f1": float(summary["f1"]),
                "support_evidence_recall": float(summary["support_evidence_recall"]),
                "accepted_edit_count": int(cost.get("accepted_edit_count", 0) or 0),
                "fallback_count": int(cost.get("fallback_count", 0) or 0),
                "invalid_action_count": int(cost.get("invalid_action_count", 0) or 0),
                "invalid_json_count": int(json_valid is False),
                "invalid_schema_count": int(schema_valid is False),
                "json_valid": json_valid,
                "schema_valid": schema_valid,
                "estimated_total_tokens": int(cost.get("estimated_total_tokens", 0) or 0),
                "provider_total_tokens": cost.get("provider_total_tokens"),
                "total_tokens": _token_value(cost),
                "token_measurement_source": cost.get(
                    "token_measurement_source", "char-estimate"
                ),
                "reduce_duration_ms": float(report["reduce_duration_ms"]),
                "model_latency_ms": (
                    float(cost["latency_ms"]) if cost.get("latency_ms") is not None else None
                ),
                "validator_reject_reason": cost.get("validator_reject_reason"),
                "validator_owned": contract.get("validator_owned"),
                "commit_outcome": contract.get("commit_outcome"),
                "replay_id": contract.get("replay_id"),
                "temperature": metadata.get("temperature"),
                "raw_response_retained": metadata.get("raw_response_retained"),
                "request_attempt_count": len(request_trace),
                "request_failure_count": sum(
                    item.get("status") != "ok" for item in request_trace
                ),
                "failure_taxonomy": _failure_counts(report),
            }
        )
    return rows


def _write_case_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    csv_rows = []
    for row in rows:
        csv_row = dict(row)
        csv_row["workload_source"] = json.dumps(
            csv_row["workload_source"], ensure_ascii=False, sort_keys=True
        )
        csv_row["failure_taxonomy"] = json.dumps(
            csv_row["failure_taxonomy"], ensure_ascii=False, sort_keys=True
        )
        csv_rows.append(csv_row)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(csv_rows[0]))
        writer.writeheader()
        writer.writerows(csv_rows)


def summarize(matrix_dir: Path) -> list[dict[str, Any]]:
    aggregate = json.loads((matrix_dir / "aggregate.json").read_text())
    summary_rows = json.loads((matrix_dir / "summary.json").read_text())
    rows: list[dict[str, Any]] = []
    for reducer, metrics in sorted(aggregate["by_reducer"].items()):
        raw_reports = [
            json.loads(_raw_report_path(matrix_dir, summary).read_text())
            for summary in summary_rows
            if str(summary["reducer"]) == reducer
        ]
        costs = [report.get("cost_accounting", {}) for report in raw_reports]
        rows.append(
            {
                "reducer": reducer,
                "precision_mean": metrics["precision"]["mean"],
                "recall_mean": metrics["recall"]["mean"],
                "f1_mean": metrics["f1"]["mean"],
                "evidence_coverage_mean": metrics["evidence_coverage"]["mean"],
                "root_evidence_coverage_mean": metrics["root_evidence_coverage"]["mean"],
                "support_evidence_recall_mean": metrics["support_evidence_recall"]["mean"],
                "reduce_ms_mean": metrics["reduce_duration_ms"]["mean"],
                "detections_mean": metrics["detected_incident_count"]["mean"],
                "estimated_tokens_mean": _mean_int(costs, "estimated_total_tokens"),
                "provider_tokens_observed_runs": sum(
                    cost.get("provider_total_tokens") is not None for cost in costs
                ),
                "total_tokens_mean": round(
                    statistics.fmean(_token_value(cost) for cost in costs), 4
                ) if costs else 0.0,
                "repair_count_mean": _mean_int(costs, "repair_count"),
                "split_count_mean": _mean_int(costs, "split_count"),
                "merge_count_mean": _mean_int(costs, "merge_count"),
                "accepted_edit_count_mean": _mean_int(costs, "accepted_edit_count"),
                "fallback_count_mean": _mean_int(costs, "fallback_count"),
                "input_candidate_count_mean": _mean_int(costs, "input_candidate_count"),
                "input_pair_count_mean": _mean_int(costs, "input_pair_count"),
                "invalid_action_count_mean": _mean_int(costs, "invalid_action_count"),
                "retry_count_mean": _mean_int(costs, "retry_count"),
                "invalid_json_runs": _count_false(costs, "json_valid"),
                "invalid_schema_runs": _count_false(costs, "schema_valid"),
                "validator_reject_reasons": _count_values(costs, "validator_reject_reason"),
            }
        )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Summarize real-online semantic-merge LLM comparison results."
    )
    parser.add_argument("matrix_dir", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--case-output", type=Path)
    parser.add_argument("--case-csv-output", type=Path)
    args = parser.parse_args()

    rows = summarize(args.matrix_dir)
    text = json.dumps(rows, ensure_ascii=False, indent=2) + "\n"
    output = args.output or args.matrix_dir.parent / "comparison_summary.json"
    output.write_text(text, encoding="utf-8")
    case_rows = summarize_cases(args.matrix_dir)
    case_output = args.case_output or args.matrix_dir.parent / "case_seed_summary.json"
    case_output.write_text(
        json.dumps(case_rows, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    case_csv_output = args.case_csv_output or args.matrix_dir.parent / "case_seed_summary.csv"
    _write_case_csv(case_csv_output, case_rows)
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
