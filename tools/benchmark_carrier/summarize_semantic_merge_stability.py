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
import random
import statistics
from collections import Counter
from pathlib import Path
from typing import Any


TARGET_REDUCER = "llm-pairwise-action-validated"
BOOTSTRAP_SEED = 2027
BOOTSTRAP_DRAWS = 10_000


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


def _model_call(item: dict[str, Any]) -> bool:
    cost = item["report"].get("cost_accounting") or {}
    return bool(
        cost.get("provider_total_tokens") is not None
        or float(cost.get("estimated_total_tokens", 0) or 0) > 0
    )


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
    called = [item for item in group if _model_call(item)]
    called_costs = [item["report"].get("cost_accounting") or {} for item in called]
    called_latency = [float(item["report"]["reduce_duration_ms"]) for item in called]
    called_tokens = [
        float(
            cost["provider_total_tokens"]
            if cost.get("provider_total_tokens") is not None
            else cost.get("estimated_total_tokens", 0)
        )
        for cost in called_costs
    ]
    provider_observed = sum(
        cost.get("provider_total_tokens") is not None for cost in called_costs
    )
    base["model_call_runs"] = len(called)
    base["model_call_rate"] = round(len(called) / len(group), 4)
    base["called_latency_ms_median"] = (
        round(statistics.median(called_latency), 4) if called_latency else None
    )
    base["called_latency_ms_p95"] = (
        round(_percentile(called_latency, 0.95), 4) if called_latency else None
    )
    base["called_tokens_mean"] = (
        round(statistics.fmean(called_tokens), 4) if called_tokens else None
    )
    base["called_tokens_p95"] = (
        round(_percentile(called_tokens, 0.95), 4) if called_tokens else None
    )
    base["called_provider_token_runs"] = provider_observed
    base["called_provider_token_coverage"] = (
        round(provider_observed / len(called), 4) if called else None
    )
    base["request_retry_count_total"] = sum(
        int(cost.get("retry_count", 0) or 0) for cost in called_costs
    )
    return base


def _bootstrap_mean_ci(
    deltas: list[float], *, seed: int = BOOTSTRAP_SEED, draws: int = BOOTSTRAP_DRAWS
) -> tuple[float, float]:
    rng = random.Random(seed)
    means = sorted(
        statistics.fmean(rng.choices(deltas, k=len(deltas))) for _ in range(draws)
    )
    return (_percentile(means, 0.025), _percentile(means, 0.975))


def _paired_comparisons(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unit_values: dict[tuple[str, int, str], float] = {
        (str(row["scenario"]), int(row["seed"]), str(row["reducer"])): float(
            row["f1_mean"]
        )
        for row in records
    }
    reducers = sorted({str(row["reducer"]) for row in records})
    if TARGET_REDUCER not in reducers:
        return []
    results = []
    for baseline in reducers:
        if baseline == TARGET_REDUCER:
            continue
        units = sorted(
            (scenario, seed)
            for scenario, seed, reducer in unit_values
            if reducer == TARGET_REDUCER
            and (scenario, seed, baseline) in unit_values
        )
        deltas = [
            unit_values[(*unit, TARGET_REDUCER)] - unit_values[(*unit, baseline)]
            for unit in units
        ]
        if not deltas:
            continue
        low, high = _bootstrap_mean_ci(deltas)
        family_deltas: dict[str, list[float]] = {}
        for (scenario, _), delta in zip(units, deltas, strict=True):
            family_deltas.setdefault(scenario, []).append(delta)
        results.append(
            {
                "target": TARGET_REDUCER,
                "baseline": baseline,
                "independent_unit": "scenario_seed_mean_across_repeated_samples",
                "unit_count": len(units),
                "repeated_rows_are_not_independent_units": True,
                "f1_delta_mean": round(statistics.fmean(deltas), 4),
                "f1_delta_paired_bootstrap_95ci": [round(low, 4), round(high, 4)],
                "bootstrap_draws": BOOTSTRAP_DRAWS,
                "bootstrap_seed": BOOTSTRAP_SEED,
                "wins_ties_losses": {
                    "wins": sum(delta > 1e-12 for delta in deltas),
                    "ties": sum(abs(delta) <= 1e-12 for delta in deltas),
                    "losses": sum(delta < -1e-12 for delta in deltas),
                },
                "by_scenario_f1_delta": {
                    scenario: round(statistics.fmean(values), 4)
                    for scenario, values in sorted(family_deltas.items())
                },
            }
        )
    return results


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
        "paired_comparisons": _paired_comparisons(records),
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
