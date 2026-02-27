#!/usr/bin/env python3
"""
SAGE Profiling Report Generator
================================

Converts the cProfile runner JSON output into a Markdown report suitable
for committing into docs-public/profiling/ or the GitHub wiki.

Usage
-----
    python tools/profiling/report_generator.py
    python tools/profiling/report_generator.py --json path/to/full_summary.json
    python tools/profiling/report_generator.py --output docs-public/profiling/hot_path_report.md

The report includes:
  - Executive summary table (hot path vs. cost vs. verdict)
  - Per-path detailed analysis
  - Recommendations for which paths to prioritize for C++ porting (#1468/#1469)
"""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime
from pathlib import Path

_REPORTS_DIR = Path(__file__).resolve().parent / "reports"
_DEFAULT_JSON = _REPORTS_DIR / "full_summary.json"
_DEFAULT_MD = _REPORTS_DIR / "hot_path_report.md"


# ---------------------------------------------------------------------------
# Decision thresholds (µs/op).  Values derived from SAGE perf targets.
# ---------------------------------------------------------------------------

_THRESHOLDS: dict[str, tuple[str, float, str]] = {
    # (metric_key, threshold_µs, description)
    "Scheduler — RoundRobin decision": ("rr_per_decision_us", 0.5, "isage-kernel/scheduler"),
    "Scheduler — Priority decision": ("pri_per_decision_us", 1.0, "isage-kernel/scheduler"),
    "Comm — Packet construction": ("pkt_construct_us", 0.2, "isage-kernel/communication"),
    "Comm — msgpack serialize": ("msgpack_ser_us", 1.0, "isage-kernel/communication"),
    "Comm — msgpack deserialize": ("msgpack_deser_us", 1.0, "isage-kernel/communication"),
    "Comm — Key routing": ("route_us", 0.1, "isage-kernel/communication"),
    "DP — Vector perturbation": ("perturb_ms_per_call", 5_000.0, "isage-libs/privacy"),
    "DP — Neighbor compensation": ("comp_ms_per_call", 50_000.0, "isage-libs/privacy"),
    "DP — Full engine call": ("engine_ms_per_call", 100_000.0, "isage-libs/privacy"),
    "IO — Batch assembly": ("batch_assembly_us", 2.0, "isage-libs/foundation/io"),
    "IO — JSON roundtrip": ("json_roundtrip_us", 10.0, "isage-libs/foundation/io"),
    "IO — Queue enqueue": ("queue_enq_us", 0.5, "isage-libs/foundation/io"),
}


def _verdict(val_us: float, threshold_us: float) -> str:
    if val_us >= threshold_us * 2:
        return "🔴 **HIGH** — C++ port recommended"
    if val_us >= threshold_us:
        return "🟡 **MED** — profile deeper"
    return "🟢 LOW — skip for now"


def _fmt_us(val: float | None) -> str:
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return "—"
    if val >= 1_000_000:
        return f"{val / 1_000_000:.1f}s"
    if val >= 1_000:
        return f"{val / 1_000:.2f}ms"
    return f"{val:.2f}µs"


