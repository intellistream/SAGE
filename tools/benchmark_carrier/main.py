from __future__ import annotations

import argparse
import json
import math
import platform
import socket
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_VARIANT_PROFILES: dict[tuple[str, str], dict[str, float | int]] = {
    ("baseline", "fifo"): {
        "interactive_ttft_ms": 310.0,
        "interactive_e2e_ms": 1620.0,
        "batch_ttft_ms": 1820.0,
        "batch_e2e_ms": 11100.0,
        "running_requests": 22,
        "waiting_requests": 41,
        "kv_cache_usage_perc": 81.0,
        "free_vram_bytes": 18_000_000_000,
        "reserved_vram_bytes": 54_000_000_000,
        "spillover_rate": 0.0,
        "reject_rate": 0.08,
        "delayed_request_rate": 0.17,
    },
    ("baseline", "load-aware"): {
        "interactive_ttft_ms": 245.0,
        "interactive_e2e_ms": 1380.0,
        "batch_ttft_ms": 1710.0,
        "batch_e2e_ms": 10400.0,
        "running_requests": 24,
        "waiting_requests": 29,
        "kv_cache_usage_perc": 76.0,
        "free_vram_bytes": 20_500_000_000,
        "reserved_vram_bytes": 52_500_000_000,
        "spillover_rate": 0.04,
        "reject_rate": 0.06,
        "delayed_request_rate": 0.13,
    },
    ("baseline", "no-spillover"): {
        "interactive_ttft_ms": 285.0,
        "interactive_e2e_ms": 1520.0,
        "batch_ttft_ms": 1790.0,
        "batch_e2e_ms": 10850.0,
        "running_requests": 23,
        "waiting_requests": 37,
        "kv_cache_usage_perc": 80.0,
        "free_vram_bytes": 18_400_000_000,
        "reserved_vram_bytes": 53_600_000_000,
        "spillover_rate": 0.0,
        "reject_rate": 0.07,
        "delayed_request_rate": 0.15,
    },
    ("baseline", "no-memory-aware"): {
        "interactive_ttft_ms": 295.0,
        "interactive_e2e_ms": 1560.0,
        "batch_ttft_ms": 1875.0,
        "batch_e2e_ms": 11500.0,
        "running_requests": 21,
        "waiting_requests": 39,
        "kv_cache_usage_perc": 89.0,
        "free_vram_bytes": 15_300_000_000,
        "reserved_vram_bytes": 57_200_000_000,
        "spillover_rate": 0.03,
        "reject_rate": 0.08,
        "delayed_request_rate": 0.19,
    },
    ("baseline", "full-policy"): {
        "interactive_ttft_ms": 210.0,
        "interactive_e2e_ms": 1190.0,
        "batch_ttft_ms": 1600.0,
        "batch_e2e_ms": 9800.0,
        "running_requests": 26,
        "waiting_requests": 21,
        "kv_cache_usage_perc": 73.0,
        "free_vram_bytes": 22_100_000_000,
        "reserved_vram_bytes": 50_900_000_000,
        "spillover_rate": 0.07,
        "reject_rate": 0.04,
        "delayed_request_rate": 0.09,
    },
    ("ablation", "no-admission-control"): {
        "interactive_ttft_ms": 330.0,
        "interactive_e2e_ms": 1760.0,
        "batch_ttft_ms": 1980.0,
        "batch_e2e_ms": 12300.0,
        "running_requests": 28,
        "waiting_requests": 46,
        "kv_cache_usage_perc": 87.0,
        "free_vram_bytes": 16_100_000_000,
        "reserved_vram_bytes": 56_300_000_000,
        "spillover_rate": 0.08,
        "reject_rate": 0.0,
        "delayed_request_rate": 0.22,
    },
    ("ablation", "no-profiling"): {
        "interactive_ttft_ms": 275.0,
        "interactive_e2e_ms": 1450.0,
        "batch_ttft_ms": 1760.0,
        "batch_e2e_ms": 10720.0,
        "running_requests": 24,
        "waiting_requests": 33,
        "kv_cache_usage_perc": 78.0,
        "free_vram_bytes": 19_200_000_000,
        "reserved_vram_bytes": 53_100_000_000,
        "spillover_rate": 0.05,
        "reject_rate": 0.05,
        "delayed_request_rate": 0.14,
    },
}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Synthetic benchmark carrier for validating the frozen VAMOS launcher contract and artifact schema."
        )
    )
    parser.add_argument("--experiment-manifest", required=True)
    parser.add_argument("--run-plan", required=True)
    parser.add_argument("--workload-replay", required=True)
    parser.add_argument("--variant-kind", required=True, choices=["baseline", "ablation"])
    parser.add_argument("--variant-name", required=True)
    parser.add_argument("--summary-output", required=True)
    parser.add_argument("--trace-output", required=True)
    parser.add_argument("--raw-log-output", required=True)
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument(
        "--output-root",
        help=(
            "Optional sandbox root for emitted artifacts. When set, output paths are rewritten under this root "
            "using the path suffix that begins at results/."
        ),
    )
    return parser.parse_args()


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return payload


