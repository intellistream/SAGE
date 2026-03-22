"""
Profiling Workload — isage-privacy DP Unlearning (sage_privacy.dp_unlearning)
=============================================================================

Measures the hot loops in differential-privacy unlearning:
  1. Vector perturbation  — NumPy noise generation over embedding batches
  2. Privacy accountant   — epsilon/delta budget accumulation
  3. Neighbor compensation — graph-walk update after unlearning
  4. Full engine run      — end-to-end unlearn() call

This workload uses the real sage_privacy classes when available, and falls
back to equivalent NumPy-based stubs that mirror the actual computation.

Run standalone:
    python workload_dp_unlearning.py [--vectors 5000] [--dim 128] [--iterations 10]
"""

from __future__ import annotations

import argparse
import time
from typing import Any

import numpy as np

# ---------------------------------------------------------------------------
# Try to import real classes
# ---------------------------------------------------------------------------


def _try_import_unlearning():
    try:
        from sage_privacy.dp_unlearning.base_mechanism import (  # noqa: PLC0415
            SimpleLaplaceMechanism,
        )
        from sage_privacy.dp_unlearning.neighbor_compensation import (  # noqa: PLC0415
            NeighborCompensation,
        )
        from sage_privacy.dp_unlearning.privacy_accountant import (  # noqa: PLC0415
            PrivacyAccountant,
        )
        from sage_privacy.dp_unlearning.unlearning_engine import (  # noqa: PLC0415
            UnlearningEngine,
        )
        from sage_privacy.dp_unlearning.vector_perturbation import (  # noqa: PLC0415
            VectorPerturbation,
        )

        return (
            SimpleLaplaceMechanism,
            VectorPerturbation,
            PrivacyAccountant,
            NeighborCompensation,
            UnlearningEngine,
            True,  # is_real
        )
    except Exception:  # noqa: BLE001
        return None


# ---------------------------------------------------------------------------
# Stubs mirroring the real computation
# ---------------------------------------------------------------------------


class _StubLaplace:
    """Stub mirroring SimpleLaplaceMechanism interface."""

    def __init__(self, epsilon: float = 1.0, sensitivity: float = 1.0):
        self.epsilon = epsilon
        self.sensitivity = sensitivity

    def compute_noise(self) -> float:
        scale = self.sensitivity / self.epsilon
        return float(np.random.laplace(0, scale))

    def add_noise(self, data: np.ndarray) -> np.ndarray:
        scale = self.sensitivity / self.epsilon
        return data + np.random.laplace(0, scale, data.shape).astype(data.dtype)

    def get_privacy_cost(self) -> tuple[float, float]:
        return (self.epsilon, 1e-5)


class _StubPerturbation:
    """Stub mirroring VectorPerturbation.perturb_single_vector() interface."""

    def __init__(self, mechanism: Any):
        self.mechanism = mechanism

    def perturb_single_vector(self, vector: np.ndarray, strategy: str = "uniform") -> np.ndarray:
        return self.mechanism.add_noise(vector)


class _StubAccountant:
    """Stub mirroring PrivacyAccountant (total_epsilon_budget, total_delta_budget, composition_type)."""

    def __init__(
        self,
        total_epsilon_budget: float = 10.0,
        total_delta_budget: float = 1e-5,
        composition_type: str = "basic",
    ):
        self._budget_eps = total_epsilon_budget
        self._budget_delta = total_delta_budget
        self._spent = 0.0

    def record_operation(
        self,
        epsilon: float,
        delta: float,
        operation: str = "unlearn",
        mechanism: str = "laplace",
        metadata: dict | None = None,
    ) -> bool:
        self._spent += epsilon
        return True

    def can_afford(self, epsilon: float) -> bool:
        return self._spent + epsilon <= self._budget_eps

    def get_remaining_budget(self) -> tuple[float, float]:
        return (max(0.0, self._budget_eps - self._spent), self._budget_delta)


