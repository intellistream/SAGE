from __future__ import annotations

import argparse
import json
import platform
import shlex
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_PATH_FLAGS = {
    "--experiment-manifest",
    "--run-plan",
    "--workload-replay",
    "--summary-output",
    "--trace-output",
    "--raw-log-output",
}
_PLACEHOLDER = "<benchmark-carrier-entrypoint>"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Render or execute the frozen VAMOS burst-overload launcher contract from the SAGE workspace."
        )
    )
    parser.add_argument(
        "--contract", required=True, help="Path to the launcher contract JSON file."
    )
    parser.add_argument(
        "--carrier-entrypoint",
        required=True,
        help="Shell-style command prefix that replaces the carrier entrypoint placeholder.",
    )
    parser.add_argument(
        "--plan-output",
        help="Optional path to write the rendered launch plan JSON. Defaults to stdout.",
    )
    parser.add_argument(
        "--benchmark-carrier-root",
        default=".",
        help="Working directory used when executing the carrier command.",
    )
    parser.add_argument(
        "--sage-root",
        default=str(Path(__file__).resolve().parents[2]),
        help="SAGE repository root used for commit capture.",
    )
    parser.add_argument(
        "--vllm-hust-root",
        help="Optional vllm-hust repository root used for commit capture.",
    )
    parser.add_argument(
        "--variant-kind",
        choices=["baseline", "ablation"],
        help="Render or execute only variants of this kind.",
    )
    parser.add_argument("--variant-name", help="Render or execute only the named variant.")
    parser.add_argument(
        "--seed", type=int, help="Override the contract seed for all selected variants."
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute the rendered commands instead of only producing a launch plan.",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop on the first failed variant execution.",
    )
    return parser.parse_args()


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return payload


def _discover_coordination_root(contract_path: Path) -> Path:
    for candidate in [contract_path.parent, *contract_path.parents]:
        if (candidate / "manifests").is_dir() and (candidate / "results").is_dir():
            return candidate
    raise ValueError(
        f"Could not infer coordination repo root from {contract_path}; expected parent with manifests/ and results/."
    )


def _git_commit(repo_root: Path | None) -> str | None:
    if repo_root is None or not repo_root.exists():
        return None
    result = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    value = result.stdout.strip()
    return value or None


def _hardware_metadata() -> dict[str, Any]:
    return {
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python_version": platform.python_version(),
    }


def _replace_seed(argv: list[str], seed: int) -> list[str]:
    updated = list(argv)
    if "--seed" in updated:
        index = updated.index("--seed")
        if index + 1 >= len(updated):
            raise ValueError("Launcher contract contains --seed without a value.")
        updated[index + 1] = str(seed)
        return updated
    updated.extend(["--seed", str(seed)])
    return updated


def _resolve_contract_paths(argv: list[str], coordination_root: Path) -> list[str]:
    resolved = list(argv)
    index = 0
    while index < len(resolved):
        token = resolved[index]
        if token in _PATH_FLAGS and index + 1 < len(resolved):
            raw_path = Path(resolved[index + 1])
            resolved[index + 1] = str(
                raw_path if raw_path.is_absolute() else coordination_root / raw_path
            )
            index += 2
            continue
        index += 1
    return resolved


def _extract_flag_value(argv: list[str], flag: str) -> str | None:
    if flag not in argv:
        return None
    index = argv.index(flag)
    if index + 1 >= len(argv):
        return None
    return argv[index + 1]


def _metadata_output_path(summary_output: str | None) -> str | None:
    if not summary_output:
        return None
    summary_path = Path(summary_output)
    return str(summary_path.with_name(f"{summary_path.stem}.run-metadata.json"))


def _output_root_from_argv(argv: list[str]) -> Path | None:
    value = _extract_flag_value(argv, "--output-root")
    if not value:
        return None
    return Path(value).resolve()


def _rewrite_for_output_root(path_value: str | None, output_root: Path | None) -> str | None:
    if not path_value or output_root is None:
        return path_value
    path = Path(path_value)
    parts = list(path.parts)
    if "results" in parts:
        suffix = Path(*parts[parts.index("results") :])
        return str(output_root / suffix)
    return str(output_root / path.name)


def _filter_variants(
    variants: list[dict[str, Any]],
    variant_kind: str | None,
    variant_name: str | None,
) -> list[dict[str, Any]]:
    filtered: list[dict[str, Any]] = []
    for item in variants:
        kind = str(item.get("kind") or "").strip()
        name = str(item.get("name") or "").strip()
        if variant_kind and kind != variant_kind:
            continue
        if variant_name and name != variant_name:
            continue
        filtered.append(item)
    return filtered


def _ensure_parent_dirs(paths: list[str | None]) -> None:
    for value in paths:
        if not value:
            continue
        Path(value).parent.mkdir(parents=True, exist_ok=True)


def _tail(text: str, limit: int = 20) -> list[str]:
    lines = [line for line in text.splitlines() if line.strip()]
    if len(lines) <= limit:
        return lines
    return lines[-limit:]


