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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--protocol-sha256", required=True)
    parser.add_argument("--grant", type=Path, required=True)
    parser.add_argument("--split", choices=("development", "heldout"), required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--development-gate", type=Path)
    args = parser.parse_args()
    if _sha256(args.protocol) != args.protocol_sha256:
        raise SystemExit("protocol SHA mismatch")
    protocol = _load(args.protocol)
    _load(args.grant)
    service = protocol["service"]
    if args.split == "heldout" and not args.development_gate:
        raise SystemExit("heldout requires --development-gate")
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
    service_launch_attempted = False
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
        if args.development_gate:
            runner_command.extend(["--development-gate", str(args.development_gate)])
        _run(
            runner_command,
            env=env,
            log=control / "runner.log",
            scan_results=scan_results,
        )
        raw_root = (
            ROOT / ".sage/benchmarks/semantic_reduce_edit_v2_real_online"
            / args.protocol_sha256 / f"{args.split}-{args.run_id}"
        )
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
        outcome, exit_code = "PASS", 0
    except BaseException as exc:
        failure = f"{type(exc).__name__}: {exc}"
    finally:
        cleanup_errors: list[str] = []
        if service_launch_attempted:
            stop_env = dict(env)
            stop_env.update(
                {
                    "VLLM_ENGINE_PORT": str(service["port"]),
                    "VLLM_ENGINE_SYSTEMD_UNIT": service["managed_unit"],
                    "VLLM_ENGINE_CONTAINER": service["container"],
                }
            )
            with (control / "cleanup.log").open("xb") as stream:
                stopped = subprocess.run(
                    ["bash", "manage.sh", "stop"],
                    cwd=ROOT / service["manager"],
                    env=stop_env,
                    stdout=stream,
                    stderr=subprocess.STDOUT,
                )
                if stopped.returncode:
                    cleanup_errors.append(f"manage-stop-exit-{stopped.returncode}")
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
        scanned_paths = {Path(item["path"]).resolve() for item in scan_results}
        for artifact in sorted(control.rglob("*")):
            if not artifact.is_file() or artifact.resolve() in scanned_paths:
                continue
            try:
                _scan_and_redact_log(
                    artifact,
                    api_key=env.get("VLLM_HUST_API_KEY", ""),
                    results=scan_results,
                )
            except RuntimeError as exc:
                cleanup_errors.append(str(exc))
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
        release.write_text(json.dumps(release_payload, indent=2) + "\n", encoding="utf-8")
        if cleanup_errors:
            exit_code = 1
    print(release.read_text(encoding="utf-8"), end="")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