class _StubNeighborCompensation:
    """Stub mirroring NeighborCompensation.compute_compensation() interface."""

    def __init__(self, k_neighbors: int = 10):
        self.k_neighbors = k_neighbors

    def compute_compensation(
        self,
        original_vector: np.ndarray,
        perturbed_vector: np.ndarray,
        neighbor_vector: np.ndarray,
        neighbor_similarity: float,
    ) -> np.ndarray:
        delta = perturbed_vector - original_vector
        return neighbor_vector + neighbor_similarity * delta * 0.1


class _StubEngine:
    """Stub mirroring UnlearningEngine.unlearn_vectors() interface."""

    def __init__(
        self,
        epsilon: float = 1.0,
        delta: float = 1e-5,
        total_budget_epsilon: float = 10.0,
        total_budget_delta: float = 1e-4,
        enable_compensation: bool = True,
    ):
        self._mech = _StubLaplace(epsilon)
        self._perturb = _StubPerturbation(self._mech)
        self._acct = _StubAccountant(total_budget_epsilon, total_budget_delta)
        self._comp = _StubNeighborCompensation()
        self._enable_compensation = enable_compensation

    def unlearn_vectors(
        self,
        vectors_to_forget: np.ndarray,
        vector_ids_to_forget: list[str],
        all_vectors: np.ndarray | None = None,
        all_vector_ids: list[str] | None = None,
        perturbation_strategy: str = "uniform",
        return_compensated_neighbors: bool = False,
    ) -> Any:
        eps, delta = self._mech.get_privacy_cost()
        if not self._acct.can_afford(eps):
            return None
        perturbed = np.array([self._perturb.perturb_single_vector(v) for v in vectors_to_forget])
        self._acct.record_operation(eps, delta, "unlearn", "laplace")
        return perturbed


# ---------------------------------------------------------------------------
# Individual benchmarks
# ---------------------------------------------------------------------------


def bench_vector_perturbation(
    Perturb: Any, Mech: Any, vectors: np.ndarray, iterations: int, is_real: bool
) -> float:
    """Return total seconds for `iterations` batch perturbation passes."""
    mech = Mech(epsilon=1.0) if is_real else Mech(epsilon=1.0)
    p = Perturb(mech)
    sample = vectors[: min(100, len(vectors))]  # perturb a 100-vec batch per call
    t0 = time.perf_counter()
    for _ in range(iterations):
        for v in sample:
            p.perturb_single_vector(v)
    return time.perf_counter() - t0


def bench_privacy_accounting(Acct: Any, iterations: int, is_real: bool) -> float:
    # Budget must exceed iterations × per-call cost; add 10× headroom
    eps_per_call, delta_per_call = 0.01, 1e-6
    a = Acct(
        total_epsilon_budget=eps_per_call * iterations * 10,
        total_delta_budget=delta_per_call * iterations * 10,
    )
    t0 = time.perf_counter()
    for _ in range(iterations):
        a.record_operation(eps_per_call, delta_per_call, "unlearn", "laplace")
        a.get_remaining_budget()
    return time.perf_counter() - t0


def bench_neighbor_compensation(
    Comp: Any, vectors: np.ndarray, unlearn_mask: np.ndarray, iterations: int, is_real: bool
) -> float:
    c = Comp()
    forget_vec = vectors[unlearn_mask][0]
    perturbed_vec = forget_vec + np.random.randn(*forget_vec.shape).astype(np.float32) * 0.1
    neighbor_vec = vectors[~unlearn_mask][0]
    t0 = time.perf_counter()
    for _ in range(iterations):
        c.compute_compensation(
            original_vector=forget_vec,
            perturbed_vector=perturbed_vec,
            neighbor_vector=neighbor_vec,
            neighbor_similarity=0.85,
        )
    return time.perf_counter() - t0


