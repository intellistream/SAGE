#!/usr/bin/env python3
"""Execute one grant-bound, fail-closed Semantic Reduce v2 online split."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import statistics
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sage.workloads.semantic_reduce_edit_evaluation import (
    OpenAIProposalSelector,
    evaluate_workload,
)
from sage.workloads.semantic_reduce_heldout import generate_heldout_workload

ROOT = Path(__file__).resolve().parents[2]
RAW_PARENT = ROOT / ".sage/benchmarks/semantic_reduce_edit_v2_real_online"
RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(*args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(ROOT), *args], text=True
    ).strip()


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _utc(value: object) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must carry a timezone")
    return parsed


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace(
        "+00:00", "Z"
    )


def _atomic_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    data = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    with temporary.open("x", encoding="utf-8") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def _atomic_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    with temporary.open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def _secret_hits(payload: object, *, api_key: str) -> list[str]:
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    hits: list[str] = []
    if len(api_key) >= 4 and api_key in text:
        hits.append("exact-api-key")
    patterns = {
        "authorization-field": r'(?i)"authorization"\s*:\s*"(?!REDACTED)[^"]+"',
        "api-key-field": r'(?i)"api[_-]?key"\s*:\s*"(?!REDACTED)[^"]+"',
        "bearer-token": r"(?i)bearer\s+[A-Za-z0-9._~+/=-]{8,}",
    }
    hits.extend(name for name, pattern in patterns.items() if re.search(pattern, text))
    return sorted(set(hits))


def _source_hashes_at_commit(protocol: dict[str, Any]) -> dict[str, str]:
    commit = protocol["repository"]["execution_commit"]
    observed: dict[str, str] = {}
    for name, item in protocol["repository"]["frozen_sources"].items():
        data = subprocess.check_output(
            ["git", "-C", str(ROOT), "show", f"{commit}:{item['path']}"]
        )
        digest = hashlib.sha256(data).hexdigest()
        if digest != item["sha256"]:
            raise ValueError(f"frozen source mismatch: {name}")
        observed[name] = digest
    return observed


def _validate_authorization(
    *,
    protocol: dict[str, Any],
    protocol_sha: str,
    grant: dict[str, Any],
    preflight: dict[str, Any],
    grant_sha: str,
    split: str,
    run_id: str,
) -> None:
    service = protocol["service"]
    expected = protocol["repository"]["execution_commit"]
    grant_service = grant.get("service", {})
    grant_model = grant.get("model", {})
    conditions = {
        "grant-status": grant.get("status") == "GRANTED",
        "protocol-sha": grant.get("protocol_sha256") == protocol_sha,
        "execution-commit": grant.get("repository_commit") == expected,
        "authorized-split": split in grant.get("authorized_splits", []),
        "run-id": grant.get("run_ids", {}).get(split) == run_id,
        "physical-npu": grant.get("resources", {}).get("physical_npus")
        == [service["physical_npu"]],
        "npu-count": grant.get("resources", {}).get("npu_count")
        == service["npu_count"],
        "topology": grant.get("resources", {}).get("topology")
        == service["topology"],
        "base-url": grant_service.get("base_url") == service["base_url"],
        "port": grant_service.get("port") == service["port"],
        "managed-unit": grant_service.get("managed_unit")
        == service["managed_unit"],
        "container": grant_service.get("container") == service["container"],
        "manager": grant_service.get("manager") == service["manager"],
        "served-model": grant_model.get("served_model_name")
        == service["served_model_name"],
        "model-path": grant_model.get("path") == service["model_path"],
        "model-config": grant_model.get("config_sha256")
        == service["model_config_sha256"],
        "generation-config": grant_model.get("generation_config_sha256")
        == service["generation_config_sha256"],
        "unexpired": _utc(grant.get("expires_utc")) > datetime.now(timezone.utc),
        "preflight-pass": preflight.get("status") == "PASS",
        "preflight-protocol": preflight.get("protocol_sha256") == protocol_sha,
        "preflight-commit": preflight.get("repository_commit") == expected,
        "preflight-grant": preflight.get("grant_sha256") == grant_sha,
        "preflight-split": preflight.get("split") == split,
        "preflight-run": preflight.get("run_id") == run_id,
        "preflight-base-url": preflight.get("service", {}).get("base_url")
        == service["base_url"],
        "preflight-managed-unit": preflight.get("service", {}).get("managed_unit")
        == service["managed_unit"],
        "preflight-container": preflight.get("service", {}).get("container")
        == service["container"],
        "preflight-port-owner": preflight.get("checks", {}).get("port_owner")
        == "exact-grant-service",
        "preflight-device-owner": preflight.get("checks", {}).get("device_owner")
        == "exact-grant-container",
        "preflight-models": preflight.get("checks", {}).get("models_endpoint")
        == "frozen-served-name-present",
        "preflight-repo": preflight.get("checks", {}).get("repository_clean") is True,
        "preflight-submodules": preflight.get("checks", {}).get("submodules_clean")
        is True,
        "preflight-env": preflight.get("checks", {}).get("conda_environment")
        == "esage-vllm-hust-dev",
        "preflight-model-hashes": preflight.get("checks", {}).get(
            "model_hashes_match"
        )
        is True,
        "preflight-source-hashes": preflight.get("checks", {}).get(
            "frozen_source_hashes_match"
        )
        is True,
        "preflight-namespace": preflight.get("checks", {}).get("namespace_fresh")
        is True,
        "preflight-disk": preflight.get("checks", {}).get("free_space_gib", 0) >= 5,
        "preflight-cleanup": preflight.get("checks", {}).get("cleanup_armed")
        is True,
    }
    failures = [name for name, passed in conditions.items() if not passed]
    if failures:
        raise ValueError("authorization/preflight rejected: " + ", ".join(failures))


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
    sampled = [
        statistics.fmean(
            value
            for family in [rng.choice(families) for _ in families]
            for value in by_family[family]
        )
        for _ in range(draws)
    ]
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
    safety_failures = sum(
        not row["evaluation"]["shared_catalog_digest_match"]
        or not row["evaluation"]["policies"]["online_model_selector"][
            "evidence_conserved"
        ]
        for row in rows
    )
    summary: dict[str, Any] = {
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
        "validator_rejection_count": sum(
            item["validator_outcome"] == "rejected" for item in model
        ),
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


def _models_snapshot(protocol: dict[str, Any], api_key: str) -> dict[str, Any]:
    request = urllib.request.Request(
        f"{protocol['service']['base_url']}/v1/models",
        headers={"Authorization": f"Bearer {api_key}"},
    )
    with urllib.request.urlopen(
        request, timeout=protocol["service"]["request_timeout_sec"]
    ) as response:
        payload = json.loads(response.read().decode("utf-8"))
    model_ids = sorted(str(item.get("id")) for item in payload.get("data", []))
    if protocol["service"]["served_model_name"] not in model_ids:
        raise ValueError("/v1/models does not contain frozen served model")
    return {"captured_utc": _now(), "model_ids": model_ids, "raw": payload}


def _expected_rows(protocol: dict[str, Any], split: str) -> int:
    return (
        len(protocol["experiment"]["families"])
        * len(protocol["experiment"][f"{split}_seeds"])
        * protocol["experiment"][f"{split}_repeats"]
    )


def _validate_development_gate(
    gate_path: Path, *, protocol_sha: str, execution_commit: str
) -> None:
    gate = _load(gate_path)
    if (
        gate.get("status") != "PASS"
        or gate.get("protocol_sha256") != protocol_sha
        or gate.get("repository_commit") != execution_commit
        or gate.get("verified_row_count") != 80
        or gate.get("secret_scan") != "PASS"
    ):
        raise ValueError("development gate is failed or provenance-mismatched")
    raw_root = Path(gate["raw_root"])
    manifest = raw_root / "manifest.json"
    ledger = raw_root / "row-ledger.json"
    if _sha256(manifest) != gate.get("manifest_sha256"):
        raise ValueError("development manifest digest mismatch")
    if _sha256(ledger) != gate.get("ledger_sha256"):
        raise ValueError("development ledger digest mismatch")
    entries = _load(ledger).get("rows", [])
    if len(entries) != 80 or len({item["row_key"] for item in entries}) != 80:
        raise ValueError("development row inventory is incomplete or duplicated")
    for entry in entries:
        row_path = raw_root / entry["path"]
        if _sha256(row_path) != entry["sha256"]:
            raise ValueError("development row digest mismatch")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", required=True, type=Path)
    parser.add_argument("--protocol-sha256", required=True)
    parser.add_argument("--grant", required=True, type=Path)
    parser.add_argument("--preflight", required=True, type=Path)
    parser.add_argument("--split", choices=("development", "heldout"), required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--development-gate", type=Path)
    args = parser.parse_args()

    if not RUN_ID_RE.fullmatch(args.run_id):
        raise SystemExit("invalid run ID")
    protocol_path = args.protocol.resolve()
    if ROOT.resolve() in protocol_path.parents:
        raise SystemExit("protocol must be an immutable external/ignored copy")
    if _sha256(args.protocol) != args.protocol_sha256:
        raise SystemExit("protocol SHA mismatch")
    protocol, grant, preflight = _load(args.protocol), _load(args.grant), _load(
        args.preflight
    )
    output_dir = RAW_PARENT / args.protocol_sha256 / f"{args.split}-{args.run_id}"
    if output_dir.exists():
        raise SystemExit("refusing to reuse canonical output namespace")
    protocol_parent = output_dir.parent
    if args.split == "heldout" and list(protocol_parent.glob("heldout-*")):
        if not grant.get("heldout_rerun_authorization_id"):
            raise SystemExit("heldout namespace already exists without reauthorization")
    if _git("status", "--porcelain"):
        raise SystemExit("execution checkout must be clean")
    execution_commit = protocol["repository"]["execution_commit"]
    if _git("rev-parse", "HEAD") != execution_commit:
        raise SystemExit("execution commit mismatch")
    if os.environ.get("CONDA_DEFAULT_ENV", Path(sys.prefix).name) != "esage-vllm-hust-dev":
        raise SystemExit("wrong conda environment")
    source_hashes = _source_hashes_at_commit(protocol)
    grant_sha, preflight_sha = _sha256(args.grant), _sha256(args.preflight)
    _validate_authorization(
        protocol=protocol,
        protocol_sha=args.protocol_sha256,
        grant=grant,
        preflight=preflight,
        grant_sha=grant_sha,
        split=args.split,
        run_id=args.run_id,
    )
    if args.split == "heldout":
        if not args.development_gate:
            raise SystemExit("heldout requires the frozen development gate")
        _validate_development_gate(
            args.development_gate,
            protocol_sha=args.protocol_sha256,
            execution_commit=execution_commit,
        )

    api_env = protocol["service"]["api_key_env"]
    api_key = os.environ.get(api_env)
    if not api_key:
        raise SystemExit(f"missing API key in {api_env}")
    output_dir.mkdir(parents=True)
    state: dict[str, Any] = {
        "schema_version": "semantic-reduce-v2-online-run/2",
        "status": "RUNNING",
        "evidence_label": "real-online",
        "visibility": "private-nonanonymous",
        "publication_eligible": False,
        "protocol_sha256": args.protocol_sha256,
        "repository_commit": execution_commit,
        "grant_sha256": grant_sha,
        "preflight_sha256": preflight_sha,
        "split": args.split,
        "run_id": args.run_id,
        "raw_root": str(output_dir.resolve()),
        "started_utc": _now(),
        "expected_row_count": _expected_rows(protocol, args.split),
        "completed_row_count": 0,
        "frozen_source_hashes": source_hashes,
        "files": {},
    }
    _atomic_json(output_dir / "manifest.json", state)
    _atomic_bytes(output_dir / "grant.json", args.grant.read_bytes())
    _atomic_bytes(output_dir / "preflight.json", args.preflight.read_bytes())
    _atomic_bytes(output_dir / "protocol.json", args.protocol.read_bytes())
    rows: list[dict[str, Any]] = []
    ledger: dict[str, Any] = {"status": "RUNNING", "rows": []}
    _atomic_json(output_dir / "row-ledger.json", ledger)

    exit_code = 1
    failure_reason: str | None = None
    try:
        for name, payload in (("grant", grant), ("preflight", preflight)):
            hits = _secret_hits(payload, api_key=api_key)
            if hits:
                raise RuntimeError(f"secret scan failed for {name}: {','.join(hits)}")
        service_snapshot = _models_snapshot(protocol, api_key)
        hits = _secret_hits(service_snapshot, api_key=api_key)
        if hits:
            raise RuntimeError("secret scan failed for /v1/models: " + ",".join(hits))
        _atomic_json(output_dir / "service-models.json", service_snapshot)

        split_seeds = protocol["experiment"][f"{args.split}_seeds"]
        repeats = protocol["experiment"][f"{args.split}_repeats"]
        units = [
            (family, int(seed), repeat)
            for repeat in range(repeats)
            for family in protocol["experiment"]["families"]
            for seed in split_seeds
        ]
        random.Random(protocol["experiment"]["order_seed"]).shuffle(units)
        for index, (family, seed, repeat) in enumerate(units):
            row_started = _now()
            sampling_seed = protocol["experiment"]["sampling_seeds"][repeat]
            selector = OpenAIProposalSelector(
                base_url=protocol["service"]["base_url"],
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
                "row_key": f"{family}|{seed}|{repeat}",
                "family": family,
                "seed": seed,
                "repeat": repeat,
                "sampling_seed": sampling_seed,
                "started_utc": row_started,
                "completed_utc": _now(),
                "evaluation": evaluation,
                "selector_trace": selector.last_trace,
            }
            hits = _secret_hits(row, api_key=api_key)
            if hits:
                raise RuntimeError("secret scan failed for row: " + ",".join(hits))
            row_path = output_dir / f"row-{index:04d}.json"
            _atomic_json(row_path, row)
            row_digest = _sha256(row_path)
            rows.append(row)
            ledger["rows"].append(
                {"row_key": row["row_key"], "path": row_path.name, "sha256": row_digest}
            )
            _atomic_json(output_dir / "row-ledger.json", ledger)
            state["completed_row_count"] = len(rows)
            _atomic_json(output_dir / "manifest.json", state)
            safety_failed = (
                not evaluation["shared_catalog_digest_match"]
                or not evaluation["policies"]["online_model_selector"][
                    "evidence_conserved"
                ]
            )
            if safety_failed:
                raise RuntimeError("immediate safety stop: catalog/evidence invariant")

        if len(rows) != state["expected_row_count"]:
            raise RuntimeError("planned row count not completed")
        summary = _summarize(rows, protocol, args.split)
        summary.update(
            {
                "protocol_sha256": args.protocol_sha256,
                "repository_commit": execution_commit,
                "grant_sha256": grant_sha,
                "completed_utc": _now(),
            }
        )
        _atomic_json(output_dir / "summary.json", summary)
        if summary["safety_failure_count"]:
            raise RuntimeError("safety failure in complete run")
        ledger["status"] = "COMPLETE"
        _atomic_json(output_dir / "row-ledger.json", ledger)
        inventory_names = [
            "grant.json",
            "preflight.json",
            "protocol.json",
            "service-models.json",
            "row-ledger.json",
            "summary.json",
            *[entry["path"] for entry in ledger["rows"]],
        ]
        state.update(
            {
                "status": "PASS",
                "completed_utc": _now(),
                "secret_scan": "PASS",
                "files": {
                    name: _sha256(output_dir / name) for name in inventory_names
                },
            }
        )
        _atomic_json(output_dir / "manifest.json", state)
        manifest_sha = _sha256(output_dir / "manifest.json")
        if args.split == "development":
            gate = {
                "schema_version": "semantic-reduce-v2-development-gate/1",
                "status": summary["development_gate"],
                "protocol_sha256": args.protocol_sha256,
                "repository_commit": execution_commit,
                "grant_sha256": grant_sha,
                "raw_root": str(output_dir.resolve()),
                "manifest_sha256": manifest_sha,
                "ledger_sha256": _sha256(output_dir / "row-ledger.json"),
                "verified_row_count": len(rows),
                "unique_row_keys": len({row["row_key"] for row in rows}),
                "secret_scan": "PASS",
                "predicate_evidence": {
                    "safety_failure_count": summary["safety_failure_count"],
                    "failure_rate": summary["request_or_parser_failure_rate"],
                    "accepted_edit_count": summary["accepted_edit_count"],
                    "accepted_merge_count": summary["accepted_merge_count"],
                    "accepted_split_count": summary["accepted_split_count"],
                },
            }
            _atomic_json(output_dir / "development-gate.json", gate)
        exit_code = 0 if summary.get("development_gate", "PASS") == "PASS" else 2
        if exit_code:
            failure_reason = "development admission gate failed"
    except BaseException as exc:
        failure_reason = f"{type(exc).__name__}: {exc}"
        exit_code = 1
    finally:
        if exit_code:
            state.update(
                {
                    "status": "FAILED_PARTIAL",
                    "failed_utc": _now(),
                    "failure_reason": failure_reason,
                    "completed_row_count": len(rows),
                    "secret_scan": "FAIL" if failure_reason and "secret scan" in failure_reason else "INCOMPLETE",
                    "files": {
                        entry["path"]: entry["sha256"] for entry in ledger["rows"]
                    },
                }
            )
            ledger["status"] = "FAILED_PARTIAL"
            ledger["failure_reason"] = failure_reason
            _atomic_json(output_dir / "row-ledger.json", ledger)
            _atomic_json(output_dir / "manifest.json", state)
    print(json.dumps(state, separators=(",", ":"), sort_keys=True))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
