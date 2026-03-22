#!/usr/bin/env python3
"""
SAGE Hot-Path Profiler — cProfile + pstats runner
===================================================

Profiles the four candidate hot paths and emits:
  1. Sorted cProfile text tables  (stdout + tool/profiling/reports/*.txt)
  2. pstats-compatible binary dumps (reports/*.prof)  — loadable by snakeviz / gprof2dot

Usage
-----
    # All paths, default workload sizes
    python tools/profiling/cprofile_runner.py

    # Single path with custom sizes
    python tools/profiling/cprofile_runner.py --path scheduler --iterations 100000

    # All paths, heavy mode
    python tools/profiling/cprofile_runner.py --heavy

    # Only write .prof files (no stdout tables)
    python tools/profiling/cprofile_runner.py --quiet

Outputs
-------
    tools/profiling/reports/
        hot_path_summary.txt     — top-20 functions per path, side-by-side
        scheduler.prof
        communication.prof
        dp_unlearning.prof
        foundation_io.prof
        full_summary.json        — machine-readable timing data

Viewing flame graphs from .prof files (requires snakeviz or gprof2dot):
    snakeviz tools/profiling/reports/dp_unlearning.prof
    gprof2dot -f pstats tools/profiling/reports/dp_unlearning.prof | dot -Tsvg -o flamegraph.svg
"""

from __future__ import annotations

import argparse
import cProfile
import io
import json
import pstats
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Make workloads importable when run from any cwd
# ---------------------------------------------------------------------------
_TOOLS_PROFILING = Path(__file__).resolve().parent
sys.path.insert(0, str(_TOOLS_PROFILING))

from workloads.workload_communication import run_communication_workload  # noqa: E402
from workloads.workload_dp_unlearning import run_dp_unlearning_workload  # noqa: E402
from workloads.workload_foundation_io import run_foundation_io_workload  # noqa: E402
from workloads.workload_scheduler import run_scheduler_workload  # noqa: E402

REPORTS_DIR = _TOOLS_PROFILING / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Configuration profiles
# ---------------------------------------------------------------------------

DEFAULT_CONFIG = {
    "scheduler": {"iterations": 50_000},
    "communication": {"iterations": 100_000, "payload_size": 1024},
    "dp_unlearning": {"num_vectors": 5_000, "dim": 128, "iterations": 10},
    "foundation_io": {"batch_size": 256, "iterations": 10_000},
}

HEAVY_CONFIG = {
    "scheduler": {"iterations": 500_000},
    "communication": {"iterations": 1_000_000, "payload_size": 4096},
    "dp_unlearning": {"num_vectors": 20_000, "dim": 256, "iterations": 50},
    "foundation_io": {"batch_size": 512, "iterations": 100_000},
}


# ---------------------------------------------------------------------------
# Profiling helpers
# ---------------------------------------------------------------------------


def profile_fn(fn, kwargs: dict, label: str, top_n: int = 20) -> tuple[dict, str]:
    """
    Run `fn(**kwargs)` under cProfile.

    Returns
    -------
    (timing_dict, pstats_text)
    """
    prof = cProfile.Profile()
    t0 = time.perf_counter()
    prof.enable()
    result = fn(**kwargs)
    prof.disable()
    wall_time = time.perf_counter() - t0

    # Write binary .prof file
    prof_path = REPORTS_DIR / f"{label}.prof"
    prof.dump_stats(str(prof_path))

    # Generate pstats text
    buf = io.StringIO()
    ps = pstats.Stats(prof, stream=buf).sort_stats(pstats.SortKey.CUMULATIVE)
    ps.print_stats(top_n)
    pstats_text = buf.getvalue()

    timing = result if isinstance(result, dict) else {}
    timing["wall_time_s"] = wall_time
    return timing, pstats_text


def _section(title: str, width: int = 72) -> str:
    bar = "=" * width
    return f"\n{bar}\n  {title}\n{bar}\n"


# ---------------------------------------------------------------------------
# Summary table helpers
# ---------------------------------------------------------------------------


