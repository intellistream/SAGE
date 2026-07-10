#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path
from typing import Any


def _mean_int(costs: list[dict[str, Any]], name: str) -> float:
    values = [int(cost.get(name, 0) or 0) for cost in costs]
    return round(statistics.fmean(values), 4) if values else 0.0


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


def summarize(matrix_dir: Path) -> list[dict[str, Any]]:
    aggregate = json.loads((matrix_dir / "aggregate.json").read_text())
    rows: list[dict[str, Any]] = []
    for reducer, metrics in sorted(aggregate["by_reducer"].items()):
        suffix = reducer.replace("-", "_")
        raw_reports = [
            json.loads(path.read_text())
            for path in sorted(matrix_dir.glob(f"*_{suffix}.json"))
        ]
        costs = [report.get("cost_accounting", {}) for report in raw_reports]
        rows.append(
            {
                "reducer": reducer,
                "precision_mean": metrics["precision"]["mean"],
                "recall_mean": metrics["recall"]["mean"],
                "f1_mean": metrics["f1"]["mean"],
                "evidence_coverage_mean": metrics["evidence_coverage"]["mean"],
                "root_evidence_coverage_mean": metrics["root_evidence_coverage"][
                    "mean"
                ],
                "support_evidence_recall_mean": metrics["support_evidence_recall"][
                    "mean"
                ],
                "reduce_ms_mean": metrics["reduce_duration_ms"]["mean"],
                "detections_mean": metrics["detected_incident_count"]["mean"],
                "estimated_tokens_mean": _mean_int(costs, "estimated_total_tokens"),
                "repair_count_mean": _mean_int(costs, "repair_count"),
                "split_count_mean": _mean_int(costs, "split_count"),
                "merge_count_mean": _mean_int(costs, "merge_count"),
                "accepted_edit_count_mean": _mean_int(costs, "accepted_edit_count"),
                "fallback_count_mean": _mean_int(costs, "fallback_count"),
                "input_candidate_count_mean": _mean_int(
                    costs, "input_candidate_count"
                ),
                "input_pair_count_mean": _mean_int(costs, "input_pair_count"),
                "invalid_action_count_mean": _mean_int(
                    costs, "invalid_action_count"
                ),
                "retry_count_mean": _mean_int(costs, "retry_count"),
                "invalid_json_runs": _count_false(costs, "json_valid"),
                "invalid_schema_runs": _count_false(costs, "schema_valid"),
                "validator_reject_reasons": _count_values(
                    costs, "validator_reject_reason"
                ),
            }
        )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Summarize real-online semantic-merge LLM comparison results."
    )
    parser.add_argument("matrix_dir", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    rows = summarize(args.matrix_dir)
    text = json.dumps(rows, ensure_ascii=False, indent=2) + "\n"
    output = args.output or args.matrix_dir.parent / "comparison_summary.json"
    output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
