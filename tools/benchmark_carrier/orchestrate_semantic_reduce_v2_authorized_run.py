#!/usr/bin/env python3
"""Run the exact authorized v2 chain and always emit scoped release evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import signal
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools/benchmark_carrier"
CONTROL_PARENT = ROOT / ".sage/control/semantic_reduce_edit_v2_real_online"


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace(
        "+00:00", "Z"
    )


def _scan_and_redact_log(
    path: Path, *, api_key: str, results: list[dict[str, Any]]
) -> None:
    original = path.read_text(encoding="utf-8", errors="replace")
    redacted = original
    findings: list[str] = []
    if api_key and api_key in redacted:
        findings.append("exact-api-key")
        redacted = redacted.replace(api_key, "<REDACTED-EXACT-API-KEY>")
    patterns = {
        "authorization-bearer": r"(?i)(authorization[^\n]{0,16}bearer\s+)[A-Za-z0-9._~+/=-]{8,}",
        "bearer-token": r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]{8,}",
        "api-key-value": r'(?i)(["\']?api[_-]?key["\']?\s*[:=]\s*["\']?)[^\s"\']{8,}',
    }
    for name, pattern in patterns.items():
        if re.search(pattern, redacted):
            findings.append(name)
            redacted = re.sub(pattern, r"\1<REDACTED>", redacted)
    if redacted != original:
        path.write_text(redacted, encoding="utf-8")
    results.append(
        {
            "path": str(path),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "status": "FAIL_REDACTED" if findings else "PASS",
            "findings": sorted(set(findings)),
        }
    )
    if findings:
        raise RuntimeError(f"credential material detected and redacted in {path.name}")


def _run(
    command: list[str],
    *,
    env: dict[str, str],
    log: Path,
    scan_results: list[dict[str, Any]],
) -> None:
    with log.open("xb") as stream:
        result = subprocess.run(
            command,
            cwd=ROOT,
            env=env,
            stdout=stream,
            stderr=subprocess.STDOUT,
        )
    _scan_and_redact_log(
        log,
        api_key=env.get("VLLM_HUST_API_KEY", ""),
        results=scan_results,
    )
    if result.returncode:
        raise RuntimeError(f"command failed ({result.returncode}): {command[0]}")


def _port_open(port: int) -> bool:
    with socket.socket() as sock:
        sock.settimeout(0.5)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def _granted_npu_has_process(npu: int) -> bool:
    result = subprocess.run(
        ["npu-smi", "info"], text=True, capture_output=True
    )
    for line in result.stdout.splitlines():
        fields = [field.strip() for field in line.split("|")]
        if len(fields) >= 4:
            device = fields[1].split()
            if device and device[0].isdigit() and int(device[0]) == npu:
                if fields[2].isdigit():
                    return True
    return False


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _scan_tree(
    root: Path,
    *,
    api_key: str,
    results: list[dict[str, Any]],
    already_scanned: set[Path] | None = None,
) -> list[str]:
    errors: list[str] = []
    seen = already_scanned or set()
    if not root.exists():
        return errors
    for artifact in sorted(root.rglob("*")):
        if not artifact.is_file() or artifact.resolve() in seen:
            continue
        try:
            _scan_and_redact_log(artifact, api_key=api_key, results=results)
        except RuntimeError as exc:
            errors.append(str(exc))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--protocol-sha256", required=True)
    parser.add_argument("--grant", type=Path, required=True)
    parser.add_argument("--split", choices=("development", "heldout"), required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--development-closure", type=Path)
    args = parser.parse_args()
    if _sha256(args.protocol) != args.protocol_sha256:
        raise SystemExit("protocol SHA mismatch")
    protocol = _load(args.protocol)
    _load(args.grant)
    service = protocol["service"]
    if args.split == "heldout" and not args.development_closure:
        raise SystemExit("heldout requires --development-closure")
    control = CONTROL_PARENT / args.protocol_sha256 / f"{args.split}-{args.run_id}"
    if control.exists():
        raise SystemExit("refusing to reuse control namespace")
    control.mkdir(parents=True)
    prelaunch = control / "prelaunch.json"
    postlaunch = control / "postlaunch.json"
    release = control / "release-request.json"
    env = dict(os.environ)
    env.update(
        {
            "SAGE_V2_CLEANUP_ARMED": "1",
            "SAGE_RUNTIME_FETCH": "0",
            "SAGE_REAL_ONLINE_NPU_DEVICE": str(service["physical_npu"]),
            "SAGE_REAL_ONLINE_PORT": str(service["port"]),
            "SAGE_REAL_ONLINE_MODEL_PATH": service["model_path"],
            "SAGE_REAL_ONLINE_MODEL_NAME": service["served_model_name"],
            "SAGE_REAL_ONLINE_SYSTEMD_UNIT": service["managed_unit"],
            "SAGE_REAL_ONLINE_CONTAINER": service["container"],
            "SAGE_REAL_ONLINE_RUN_ID": f"v2-{args.split}-{args.run_id}",
            "SAGE_REAL_ONLINE_OUTPUT_ROOT": str(control / "service-launch"),
        }
    )
    common = [
        "--protocol", str(args.protocol.resolve()),
        "--protocol-sha256", args.protocol_sha256,
        "--grant", str(args.grant.resolve()),
        "--split", args.split,
        "--run-id", args.run_id,
    ]
    prelaunch_fresh_names = False
    service_launch_attempted = False
    service_ownership_verified = False
    runner_complete = False
    termination_signal: int | None = None
    scan_results: list[dict[str, Any]] = []

    def _mark_signal(signum: int, _frame: object) -> None:
        nonlocal termination_signal
        termination_signal = signum
        raise KeyboardInterrupt(f"received signal {signum}")

    signal.signal(signal.SIGINT, _mark_signal)
    signal.signal(signal.SIGTERM, _mark_signal)
    outcome = "FAILED"
    failure: str | None = None
    exit_code = 1
    try:
        _run(
            [
                sys.executable,
                str(TOOLS / "preflight_semantic_reduce_v2_online.py"),
                "--phase", "prelaunch",
                *common,
                "--output", str(prelaunch),
            ],
            env=env,
            log=control / "prelaunch.log",
            scan_results=scan_results,
        )
        prelaunch_fresh_names = True
        service_launch_attempted = True
        _run(
            [
                "bash",
                str(TOOLS / "run_npu3_semantic_mapreduce_experiment.sh"),
                "--keep-server",
                "--skip-online-probe",
                "--skip-llm-reducer",
                "--npu", str(service["physical_npu"]),
                "--port", str(service["port"]),
                "--model-path", service["model_path"],
                "--served-model", service["served_model_name"],
                "--run-id", f"v2-{args.split}-{args.run_id}",
                "--output-root", str(control / "service-launch"),
            ],
            env=env,
            log=control / "service-launch.log",
            scan_results=scan_results,
        )
        service_ownership_verified = True
        _run(
            [
                sys.executable,
                str(TOOLS / "preflight_semantic_reduce_v2_online.py"),
                "--phase", "postlaunch",
                *common,
                "--prelaunch", str(prelaunch),
                "--output", str(postlaunch),
            ],
            env=env,
            log=control / "postlaunch.log",
            scan_results=scan_results,
        )
        runner_command = [
            sys.executable,
            str(TOOLS / "run_semantic_reduce_edit_v2_online_matrix.py"),
            *common,
            "--preflight", str(postlaunch),
        ]
        if args.development_closure:
            runner_command.extend(
                ["--development-closure", str(args.development_closure)]
            )
        _run(
            runner_command,
            env=env,
            log=control / "runner.log",
            scan_results=scan_results,
        )
        runner_complete = True
        outcome = "RAW_PROVISIONAL_COMPLETE"
    except BaseException as exc:
        failure = f"{type(exc).__name__}: {exc}"
    finally:
        cleanup_errors: list[str] = []
        if service_launch_attempted and prelaunch_fresh_names:
            with (control / "cleanup.log").open("xb") as stream:
                subprocess.run(
                    ["systemctl", "--user", "stop", service["managed_unit"]],
                    cwd=ROOT,
                    env=env,
                    stdout=stream,
                    stderr=subprocess.STDOUT,
                )
                inspect = subprocess.run(
                    [
                        "sudo", "-n", "docker", "inspect", "-f",
                        "{{.State.Running}}", service["container"],
                    ],
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                )
                if inspect.returncode == 0 and inspect.stdout.strip() == "true":
                    docker_stop = subprocess.run(
                        ["sudo", "-n", "docker", "stop", service["container"]],
                        stdout=stream,
                        stderr=subprocess.STDOUT,
                    )
                    if docker_stop.returncode:
                        cleanup_errors.append(
                            f"docker-stop-exit-{docker_stop.returncode}"
                        )
                remove = subprocess.run(
                    ["sudo", "-n", "docker", "rm", service["container"]],
                    stdout=stream,
                    stderr=subprocess.STDOUT,
                )
                if remove.returncode not in {0, 1}:
                    cleanup_errors.append(f"docker-rm-exit-{remove.returncode}")
            try:
                _scan_and_redact_log(
                    control / "cleanup.log",
                    api_key=env.get("VLLM_HUST_API_KEY", ""),
                    results=scan_results,
                )
            except RuntimeError as exc:
                cleanup_errors.append(str(exc))
            for _ in range(30):
                if not _port_open(int(service["port"])) and not _granted_npu_has_process(
                    int(service["physical_npu"])
                ):
                    break
                time.sleep(1)
            else:
                cleanup_errors.append("device-or-port-still-occupied")
        unit_active = subprocess.run(
            ["systemctl", "--user", "is-active", service["managed_unit"]],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode == 0
        container_present = subprocess.run(
            ["sudo", "-n", "docker", "inspect", service["container"]],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode == 0
        if unit_active or container_present:
            cleanup_errors.append("grant-named-unit-or-container-still-present")
        cleanup_observation = {
            "schema_version": "semantic-reduce-v2-cleanup-observation/1",
            "status": "PASS" if not cleanup_errors else "FAIL",
            "protocol_sha256": args.protocol_sha256,
            "grant_sha256": _sha256(args.grant),
            "split": args.split,
            "run_id": args.run_id,
            "ownership_basis": {
                "unit_and_container_absent_prelaunch": prelaunch_fresh_names,
                "postlaunch_process_lineage_verified": service_ownership_verified,
                "cleanup_used_only_exact_systemd_unit_and_container": True,
                "manage_sh_stop_used": False,
            },
            "observed_clear": {
                "npu": not _granted_npu_has_process(int(service["physical_npu"])),
                "port": not _port_open(int(service["port"])),
                "managed_unit_active": unit_active,
                "container_present": container_present,
            },
            "errors": cleanup_errors,
            "completed_utc": _now(),
        }
        _write_json(control / "cleanup-observation.json", cleanup_observation)

        raw_root = (
            ROOT / ".sage/benchmarks/semantic_reduce_edit_v2_real_online"
            / args.protocol_sha256 / f"{args.split}-{args.run_id}"
        )
        raw_scan_results: list[dict[str, Any]] = []
        raw_scan_errors = _scan_tree(
            raw_root,
            api_key=env.get("VLLM_HUST_API_KEY", ""),
            results=raw_scan_results,
        )
        raw_secret_scan = {
            "schema_version": "semantic-reduce-v2-raw-secret-scan/1",
            "status": "PASS" if raw_scan_results and not raw_scan_errors else "FAIL",
            "scanned_files": raw_scan_results,
            "errors": raw_scan_errors,
            "completed_utc": _now(),
        }
        _write_json(control / "raw-secret-scan.json", raw_secret_scan)
        if raw_scan_errors:
            cleanup_errors.extend(raw_scan_errors)

        verification_pass = False
        if runner_complete and not cleanup_errors and raw_secret_scan["status"] == "PASS":
            try:
                _run(
                    [
                        sys.executable,
                        str(TOOLS / "verify_semantic_reduce_v2_online_run.py"),
                        "--raw-root", str(raw_root),
                        "--expected-protocol-sha256", args.protocol_sha256,
                        "--expected-repository-commit",
                        protocol["repository"]["execution_commit"],
                        "--output", str(control / "verification.json"),
                    ],
                    env=env,
                    log=control / "verification.log",
                    scan_results=scan_results,
                )
                verification_pass = _load(control / "verification.json").get("status") == "PASS"
            except BaseException as exc:
                cleanup_errors.append(f"raw-verifier: {type(exc).__name__}: {exc}")

        scanned_paths = {Path(item["path"]).resolve() for item in scan_results}
        cleanup_errors.extend(
            _scan_tree(
                control,
                api_key=env.get("VLLM_HUST_API_KEY", ""),
                results=scan_results,
                already_scanned=scanned_paths,
            )
        )
        secret_scan = {
            "schema_version": "semantic-reduce-v2-control-secret-scan/1",
            "status": (
                "PASS"
                if scan_results
                and all(item["status"] == "PASS" for item in scan_results)
                else "FAIL"
            ),
            "scanned_files": scan_results,
            "completed_utc": _now(),
        }
        (control / "control-secret-scan.json").write_text(
            json.dumps(secret_scan, indent=2) + "\n", encoding="utf-8"
        )
        if secret_scan["status"] != "PASS":
            cleanup_errors.append("control-secret-scan-failed")
        release_payload = {
            "schema_version": "semantic-reduce-v2-release-request/1",
            "status": "REQUEST_ONLY_CENTRAL_ACK_REQUIRED",
            "protocol_sha256": args.protocol_sha256,
            "repository_commit": protocol["repository"]["execution_commit"],
            "grant_sha256": _sha256(args.grant),
            "split": args.split,
            "run_id": args.run_id,
            "experiment_outcome": outcome,
            "failure": failure,
            "termination_signal": termination_signal,
            "cleanup": {
                "grant_named_unit": service["managed_unit"],
                "grant_named_container": service["container"],
                "grant_named_npu": service["physical_npu"],
                "grant_named_port": service["port"],
                "status": "PASS" if not cleanup_errors else "FAIL",
                "errors": cleanup_errors,
            },
            "control_secret_scan": {
                "status": secret_scan["status"],
                "report_sha256": _sha256(control / "control-secret-scan.json"),
            },
            "queue_mutation_performed": False,
            "release_requested_utc": _now(),
        }
        _write_json(release, release_payload)
        local_pass = (
            runner_complete
            and verification_pass
            and not cleanup_errors
            and cleanup_observation["status"] == "PASS"
            and raw_secret_scan["status"] == "PASS"
            and secret_scan["status"] == "PASS"
        )
        if local_pass:
            inventory = {
                str(path.relative_to(control)): _sha256(path)
                for path in sorted(control.rglob("*"))
                if path.is_file()
            }
            handoff = {
                "schema_version": "semantic-reduce-v2-execution-handoff/1",
                "status": "LOCAL_GATES_PASS_PENDING_CENTRAL_RELEASE_ACK",
                "paper_admissible": False,
                "protocol_sha256": args.protocol_sha256,
                "repository_commit": protocol["repository"]["execution_commit"],
                "grant_sha256": _sha256(args.grant),
                "split": args.split,
                "run_id": args.run_id,
                "raw_root": str(raw_root.resolve()),
                "raw_manifest_sha256": _sha256(raw_root / "manifest.json"),
                "raw_ledger_sha256": _sha256(raw_root / "row-ledger.json"),
                "raw_summary_sha256": _sha256(raw_root / "summary.json"),
                "verified_row_count": _load(control / "verification.json")[
                    "verified_row_count"
                ],
                "control_inventory": inventory,
                "release_request_sha256": _sha256(release),
                "completed_utc": _now(),
            }
            _write_json(control / "execution-handoff.json", handoff)
            outcome, exit_code = "LOCAL_GATES_PASS_PENDING_CENTRAL_ACK", 0
        else:
            disposition = {
                "status": "FAILED_LOCAL_CLOSURE",
                "paper_admissible": False,
                "protocol_sha256": args.protocol_sha256,
                "grant_sha256": _sha256(args.grant),
                "split": args.split,
                "run_id": args.run_id,
                "runner_complete": runner_complete,
                "raw_verification_pass": verification_pass,
                "cleanup_errors": cleanup_errors,
                "failure": failure,
                "completed_utc": _now(),
            }
            _write_json(control / "execution-disposition.json", disposition)
            exit_code = 1
    print(release.read_text(encoding="utf-8"), end="")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
