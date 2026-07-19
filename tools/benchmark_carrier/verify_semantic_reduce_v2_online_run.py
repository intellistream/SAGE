#!/usr/bin/env python3
"""Independently verify a complete Semantic Reduce v2 real-online raw root."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from run_semantic_reduce_edit_v2_online_matrix import _secret_hits, _summarize

ROOT = Path(__file__).resolve().parents[2]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def verify_run(
    raw_root: Path,
    *,
    expected_protocol_sha256: str,
    expected_repository_commit: str,
) -> dict[str, Any]:
    raw_root = raw_root.resolve()
    manifest = _load(raw_root / "manifest.json")
    if manifest.get("status") != "PASS":
        _fail("manifest is not PASS")
    if manifest.get("evidence_label") != "real-online":
        _fail("wrong evidence label")
    if manifest.get("visibility") != "private-nonanonymous":
        _fail("raw visibility boundary is missing")
    if manifest.get("publication_eligible") is not False:
        _fail("raw root incorrectly marked publication eligible")
    if manifest.get("protocol_sha256") != expected_protocol_sha256:
        _fail("protocol SHA mismatch")
    if manifest.get("repository_commit") != expected_repository_commit:
        _fail("repository commit mismatch")
    if Path(manifest.get("raw_root", "")).resolve() != raw_root:
        _fail("noncanonical raw-root binding")

    inventory = manifest.get("files")
    if not isinstance(inventory, dict):
        _fail("manifest inventory missing")
    actual = {
        path.name
        for path in raw_root.iterdir()
        if path.is_file() and path.name not in {"manifest.json", "development-gate.json"}
    }
    if set(inventory) != actual:
        _fail("manifest inventory is not exact")
    for name, digest in inventory.items():
        if _sha256(raw_root / name) != digest:
            _fail(f"file digest mismatch: {name}")

    protocol = _load(raw_root / "protocol.json")
    if _sha256(raw_root / "protocol.json") != expected_protocol_sha256:
        _fail("protocol snapshot does not match expected protocol SHA")
    if _sha256(raw_root / "protocol.json") != inventory["protocol.json"]:
        _fail("protocol snapshot inventory mismatch")
    if protocol["repository"]["execution_commit"] != expected_repository_commit:
        _fail("protocol snapshot commit mismatch")
    grant = _load(raw_root / "grant.json")
    preflight = _load(raw_root / "preflight.json")
    if manifest.get("grant_sha256") != _sha256(raw_root / "grant.json"):
        _fail("grant digest binding mismatch")
    if manifest.get("preflight_sha256") != _sha256(raw_root / "preflight.json"):
        _fail("preflight digest binding mismatch")

    observed_sources: dict[str, str] = {}
    for name, item in protocol["repository"]["frozen_sources"].items():
        data = subprocess.check_output(
            [
                "git",
                "-C",
                str(ROOT),
                "show",
                f"{expected_repository_commit}:{item['path']}",
            ]
        )
        observed_sources[name] = hashlib.sha256(data).hexdigest()
        if observed_sources[name] != item["sha256"]:
            _fail(f"frozen source drift: {name}")
    if manifest.get("frozen_source_hashes") != observed_sources:
        _fail("manifest frozen-source inventory mismatch")
    for path, expected in protocol["repository"]["frozen_submodules"].items():
        actual = subprocess.check_output(
            ["git", "-C", str(ROOT / path), "rev-parse", "HEAD"], text=True
        ).strip()
        dirty = subprocess.check_output(
            ["git", "-C", str(ROOT / path), "status", "--porcelain"], text=True
        ).strip()
        if actual != expected or dirty:
            _fail(f"submodule provenance drift: {path}")

    service = protocol["service"]
    split = manifest["split"]
    run_id = manifest["run_id"]
    grant_checks = {
        "status": grant.get("status") == "GRANTED",
        "protocol": grant.get("protocol_sha256") == expected_protocol_sha256,
        "commit": grant.get("repository_commit") == expected_repository_commit,
        "split": split in grant.get("authorized_splits", []),
        "run-id": grant.get("run_ids", {}).get(split) == run_id,
        "expiry": datetime.fromisoformat(
            str(grant.get("expires_utc")).replace("Z", "+00:00")
        )
        > datetime.now(timezone.utc),
        "resources": grant.get("resources", {}).get("physical_npus")
        == [service["physical_npu"]]
        and grant.get("resources", {}).get("npu_count") == service["npu_count"]
        and grant.get("resources", {}).get("topology") == service["topology"],
        "service": grant.get("service")
        == {
            "base_url": service["base_url"],
            "port": service["port"],
            "managed_unit": service["managed_unit"],
            "container": service["container"],
            "manager": service["manager"],
        },
        "model": grant.get("model")
        == {
            "served_model_name": service["served_model_name"],
            "path": service["model_path"],
            "config_sha256": service["model_config_sha256"],
            "generation_config_sha256": service["generation_config_sha256"],
        },
    }
    if failed := [name for name, passed in grant_checks.items() if not passed]:
        _fail("grant provenance mismatch: " + ",".join(failed))
    preflight_checks = {
        "status": preflight.get("status") == "PASS",
        "protocol": preflight.get("protocol_sha256") == expected_protocol_sha256,
        "commit": preflight.get("repository_commit") == expected_repository_commit,
        "grant": preflight.get("grant_sha256") == manifest.get("grant_sha256"),
        "split": preflight.get("split") == split,
        "run-id": preflight.get("run_id") == run_id,
        "service": preflight.get("service")
        == {
            "base_url": service["base_url"],
            "port": service["port"],
            "managed_unit": service["managed_unit"],
            "container": service["container"],
        },
        "device-owner": preflight.get("checks", {}).get("device_owner")
        == "exact-grant-container",
        "port-owner": preflight.get("checks", {}).get("port_owner")
        == "exact-grant-service",
        "model": preflight.get("checks", {}).get("models_endpoint")
        == "frozen-served-name-present",
        "smoke": preflight.get("checks", {}).get("structured_output_smoke")
        == "strict-proposal-ids-pass",
        "secret-scan": preflight.get("checks", {}).get("raw_secret_scan") == "PASS",
    }
    if failed := [name for name, passed in preflight_checks.items() if not passed]:
        _fail("preflight provenance mismatch: " + ",".join(failed))
    for name in ("protocol.json", "grant.json", "preflight.json", "service-models.json"):
        if _secret_hits(_load(raw_root / name), api_key="__UNMATCHABLE_SECRET_SENTINEL__"):
            _fail(f"generic secret scanner failed: {name}")

    seeds = {int(value) for value in protocol["experiment"][f"{split}_seeds"]}
    repeats = set(range(protocol["experiment"][f"{split}_repeats"]))
    expected_keys = {
        f"{family}|{seed}|{repeat}"
        for family in protocol["experiment"]["families"]
        for seed in seeds
        for repeat in repeats
    }
    ledger = _load(raw_root / "row-ledger.json")
    if ledger.get("status") != "COMPLETE":
        _fail("row ledger is not complete")
    entries = ledger.get("rows")
    if not isinstance(entries, list):
        _fail("row ledger entries missing")
    if {entry.get("row_key") for entry in entries} != expected_keys:
        _fail("row keys do not exactly cover the frozen matrix")
    if len(entries) != len(expected_keys):
        _fail("duplicate row keys")

    rows: list[dict[str, Any]] = []
    for index, entry in enumerate(entries):
        row_path = raw_root / str(entry["path"])
        if _sha256(row_path) != entry["sha256"]:
            _fail(f"row digest mismatch: {row_path.name}")
        row = _load(row_path)
        if row.get("sequence_index") != index:
            _fail("sequence index drift")
        if row.get("row_key") != entry["row_key"]:
            _fail("row key/ledger mismatch")
        if not row.get("started_utc") or not row.get("completed_utc"):
            _fail("row timestamps missing")
        if _secret_hits(row, api_key="__UNMATCHABLE_SECRET_SENTINEL__"):
            _fail(f"generic secret scanner failed: {row_path.name}")
        evaluation = row.get("evaluation", {})
        if evaluation.get("shared_catalog_digest_match") is not True:
            _fail("shared catalog digest mismatch")
        policies = evaluation.get("policies", {})
        if policies.get("online_model_selector", {}).get("evidence_conserved") is not True:
            _fail("evidence conservation failure")
        rows.append(row)

    observed_summary = _load(raw_root / "summary.json")
    recomputed = _summarize(rows, protocol, split)
    for key, value in recomputed.items():
        if observed_summary.get(key) != value:
            _fail(f"summary mismatch: {key}")
    if observed_summary.get("protocol_sha256") != expected_protocol_sha256:
        _fail("summary protocol SHA mismatch")
    if observed_summary.get("repository_commit") != expected_repository_commit:
        _fail("summary repository commit mismatch")
    if observed_summary.get("grant_sha256") != manifest.get("grant_sha256"):
        _fail("summary grant digest mismatch")
    if manifest.get("completed_row_count") != len(expected_keys):
        _fail("manifest completed-row count mismatch")
    if manifest.get("secret_scan") != "PASS":
        _fail("runner exact-value secret scan did not pass")

    if split == "development":
        gate_path = raw_root / "development-gate.json"
        gate = _load(gate_path)
        if gate.get("status") != recomputed.get("development_gate"):
            _fail("development predicate mismatch")
        if gate.get("manifest_sha256") != _sha256(raw_root / "manifest.json"):
            _fail("development gate manifest digest mismatch")
        if gate.get("ledger_sha256") != _sha256(raw_root / "row-ledger.json"):
            _fail("development gate ledger digest mismatch")
        if gate.get("summary_sha256") != _sha256(raw_root / "summary.json"):
            _fail("development gate summary digest mismatch")
        if gate.get("grant_sha256") != manifest.get("grant_sha256"):
            _fail("development gate grant digest mismatch")
        if gate.get("verified_row_count") != len(expected_keys):
            _fail("development gate row count mismatch")
        if gate.get("unique_row_keys") != len(expected_keys):
            _fail("development gate uniqueness mismatch")
        expected_predicates = {
            "safety_failure_count": recomputed["safety_failure_count"],
            "failure_rate": recomputed["request_or_parser_failure_rate"],
            "accepted_edit_count": recomputed["accepted_edit_count"],
            "accepted_merge_count": recomputed["accepted_merge_count"],
            "accepted_split_count": recomputed["accepted_split_count"],
        }
        if gate.get("predicate_evidence") != expected_predicates:
            _fail("development gate predicate evidence mismatch")

    return {
        "status": "PASS",
        "raw_root": str(raw_root),
        "protocol_sha256": expected_protocol_sha256,
        "repository_commit": expected_repository_commit,
        "split": split,
        "verified_row_count": len(rows),
        "manifest_sha256": _sha256(raw_root / "manifest.json"),
        "ledger_sha256": _sha256(raw_root / "row-ledger.json"),
        "summary_sha256": _sha256(raw_root / "summary.json"),
        "secret_scan": "PASS",
        "summary_recomputed": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-root", type=Path, required=True)
    parser.add_argument("--expected-protocol-sha256", required=True)
    parser.add_argument("--expected-repository-commit", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = verify_run(
        args.raw_root,
        expected_protocol_sha256=args.expected_protocol_sha256,
        expected_repository_commit=args.expected_repository_commit,
    )
    if args.output:
        if args.output.exists():
            _fail("refusing to overwrite verifier output")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, separators=(",", ":"), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