def build_report(data: dict, run_date: str | None = None) -> str:
    run_date = run_date or datetime.now().strftime("%Y-%m-%d %H:%M")

    # Flatten all timing values
    flat: dict[str, float] = {}
    for section in data.values():
        if isinstance(section, dict):
            flat.update(section)

    # Convert ms-named metrics to µs for comparison
    def _to_us(metric: str, val: float) -> float:
        # Only convert ms→µs when the metric name explicitly ends with _ms or contains _ms_
        # Avoid false positive on "msgpack" which contains "ms" as a substring.
        if metric.endswith("_ms") or "_ms_" in metric or metric.endswith("_ms_per_call"):
            return val * 1000
        return val

    lines: list[str] = []

    lines += [
        "# SAGE Hot-Path Profiling Report",
        "",
        f"> Generated: {run_date}  ",
        "> Issue: [#1467](https://github.com/intellistream/SAGE/issues/1467)  ",
        "> Feeds into: [#1468](https://github.com/intellistream/SAGE/issues/1468) (isage-kernel C++) · "
        "[#1469](https://github.com/intellistream/SAGE/issues/1469) (isage-libs C++)",
        "",
        "---",
        "",
        "## Executive Summary",
        "",
        "| Hot Path | Package | Measured | Threshold | Verdict |",
        "|----------|---------|----------|-----------|---------|",
    ]

    high_paths: list[str] = []
    med_paths: list[str] = []
    low_paths: list[str] = []

    for label, (metric, threshold_us, pkg) in _THRESHOLDS.items():
        raw_val = flat.get(metric)
        if raw_val is None:
            disp = "—"
            verdict = "❓ no data"
        else:
            val_us = _to_us(metric, raw_val)
            disp = _fmt_us(val_us)
            verdict = _verdict(val_us, threshold_us)
            if "HIGH" in verdict:
                high_paths.append(f"- **{label}** ({pkg}) — {disp}")
            elif "MED" in verdict:
                med_paths.append(f"- {label} ({pkg}) — {disp}")
            else:
                low_paths.append(f"- {label} ({pkg}) — {disp}")

        lines.append(f"| {label} | `{pkg}` | {disp} | {_fmt_us(threshold_us)} | {verdict} |")

    lines += [
        "",
        "---",
        "",
        "## Recommendations",
        "",
        "### 🔴 Worth C++-porting (HIGH priority)",
    ]
    lines += high_paths or ["- *(none exceeded threshold)*"]
    lines += [
        "",
        "### 🟡 Profile deeper before deciding (MED priority)",
    ]
    lines += med_paths or ["- *(none in medium range)*"]
    lines += [
        "",
        "### 🟢 Not worth porting yet (LOW / skip)",
    ]
    lines += low_paths or ["- *(all paths below threshold)*"]

    # Per-section detail
    lines += [
        "",
        "---",
        "",
        "## Per-Path Detail",
        "",
    ]

    section_labels = {
        "scheduler": "### Scheduler / Task Dispatch (`isage-kernel`)",
        "communication": "### Communication / Packet Serialization (`isage-kernel`)",
        "dp_unlearning": "### DP Unlearning (`isage-libs/privacy`)",
        "foundation_io": "### Foundation I/O (`isage-libs/foundation/io`)",
    }

    for section, header in section_labels.items():
        section_data = data.get(section)
        if not section_data:
            continue
        lines.append(header)
        lines.append("")
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        for k, v in section_data.items():
            if k.startswith("_") or k in ("iterations",):
                continue
            if isinstance(v, float) and math.isnan(v):
                lines.append(f"| `{k}` | — |")
            elif isinstance(v, float):
                lines.append(f"| `{k}` | {v:.4f} |")
            else:
                lines.append(f"| `{k}` | {v} |")
        lines.append("")

    lines += [
        "---",
        "",
        "## How to Re-run",
        "",
        "```bash",
        "# From SAGE repo root",
        "python tools/profiling/cprofile_runner.py",
        "",
        "# Heavy mode (larger workloads)",
        "python tools/profiling/cprofile_runner.py --heavy",
        "",
        "# Single path",
        "python tools/profiling/cprofile_runner.py --path dp_unlearning",
        "",
        "# Flame graph via py-spy (requires: pip install py-spy)",
        "bash tools/profiling/flame_graph.sh dp_unlearning",
        "```",
        "",
        "## Notes",
        "",
        "- Measurements are wall-clock (perf_counter), not CPU-only.",
        "- DP Unlearning benchmarks include NumPy allocation; "
        "C++ target should reuse pre-allocated buffers.",
        "- Communication benchmarks include stub Packet (no real network); "
        "validate with actual Flownet traffic.",
        "- See `.prof` files in `tools/profiling/reports/` for deep dives "
        "with `snakeviz` or `gprof2dot`.",
        "",
    ]

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate profiling Markdown report")
    parser.add_argument(
        "--json",
        default=str(_DEFAULT_JSON),
        help=f"Path to full_summary.json (default: {_DEFAULT_JSON})",
    )
    parser.add_argument(
        "--output",
        default=str(_DEFAULT_MD),
        help=f"Output Markdown path (default: {_DEFAULT_MD})",
    )
    args = parser.parse_args()

    json_path = Path(args.json)
    if not json_path.exists():
        print(
            f"[report] {json_path} not found — run cprofile_runner.py first.\n"
            f"  python tools/profiling/cprofile_runner.py"
        )
        raise SystemExit(1)

    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    report = build_report(data)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report, encoding="utf-8")
    print(f"[report] Markdown report → {out_path}")
    print("[report] Copy to docs-public/profiling/ or GitHub wiki when ready.")


if __name__ == "__main__":
    main()