def _read_replay(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        payload = json.loads(line)
        if not isinstance(payload, dict):
            raise ValueError(f"Replay line {line_number} must be a JSON object.")
        rows.append(payload)
    return rows


def _quantile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = max(0, min(len(ordered) - 1, math.ceil(len(ordered) * percentile / 100.0) - 1))
    return round(ordered[rank], 6)


def _git_commit(repo_root: Path) -> str | None:
    if not repo_root.exists():
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


def _resolve_output_path(path_str: str, output_root: Path | None) -> Path:
    path = Path(path_str)
    if output_root is None:
        return path
    if path.is_absolute():
        parts = list(path.parts)
        if "results" in parts:
            suffix = Path(*parts[parts.index("results") :])
            return output_root / suffix
        return output_root / path.name
    return output_root / path


def _load_run_plan(path: Path) -> dict[str, Any]:
    payload = _load_json(path)
    variants = payload.get("variants")
    metrics = payload.get("metrics")
    if not isinstance(variants, list) or not isinstance(metrics, dict):
        raise ValueError(f"Run plan missing variants/metrics in {path}")
    return payload


def _find_variant(run_plan: dict[str, Any], kind: str, name: str) -> dict[str, Any]:
    for item in run_plan.get("variants") or []:
        if not isinstance(item, dict):
            continue
        if str(item.get("kind") or "") == kind and str(item.get("name") or "") == name:
            return item
    raise ValueError(f"Variant {kind}:{name} not present in run plan")


def _metric_names(run_plan: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for values in (run_plan.get("metrics") or {}).values():
        if isinstance(values, list):
            names.extend(str(item) for item in values)
    return names


def _decision_for_event(
    index: int,
    request_id: str,
    phase: str,
    profile: dict[str, float | int],
) -> tuple[str, bool]:
    score = ((index * 17) + len(request_id)) % 1000 / 1000.0
    reject_rate = float(profile["reject_rate"])
    delayed_rate = float(profile["delayed_request_rate"])
    spillover_rate = float(profile["spillover_rate"])
    if score < reject_rate:
        return "rejected", False
    if phase == "overload-burst" and score < reject_rate + spillover_rate:
        return "spillover", True
    if score < reject_rate + delayed_rate:
        return "delayed", False
    return "admitted", False


def _latencies_for_event(
    deadline_class: str,
    phase: str,
    index: int,
    profile: dict[str, float | int],
) -> tuple[float, float]:
    if deadline_class == "interactive-high":
        ttft = float(profile["interactive_ttft_ms"])
        e2e = float(profile["interactive_e2e_ms"])
    else:
        ttft = float(profile["batch_ttft_ms"])
        e2e = float(profile["batch_e2e_ms"])
    if phase == "overload-burst":
        ttft *= 1.22
        e2e *= 1.18
    elif phase == "recovery":
        ttft *= 0.94
        e2e *= 0.96
    jitter = ((index % 7) - 3) * 0.015
    return round(ttft * (1.0 + jitter), 6), round(e2e * (1.0 + jitter / 2.0), 6)


def _build_metrics(
    run_plan: dict[str, Any],
    rows: list[dict[str, Any]],
    total_duration_s: float,
    profile: dict[str, float | int],
) -> dict[str, Any]:
    admitted = [row for row in rows if row["decision"] != "rejected"]
    ttft_values = [float(row["ttft_ms"]) for row in admitted]
    e2e_values = [float(row["e2e_ms"]) for row in admitted]
    requests_total = len(rows)
    reject_count = sum(1 for row in rows if row["decision"] == "rejected")
    delayed_count = sum(1 for row in rows if row["decision"] == "delayed")
    spillover_count = sum(1 for row in rows if row["used_spillover"])
    violation_count = sum(1 for row in rows if row["slo_violated"])
    throughput_rps = 0.0 if total_duration_s <= 0 else len(admitted) / total_duration_s

    metrics = {
        "ttft_p50_ms": _quantile(ttft_values, 50.0),
        "ttft_p95_ms": _quantile(ttft_values, 95.0),
        "e2e_p95_ms": _quantile(e2e_values, 95.0),
        "throughput_rps": round(throughput_rps, 6),
        "running_requests": int(profile["running_requests"]),
        "waiting_requests": int(profile["waiting_requests"]),
        "kv_cache_usage_perc": float(profile["kv_cache_usage_perc"]),
        "free_vram_bytes": int(profile["free_vram_bytes"]),
        "reserved_vram_bytes": int(profile["reserved_vram_bytes"]),
        "slo_violation_rate": round(violation_count / requests_total if requests_total else 0.0, 6),
        "spillover_rate": round(spillover_count / requests_total if requests_total else 0.0, 6),
        "reject_rate": round(reject_count / requests_total if requests_total else 0.0, 6),
        "delayed_request_rate": round(delayed_count / requests_total if requests_total else 0.0, 6),
    }

    for metric_name in _metric_names(run_plan):
        metrics.setdefault(metric_name, None)
    return metrics


def main() -> int:
    args = _parse_args()
    run_plan_path = Path(args.run_plan).resolve()
    replay_path = Path(args.workload_replay).resolve()
    experiment_manifest = Path(args.experiment_manifest).resolve()
    output_root = Path(args.output_root).resolve() if args.output_root else None

    run_plan = _load_run_plan(run_plan_path)
    _find_variant(run_plan, args.variant_kind, args.variant_name)
    replay = _read_replay(replay_path)
    profile = _VARIANT_PROFILES.get((args.variant_kind, args.variant_name))
    if profile is None:
        raise ValueError(
            f"No synthetic carrier profile defined for {args.variant_kind}:{args.variant_name}"
        )

    summary_output = _resolve_output_path(args.summary_output, output_root)
    trace_output = _resolve_output_path(args.trace_output, output_root)
    raw_log_output = _resolve_output_path(args.raw_log_output, output_root)
    summary_output.parent.mkdir(parents=True, exist_ok=True)
    trace_output.parent.mkdir(parents=True, exist_ok=True)
    raw_log_output.parent.mkdir(parents=True, exist_ok=True)

    total_duration_s = 0.0
    if replay:
        total_duration_s = max(
            float((item.get("metadata") or {}).get("scheduled_at_s") or 0.0) for item in replay
        )
        total_duration_s = max(total_duration_s, 1.0)

    run_started_at = datetime.now(timezone.utc).isoformat()
    trace_rows: list[dict[str, Any]] = []
    raw_rows: list[dict[str, Any]] = []
    for index, event in enumerate(replay):
        metadata = dict(event.get("metadata") or {})
        serving_context = dict(event.get("serving_context") or {})
        trace_tags = dict(serving_context.get("trace_tags") or {})
        phase = str(metadata.get("phase") or trace_tags.get("phase") or "unknown")
        deadline_class = str(serving_context.get("deadline_class") or "unknown")
        request_id = str(event.get("request_id") or f"request-{index:05d}")
        decision, used_spillover = _decision_for_event(index, request_id, phase, profile)
        ttft_ms, e2e_ms = _latencies_for_event(deadline_class, phase, index, profile)
        if decision == "delayed":
            ttft_ms = round(ttft_ms * 1.18, 6)
            e2e_ms = round(e2e_ms * 1.12, 6)
        target_ttft_ms = serving_context.get("target_ttft_ms")
        target_e2e_ms = serving_context.get("target_e2e_ms")
        slo_violated = False
        if target_ttft_ms is not None and ttft_ms > float(target_ttft_ms):
            slo_violated = True
        if target_e2e_ms is not None and e2e_ms > float(target_e2e_ms):
            slo_violated = True
        row = {
            "request_id": request_id,
            "scheduled_at_s": float(metadata.get("scheduled_at_s") or 0.0),
            "phase": phase,
            "deadline_class": deadline_class,
            "variant_kind": args.variant_kind,
            "variant_name": args.variant_name,
            "decision": decision,
            "used_spillover": used_spillover,
            "ttft_ms": ttft_ms,
            "e2e_ms": e2e_ms,
            "slo_violated": slo_violated,
        }
        raw_rows.append(row)
        trace_rows.append(
            {
                "request_id": request_id,
                "variant_kind": args.variant_kind,
                "variant_name": args.variant_name,
                "phase": phase,
                "deadline_class": deadline_class,
                "decision_trace": {
                    "decision": decision,
                    "used_spillover": used_spillover,
                    "priority": serving_context.get("priority"),
                    "model_id": serving_context.get("model_id"),
                    "target_ttft_ms": target_ttft_ms,
                    "target_e2e_ms": target_e2e_ms,
                },
            }
        )

    metrics = _build_metrics(run_plan, raw_rows, total_duration_s, profile)
    run_finished_at = datetime.now(timezone.utc).isoformat()
    summary = {
        "kind": args.variant_kind,
        "name": args.variant_name,
        "variant": args.variant_name,
        "experiment": str(
            run_plan.get("experiment", {}).get("name") or "burst-overload-baseline-matrix"
        ),
        "generated_at": run_finished_at,
        "carrier_mode": "synthetic-contract-validation",
        "artifacts": {
            "summary": str(summary_output),
            "trace": str(trace_output),
            "raw_log": str(raw_log_output),
        },
        "inputs": {
            "experiment_manifest": str(experiment_manifest),
            "run_plan": str(run_plan_path),
            "workload_replay": str(replay_path),
            "seed": args.seed,
        },
        "systems": dict(run_plan.get("systems") or {}),
        "execution_metadata": {
            "sage_commit": _git_commit(Path(__file__).resolve().parents[2]),
            "benchmark_carrier_commit": _git_commit(Path(__file__).resolve().parents[2]),
            "hardware_metadata": _hardware_metadata(),
            "run_started_at": run_started_at,
            "run_finished_at": run_finished_at,
            "full_command_line": " ".join(__import__("sys").argv),
        },
        "metrics": metrics,
        "notes": [
            "Synthetic benchmark carrier output for validating the frozen launcher contract and artifact schema.",
            "These outputs are not execution-plane evidence and should not replace real archived runs in VAMOS.",
        ],
    }

    raw_log_output.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in raw_rows) + ("\n" if raw_rows else ""),
        encoding="utf-8",
    )
    trace_output.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in trace_rows)
        + ("\n" if trace_rows else ""),
        encoding="utf-8",
    )
    summary_output.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {"summary_output": str(summary_output), "variant": args.variant_name}, sort_keys=True
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
