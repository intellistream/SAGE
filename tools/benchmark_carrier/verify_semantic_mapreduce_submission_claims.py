#!/usr/bin/env python3
"""Cross-check submission-facing numeric claims against frozen evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Mapping
from pathlib import Path

ACTION = "llm-pairwise-action-validated"
HYBRID = "hybrid-hint"


def _load(path: Path) -> Mapping[str, object] | list[object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _row(rows: list[dict[str, object]], reducer: str) -> dict[str, object]:
    return next(row for row in rows if row["reducer"] == reducer)


def _paired(stability: dict[str, object]) -> dict[str, object]:
    return next(
        row
        for row in stability["paired_comparisons"]
        if row["target"] == ACTION and row["baseline"] == HYBRID
    )


def _require(checks: dict[str, bool], name: str, condition: bool) -> None:
    checks[name] = bool(condition)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paper", required=True, type=Path)
    parser.add_argument("--primary-comparison", required=True, type=Path)
    parser.add_argument("--primary-stability", required=True, type=Path)
    parser.add_argument("--second-comparison", required=True, type=Path)
    parser.add_argument("--second-stability", required=True, type=Path)
    parser.add_argument("--external-replay", required=True, type=Path)
    parser.add_argument("--runtime-contract", required=True, type=Path)
    parser.add_argument("--v2-heldout", required=True, type=Path)
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--expected-archive-sha256", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    paper = args.paper.read_text(encoding="utf-8")
    primary = _load(args.primary_comparison)
    primary_stability = _load(args.primary_stability)
    second = _load(args.second_comparison)
    second_stability = _load(args.second_stability)
    external = _load(args.external_replay)
    runtime = _load(args.runtime_contract)
    heldout = _load(args.v2_heldout)
    p_action, p_hybrid = _row(primary, ACTION), _row(primary, HYBRID)
    s_action, s_hybrid = _row(second, ACTION), _row(second, HYBRID)
    p_pair, s_pair = _paired(primary_stability), _paired(second_stability)
    p_cost = primary_stability["by_reducer"][ACTION]
    s_cost = second_stability["by_reducer"][ACTION]

    checks: dict[str, bool] = {}
    _require(checks, "primary_f1", (p_action["f1_mean"], p_hybrid["f1_mean"]) == (0.8645, 0.7801))
    _require(checks, "primary_paired_units", p_pair["unit_count"] == 27 and p_pair["f1_delta_mean"] == 0.0844)
    _require(checks, "primary_ci", p_pair["f1_delta_paired_bootstrap_95ci"] == [0.0328, 0.1449])
    _require(checks, "primary_cost", p_cost["model_call_runs"] == 65 and p_cost["called_latency_ms_median"] == 160)
    _require(checks, "second_f1", (s_action["f1_mean"], s_hybrid["f1_mean"]) == (0.8392, 0.7801))
    _require(checks, "second_paired_units", s_pair["unit_count"] == 27 and s_pair["f1_delta_mean"] == 0.0591)
    _require(checks, "second_ci", s_pair["f1_delta_paired_bootstrap_95ci"] == [0.0147, 0.1149])
    _require(checks, "second_cost", s_cost["model_call_runs"] == 39 and s_cost["called_latency_ms_median"] == 276.2)
    _require(checks, "external_boundary", external["evidence_label"] == "replay" and external["validation_scope"] == "reducer-only-label-conditioned" and external["end_to_end_detection_claim"] is False)
    _require(checks, "runtime_rows", runtime["row_count"] == 27 and all(runtime[key] == 27 for key in ("valid_commit_passes", "state_changing_commit_passes", "invalid_edit_rejections", "baseline_preservation_passes", "checkpoint_restore_passes", "independent_checkpoint_passes", "deterministic_replay_passes")))
    _require(
        checks,
        "v2_heldout_scope",
        heldout["unit_count"] == 40
        and heldout["oracle_repairable_unit_count"] == 36
        and heldout["improving_merge_unit_count"] == 29
        and heldout["improving_split_unit_count"] == 14
        and heldout["shared_catalog_digest_match"] is True
        and heldout["online_readiness"] == "OFFLINE_GATES_ONLY"
        and heldout["online_execution_performed"] is False,
    )
    _require(checks, "archive_sha256", _sha256(args.archive) == args.expected_archive_sha256)
    for literal in ("0.8645", "0.7801", "0.8392", "+0.0591", "40 units", "29 units", "no endpoint or model", "label-conditioned", "not cross-family or production robustness"):
        _require(checks, f"paper_literal:{literal}", literal in paper)

    failures = [name for name, passed in checks.items() if not passed]
    result = {"status": "PASS" if not failures else "FAIL", "failures": failures, "checks": checks}
    rendered = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
