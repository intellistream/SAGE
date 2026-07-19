#!/usr/bin/env python3
"""Run the SHA-bound real-online v2 proposal-selector matrix after a grant."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import statistics
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sage.workloads.semantic_reduce_edit_evaluation import (
    OpenAIProposalSelector,
    evaluate_workload,
)
from sage.workloads.semantic_reduce_heldout import generate_heldout_workload


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], text=True).strip()


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _validate_authorization(
    *, protocol: dict[str, Any], protocol_sha: str, grant: dict[str, Any]
) -> None:
    expected = protocol["repository"]["execution_commit"]
    conditions = {
        "grant_status": grant.get("status") == "granted",
        "protocol_sha": grant.get("protocol_sha256") == protocol_sha,
        "repository_commit": grant.get("repository_commit") == expected,
        "physical_device": grant.get("selected_physical_npu")
        == protocol["service"]["physical_npu"],
        "not_expired": _utc(str(grant.get("expires_utc")))
        > datetime.now(timezone.utc),
    }
    failures = [name for name, passed in conditions.items() if not passed]
    if failures:
        raise SystemExit("reservation grant rejected: " + ", ".join(failures))


def _clustered_ci(rows: list[dict[str, Any]], *, draws: int, seed: int) -> list[float]:
    unit_deltas: dict[tuple[str, int], list[float]] = {}
    for row in rows:
        policies = row["evaluation"]["policies"]
        delta = (
            policies["online_model_selector"]["f1"]
            - policies["deterministic_selector"]["f1"]
        )
        unit_deltas.setdefault((row["family"], row["seed"]), []).append(delta)
    by_family: dict[str, list[float]] = {}
    for (family, _), values in unit_deltas.items():
        by_family.setdefault(family, []).append(statistics.fmean(values))
    families = sorted(by_family)
    rng = random.Random(seed)
    sampled: list[float] = []
    for _ in range(draws):
        chosen = [rng.choice(families) for _ in families]
        sampled.append(
            statistics.fmean(value for family in chosen for value in by_family[family])
        )
    sampled.sort()
    return [
        round(sampled[int(0.025 * (draws - 1))], 6),
        round(sampled[int(0.975 * (draws - 1))], 6),
    ]


def _summarize(
    rows: list[dict[str, Any]], protocol: dict[str, Any], split: str
) -> dict[str, Any]:
    model = [row["evaluation"]["policies"]["online_model_selector"] for row in rows]
    deterministic = [
        row["evaluation"]["policies"]["deterministic_selector"] for row in rows
    ]
    deltas = [
        left["f1"] - right["f1"]
        for left, right in zip(model, deterministic, strict=True)
    ]
    unit_delta: dict[tuple[str, int], list[float]] = {}
    for row, delta in zip(rows, deltas, strict=True):
        unit_delta.setdefault((row["family"], row["seed"]), []).append(delta)
    unit_means = [statistics.fmean(values) for values in unit_delta.values()]
    failures = sum(row["selector_trace"]["outcome"] != "parsed" for row in rows)
    accepted_edits = sum(item["accepted_edit_count"] for item in model)
    accepted_merges = sum(item["merge_count"] for item in model)
    accepted_splits = sum(item["split_count"] for item in model)
    validator_rejections = sum(
        item["validator_outcome"] == "rejected" for item in model
    )
    safety_failures = sum(
        not row["evaluation"]["shared_catalog_digest_match"]
        or not row["evaluation"]["policies"]["online_model_selector"][
            "evidence_conserved"
        ]
        for row in rows
    )
    summary = {
        "evidence_label": "real-online",
        "split": split,
        "row_count": len(rows),
        "unit_count": len(unit_means),
        "repeats_per_unit": protocol["experiment"][f"{split}_repeats"],
        "model_mean_f1": round(statistics.fmean(item["f1"] for item in model), 6),
        "deterministic_mean_f1": round(
            statistics.fmean(item["f1"] for item in deterministic), 6
        ),
        "paired_unit_delta_mean": round(statistics.fmean(unit_means), 6),
        "family_clustered_bootstrap_95ci": _clustered_ci(
            rows,
            draws=protocol["statistics"]["bootstrap_draws"],
            seed=protocol["statistics"]["bootstrap_seed"],
        ),
        "unit_wins_ties_losses": {
            "wins": sum(value > 1e-12 for value in unit_means),
            "ties": sum(abs(value) <= 1e-12 for value in unit_means),
            "losses": sum(value < -1e-12 for value in unit_means),
        },
        "request_or_parser_failure_count": failures,
        "request_or_parser_failure_rate": round(failures / max(1, len(rows)), 6),
        "safety_failure_count": safety_failures,
        "accepted_edit_count": accepted_edits,
        "accepted_merge_count": accepted_merges,
        "accepted_split_count": accepted_splits,
        "validator_rejection_count": validator_rejections,
        "online_execution_performed": True,
    }
    if split == "development":
        summary["development_gate"] = (
            "PASS"
            if safety_failures == 0
            and summary["request_or_parser_failure_rate"]
            <= protocol["stopping_rules"]["development_max_failure_rate"]
            and accepted_edits > 0
            and accepted_merges > 0
            and accepted_splits > 0
            else "FAIL"
        )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", required=True, type=Path)
    parser.add_argument("--protocol-sha256", required=True)
    parser.add_argument("--grant", required=True, type=Path)
    parser.add_argument("--split", choices=("development", "heldout"), required=True)
    parser.add_argument("--development-gate", type=Path)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    if _sha256(args.protocol) != args.protocol_sha256:
        raise SystemExit("protocol SHA mismatch")
    if args.output_dir.exists():
        raise SystemExit("refusing to reuse output directory")
    protocol, grant = _load(args.protocol), _load(args.grant)
    _validate_authorization(protocol=protocol, protocol_sha=args.protocol_sha256, grant=grant)
    if _git("status", "--porcelain"):
        raise SystemExit("execution checkout must be clean")
    if _git("rev-parse", "HEAD") != protocol["repository"]["execution_commit"]:
        raise SystemExit("execution commit mismatch")
    if os.environ.get("CONDA_DEFAULT_ENV", Path(os.sys.prefix).name) != "esage-vllm-hust-dev":
        raise SystemExit("wrong conda environment")
    if args.split == "heldout":
        if not args.development_gate:
            raise SystemExit("heldout requires a frozen development gate")
        development = _load(args.development_gate)
        if (
            development.get("development_gate") != "PASS"
            or development.get("protocol_sha256") != args.protocol_sha256
        ):
            raise SystemExit("development gate is absent, failed, or SHA-mismatched")

    api_env = protocol["service"]["api_key_env"]
    api_key = os.environ.get(api_env)
    if not api_key:
        raise SystemExit(f"missing API key in {api_env}")
    if protocol["service"]["served_model_name"] != grant.get("served_model_name"):
        raise SystemExit("served model in grant does not match protocol")

    split_seeds = protocol["experiment"][f"{args.split}_seeds"]
    repeats = protocol["experiment"][f"{args.split}_repeats"]
    units = [
        (family, int(seed), repeat)
        for repeat in range(repeats)
        for family in protocol["experiment"]["families"]
        for seed in split_seeds
    ]
    random.Random(protocol["experiment"]["order_seed"]).shuffle(units)
    args.output_dir.mkdir(parents=True)
    rows: list[dict[str, Any]] = []
    for index, (family, seed, repeat) in enumerate(units):
        sampling_seed = protocol["experiment"]["sampling_seeds"][repeat]
        selector = OpenAIProposalSelector(
            base_url=args.base_url,
            model=protocol["service"]["served_model_name"],
            api_key=api_key,
            sampling_seed=sampling_seed,
            temperature=protocol["experiment"]["temperature"],
            timeout_sec=protocol["service"]["request_timeout_sec"],
        )
        evaluation = evaluate_workload(
            generate_heldout_workload(family, seed=seed, split=args.split),
            model_selector=selector,
            evidence_label="real-online",
        )
        row = {
            "sequence_index": index,
            "family": family,
            "seed": seed,
            "repeat": repeat,
            "sampling_seed": sampling_seed,
            "evaluation": evaluation,
            "selector_trace": selector.last_trace,
        }
        rows.append(row)
        (args.output_dir / f"row-{index:04d}.json").write_text(
            json.dumps(row, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

    summary = _summarize(rows, protocol, args.split)
    summary["protocol_sha256"] = args.protocol_sha256
    summary["repository_commit"] = protocol["repository"]["execution_commit"]
    summary["grant_sha256"] = _sha256(args.grant)
    summary["completed_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    (args.output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    (args.output_dir / "manifest.json").write_text(
        json.dumps(
            {
                "evidence_label": "real-online",
                "protocol_sha256": args.protocol_sha256,
                "grant_sha256": _sha256(args.grant),
                "split": args.split,
                "raw_file_count": len(rows),
                "credentials_retained": False,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, sort_keys=True))
    return 0 if summary.get("development_gate", "PASS") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
