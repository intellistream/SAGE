"""Local tracing microbenchmark; not an inference throughput or hardware claim.

PYTHONPATH=src python tools/benchmark_carrier/benchmark_inference_trace.py --output report.json
Each timing sample uses a fresh process. Allocation probes run separately because
tracemalloc changes timing; RSS includes interpreter, imports and exporter worker.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import platform
import resource
import statistics
import subprocess
import sys
import tempfile
import time
import tracemalloc
from pathlib import Path

from sage.tracing import NDJSONExporter, Tracer, get_tracer, use_tracer


class DiscardExporter:
    def export(self, record):
        pass


def worker(mode, count, allocations):
    with tempfile.TemporaryDirectory(prefix="sage-trace-benchmark-") as directory:
        if allocations:
            tracemalloc.start()
        tracer = (
            None
            if mode == "off"
            else Tracer(NDJSONExporter(directory) if mode == "ndjson" else DiscardExporter())
        )
        with use_tracer(tracer) if tracer else contextlib.nullcontext():
            with get_tracer().span("benchmark.root"):
                for _ in range(1000):
                    with get_tracer().span("benchmark.warmup"):
                        pass
                if tracer:
                    assert tracer.flush(30)
                before = tracer.stats() if tracer else {}
                rss_before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
                start = time.perf_counter_ns()
                for _ in range(count):
                    with get_tracer().span("benchmark.step"):
                        pass
                enqueued = time.perf_counter_ns()
                if tracer:
                    assert tracer.flush(30)
                drained = time.perf_counter_ns()
                after = tracer.stats() if tracer else {}
        if tracer:
            assert tracer.close(30)
        memory = tracemalloc.get_traced_memory()[1] if allocations else None
        if allocations:
            tracemalloc.stop()
        rss_peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return {
            "mode": mode,
            "spans": count,
            "allocation_probe": allocations,
            "enqueue_wall_ns": enqueued - start,
            "drained_wall_ns": drained - start,
            "rss_before_kib": rss_before,
            "rss_peak_kib": rss_peak,
            "rss_high_water_delta_kib": rss_peak - rss_before,
            "tracemalloc_peak_bytes": memory,
            "counts": {key: after[key] - before[key] for key in after if key != "queue_depth"},
            "spool_bytes": sum(p.stat().st_size for p in Path(directory).glob("*.ndjson")),
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--count", type=int, default=10000)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--worker", choices=["off", "memory", "ndjson"])
    parser.add_argument("--allocations", action="store_true")
    args = parser.parse_args()
    if args.worker:
        print(json.dumps(worker(args.worker, args.count, args.allocations)))
        return
    if args.count < 10000 or args.repeats < 3 or not args.output:
        parser.error("provide --output; count >= 10000 and repeats >= 3 required")
    samples = []
    for repetition in range(args.repeats + 1):
        for mode in ["off", "memory", "ndjson"]:
            command = [sys.executable, __file__, "--worker", mode, "--count", str(args.count)]
            if repetition == args.repeats:
                command.append("--allocations")
            samples.append(json.loads(subprocess.check_output(command, text=True)))
    summary = {}
    for mode in ["off", "memory", "ndjson"]:
        runs = [s for s in samples if s["mode"] == mode and not s["allocation_probe"]]
        summary[mode] = {
            "repeats": len(runs),
            "spans_per_repeat": args.count,
            **{
                key + "_median": statistics.median(s[key] for s in runs)
                for key in [
                    "enqueue_wall_ns",
                    "drained_wall_ns",
                    "rss_peak_kib",
                    "rss_high_water_delta_kib",
                ]
            },
            "dropped_events_each_repeat": [s["counts"].get("dropped_events", 0) for s in runs],
        }
    report = {
        "environment": {
            "python": sys.version,
            "executable": sys.executable,
            "platform": platform.platform(),
            "cpu_count": os.cpu_count(),
        },
        "method": "fresh process per sample; 1000 warmup; 10000 child spans; 1024-event queue; allocation probes separate; no affinity pinning; RSS high-water KiB",
        "summary": summary,
        "samples": samples,
    }
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
