#!/usr/bin/env python3
"""Aggregate real-online Semantic MapReduce candidate-budget runs.

The output is a derived artifact whose source rows retain their real-online
provenance. It describes quality, latency, and estimated token cost; it does not
claim a serving-performance speedup.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def summarize(run_dirs: list[Path]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    sources: list[dict[str, Any]] = []
    for run_dir in run_dirs:
        metadata = json.loads((run_dir / "run_metadata.json").read_text(encoding="utf-8"))
        comparison = json.loads(
            (run_dir / "comparison_summary.json").read_text(encoding="utf-8")
        )
        stability = json.loads(
            (run_dir / "stability_summary.json").read_text(encoding="utf-8")
        )
        if metadata.get("evidence_label") != "real-online":
            raise ValueError(f"source run is not real-online: {run_dir}")
        budget = int(metadata["llm_reducer"]["max_candidates"])
        model = str(metadata["endpoint"]["model"])
        sources.append(
            {
                "run_id": metadata["run_id"],
                "path": str(run_dir),
                "parent_commit": metadata["git"]["commit"],
                "model": model,
                "candidate_budget": budget,
                "samples": int(metadata["workload"].get("samples", 1)),
            }
        )
        stability_by_reducer = stability.get("by_reducer", {})
        for item in comparison:
            reducer = str(item["reducer"])
            stable = stability_by_reducer.get(reducer, {})
            rows.append(
                {
                    "model": model,
                    "candidate_budget": budget,
                    "reducer": reducer,
                    "f1_mean": float(item["f1_mean"]),
                    "support_evidence_recall_mean": float(
                        item["support_evidence_recall_mean"]
                    ),
                    "reduce_ms_mean": float(item["reduce_ms_mean"]),
                    "latency_ms_p95": float(stable.get("latency_ms_p95", 0)),
                    "estimated_tokens_mean": float(item["estimated_tokens_mean"]),
                    "total_tokens_mean": float(item["total_tokens_mean"]),
                    "provider_tokens_observed_runs": int(
                        item["provider_tokens_observed_runs"]
                    ),
                    "tokens_p95": float(stable.get("tokens_p95", 0)),
                    "action_exact_agreement_mean": float(
                        stable.get("action_exact_agreement_mean", 0)
                    ),
                    "fallback_count_mean": float(item["fallback_count_mean"]),
                    "invalid_action_count_mean": float(
                        item["invalid_action_count_mean"]
                    ),
                    "invalid_schema_runs": int(item["invalid_schema_runs"]),
                }
            )
    return {
        "evidence_label": "derived-artifact",
        "source_evidence_label": "real-online",
        "interpretation": (
            "Quality/latency/estimated-token tradeoff over controlled candidate "
            "budgets; latency is reducer latency, not end-to-end serving speedup."
        ),
        "sources": sorted(sources, key=lambda item: item["candidate_budget"]),
        "curve": sorted(
            rows, key=lambda item: (item["candidate_budget"], item["reducer"])
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dirs", nargs="+", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = summarize(args.run_dirs)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
