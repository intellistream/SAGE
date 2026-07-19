#!/usr/bin/env python3
"""Run the offline Semantic MapReduce experiment suite.

This orchestrator is the reproducible entry point for experiments that do not
launch a live model server. It runs the public-source probe plus the repo-local
large-scale and semantic-merge workloads, then records a suite-level manifest
that links all child artifacts and workload sources.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


DEFAULT_OUTPUT_ROOT = ".sage/benchmarks/semantic_mapreduce_offline_suite"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the offline Semantic MapReduce experiment suite."
    )
    parser.add_argument("--output-root", default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--run-id")
    parser.add_argument(
        "--profile",
        choices=("smoke", "paper"),
        default="smoke",
        help="Smoke is fast; paper reruns the larger offline matrices.",
    )
    parser.add_argument("--skip-shared-workload-probe", action="store_true")
    parser.add_argument("--skip-public-source-probe", action="store_true")
    parser.add_argument("--skip-coverage-sweep", action="store_true")
    parser.add_argument("--skip-large-scale", action="store_true")
    parser.add_argument("--skip-semantic-merge", action="store_true")
    parser.add_argument("--max-download-mb", type=float, default=64.0)
    return parser.parse_args()


def _git_output(args: list[str], *, cwd: Path | None = None) -> str:
    try:
        command = ["git"]
        if cwd is not None:
            command.extend(["-C", str(cwd)])
        command.extend(args)
        return subprocess.check_output(
            command, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def _submodule_info(path: str) -> dict[str, Any]:
    module_path = Path(path)
    if not module_path.exists():
        return {"path": path, "present": False}
    return {
        "path": path,
        "present": True,
        "commit": _git_output(["rev-parse", "HEAD"], cwd=module_path),
        "branch": _git_output(["rev-parse", "--abbrev-ref", "HEAD"], cwd=module_path),
        "dirty": bool(_git_output(["status", "--porcelain"], cwd=module_path)),
    }


def _base_manifest(outdir: Path, args: argparse.Namespace) -> dict[str, Any]:
    return {
        "run_id": outdir.name,
        "created_unix": int(time.time()),
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "command_args": vars(args),
        "command_line": " ".join(sys.argv),
        "python": {
            "version": platform.python_version(),
            "executable": sys.executable,
        },
        "conda_env": os.environ.get("CONDA_DEFAULT_ENV", ""),
        "git": {
            "commit": _git_output(["rev-parse", "HEAD"]),
            "branch": _git_output(["rev-parse", "--abbrev-ref", "HEAD"]),
            "dirty": bool(_git_output(["status", "--porcelain"])),
        },
        "evidence_label": "derived-artifact",
        "shared_workload_submodule": _submodule_info(
            "third_party/llm-serving-workloads"
        ),
        "runtime_submodules": {
            path: _submodule_info(path)
            for path in (
                "external/vllm-hust",
                "external/vllm-ascend-hust",
                "external/triton-ascend-hust",
                "external/vllm-hust-dev-hub",
                "third_party/ascend-runtime-manager",
            )
        },
    }


def _run_child(
    *,
    name: str,
    command: list[str],
    outdir: Path,
    env: dict[str, str],
) -> dict[str, Any]:
    started = time.perf_counter()
    log_path = outdir / f"{name}.log"
    with log_path.open("w", encoding="utf-8") as log:
        log.write("$ " + " ".join(command) + "\n")
        log.flush()
        proc = subprocess.run(
            command,
            env=env,
            text=True,
            stdout=log,
            stderr=subprocess.STDOUT,
        )
    duration_ms = round((time.perf_counter() - started) * 1000, 2)
    status = {
        "name": name,
        "command": command,
        "returncode": proc.returncode,
        "duration_ms": duration_ms,
        "log": str(log_path),
    }
    if proc.returncode != 0:
        failed = outdir / "FAILED.txt"
        failed.write_text(
            f"child={name}\nreturncode={proc.returncode}\nlog={log_path}\n",
            encoding="utf-8",
        )
    return status


def _child_commands(args: argparse.Namespace, outdir: Path) -> list[tuple[str, list[str]]]:
    python = sys.executable
    commands: list[tuple[str, list[str]]] = []
    if not args.skip_shared_workload_probe:
        seeds = "7,11,13" if args.profile == "paper" else "7"
        commands.append(
            (
                "shared-workload-probe",
                [
                    python,
                    "tools/benchmark_carrier/run_shared_llm_serving_workload_probe.py",
                    "--output-root",
                    str(outdir / "shared_llm_serving_workloads"),
                    "--run-id",
                    f"{outdir.name}-shared-workload-{args.profile}",
                    "--seeds",
                    seeds,
                ],
            )
        )

    if not args.skip_public_source_probe:
        commands.append(
            (
                "public-source-probe",
                [
                    python,
                    "tools/benchmark_carrier/probe_public_semantic_mapreduce_sources.py",
                    "--output-root",
                    str(outdir / "public_sources"),
                    "--run-id",
                    f"{outdir.name}-public-source-probe",
                    "--max-download-mb",
                    str(args.max_download_mb),
                ],
            )
        )

    if not args.skip_coverage_sweep:
        if args.profile == "paper":
            sizes = "2000:4:8,10000:8:12,50000:16:12,100000:32:16"
            seeds = "7,11,13,17,19,23,29,31,37,41"
            map_policies = "tail-aware,baseline-aware"
        else:
            sizes = "2000:4:8,10000:8:12"
            seeds = "7"
            map_policies = "tail-aware,baseline-aware"
        commands.append(
            (
                "large-scale-coverage",
                [
                    python,
                    "tools/benchmark_carrier/run_large_scale_analysis_coverage_sweep.py",
                    "--output-root",
                    str(outdir / "large_scale_coverage"),
                    "--run-id",
                    f"{outdir.name}-coverage-{args.profile}",
                    "--sizes",
                    sizes,
                    "--seeds",
                    seeds,
                    "--map-policies",
                    map_policies,
                    "--reducers",
                    "map-only,window-aggregate,deterministic,llm-stub",
                ],
            )
        )

    if not args.skip_large_scale:
        if args.profile == "paper":
            sizes = "50000:16:12,100000:32:16"
            seeds = "7,11,13,17,19,23,29,31,37,41"
            reducers = "map-only,window-aggregate,deterministic,llm-stub"
            map_policies = "baseline-aware"
        else:
            sizes = "1000:2:4"
            seeds = "7"
            reducers = "map-only,window-aggregate,deterministic,llm-stub"
            map_policies = "baseline-aware"
        commands.append(
            (
                "large-scale-analysis",
                [
                    python,
                    "tools/benchmark_carrier/run_large_scale_analysis_matrix.py",
                    "--output-root",
                    str(outdir / "large_scale_analysis"),
                    "--run-id",
                    f"{outdir.name}-large-scale-{args.profile}",
                    "--sizes",
                    sizes,
                    "--seeds",
                    seeds,
                    "--reducers",
                    reducers,
                    "--map-policies",
                    map_policies,
                ],
            )
        )

    if not args.skip_semantic_merge:
        if args.profile == "paper":
            seeds = "7,11,13,17,19,23,29,31,37,41"
            reducers = (
                "map-only,service-local,window-aggregate,"
                "constrained-agglomerative,semantic-graph,hybrid-hint,llm-stub"
            )
            scenarios = (
                "single-service,cascade,shared-bottleneck,concurrent,"
                "false-correlation,partial-evidence,ambiguous-overmerge,"
                "ambiguous-disconnected-merge,ambiguous-temporal-split"
            )
        else:
            seeds = "7"
            reducers = (
                "map-only,window-aggregate,constrained-agglomerative,"
                "semantic-graph,hybrid-hint,llm-stub"
            )
            scenarios = "cascade,partial-evidence,false-correlation"
        commands.append(
            (
                "semantic-merge",
                [
                    python,
                    "tools/benchmark_carrier/run_semantic_merge_matrix.py",
                    "--output-root",
                    str(outdir / "semantic_merge_analysis"),
                    "--run-id",
                    f"{outdir.name}-semantic-merge-{args.profile}",
                    "--seeds",
                    seeds,
                    "--reducers",
                    reducers,
                    "--scenarios",
                    scenarios,
                ],
            )
        )
    return commands


def main() -> int:
    args = _parse_args()
    run_id = args.run_id or time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    outdir = Path(args.output_root) / run_id
    outdir.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["PYTHONPATH"] = "src" + os.pathsep + env.get("PYTHONPATH", "")

    manifest = _base_manifest(outdir, args)
    child_statuses: list[dict[str, Any]] = []
    commands = _child_commands(args, outdir)
    for name, command in commands:
        print(f"running {name}: {' '.join(command)}")
        status = _run_child(name=name, command=command, outdir=outdir, env=env)
        child_statuses.append(status)
        print(
            f"done {name} returncode={status['returncode']} "
            f"duration_ms={status['duration_ms']}"
        )
        if status["returncode"] != 0:
            manifest["children"] = child_statuses
            (outdir / "suite_metadata.json").write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            print(f"RESULT_DIR={outdir}")
            return int(status["returncode"])

    manifest["children"] = child_statuses
    manifest["completed_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    (outdir / "suite_metadata.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"RESULT_DIR={outdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
