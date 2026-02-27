"""
Profiling Workload — isage-kernel Scheduler / Task Dispatch
============================================================

Simulates heavy task-dispatch traffic to measure scheduler hot path:
  - make_decision() loop (N decisioned tasks)
  - PlacementDecision construction overhead
  - SchedulerPolicy lookup / strategy selection cost

Run standalone:
    python workload_scheduler.py [--iterations 50000]
"""

from __future__ import annotations

import argparse
import time
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Lightweight stubs that mirror the real sage.kernel API so this workload
# can be executed even when isage-kernel is not installed.  When the real
# package is available the real classes are used instead.
# ---------------------------------------------------------------------------


def _try_import_real():
    """Return (Scheduler, PlacementDecision, TaskNode stubs or real impls)."""
    try:
        from sage.kernel.scheduler.api import Scheduler  # noqa: PLC0415
        from sage.kernel.scheduler.decision import PlacementDecision  # noqa: PLC0415
        from sage.kernel.scheduler.impl.priority_scheduler import (  # noqa: PLC0415
            PriorityScheduler,
        )
        from sage.kernel.scheduler.impl.round_robin_scheduler import (  # noqa: PLC0415
            RoundRoundScheduler,
        )

        return Scheduler, PlacementDecision, RoundRoundScheduler, PriorityScheduler
    except Exception:  # noqa: BLE001
        return None


# ---------------------------------------------------------------------------
# Synthetic stubs (used when package is absent / import fails)
# ---------------------------------------------------------------------------


@dataclass
class _FakeTaskNode:
    name: str
    parallelism: int = 1
    cpu_required: float = 1.0
    memory_required: str = "1GB"
    priority: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class _FakePlacementDecision:
    node_name: str
    assigned_workers: list[str]
    delay: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class _FakeRoundRobinScheduler:
    def __init__(self, worker_count: int = 4):
        self._workers = [f"worker-{i}" for i in range(worker_count)]
        self._idx = 0

    def make_decision(self, node: _FakeTaskNode) -> _FakePlacementDecision:
        assigned = self._workers[self._idx % len(self._workers)]
        self._idx += 1
        return _FakePlacementDecision(
            node_name=node.name,
            assigned_workers=[assigned],
        )


class _FakePriorityScheduler:
    def __init__(self, worker_count: int = 4):
        self._workers = [f"worker-{i}" for i in range(worker_count)]

    def make_decision(self, node: _FakeTaskNode) -> _FakePlacementDecision:
        # Simulate priority-based selection with a sort
        chosen = sorted(self._workers, key=lambda w: hash(node.name + w))[0]
        return _FakePlacementDecision(
            node_name=node.name,
            assigned_workers=[chosen],
        )


# ---------------------------------------------------------------------------
# Workload
# ---------------------------------------------------------------------------


def run_scheduler_workload(iterations: int = 50_000) -> dict[str, float]:
    """
    Drive the scheduler in a tight loop and return timing stats.

    Returns
    -------
    dict with keys: rr_total_s, rr_per_decision_us, pri_total_s, pri_per_decision_us
    """
    _real = _try_import_real()
    if _real:
        _Scheduler, _Decision, RRScheduler, PriScheduler = _real
        print("[scheduler] Using real isage-kernel scheduler classes")
    else:
        RRScheduler = _FakeRoundRobinScheduler  # type: ignore[assignment]
        PriScheduler = _FakePriorityScheduler  # type: ignore[assignment]
        print("[scheduler] isage-kernel not available — running synthetic stub")

    tasks = [
        _FakeTaskNode(name=f"op-{i}", parallelism=(i % 8) + 1, priority=i % 5)
        for i in range(min(1000, iterations))
    ]

    # --- Round-robin ---
    rr = RRScheduler(worker_count=8)
    t0 = time.perf_counter()
    for i in range(iterations):
        node = tasks[i % len(tasks)]
        rr.make_decision(node)
    rr_total = time.perf_counter() - t0

    # --- Priority-based ---
    pri = PriScheduler(worker_count=8)
    t0 = time.perf_counter()
    for i in range(iterations):
        node = tasks[i % len(tasks)]
        pri.make_decision(node)
    pri_total = time.perf_counter() - t0

    results = {
        "rr_total_s": rr_total,
        "rr_per_decision_us": rr_total / iterations * 1e6,
        "pri_total_s": pri_total,
        "pri_per_decision_us": pri_total / iterations * 1e6,
        "iterations": iterations,
    }

    print(
        f"[scheduler] RoundRobin   : {results['rr_per_decision_us']:.3f} µs/decision"
        f"  ({iterations:,} iters, total={rr_total:.3f}s)"
    )
    print(
        f"[scheduler] Priority     : {results['pri_per_decision_us']:.3f} µs/decision"
        f"  ({iterations:,} iters, total={pri_total:.3f}s)"
    )
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scheduler profiling workload")
    parser.add_argument("--iterations", type=int, default=50_000)
    args = parser.parse_args()
    run_scheduler_workload(args.iterations)
