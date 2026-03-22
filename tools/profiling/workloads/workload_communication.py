"""
Profiling Workload — SAGE Runtime Packet / Communication Path
==============================================================

Measures the cost of:
  1. Packet construction (Python object creation + timestamp)
  2. msgpack serialization/deserialization (Python-layer overhead)
  3. Router message dispatch (packet routing decision)

These are the hot paths in inter-operator communication at high throughput.

Run standalone:
    python workload_communication.py [--iterations 100000] [--payload-size 1024]
"""

from __future__ import annotations

import argparse
import math
import struct
import time
from typing import Any

# ---------------------------------------------------------------------------
# Try to import real Packet; fall back to a stub
# ---------------------------------------------------------------------------


def _try_import_packet():
    try:
        from sage.stream._runtime_kernel_types import Packet  # noqa: PLC0415

        return Packet
    except Exception:  # noqa: BLE001
        return None


class _StubPacket:
    """Stub matching the real Packet interface."""

    __slots__ = (
        "payload",
        "input_index",
        "partition_key",
        "partition_strategy",
        "timestamp",
    )

    def __init__(
        self,
        payload: Any,
        input_index: int = 0,
        partition_key: Any = None,
        partition_strategy: str | None = None,
    ):
        self.payload = payload
        self.input_index = input_index
        self.partition_key = partition_key
        self.partition_strategy = partition_strategy
        self.timestamp = time.time_ns()

    def is_keyed(self) -> bool:
        return self.partition_key is not None

    def inherit_partition_info(self, new_payload: Any) -> _StubPacket:
        return _StubPacket(
            payload=new_payload,
            input_index=self.input_index,
            partition_key=self.partition_key,
            partition_strategy=self.partition_strategy,
        )


# ---------------------------------------------------------------------------
# msgpack helpers
# ---------------------------------------------------------------------------


def _get_msgpack():
    try:
        import msgpack  # noqa: PLC0415

        return msgpack
    except ImportError:
        return None


def _manual_serialize(data: dict) -> bytes:
    """Fallback: struct-based binary packing (no msgpack dependency)."""
    payload_bytes = str(data.get("payload", "")).encode()
    return struct.pack(
        f"!BIi{len(payload_bytes)}s",
        data.get("input_index", 0),
        len(data.get("partition_key") or b""),
        data.get("timestamp", 0) & 0x7FFFFFFF,
        payload_bytes,
    )


# ---------------------------------------------------------------------------
# Individual benchmarks
# ---------------------------------------------------------------------------


def bench_packet_construction(
    Packet,  # noqa: N803
    iterations: int,
    payload: Any,
) -> float:
    """Return total seconds for `iterations` Packet constructions."""
    t0 = time.perf_counter()
    for i in range(iterations):
        Packet(
            payload=payload,
            input_index=i % 8,
            partition_key=i % 64,
        )
    return time.perf_counter() - t0


def bench_msgpack_roundtrip(msgpack, iterations: int, payload_size: int) -> tuple[float, float]:
    """Return (ser_seconds, deser_seconds) for `iterations` msgpack roundtrips."""
    data = {
        "payload": b"x" * payload_size,
        "input_index": 0,
        "partition_key": 42,
        "timestamp": time.time_ns(),
    }
    packer = msgpack.Packer(use_bin_type=True)

    # Serialization
    t0 = time.perf_counter()
    serialized = None
    for _ in range(iterations):
        serialized = packer.pack(data)
    ser_total = time.perf_counter() - t0

    # Deserialization
    t0 = time.perf_counter()
    for _ in range(iterations):
        msgpack.unpackb(serialized, raw=False)
    deser_total = time.perf_counter() - t0

    return ser_total, deser_total


def bench_key_routing(Packet, iterations: int) -> float:  # noqa: N803
    """Simulate partition key hashing / routing decision."""
    packets = [
        Packet(payload=i, input_index=i % 4, partition_key=f"user:{i % 1000}")
        for i in range(min(1000, iterations))
    ]
    num_partitions = 16
    t0 = time.perf_counter()
    for i in range(iterations):
        pkt = packets[i % len(packets)]
        # Simulate hash-routing decision (as router.py would do)
        if pkt.is_keyed():
            _ = hash(pkt.partition_key) % num_partitions
    return time.perf_counter() - t0


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------


def run_communication_workload(
    iterations: int = 100_000, payload_size: int = 1024
) -> dict[str, float]:
    """
    Run all communication benchmarks and return timing stats.

    Returns
    -------
    dict with timing keys (seconds and µs/op)
    """
    Packet = _try_import_packet() or _StubPacket  # noqa: N806
    if Packet is _StubPacket:
        print("[comm] in-tree Packet not available — running with stub Packet")
    else:
        print("[comm] Using real sage.stream._runtime_kernel_types.Packet")

    msgpack = _get_msgpack()

    payload = b"x" * payload_size

    # 1. Packet construction
    pkt_total = bench_packet_construction(Packet, iterations, payload)

    # 2. msgpack roundtrip
    if msgpack:
        ser_total, deser_total = bench_msgpack_roundtrip(msgpack, iterations, payload_size)
    else:
        print("[comm] msgpack not installed — skipping serialization bench")
        ser_total = deser_total = math.nan

    # 3. Key routing
    route_total = bench_key_routing(Packet, iterations)

    results = {
        "iterations": iterations,
        "payload_size_bytes": payload_size,
        "pkt_construct_total_s": pkt_total,
        "pkt_construct_us": pkt_total / iterations * 1e6,
        "msgpack_ser_total_s": ser_total,
        "msgpack_ser_us": (ser_total / iterations * 1e6) if not math.isnan(ser_total) else math.nan,
        "msgpack_deser_total_s": deser_total,
        "msgpack_deser_us": (deser_total / iterations * 1e6)
        if not math.isnan(deser_total)
        else math.nan,
        "route_total_s": route_total,
        "route_us": route_total / iterations * 1e6,
    }

    def _fmt(val: float, unit: str = "µs") -> str:
        return f"{val:.3f} {unit}" if not math.isnan(val) else "N/A"

    print(
        f"[comm] Packet construction : {_fmt(results['pkt_construct_us'])} /pkt"
        f"  (total={pkt_total:.3f}s)"
    )
    print(
        f"[comm] msgpack serialize   : {_fmt(results['msgpack_ser_us'])} /msg"
        f"  (payload={payload_size}B)"
    )
    print(f"[comm] msgpack deserialize : {_fmt(results['msgpack_deser_us'])} /msg")
    print(f"[comm] Key routing         : {_fmt(results['route_us'])} /pkt")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Communication profiling workload")
    parser.add_argument("--iterations", type=int, default=100_000)
    parser.add_argument("--payload-size", type=int, default=1024)
    args = parser.parse_args()
    run_communication_workload(args.iterations, args.payload_size)
