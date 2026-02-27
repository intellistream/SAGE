"""
Profiling Workload — isage-libs Foundation I/O (sage.libs.foundation.io)
========================================================================

Measures the hot paths in streaming data ingestion:
  1. BatchFunction execution overhead (Python call + data copy)
  2. Streaming queue throughput (enqueue/dequeue tight loop)
  3. Batch assembly — accumulate N items then flush
  4. JSON decode path (common text payload)

Run standalone:
    python workload_foundation_io.py [--batch-size 256] [--iterations 10000]
"""

from __future__ import annotations

import argparse
import io
import json
import queue
import time
from typing import Any

# ---------------------------------------------------------------------------
# Try to import real sage.libs.foundation.io / batch classes
# ---------------------------------------------------------------------------


def _try_import_foundation():
    try:
        from sage.libs.foundation.io.batch import BatchFunction  # noqa: PLC0415

        return BatchFunction
    except Exception:  # noqa: BLE001
        return None


# ---------------------------------------------------------------------------
# Stubs
# ---------------------------------------------------------------------------


class _StubBatchFunction:
    """Mimics sage.libs.foundation.io.batch.BatchFunction behavior."""

    def __init__(self, fn, batch_size: int = 64):
        self._fn = fn
        self._batch_size = batch_size
        self._buffer: list = []

    def add(self, item: Any) -> list | None:
        self._buffer.append(item)
        if len(self._buffer) >= self._batch_size:
            batch = self._buffer
            self._buffer = []
            return self._fn(batch)
        return None

    def flush(self) -> list | None:
        if self._buffer:
            batch = self._buffer
            self._buffer = []
            return self._fn(batch)
        return None


# ---------------------------------------------------------------------------
# Individual benchmarks
# ---------------------------------------------------------------------------


def bench_batch_assembly(BatchFn, batch_size: int, iterations: int) -> tuple[float, int]:  # noqa: N803
    """Return (total_seconds, num_batches_flushed)."""
    batches_flushed = 0

    def _noop(batch: list) -> list:
        return batch

    bf = BatchFn(_noop, batch_size=batch_size)
    t0 = time.perf_counter()
    for i in range(iterations):
        result = bf.add({"id": i, "value": i * 1.5})
        if result is not None:
            batches_flushed += 1
    bf.flush()
    return time.perf_counter() - t0, batches_flushed


def bench_queue_throughput(iterations: int) -> tuple[float, float]:
    """
    Return (enqueue_sec, dequeue_sec) for a stdlib queue.Queue.
    This models the in-process queue that separates source and operator threads.
    """
    q: queue.Queue = queue.Queue(maxsize=0)
    payload = b"x" * 256  # 256-byte payload

    t0 = time.perf_counter()
    for i in range(iterations):
        q.put_nowait(payload)
    enq_total = time.perf_counter() - t0

    t0 = time.perf_counter()
    for _ in range(iterations):
        q.get_nowait()
    deq_total = time.perf_counter() - t0

    return enq_total, deq_total


def bench_json_decode(iterations: int, payload_size: int = 512) -> float:
    """Return total seconds for `iterations` JSON decode+encode cycles."""
    record = {
        "id": 12345,
        "text": "a" * payload_size,
        "tags": ["nlp", "rag", "streaming"],
        "score": 0.9875,
    }
    raw = json.dumps(record).encode()

    t0 = time.perf_counter()
    for _ in range(iterations):
        obj = json.loads(raw)
        _ = json.dumps(obj).encode()
    return time.perf_counter() - t0


def bench_file_io(iterations: int, record_size: int = 512) -> tuple[float, float]:
    """Return (write_sec, read_sec) against an in-memory buffer (BytesIO)."""
    data = b"x" * record_size
    buf = io.BytesIO()

    t0 = time.perf_counter()
    for _ in range(iterations):
        buf.write(data)
    write_total = time.perf_counter() - t0

    buf.seek(0)
    t0 = time.perf_counter()
    for _ in range(iterations):
        chunk = buf.read(record_size)
        if not chunk:
            buf.seek(0)
    read_total = time.perf_counter() - t0

    return write_total, read_total


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------


def run_foundation_io_workload(batch_size: int = 256, iterations: int = 10_000) -> dict[str, float]:
    """
    Run Foundation I/O benchmarks and return timing stats.
    """
    BatchFn = _try_import_foundation() or _StubBatchFunction  # noqa: N806
    if BatchFn is _StubBatchFunction:
        print("[foundation_io] sage.libs not available — running stubs")
    else:
        print("[foundation_io] Using real sage.libs.foundation.io.batch.BatchFunction")

    # 1. Batch assembly
    batch_total, batches_flushed = bench_batch_assembly(BatchFn, batch_size, iterations)

    # 2. Queue throughput
    enq_total, deq_total = bench_queue_throughput(iterations)

    # 3. JSON decode/encode
    json_total = bench_json_decode(iterations)

    # 4. File I/O (BytesIO proxy)
    write_total, read_total = bench_file_io(iterations)

    results = {
        "batch_size": batch_size,
        "iterations": iterations,
        "batch_assembly_total_s": batch_total,
        "batch_assembly_us": batch_total / iterations * 1e6,
        "batches_flushed": batches_flushed,
        "queue_enq_total_s": enq_total,
        "queue_enq_us": enq_total / iterations * 1e6,
        "queue_deq_total_s": deq_total,
        "queue_deq_us": deq_total / iterations * 1e6,
        "json_roundtrip_total_s": json_total,
        "json_roundtrip_us": json_total / iterations * 1e6,
        "file_write_total_s": write_total,
        "file_write_us": write_total / iterations * 1e6,
        "file_read_total_s": read_total,
        "file_read_us": read_total / iterations * 1e6,
    }

    print(
        f"[foundation_io] Batch assembly   : {results['batch_assembly_us']:.2f} µs/item"
        f"  (batch={batch_size}, flushed={batches_flushed})"
    )
    print(f"[foundation_io] Queue enqueue    : {results['queue_enq_us']:.2f} µs/item")
    print(f"[foundation_io] Queue dequeue    : {results['queue_deq_us']:.2f} µs/item")
    print(f"[foundation_io] JSON roundtrip   : {results['json_roundtrip_us']:.2f} µs/record")
    print(f"[foundation_io] BytesIO write    : {results['file_write_us']:.2f} µs/record")
    print(f"[foundation_io] BytesIO read     : {results['file_read_us']:.2f} µs/record")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Foundation I/O profiling workload")
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--iterations", type=int, default=10_000)
    args = parser.parse_args()
    run_foundation_io_workload(args.batch_size, args.iterations)
