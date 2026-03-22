# SAGE Hot-Path Profiling Infrastructure

> Issue: [#1467](https://github.com/intellistream/SAGE/issues/1467)\
> Feeds: [#1468](https://github.com/intellistream/SAGE/issues/1468) ·
> [#1469](https://github.com/intellistream/SAGE/issues/1469)

## Overview

This directory contains the profiling workloads and tooling to:

1. Identify the **actual** hot paths before any C++ porting work
1. Collect cProfile `.prof` files for deep-dive analysis
1. (Optionally) generate py-spy / perf flame graph SVGs
1. Generate a Markdown report suitable for `docs/profiling/`

## Hot-Path Candidates

| Surface                        | Path                          | Suspected Cost Driver                                      |
| ------------------------------ | ----------------------------- | ---------------------------------------------------------- |
| `sage.runtime`                 | `scheduler/`                  | Task dispatch loop — `make_decision()` called per-operator |
| `sage.stream` / `sage.runtime` | `runtime/communication/`      | `Packet` construction + routing / serialization overhead   |
| `isage-privacy`                | `sage_privacy/dp_unlearning/` | NumPy noise generation over large vector batches           |
| Historical ingestion path      | `foundation/io/`              | Batch assembly + JSON decode in streaming ingestion        |

## Quick Start

```bash
# From SAGE repo root
cd /path/to/SAGE

# 1. Run all profilers (default workload sizes, ~60s)
python tools/profiling/cprofile_runner.py

# 2. Heavier workloads for more accurate numbers
python tools/profiling/cprofile_runner.py --heavy

# 3. Single path
python tools/profiling/cprofile_runner.py --path dp_unlearning

# 4. Generate Markdown report from JSON results
python tools/profiling/report_generator.py

# 5. Full flame-graph pipeline (installs py-spy if missing)
bash tools/profiling/flame_graph.sh --install
```

## Directory Layout

```text
tools/profiling/
├── README.md                    # This file
├── cprofile_runner.py           # Main cProfile orchestrator
├── report_generator.py          # JSON → Markdown report
├── flame_graph.sh               # py-spy + perf SVG collector
├── workloads/
│   ├── workload_scheduler.py         # scheduler bench (historical kernel vs in-tree runtime)
│   ├── workload_communication.py     # packet / communication bench
│   ├── workload_dp_unlearning.py     # isage-privacy DP unlearning bench
│   └── workload_foundation_io.py     # historical foundation/io bench
└── reports/                     # ← generated, not committed (gitignored)
    ├── hot_path_summary.txt
    ├── hot_path_report.md        # Copy to docs/profiling/ when ready
    ├── full_summary.json
    ├── scheduler.prof
    ├── communication.prof
    ├── dp_unlearning.prof
    ├── foundation_io.prof
    └── flamegraph/
        ├── scheduler.svg
        ├── dp_unlearning.svg
        └── ...
```

## Interpreting Results

### cProfile Tables

The `cprofile_runner.py` outputs `pstats` tables sorted by cumulative time. Focus on:

- Lines where `tottime` (exclusive CPU time) is large → these are the leaves consuming real time
- Functions called millions of times with `percall` > 1µs → candidates for C++ inlining

### Verdict Table

After all paths run, a verdict table is printed:

```text
🔴 HIGH  → C++ port directly benefits (>2× threshold)
🟡 MED   → profile deeper with larger data or real traffic
🟢 LOW   → Python overhead is acceptable, not worth porting
```

### Viewing .prof Files

```bash
# Interactive browser (requires snakeviz)
pip install snakeviz
snakeviz tools/profiling/reports/dp_unlearning.prof

# DOT / SVG call graph
pip install gprof2dot
gprof2dot -f pstats tools/profiling/reports/dp_unlearning.prof \
  | dot -Tsvg -o dp_unlearning_callgraph.svg
```

### Viewing py-spy Flame Graphs

Open the `.svg` output in a browser:

```bash
xdg-open tools/profiling/reports/flamegraph/dp_unlearning_flamegraph.svg
```

The `.svg` interactive flame graph can be panned/zoomed with the mouse. For Speedscope format
(`.svg` labeled speedscope):

```bash
npx speedscope tools/profiling/reports/flamegraph/dp_unlearning.svg
```

## Thresholds & Priorities

Thresholds are defined in `report_generator.py` `_THRESHOLDS`. Adjust after the first real-traffic
measurement:

| Metric                | Default threshold | Rationale                           |
| --------------------- | ----------------: | ----------------------------------- |
| `pkt_construct_us`    |            0.2 µs | 5 M pkt/s target → 200 ns budget    |
| `msgpack_ser_us`      |            1.0 µs | Network latency dominated otherwise |
| `rr_per_decision_us`  |            0.5 µs | 2 M tasks/s throughput              |
| `perturb_ms_per_call` |              5 ms | Unlearning batch of 5 k vectors     |
| `comp_ms_per_call`    |             50 ms | Neighbor update budget              |

## Committing Results

```bash
# After run, copy to docs/
mkdir -p docs/profiling
cp tools/profiling/reports/hot_path_report.md docs/profiling/
git add docs/profiling/hot_path_report.md
git commit -m "docs: add hot-path profiling report (closes #1467)"
```

The `.prof` / `.svg` files are large binaries — optionally upload to the GitHub issue as attachments
rather than committing.

## Updating P6 Priority

After running, update issues #1468 / #1469 based on the 🔴 findings:

- Paths consistently 🔴 HIGH → immediate C++ scope
- Paths 🟡 MED → deferred, measure again with synthetic Flownet traffic
- Paths 🟢 LOW → removed from C++ scope