def bench_full_engine(
    Engine: Any, vectors: np.ndarray, num_iterations: int, is_real: bool
) -> float:
    if is_real:
        engine = Engine(epsilon=2.0, delta=1e-5, total_budget_epsilon=500.0)
    else:
        engine = Engine(epsilon=2.0, delta=1e-5, total_budget_epsilon=500.0)
    n = max(1, len(vectors) // 20)  # unlearn 5% each round
    ids_all = [str(i) for i in range(len(vectors))]
    t0 = time.perf_counter()
    for i in range(num_iterations):
        idx = np.arange(i * n % len(vectors), min(i * n % len(vectors) + n, len(vectors)))
        engine.unlearn_vectors(
            vectors_to_forget=vectors[idx],
            vector_ids_to_forget=[ids_all[j] for j in idx],
            all_vectors=vectors,
            all_vector_ids=ids_all,
        )
    return time.perf_counter() - t0


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------


def run_dp_unlearning_workload(
    num_vectors: int = 5_000,
    dim: int = 128,
    iterations: int = 10,
) -> dict[str, float]:
    """
    Run DP unlearning benchmarks and return timing stats.
    """
    real = _try_import_unlearning()
    if real:
        Mech, Perturb, Acct, Comp, Engine, is_real = real
        print("[dp_unlearn] Using real sage_privacy.dp_unlearning classes")
    else:
        Mech, Perturb, Acct, Comp, Engine, is_real = (
            _StubLaplace,
            _StubPerturbation,
            _StubAccountant,
            _StubNeighborCompensation,
            _StubEngine,
            False,
        )
        print("[dp_unlearn] sage.libs not available — running synthetic stubs")

    rng = np.random.default_rng(42)
    vectors = rng.standard_normal((num_vectors, dim)).astype(np.float32)
    unlearn_n = max(1, num_vectors // 20)
    unlearn_mask = np.zeros(num_vectors, dtype=bool)
    unlearn_mask[:unlearn_n] = True

    # 1. Vector perturbation  (batch of 100 vectors × iterations)
    perturb_total = bench_vector_perturbation(Perturb, Mech, vectors, iterations, is_real)

    # 2. Privacy accounting
    acct_total = bench_privacy_accounting(Acct, iterations * 100, is_real)

    # 3. Neighbor compensation
    comp_total = bench_neighbor_compensation(Comp, vectors, unlearn_mask, iterations, is_real)

    # 4. Full engine
    engine_total = bench_full_engine(Engine, vectors, iterations, is_real)

    throughput_vecs = num_vectors * iterations / engine_total if engine_total > 0 else 0

    results = {
        "num_vectors": num_vectors,
        "dim": dim,
        "iterations": iterations,
        "perturb_total_s": perturb_total,
        "perturb_ms_per_call": perturb_total / iterations * 1e3,
        "acct_total_s": acct_total,
        "acct_us_per_call": acct_total / (iterations * 100) * 1e6,
        "comp_total_s": comp_total,
        "comp_ms_per_call": comp_total / iterations * 1e3,
        "engine_total_s": engine_total,
        "engine_ms_per_call": engine_total / iterations * 1e3,
        "engine_vectors_per_sec": throughput_vecs,
    }

    print(
        f"[dp_unlearn] Perturbation   : {results['perturb_ms_per_call']:.2f} ms/call"
        f"  ({num_vectors} vecs, dim={dim})"
    )
    print(f"[dp_unlearn] Acct update    : {results['acct_us_per_call']:.2f} µs/call")
    print(
        f"[dp_unlearn] Neighbor comp  : {results['comp_ms_per_call']:.2f} ms/call"
        f"  (unlearn={unlearn_n} vecs)"
    )
    print(
        f"[dp_unlearn] Full engine    : {results['engine_ms_per_call']:.2f} ms/call"
        f"  ({throughput_vecs:.0f} vecs/s)"
    )
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DP Unlearning profiling workload")
    parser.add_argument("--vectors", type=int, default=5_000)
    parser.add_argument("--dim", type=int, default=128)
    parser.add_argument("--iterations", type=int, default=10)
    args = parser.parse_args()
    run_dp_unlearning_workload(args.vectors, args.dim, args.iterations)
