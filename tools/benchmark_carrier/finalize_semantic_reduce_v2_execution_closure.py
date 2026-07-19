#!/usr/bin/env python3
"""Finalize paper admissibility only after local gates and central release ACK."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _timestamp(value: object) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return parsed


def _git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--expected-protocol-sha256", required=True)
    parser.add_argument("--execution-handoff", type=Path, required=True)
    parser.add_argument("--central-release-ack", type=Path, required=True)
    parser.add_argument("--central-queue-repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite final closure")
    if _sha256(args.protocol) != args.expected_protocol_sha256:
        raise SystemExit("protocol SHA mismatch")
    protocol = _load(args.protocol)
    handoff = _load(args.execution_handoff)
    ack = _load(args.central_release_ack)
    control = args.execution_handoff.resolve().parent
    canonical_output = (
        Path(protocol["repository"]["path"])
        / protocol["raw_evidence"]["final_closure_root"]
        .replace("$PROTOCOL_SHA256", args.expected_protocol_sha256)
        .replace("$SPLIT", str(handoff.get("split")))
        .replace("$RUN_ID", str(handoff.get("run_id")))
    ).resolve()
    if args.output.resolve() != canonical_output:
        raise SystemExit("final closure output is not the canonical protocol path")
    expected = {
        "status": "LOCAL_GATES_PASS_PENDING_CENTRAL_RELEASE_ACK",
        "paper_admissible": False,
        "protocol_sha256": args.expected_protocol_sha256,
        "repository_commit": protocol["repository"]["execution_commit"],
    }
    if any(handoff.get(key) != value for key, value in expected.items()):
        raise SystemExit("execution handoff is not a matching local PASS")
    actual_inventory = {
        str(path.relative_to(control)): _sha256(path)
        for path in sorted(control.rglob("*"))
        if path.is_file()
        and path.resolve() != args.execution_handoff.resolve()
        and path.name != "control-secret-scan.json"
    }
    if actual_inventory != handoff.get("control_inventory"):
        raise SystemExit("control inventory drift after local handoff")
    release_path = control / "release-request.json"
    verification_path = control / "verification.json"
    raw_scan_path = control / "raw-secret-scan.json"
    control_scan_path = control / "control-secret-scan.json"
    cleanup_path = control / "cleanup-observation.json"
    prelaunch_path = control / "prelaunch.json"
    postlaunch_path = control / "postlaunch.json"
    release, verification = _load(release_path), _load(verification_path)
    raw_scan, control_scan = _load(raw_scan_path), _load(control_scan_path)
    cleanup = _load(cleanup_path)
    prelaunch, postlaunch = _load(prelaunch_path), _load(postlaunch_path)
    expected_scan_coverage = {
        str(path.relative_to(control)): _sha256(path)
        for path in sorted(control.rglob("*"))
        if path.is_file() and path.name != "control-secret-scan.json"
    }
    verified_grant_sha = verification.get("grant_sha256")
    local_checks = {
        "release-request": _sha256(release_path)
        == handoff.get("release_request_sha256"),
        "raw-verification": verification.get("status") == "PASS",
        "raw-secret-scan": raw_scan.get("status") == "PASS",
        "control-secret-scan": control_scan.get("status") == "PASS",
        "control-secret-scan-coverage": control_scan.get("coverage")
        == expected_scan_coverage
        and control_scan.get("expected_coverage") == expected_scan_coverage
        and control_scan.get("self_exclusion") == "control-secret-scan.json",
        "cleanup": cleanup.get("status") == "PASS",
        "prelaunch-chain": postlaunch.get("prelaunch_sha256")
        == _sha256(prelaunch_path)
        and all(
            prelaunch.get(key) == postlaunch.get(key)
            for key in (
                "protocol_sha256",
                "repository_commit",
                "grant_sha256",
                "split",
                "run_id",
            )
        ),
        "port-process-lineage": postlaunch.get("checks", {}).get(
            "port_owner_process_lineage"
        )
        is True,
        "release-request-only": release.get("status")
        == "REQUEST_ONLY_CENTRAL_ACK_REQUIRED",
        "release-local-status": release.get("cleanup", {}).get("status") == "PASS"
        and release.get("control_secret_scan", {}).get("status")
        == "PENDING_FINAL_COVERAGE",
        "no-queue-mutation": release.get("queue_mutation_performed") is False,
        "grant-chain": bool(verified_grant_sha)
        and verified_grant_sha == handoff.get("grant_sha256")
        == release.get("grant_sha256")
        == prelaunch.get("grant_sha256")
        == postlaunch.get("grant_sha256"),
        "cleanup-ownership": cleanup.get("ownership_basis")
        == {
            "unit_and_container_absent_prelaunch": True,
            "postlaunch_process_lineage_verified": True,
            "cleanup_used_only_exact_systemd_unit_and_container": True,
            "manage_sh_stop_used": False,
        }
        and cleanup.get("observed_clear")
        == {
            "npu": True,
            "port": True,
            "managed_unit_active": False,
            "container_present": False,
        },
    }
    if failed := [name for name, passed in local_checks.items() if not passed]:
        raise SystemExit("local closure gate failed: " + ",".join(failed))
    service = protocol["service"]
    authority = protocol["central_release_ack_contract"]
    queue_repo = args.central_queue_repo.resolve()
    ack_path = args.central_release_ack.resolve()
    expected_ack_relative = authority["ack_path_template"].replace(
        "$PROTOCOL_SHA256", args.expected_protocol_sha256
    ).replace("$SPLIT", str(handoff["split"])).replace("$RUN_ID", str(handoff["run_id"]))
    if ack_path != (queue_repo / expected_ack_relative).resolve():
        raise SystemExit("central ACK path is not authority-canonical")
    queue_commit = _git(queue_repo, "rev-parse", "HEAD")
    upstream_commit = _git(queue_repo, "rev-parse", "@{upstream}")
    if queue_commit != upstream_commit:
        raise SystemExit("central ACK is not anchored at the queue upstream")
    if _git(queue_repo, "merge-base", "--is-ancestor", authority["queue_base_commit"], queue_commit):
        raise SystemExit("central ACK commit is not descended from the reviewed queue base")
    committed_ack = subprocess.check_output(
        ["git", "-C", str(queue_repo), "show", f"{queue_commit}:{expected_ack_relative}"]
    )
    if hashlib.sha256(committed_ack).hexdigest() != _sha256(ack_path):
        raise SystemExit("central ACK bytes are not committed at the upstream queue head")
    if (
        _git(queue_repo, "branch", "--show-current") != authority["queue_branch"]
        or _git(queue_repo, "remote", "get-url", "origin")
        != authority["queue_origin_url"]
    ):
        raise SystemExit("central ACK queue origin/branch authority mismatch")
    ack_checks = {
        "status": ack.get("status") == "RELEASE_ACKNOWLEDGED",
        "protocol": ack.get("protocol_sha256") == args.expected_protocol_sha256,
        "commit": ack.get("repository_commit")
        == protocol["repository"]["execution_commit"],
        "grant": ack.get("grant_sha256") == handoff.get("grant_sha256"),
        "release": ack.get("release_request_sha256") == _sha256(release_path),
        "split": ack.get("split") == handoff.get("split"),
        "run-id": ack.get("run_id") == handoff.get("run_id"),
        "resources": ack.get("released_resources")
        == {
            "physical_npus": [service["physical_npu"]],
            "port": service["port"],
            "managed_unit": service["managed_unit"],
            "container": service["container"],
        },
        "temporal": _timestamp(ack.get("acknowledged_utc"))
        >= _timestamp(release.get("release_requested_utc")),
        "authority": ack.get("central_writer_id") in authority["allowed_central_writer_ids"],
        "queue-base": ack.get("queue_base_commit") == authority["queue_base_commit"]
        and ack.get("queue_authority_source_sha256")
        == authority["queue_authority_source_sha256"],
        "queue-anchor": ack.get("queue_ack_commit") == queue_commit,
    }
    if failed := [name for name, passed in ack_checks.items() if not passed]:
        raise SystemExit("central release acknowledgement rejected: " + ",".join(failed))
    raw_root = Path(handoff["raw_root"])
    raw_manifest = raw_root / "manifest.json"
    raw_ledger = raw_root / "row-ledger.json"
    raw_summary = raw_root / "summary.json"
    raw_inventory = {
        str(path.relative_to(raw_root)): _sha256(path)
        for path in sorted(raw_root.rglob("*"))
        if path.is_file()
    }
    raw_scan_coverage = {
        str(Path(item["path"]).resolve().relative_to(raw_root.resolve())): item["sha256"]
        for item in raw_scan.get("scanned_files", [])
        if Path(item.get("path", "")).resolve().is_relative_to(raw_root.resolve())
        and item.get("status") == "PASS"
    }
    if (
        _sha256(raw_manifest) != handoff["raw_manifest_sha256"]
        or _sha256(raw_ledger) != handoff["raw_ledger_sha256"]
        or _sha256(raw_summary) != handoff["raw_summary_sha256"]
        or raw_inventory != handoff.get("raw_inventory")
        or raw_scan_coverage != raw_inventory
    ):
        raise SystemExit("raw evidence drift after local verification")
    row_count = 80 if handoff["split"] == "development" else 200
    if handoff.get("verified_row_count") != row_count:
        raise SystemExit("verified row count mismatch")
    expected_verification = {
        "status": "PASS",
        "raw_root": str(raw_root),
        "protocol_sha256": args.expected_protocol_sha256,
        "repository_commit": protocol["repository"]["execution_commit"],
        "grant_sha256": handoff["grant_sha256"],
        "split": handoff["split"],
        "verified_row_count": row_count,
        "manifest_sha256": handoff["raw_manifest_sha256"],
        "ledger_sha256": handoff["raw_ledger_sha256"],
        "summary_sha256": handoff["raw_summary_sha256"],
        "secret_scan": "PASS",
        "summary_recomputed": True,
    }
    if any(verification.get(key) != value for key, value in expected_verification.items()):
        raise SystemExit("raw verifier output is not bound to the final raw inventory")
    closure = {
        "schema_version": "semantic-reduce-v2-final-execution-closure/1",
        "status": "PASS",
        "paper_admissible": True,
        "protocol_sha256": args.expected_protocol_sha256,
        "repository_commit": protocol["repository"]["execution_commit"],
        "grant_sha256": handoff["grant_sha256"],
        "split": handoff["split"],
        "run_id": handoff["run_id"],
        "raw_root": str(raw_root.resolve()),
        "manifest_sha256": handoff["raw_manifest_sha256"],
        "ledger_sha256": handoff["raw_ledger_sha256"],
        "summary_sha256": handoff["raw_summary_sha256"],
        "verified_row_count": row_count,
        "raw_verification_sha256": _sha256(verification_path),
        "raw_secret_scan": "PASS",
        "raw_secret_scan_sha256": _sha256(raw_scan_path),
        "control_secret_scan": "PASS",
        "control_secret_scan_sha256": _sha256(control_scan_path),
        "cleanup": "PASS",
        "cleanup_observation_sha256": _sha256(cleanup_path),
        "release_request_sha256": _sha256(release_path),
        "central_release_acknowledgement": "PASS",
        "central_release_ack_sha256": _sha256(args.central_release_ack),
        "execution_handoff_sha256": _sha256(args.execution_handoff),
        "completed_utc": ack["acknowledged_utc"],
    }
    if handoff["split"] == "development":
        candidate = _load(raw_root / "development-candidate.json")
        closure.update(
            {
                "unique_row_keys": candidate["unique_row_keys"],
                "predicate_evidence": candidate["predicate_evidence"],
                "development_candidate_sha256": _sha256(
                    raw_root / "development-candidate.json"
                ),
            }
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(closure, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(closure, separators=(",", ":"), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