def _build_variant_record(
    spec: dict[str, Any],
    coordination_root: Path,
    carrier_prefix: list[str],
    seed_override: int | None,
    sage_commit: str | None,
    vllm_hust_commit: str | None,
    benchmark_carrier_commit: str | None,
    benchmark_carrier_root: Path,
) -> dict[str, Any]:
    command_template = dict(spec.get("command_template") or {})
    argv = list(command_template.get("argv") or [])
    if not argv or argv[0] != _PLACEHOLDER:
        raise ValueError("Launcher contract variant is missing the carrier entrypoint placeholder.")
    rendered_argv = [*carrier_prefix, *argv[1:]]
    rendered_argv = _resolve_contract_paths(rendered_argv, coordination_root)
    if seed_override is not None:
        rendered_argv = _replace_seed(rendered_argv, seed_override)

    output_root = _output_root_from_argv(rendered_argv)
    summary_output = _extract_flag_value(rendered_argv, "--summary-output")
    trace_output = _extract_flag_value(rendered_argv, "--trace-output")
    raw_log_output = _extract_flag_value(rendered_argv, "--raw-log-output")
    seed_value = _extract_flag_value(rendered_argv, "--seed")
    run_id = spec.get("run_id")
    metadata_output = _rewrite_for_output_root(_metadata_output_path(summary_output), output_root)

    return {
        "kind": spec.get("kind"),
        "name": spec.get("name"),
        "results_namespace": spec.get("results_namespace"),
        "run_id": run_id,
        "required_captured_metadata": list(spec.get("required_captured_metadata") or []),
        "command": {
            "argv": rendered_argv,
            "full_command_line": shlex.join(rendered_argv),
            "cwd": str(benchmark_carrier_root),
        },
        "outputs": {
            "summary": summary_output,
            "trace": trace_output,
            "raw_log": raw_log_output,
            "metadata": metadata_output,
        },
        "metadata": {
            "run_id": run_id,
            "seed": int(seed_value) if seed_value is not None else None,
            "sage_commit": sage_commit,
            "vllm_hust_commit": vllm_hust_commit,
            "benchmark_carrier_commit": benchmark_carrier_commit,
            "hardware_metadata": _hardware_metadata(),
            "run_started_at": None,
            "run_finished_at": None,
        },
        "execution": {
            "status": "planned",
            "exit_code": None,
            "stdout_tail": [],
            "stderr_tail": [],
        },
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _execute_variant(record: dict[str, Any]) -> None:
    outputs = dict(record.get("outputs") or {})
    _ensure_parent_dirs(
        [
            outputs.get("summary"),
            outputs.get("trace"),
            outputs.get("raw_log"),
            outputs.get("metadata"),
        ]
    )

    metadata = dict(record.get("metadata") or {})
    metadata["run_started_at"] = datetime.now(timezone.utc).isoformat()
    record["metadata"] = metadata

    command = dict(record.get("command") or {})
    argv = list(command.get("argv") or [])
    result = subprocess.run(
        argv,
        cwd=command.get("cwd") or None,
        check=False,
        capture_output=True,
        text=True,
    )

    metadata["run_finished_at"] = datetime.now(timezone.utc).isoformat()
    record["metadata"] = metadata
    record["execution"] = {
        "status": "completed" if result.returncode == 0 else "failed",
        "exit_code": result.returncode,
        "stdout_tail": _tail(result.stdout),
        "stderr_tail": _tail(result.stderr),
    }

    metadata_output = outputs.get("metadata")
    if metadata_output:
        _write_json(Path(metadata_output), record)


def main() -> int:
    args = _parse_args()
    contract_path = Path(args.contract).resolve()
    contract = _load_json(contract_path)
    if str(contract.get("contract_kind") or "").strip() != "benchmark-carrier-launcher-contract":
        raise ValueError(f"Unsupported contract_kind in {contract_path}")

    coordination_root = _discover_coordination_root(contract_path)
    carrier_prefix = shlex.split(args.carrier_entrypoint)
    if not carrier_prefix:
        raise ValueError("--carrier-entrypoint must not be empty.")

    benchmark_carrier_root = Path(args.benchmark_carrier_root).resolve()
    sage_root = Path(args.sage_root).resolve()
    vllm_hust_root = Path(args.vllm_hust_root).resolve() if args.vllm_hust_root else None

    sage_commit = _git_commit(sage_root)
    vllm_hust_commit = _git_commit(vllm_hust_root)
    benchmark_carrier_commit = _git_commit(benchmark_carrier_root)

    specs = list(contract.get("variant_launch_specs") or [])
    selected_specs = _filter_variants(specs, args.variant_kind, args.variant_name)
    if not selected_specs:
        raise ValueError("No launcher contract variants matched the requested filters.")

    plan = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "contract_path": str(contract_path),
        "coordination_root": str(coordination_root),
        "carrier_entrypoint": args.carrier_entrypoint,
        "benchmark_carrier_root": str(benchmark_carrier_root),
        "systems": dict(contract.get("systems") or {}),
        "variant_count": len(selected_specs),
        "variants": [
            _build_variant_record(
                spec=spec,
                coordination_root=coordination_root,
                carrier_prefix=carrier_prefix,
                seed_override=args.seed,
                sage_commit=sage_commit,
                vllm_hust_commit=vllm_hust_commit,
                benchmark_carrier_commit=benchmark_carrier_commit,
                benchmark_carrier_root=benchmark_carrier_root,
            )
            for spec in selected_specs
        ],
    }

    if args.execute:
        for record in plan["variants"]:
            _execute_variant(record)
            execution = dict(record.get("execution") or {})
            if args.fail_fast and execution.get("status") == "failed":
                break

    plan_output = Path(args.plan_output).resolve() if args.plan_output else None
    if plan_output is not None:
        _write_json(plan_output, plan)
    else:
        json.dump(plan, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
