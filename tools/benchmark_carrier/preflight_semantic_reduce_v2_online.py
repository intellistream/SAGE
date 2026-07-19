#!/usr/bin/env python3
"""Collect grant-bound pre/post-launch physical checks for v2 online runs."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import socket
import subprocess
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _run(*command: str, check: bool = True) -> str:
    result = subprocess.run(command, text=True, capture_output=True)
    if check and result.returncode:
        raise RuntimeError(f"command failed ({result.returncode}): {' '.join(command)}")
    return result.stdout


def _git(path: Path, *args: str) -> str:
    return _run("git", "-C", str(path), *args).strip()


def _utc(value: object) -> datetime:
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _port_open(port: int) -> bool:
    with socket.socket() as sock:
        sock.settimeout(0.5)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def _listener_pids(port: int) -> set[int]:
    output = _run(
        "sudo", "-n", "ss", "-H", "-ltnp", "sport", "=", f":{port}"
    )
    return {int(value) for value in re.findall(r"pid=(\d+)", output)}


def _secret_free(payload: object, api_key: str) -> bool:
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    lowered = text.lower()
    return (
        api_key not in text
        and '"authorization": "bearer ' not in lowered
        and '"api_key":' not in lowered
        and '"api-key":' not in lowered
    )


def _structured_smoke(
    *, service: dict[str, Any], api_key: str
) -> dict[str, Any]:
    request_payload = {
        "model": service["served_model_name"],
        "messages": [
            {
                "role": "system",
                "content": "Return only a strict JSON proposal_ids object.",
            },
            {
                "role": "user",
                "content": (
                    "This is a non-benchmark parser smoke. The only allowed ID is "
                    "A0001. Return {\"proposal_ids\":[]} or "
                    "{\"proposal_ids\":[\"A0001\"]}."
                ),
            },
        ],
        "temperature": 0.0,
        "seed": 99173,
        "max_tokens": 64,
        "response_format": {"type": "json_object"},
    }
    request = urllib.request.Request(
        f"{service['base_url']}/v1/chat/completions",
        data=json.dumps(request_payload).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=service["request_timeout_sec"]) as response:
        body = response.read().decode("utf-8")
    response_payload = json.loads(body)
    choices = response_payload.get("choices") or []
    content = str((choices[0].get("message") or {}).get("content") or "")
    parsed = json.loads(content)
    proposal_ids = parsed.get("proposal_ids")
    if (
        not isinstance(proposal_ids, list)
        or not all(isinstance(value, str) for value in proposal_ids)
        or not set(proposal_ids) <= {"A0001"}
        or len(proposal_ids) != len(set(proposal_ids))
    ):
        raise RuntimeError("structured-output smoke violated strict proposal ID schema")
    snapshot = {
        "request_payload": request_payload,
        "raw_response_body": body,
        "provider_usage": response_payload.get("usage"),
        "parsed_proposal_ids": proposal_ids,
    }
    if not _secret_free(snapshot, api_key):
        raise RuntimeError("structured-output smoke retained a credential")
    return snapshot


def _npu_pairs(text: str) -> set[tuple[int, int]]:
    pairs: set[tuple[int, int]] = set()
    for line in text.splitlines():
        fields = [field.strip() for field in line.split("|")]
        if len(fields) < 4:
            continue
        device_fields = fields[1].split()
        pid = fields[2]
        if device_fields and device_fields[0].isdigit() and pid.isdigit():
            pairs.add((int(device_fields[0]), int(pid)))
    return pairs


def _validate_static(
    protocol: dict[str, Any], protocol_sha: str, grant: dict[str, Any], grant_sha: str,
    *, split: str, run_id: str
) -> dict[str, Any]:
    service = protocol["service"]
    commit = protocol["repository"]["execution_commit"]
    now = datetime.now(timezone.utc)
    issued = _utc(grant.get("issued_at_utc"))
    allocation_start = _utc(grant.get("allocation_start_utc"))
    checks = {
        "protocol": grant.get("protocol_sha256") == protocol_sha,
        "commit": grant.get("repository_commit") == commit,
        "status": grant.get("status") == "GRANTED",
        "grant-issued-before-allocation": issued <= allocation_start,
        "grant-issued-not-in-future": issued <= now,
        "allocation-started": allocation_start <= now,
        "expiry": _utc(grant.get("expires_utc")) > now,
        "allocation-duration": _utc(grant.get("expires_utc"))
        - _utc(grant.get("allocation_start_utc"))
        >= timedelta(minutes=protocol["reservation_shape"]["requested_duration_minutes"]),
        "remaining-experiment-window": _utc(grant.get("expires_utc"))
        - datetime.now(timezone.utc)
        >= timedelta(
            minutes=protocol["reservation_shape"][
                "minimum_remaining_at_admission_minutes"
            ]
        ),
        "split": grant.get("authorized_splits") == [split],
        "run-id": grant.get("run_ids", {}).get(split) == run_id,
        "npu": grant.get("resources", {}).get("physical_npus")
        == [service["physical_npu"]],
        "npu-count": grant.get("resources", {}).get("npu_count")
        == service["npu_count"],
        "topology": grant.get("resources", {}).get("topology")
        == service["topology"],
        "base-url": grant.get("service", {}).get("base_url") == service["base_url"],
        "port": grant.get("service", {}).get("port") == service["port"],
        "unit": grant.get("service", {}).get("managed_unit")
        == service["managed_unit"],
        "container": grant.get("service", {}).get("container")
        == service["container"],
        "manager": grant.get("service", {}).get("manager") == service["manager"],
        "model-name": grant.get("model", {}).get("served_model_name")
        == service["served_model_name"],
        "model-path": grant.get("model", {}).get("path") == service["model_path"],
        "model-config": grant.get("model", {}).get("config_sha256")
        == service["model_config_sha256"],
        "generation-config": grant.get("model", {}).get("generation_config_sha256")
        == service["generation_config_sha256"],
        "grant-sha": bool(grant_sha),
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError("grant binding failed: " + ", ".join(failed))
    return checks


def _validate_heldout_development_closure(
    path: Path, *, protocol_sha: str, commit: str, grant: dict[str, Any]
) -> dict[str, Any]:
    closure = _load(path)
    closure_sha = _sha256(path)
    completed = _utc(closure.get("completed_utc"))
    issued = _utc(grant.get("issued_at_utc"))
    raw_root = Path(str(closure.get("raw_root", ""))).resolve()
    expected_root = (
        ROOT / ".sage/benchmarks/semantic_reduce_edit_v2_real_online"
        / protocol_sha / f"development-{closure.get('run_id')}"
    ).resolve()
    checks = {
        "closure-status": closure.get("status") == "PASS",
        "closure-paper-admissible": closure.get("paper_admissible") is True,
        "closure-split": closure.get("split") == "development",
        "closure-protocol": closure.get("protocol_sha256") == protocol_sha,
        "closure-commit": closure.get("repository_commit") == commit,
        "closure-row-count": closure.get("verified_row_count") == 80,
        "closure-raw-root-canonical": raw_root == expected_root,
        "grant-closure-sha": grant.get("development_closure_sha256") == closure_sha,
        "grant-development-raw-root": Path(
            str(grant.get("development_raw_root", ""))
        ).resolve() == raw_root,
        "grant-issued-after-development": issued > completed,
    }
    for filename, field in (
        ("manifest.json", "manifest_sha256"),
        ("row-ledger.json", "ledger_sha256"),
        ("summary.json", "summary_sha256"),
    ):
        candidate = raw_root / filename
        checks[f"closure-{filename}-digest"] = (
            candidate.is_file() and _sha256(candidate) == closure.get(field)
        )
    if failed := [name for name, passed in checks.items() if not passed]:
        raise RuntimeError("heldout development closure rejected before launch: " + ", ".join(failed))
    return {"sha256": closure_sha, "raw_root": str(raw_root), "completed_utc": closure["completed_utc"]}


def _source_hashes(protocol: dict[str, Any]) -> dict[str, str]:
    commit = protocol["repository"]["execution_commit"]
    result: dict[str, str] = {}
    for name, item in protocol["repository"]["frozen_sources"].items():
        data = subprocess.check_output(
            ["git", "-C", str(ROOT), "show", f"{commit}:{item['path']}"]
        )
        digest = hashlib.sha256(data).hexdigest()
        if digest != item["sha256"]:
            raise RuntimeError(f"source hash mismatch: {name}")
        result[name] = digest
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("prelaunch", "postlaunch"), required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--protocol-sha256", required=True)
    parser.add_argument("--grant", type=Path, required=True)
    parser.add_argument("--split", choices=("development", "heldout"), required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--prelaunch", type=Path)
    parser.add_argument("--development-closure", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite preflight output")
    if _sha256(args.protocol) != args.protocol_sha256:
        raise SystemExit("protocol SHA mismatch")
    protocol, grant = _load(args.protocol), _load(args.grant)
    grant_sha = _sha256(args.grant)
    static = _validate_static(
        protocol, args.protocol_sha256, grant, grant_sha,
        split=args.split, run_id=args.run_id
    )
    development_binding = None
    if args.split == "heldout":
        if not args.development_closure:
            raise SystemExit("heldout preflight requires --development-closure")
        development_binding = _validate_heldout_development_closure(
            args.development_closure,
            protocol_sha=args.protocol_sha256,
            commit=protocol["repository"]["execution_commit"],
            grant=grant,
        )
    service = protocol["service"]
    commit = protocol["repository"]["execution_commit"]
    if _git(ROOT, "rev-parse", "HEAD") != commit or _git(ROOT, "status", "--porcelain"):
        raise SystemExit("execution checkout is not clean at the frozen commit")
    if os.environ.get("CONDA_DEFAULT_ENV", Path(sys.prefix).name) != "esage-vllm-hust-dev":
        raise SystemExit("wrong conda environment")
    source_hashes = _source_hashes(protocol)
    required_submodules = protocol["repository"]["frozen_submodules"]
    submodules: dict[str, dict[str, object]] = {}
    for path, expected in required_submodules.items():
        absolute = ROOT / path
        submodules[path] = {
            "commit": _git(absolute, "rev-parse", "HEAD"),
            "dirty": bool(_git(absolute, "status", "--porcelain")),
        }
        if submodules[path] != {"commit": expected, "dirty": False}:
            raise SystemExit(f"submodule drift: {path}")
    model_path = Path(service["model_path"])
    model_hashes = {
        "config_sha256": _sha256(model_path / "config.json"),
        "generation_config_sha256": _sha256(model_path / "generation_config.json"),
    }
    if model_hashes != {
        "config_sha256": service["model_config_sha256"],
        "generation_config_sha256": service["generation_config_sha256"],
    }:
        raise SystemExit("model metadata hash drift")
    raw_root = (
        ROOT / ".sage/benchmarks/semantic_reduce_edit_v2_real_online"
        / args.protocol_sha256 / f"{args.split}-{args.run_id}"
    )
    if raw_root.exists():
        raise SystemExit("canonical raw namespace already exists")
    free_gib = os.statvfs(ROOT).f_bavail * os.statvfs(ROOT).f_frsize / 2**30
    npu_text = _run("npu-smi", "info")
    npu = int(service["physical_npu"])
    port = int(service["port"])

    checks: dict[str, Any] = {
        "repository_clean": True,
        "submodules_clean": True,
        "conda_environment": "esage-vllm-hust-dev",
        "model_hashes_match": True,
        "frozen_source_hashes_match": True,
        "namespace_fresh": True,
        "free_space_gib": round(free_gib, 3),
        "cleanup_armed": os.environ.get("SAGE_V2_CLEANUP_ARMED") == "1",
    }
    if not checks["cleanup_armed"] or free_gib < 5:
        raise SystemExit("cleanup trap or free-space gate failed")
    observations: dict[str, Any] = {
        "source_hashes": source_hashes,
        "submodules": submodules,
        "model_hashes": model_hashes,
        "npu_process_pairs": sorted([list(pair) for pair in _npu_pairs(npu_text)]),
    }
    if args.phase == "prelaunch":
        if any(device == npu for device, _ in _npu_pairs(npu_text)):
            raise SystemExit("granted NPU is not idle before launch")
        if _port_open(port):
            raise SystemExit("granted port is not free before launch")
        unit_state = _run(
            "systemctl", "--user", "show", "-p", "LoadState", "--value",
            service["managed_unit"]
        ).strip()
        container_inspect = subprocess.run(
            ["sudo", "-n", "docker", "inspect", service["container"]],
            text=True, capture_output=True,
        )
        if unit_state != "not-found":
            raise SystemExit("grant-named managed unit already exists before launch")
        if container_inspect.returncode == 0:
            raise SystemExit("grant-named container already exists before launch")
        if "No such object" not in container_inspect.stderr:
            raise SystemExit("docker absence probe failed closed")
        checks.update(
            {
                "device_idle": True,
                "port_free": True,
                "managed_unit_absent": True,
                "container_absent": True,
            }
        )
    else:
        if not args.prelaunch:
            raise SystemExit("postlaunch requires the matching passing prelaunch record")
        prelaunch = _load(args.prelaunch)
        expected_prelaunch = {
            "status": "PASS_PRELAUNCH",
            "protocol_sha256": args.protocol_sha256,
            "repository_commit": commit,
            "grant_sha256": grant_sha,
            "split": args.split,
            "run_id": args.run_id,
        }
        if any(prelaunch.get(key) != value for key, value in expected_prelaunch.items()):
            raise SystemExit("prelaunch record provenance mismatch")
        if not all(
            prelaunch.get("checks", {}).get(key) is True
            for key in (
                "device_idle",
                "port_free",
                "managed_unit_absent",
                "container_absent",
            )
        ):
            raise SystemExit("prelaunch ownership/idle predicates are incomplete")
        container = service["container"]
        unit = service["managed_unit"]
        running = _run(
            "sudo", "-n", "docker", "inspect", "-f", "{{.State.Running}}", container
        ).strip() == "true"
        unit_active = _run("systemctl", "--user", "is-active", unit).strip() == "active"
        top = _run("sudo", "-n", "docker", "top", container, "-eo", "pid")
        container_pids = {
            int(line.strip()) for line in top.splitlines()[1:] if line.strip().isdigit()
        }
        device_pids = {pid for device, pid in _npu_pairs(npu_text) if device == npu}
        if not running or not unit_active or not device_pids or not device_pids <= container_pids:
            raise SystemExit("managed unit/container does not exactly own granted NPU")
        if not _port_open(port):
            raise SystemExit("granted port is not listening")
        listener_pids = _listener_pids(port)
        if not listener_pids or not listener_pids <= container_pids:
            raise SystemExit("listening socket is not owned by the grant container")
        api_key = os.environ.get(service["api_key_env"])
        if not api_key:
            raise SystemExit("API key missing for model identity probe")
        request = urllib.request.Request(
            f"{service['base_url']}/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            models = json.loads(response.read().decode("utf-8"))
        model_ids = sorted(str(item.get("id")) for item in models.get("data", []))
        if service["served_model_name"] not in model_ids:
            raise SystemExit("frozen served model absent from /v1/models")
        smoke = _structured_smoke(service=service, api_key=api_key)
        if not _secret_free(models, api_key):
            raise SystemExit("/v1/models snapshot retained a credential")
        checks.update(
            {
                "device_owner": "exact-grant-container",
                "port_owner": "exact-grant-service",
                "port_owner_process_lineage": True,
                "models_endpoint": "frozen-served-name-present",
                "structured_output_smoke": "strict-proposal-ids-pass",
                "raw_secret_scan": "PASS",
            }
        )
        observations.update(
            {
                "container_pids": sorted(container_pids),
                "granted_device_pids": sorted(device_pids),
                "listener_pids": sorted(listener_pids),
                "model_ids": model_ids,
                "models_endpoint_response": models,
                "structured_output_smoke": smoke,
            }
        )
    result = {
        "schema_version": "semantic-reduce-v2-physical-preflight/1",
        "status": "PASS" if args.phase == "postlaunch" else "PASS_PRELAUNCH",
        "phase": args.phase,
        "protocol_sha256": args.protocol_sha256,
        "repository_commit": commit,
        "grant_sha256": grant_sha,
        "split": args.split,
        "run_id": args.run_id,
        "service": {
            "base_url": service["base_url"],
            "port": port,
            "managed_unit": service["managed_unit"],
            "container": service["container"],
        },
        "static_grant_checks": static,
        "development_closure_binding": development_binding,
        "checks": checks,
        "observations": observations,
        "captured_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    if args.phase == "postlaunch":
        result["prelaunch_sha256"] = _sha256(args.prelaunch)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, separators=(",", ":"), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
