#!/usr/bin/env python3
"""Summarize repeated Semantic MapReduce reducer samples.

This is a derived-artifact aggregator. It never upgrades replay, simulation, or
probe inputs to real-online evidence; the output inherits its evidence label
from the matrix manifest.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import statistics
from collections import Counter
from pathlib import Path
from typing import Any


def _raw_report_path(matrix_dir: Path, row: dict[str, Any]) -> Path:
    reducer = str(row["reducer"])
    stem = f"{row['scenario']}_seed{row['seed']}_{reducer.replace('-', '_')}"
    sample_path = matrix_dir / f"{stem}_sample{int(row.get('sample_id', 1))}.json"
    return sample_path if sample_path.exists() else matrix_dir / f"{stem}.json"


def _percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = round((len(ordered) - 1) * fraction)
    return float(ordered[index])


def _action_signature(report: dict[str, Any]) -> str:
    metadata = (report.get("reducer_trace") or {}).get("metadata") or {}
    actions = metadata.get("action_trace") or []
    normalized = [
        {
            "pair": int(item.get("pair", -1)),
            "action": str(item.get("action", "")),
            "valid": bool(item.get("valid", False)),
        }
        for item in actions
    ]
    return hashlib.sha256(
        json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _group_summary(group: list[dict[str, Any]]) -> dict[str, Any]:
    f1 = [float(item["row"]["f1"]) for item in group]
    latency = [float(item["report"]["reduce_duration_ms"]) for item in group]
    costs = [item["report"].get("cost_accounting") or {} for item in group]
    tokens = [
        float(
            cost["provider_total_tokens"]
            if cost.get("provider_total_tokens") is not None
            else cost.get("estimated_total_tokens", 0)
        )
        for cost in costs
    ]
    signatures = Counter(_action_signature(item["report"]) for item in group)
    modal = signatures.most_common(1)[0][1] if signatures else 0
    return {
        "samples": len(group),
        "f1_mean": round(statistics.fmean(f1), 4),
        "f1_stdev": round(statistics.pstdev(f1), 4),
        "f1_min": min(f1),
        "f1_max": max(f1),
        "latency_ms_median": round(statistics.median(latency), 4),
        "latency_ms_p95": round(_percentile(latency, 0.95), 4),
        "tokens_mean": round(statistics.fmean(tokens), 4),
        "tokens_p95": round(_percentile(tokens, 0.95), 4),
        "provider_tokens_observed_runs": sum(
            cost.get("provider_total_tokens") is not None for cost in costs
        ),
        "action_exact_agreement": round(modal / len(group), 4),
        "unique_action_signatures": len(signatures),
        "fallback_runs": sum(
            int((item["report"].get("cost_accounting") or {}).get("fallback_count", 0)) > 0
            for item in group
        ),
        "invalid_action_runs": sum(
            int((item["report"].get("cost_accounting") or {}).get("invalid_action_count", 0)) > 0
            for item in group
        ),
        "invalid_schema_runs": sum(
            (item["report"].get("cost_accounting") or {}).get("schema_valid") is False
            for item in group
        ),
    }


def _reducer_summary(
    group: list[dict[str, Any]], case_records: list[dict[str, Any]]
) -> dict[str, Any]:
    base = _group_summary(group)
    agreements = [float(record["action_exact_agreement"]) for record in case_records]
    within_stdev = [float(record["f1_stdev"]) for record in case_records]
    base.pop("action_exact_agreement", None)
    base.pop("unique_action_signatures", None)
    base["case_seed_count"] = len(case_records)
    base["within_case_f1_stdev_mean"] = round(statistics.fmean(within_stdev), 4)
    base["within_case_f1_stdev_max"] = round(max(within_stdev), 4)
    base["action_exact_agreement_mean"] = round(statistics.fmean(agreements), 4)
    base["action_exact_agreement_min"] = round(min(agreements), 4)
    return base


def summarize(matrix_dir: Path) -> dict[str, Any]:
    manifest = json.loads((matrix_dir / "manifest.json").read_text(encoding="utf-8"))
    rows = json.loads((matrix_dir / "summary.json").read_text(encoding="utf-8"))
    records: list[dict[str, Any]] = []
    grouped: dict[tuple[str, int, str], list[dict[str, Any]]] = {}
    by_reducer: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        report = json.loads(_raw_report_path(matrix_dir, row).read_text(encoding="utf-8"))
        item = {"row": row, "report": report}
        grouped.setdefault(
            (str(row["scenario"]), int(row["seed"]), str(row["reducer"])), []
        ).append(item)
        by_reducer.setdefault(str(row["reducer"]), []).append(item)
    for (scenario, seed, reducer), group in sorted(grouped.items()):
        records.append(
            {"scenario": scenario, "seed": seed, "reducer": reducer, **_group_summary(group)}
        )
    return {
        "evidence_label": "derived-artifact",
        "source_evidence_label": manifest.get("evidence_label", "unknown"),
        "source_run_id": manifest.get("run_id", matrix_dir.name),
        "source_matrix": str(matrix_dir),
        "samples_per_case": int(manifest.get("samples", 1)),
        "case_seed_reducer": records,
        "by_reducer": {
            reducer: _reducer_summary(
                group,
                [record for record in records if record["reducer"] == reducer],
            )
            for reducer, group in sorted(by_reducer.items())
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("matrix_dir", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--csv-output", type=Path)
    args = parser.parse_args()
    result = summarize(args.matrix_dir)
    output = args.output or args.matrix_dir.parent / "stability_summary.json"
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    csv_output = args.csv_output or args.matrix_dir.parent / "stability_summary.csv"
    rows = result["case_seed_reducer"]
    with csv_output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
