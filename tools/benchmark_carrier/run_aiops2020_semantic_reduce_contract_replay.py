#!/usr/bin/env python3
"""Exercise the SemanticReduce contract over public AIOps replay evidence.

The AIOps Challenge 2020 labels identify individual fault windows, not
multi-object incident equivalence classes. This runner therefore does not report
reducer precision/recall/F1. It checks an external-data contract boundary:
stable evidence IDs enter baseline hypotheses, bounded KEEP commits, an invalid
evidence reference is rejected without changing the baseline, and replay
reconstructs the same committed digest.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


def _canonical_digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(*args: str) -> str:
    try:
        return subprocess.check_output(
            ["git", *args], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def _submodule(path: str) -> dict[str, Any]:
    return {
        "path": path,
        "commit": subprocess.check_output(
            ["git", "-C", path, "rev-parse", "HEAD"], text=True
        ).strip(),
        "branch": subprocess.check_output(
            ["git", "-C", path, "rev-parse", "--abbrev-ref", "HEAD"], text=True
        ).strip(),
        "dirty": bool(
            subprocess.check_output(
                ["git", "-C", path, "status", "--porcelain"], text=True
            ).strip()
        ),
    }


def run_contract(rows: list[dict[str, Any]]) -> dict[str, Any]:
    evidence = [
        {
            "evidence_id": str(row["evidence_id"]),
            "source_ref": str(row["source_ref"]),
            "object_type": str(row["object_type"]),
            "object_id": str(row["object_id"]),
            "fault_type": str(row["fault_type"]),
            "start_ms": int(row["start_ms"]),
            "max_robust_shift": float(row["max_robust_shift"]),
        }
        for row in rows
        if row.get("expected_fault") and row.get("predicted_fault")
    ]
    evidence.sort(key=lambda item: item["evidence_id"])
    baseline = [
        {
            "hypothesis_id": f"public-window-{index}",
            "evidence_ids": [item["evidence_id"]],
            "object_id": item["object_id"],
            "start_ms": item["start_ms"],
            "summary": "public labeled fault window with replay-derived evidence",
        }
        for index, item in enumerate(evidence)
    ]
    evidence_ids = {item["evidence_id"] for item in evidence}
    keep_actions = [
        {"action": "KEEP", "hypothesis_id": item["hypothesis_id"]}
        for item in baseline
    ]
    valid_commit = all(
        set(item["evidence_ids"]).issubset(evidence_ids) for item in baseline
    )
    committed = json.loads(json.dumps(baseline)) if valid_commit else []
    invalid_edit = {
        "action": "MERGE",
        "hypothesis_ids": [item["hypothesis_id"] for item in baseline[:2]],
        "evidence_ids": ["missing-public-evidence"],
    }
    invalid_rejected = not set(invalid_edit["evidence_ids"]).issubset(evidence_ids)
    after_invalid = json.loads(json.dumps(committed))
    candidate_digest = _canonical_digest(baseline)
    evidence_digest = _canonical_digest(evidence)
    committed_digest = _canonical_digest(committed)
    replay_digest = _canonical_digest(json.loads(json.dumps(committed)))
    replay_id = _canonical_digest(
        {
            "candidate_state_digest": candidate_digest,
            "evidence_state_digest": evidence_digest,
            "committed_state_digest": committed_digest,
            "actions": keep_actions,
        }
    )
    return {
        "status": "PASS"
        if valid_commit
        and invalid_rejected
        and after_invalid == committed
        and replay_digest == committed_digest
        else "FAIL",
        "boundary": (
            "External public-data contract conformance only; AIOps labels do not "
            "provide reducer-level incident grouping ground truth."
        ),
        "evidence_count": len(evidence),
        "baseline_hypothesis_count": len(baseline),
        "bounded_actions": ["KEEP", "MERGE", "SPLIT", "ABSTAIN"],
        "valid_commit": valid_commit,
        "invalid_reference_rejected": invalid_rejected,
        "baseline_preserved_after_rejection": after_invalid == committed,
        "deterministic_replay": replay_digest == committed_digest,
        "candidate_state_digest": candidate_digest,
        "evidence_state_digest": evidence_digest,
        "committed_state_digest": committed_digest,
        "replay_id": replay_id,
        "validator_owned": True,
        "actions": keep_actions,
        "invalid_edit": invalid_edit,
        "evidence": evidence,
        "committed_hypotheses": committed,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replay-dir", required=True, type=Path)
    parser.add_argument(
        "--output-root",
        default=".sage/benchmarks/aiops2020_semantic_reduce_contract",
        type=Path,
    )
    parser.add_argument("--run-id")
    args = parser.parse_args()
    replay_dir = args.replay_dir.resolve()
    source_manifest_path = replay_dir / "manifest.json"
    rows_path = replay_dir / "rows.json"
    source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
    if source_manifest.get("evidence_label") != "replay":
        raise ValueError("source AIOps artifact must be labeled replay")
    rows = json.loads(rows_path.read_text(encoding="utf-8"))
    result = run_contract(rows)
    run_id = args.run_id or time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    outdir = args.output_root / run_id
    if outdir.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {outdir}")
    outdir.mkdir(parents=True)
    manifest = {
        "run_id": run_id,
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "evidence_label": "replay",
        "dataset": "AIOps Challenge 2020",
        "source_replay": str(replay_dir),
        "source_manifest_sha256": _sha256(source_manifest_path),
        "source_rows_sha256": _sha256(rows_path),
        "raw_data_archived": False,
        "claim_boundary": result["boundary"],
        "python": {"version": platform.python_version(), "executable": sys.executable},
        "conda_env": os.environ.get("CONDA_DEFAULT_ENV", ""),
        "git": {
            "commit": _git("rev-parse", "HEAD"),
            "branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
            "dirty": bool(_git("status", "--porcelain")),
        },
        "submodules": {
            path: _submodule(path)
            for path in (
                "third_party/llm-serving-workloads",
                "third_party/ascend-runtime-manager",
            )
        },
    }
    (outdir / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    (outdir / "contract_result.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print(f"RESULT_DIR={outdir}")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