_CPP_VERDICT = {
    # threshold: µs/op → "worth C++ porting"
    # These are illustrative; update after actual measurement.
    "scheduler_rr": ("rr_per_decision_us", 0.5),
    "scheduler_pri": ("pri_per_decision_us", 1.0),
    "comm_construct": ("pkt_construct_us", 0.2),
    "comm_ser": ("msgpack_ser_us", 1.0),
    "comm_deser": ("msgpack_deser_us", 1.0),
    "comm_route": ("route_us", 0.1),
    "dp_perturb": ("perturb_ms_per_call", 5.0),
    "dp_comp": ("comp_ms_per_call", 50.0),
    "dp_engine": ("engine_ms_per_call", 100.0),
    "io_batch": ("batch_assembly_us", 2.0),
    "io_json": ("json_roundtrip_us", 10.0),
    "io_queue_enq": ("queue_enq_us", 0.5),
}


def _verdict(value: float, threshold: float) -> str:
    if value >= threshold * 2:
        return "🔴 HIGH  (C++ recommended)"
    if value >= threshold:
        return "🟡 MED   (profile more)"
    return "🟢 LOW   (skip C++)"


def build_verdict_table(all_results: dict[str, dict]) -> str:
    """Produce a human-readable verdict table from all timing results."""
    flat = {}
    for section_results in all_results.values():
        flat.update(section_results)

    lines = [
        "┌─────────────────────────────┬─────────────────┬──────────────────────────────┐",
        "│ Hot Path                    │  Measured (µs)  │ Verdict                      │",
        "├─────────────────────────────┼─────────────────┼──────────────────────────────┤",
    ]
    for key, (metric, threshold) in _CPP_VERDICT.items():
        val = flat.get(metric)
        if val is None:
            continue
        # Convert ms to µs for display if metric is in ms
        disp_val = val * 1000 if "ms" in metric else val
        verdict = _verdict(val, threshold)
        lines.append(f"│ {key:<27} │ {disp_val:>13.2f}µs │ {verdict:<28} │")
    lines.append("└─────────────────────────────┴─────────────────┴──────────────────────────────┘")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

ALL_PATHS = ("scheduler", "communication", "dp_unlearning", "foundation_io")

WORKLOADS = {
    "scheduler": (run_scheduler_workload, "iterations"),
    "communication": (run_communication_workload, None),
    "dp_unlearning": (run_dp_unlearning_workload, None),
    "foundation_io": (run_foundation_io_workload, None),
}


def run(
    paths: list[str],
    config: dict[str, dict],
    top_n: int = 20,
    quiet: bool = False,
) -> dict[str, dict]:
    all_results: dict[str, dict] = {}
    report_lines: list[str] = []

    for path in paths:
        fn, _ = WORKLOADS[path]
        kwargs = config.get(path, {})
        label_map = {
            "dp_unlearning": "dp_unlearning",
        }
        label = label_map.get(path, path)

        print(_section(f"Profiling: {path}"))
        timing, pstats_text = profile_fn(fn, kwargs, label)
        all_results[path] = timing

        section_header = _section(f"cProfile top-{top_n}: {path}")
        report_lines.append(section_header)
        report_lines.append(pstats_text)

        if not quiet:
            print(pstats_text[:3000])  # avoid terminal flood

    verdict = build_verdict_table(all_results)
    report_lines.append(_section("Hot-Path Verdict"))
    report_lines.append(verdict)
    report_lines.append("")

    print(_section("Hot-Path Verdict"))
    print(verdict)

    # Write summary text report
    summary_txt = REPORTS_DIR / "hot_path_summary.txt"
    summary_txt.write_text("\n".join(report_lines), encoding="utf-8")
    print(f"\n[profiler] Text report  → {summary_txt}")

    # Write JSON
    summary_json = REPORTS_DIR / "full_summary.json"
    summary_json.write_text(json.dumps(all_results, indent=2, default=str), encoding="utf-8")
    print(f"[profiler] JSON summary → {summary_json}")
    print(f"[profiler] .prof files  → {REPORTS_DIR}/")

    return all_results


def main() -> None:
    parser = argparse.ArgumentParser(
        description="SAGE hot-path cProfile runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--path",
        choices=list(ALL_PATHS),
        help="Profile only this path (default: all)",
    )
    parser.add_argument(
        "--heavy",
        action="store_true",
        help="Use larger workload sizes",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=None,
        help="Override iterations for all paths",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=20,
        help="Number of functions in pstats output (default: 20)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress pstats stdout, only write files",
    )
    args = parser.parse_args()

    config = HEAVY_CONFIG if args.heavy else DEFAULT_CONFIG

    if args.iterations:
        for key in config:
            config[key]["iterations"] = args.iterations

    paths = [args.path] if args.path else list(ALL_PATHS)

    run(paths, config, top_n=args.top_n, quiet=args.quiet)


if __name__ == "__main__":
    main()
