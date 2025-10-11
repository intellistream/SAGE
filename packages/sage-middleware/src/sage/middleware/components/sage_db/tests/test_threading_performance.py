#!/usr/bin/env python3
"""
Multi-threading performance test for SageDB with GIL release.

This script benchmarks the performance improvement from GIL release
in the Python bindings. Expected results:
- Single thread: ~120 QPS baseline
- 2 threads: ~235 QPS (1.96x)
- 4 threads: ~460 QPS (3.83x)
- 8 threads: ~480+ QPS (4.0x+)
"""

import sys
import threading
import time
from pathlib import Path
from typing import List, Tuple

import numpy as np

# Add the package to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from python.sage_db import DatabaseConfig, DistanceMetric, IndexType, SageDB
except ImportError:
    print("❌ Failed to import SageDB. Please build the extension first:")
    print("   cd packages/sage-middleware/src/sage/middleware/components/sage_db")
    print("   ./build.sh")
    sys.exit(1)


def prepare_test_database(dimension: int = 768, num_vectors: int = 10000) -> SageDB:
    """Create and populate a test database."""
    print(f"📊 Preparing test database ({num_vectors} vectors, {dimension} dims)...")

    config = DatabaseConfig(dimension)
    config.index_type = IndexType.FLAT  # Use FLAT for consistent performance
    config.metric = DistanceMetric.L2

    db = SageDB.from_config(config)

    # Add random vectors
    np.random.seed(42)
    vectors = np.random.rand(num_vectors, dimension).astype(np.float32)

    start = time.time()
    db.add_batch(vectors.tolist())
    elapsed = time.time() - start

    print(
        f"✅ Database ready. Insertion took {elapsed:.2f}s ({num_vectors/elapsed:.0f} vectors/s)"
    )
    return db


def benchmark_single_thread(
    db: SageDB, num_queries: int = 1000, dimension: int = 768
) -> float:
    """Benchmark single-threaded search performance."""
    print(f"\n🔍 Single-threaded benchmark ({num_queries} queries)...")

    np.random.seed(123)
    queries = np.random.rand(num_queries, dimension).astype(np.float32)

    start = time.time()
    for query in queries:
        db.search(query.tolist(), k=10)
    elapsed = time.time() - start

    qps = num_queries / elapsed
    print(f"   QPS: {qps:.1f}")
    print(f"   Avg latency: {elapsed * 1000 / num_queries:.2f}ms")

    return qps


def benchmark_multi_thread(
    db: SageDB, num_threads: int, queries_per_thread: int = 500, dimension: int = 768
) -> Tuple[float, float]:
    """Benchmark multi-threaded search performance."""
    print(
        f"\n🔍 Multi-threaded benchmark ({num_threads} threads, {queries_per_thread} queries/thread)..."
    )

    # Prepare queries for each thread
    np.random.seed(456)
    all_queries = [
        np.random.rand(queries_per_thread, dimension).astype(np.float32)
        for _ in range(num_threads)
    ]

    results = [0.0] * num_threads

    def worker(thread_id: int, queries: np.ndarray):
        """Worker function for each thread."""
        thread_start = time.time()
        for query in queries:
            db.search(query.tolist(), k=10)
        thread_elapsed = time.time() - thread_start
        results[thread_id] = thread_elapsed

    # Start all threads
    threads = []
    start = time.time()

    for i in range(num_threads):
        t = threading.Thread(target=worker, args=(i, all_queries[i]))
        threads.append(t)
        t.start()

    # Wait for all threads
    for t in threads:
        t.join()

    total_elapsed = time.time() - start
    total_queries = num_threads * queries_per_thread
    total_qps = total_queries / total_elapsed

    # Calculate per-thread stats
    avg_thread_time = sum(results) / len(results)
    per_thread_qps = queries_per_thread / avg_thread_time

    print(f"   Total QPS: {total_qps:.1f}")
    print(f"   Per-thread QPS: {per_thread_qps:.1f}")
    print(f"   Total time: {total_elapsed:.2f}s")
    print(f"   Avg thread time: {avg_thread_time:.2f}s")

    return total_qps, per_thread_qps


def benchmark_batch_search(
    db: SageDB, batch_size: int = 100, num_batches: int = 10, dimension: int = 768
) -> float:
    """Benchmark batch search performance."""
    print(
        f"\n🔍 Batch search benchmark ({num_batches} batches × {batch_size} queries)..."
    )

    np.random.seed(789)

    total_time = 0.0
    total_queries = 0

    for i in range(num_batches):
        queries = np.random.rand(batch_size, dimension).astype(np.float32)

        start = time.time()
        results = db.batch_search(queries.tolist(), k=10)
        elapsed = time.time() - start

        total_time += elapsed
        total_queries += batch_size

        if i == 0:
            print(f"   First batch: {batch_size / elapsed:.1f} QPS")

    avg_qps = total_queries / total_time
    print(f"   Average QPS: {avg_qps:.1f}")
    print(f"   Total queries: {total_queries}")

    return avg_qps


def main():
    """Run all benchmarks."""
    print("=" * 70)
    print("SageDB Multi-Threading Performance Benchmark")
    print("Testing GIL Release Implementation")
    print("=" * 70)

    # Configuration
    DIMENSION = 768
    NUM_VECTORS = 10000
    NUM_QUERIES = 1000
    QUERIES_PER_THREAD = 500

    # Prepare database
    db = prepare_test_database(DIMENSION, NUM_VECTORS)

    # Benchmark 1: Single-threaded baseline
    baseline_qps = benchmark_single_thread(db, NUM_QUERIES, DIMENSION)

    # Benchmark 2: Multi-threaded scaling
    results = {}
    for num_threads in [2, 4, 8]:
        total_qps, per_thread_qps = benchmark_multi_thread(
            db, num_threads, QUERIES_PER_THREAD, DIMENSION
        )
        results[num_threads] = {
            "total_qps": total_qps,
            "per_thread_qps": per_thread_qps,
            "speedup": total_qps / baseline_qps,
        }

    # Benchmark 3: Batch search (TODO: fix parameter binding)
    # batch_qps = benchmark_batch_search(db, batch_size=100, num_batches=10, dimension=DIMENSION)
    batch_qps = 0  # placeholder

    # Summary
    print("\n" + "=" * 70)
    print("PERFORMANCE SUMMARY")
    print("=" * 70)
    print(f"\nBaseline (1 thread):  {baseline_qps:>8.1f} QPS")
    print(f"\nMulti-threaded Performance:")
    print(f"{'Threads':<10} {'Total QPS':<12} {'Speedup':<12} {'Per-Thread QPS':<15}")
    print("-" * 50)

    for num_threads, data in results.items():
        speedup = data["speedup"]
        efficiency = (speedup / num_threads) * 100
        print(
            f"{num_threads:<10} {data['total_qps']:<12.1f} {speedup:<12.2f}x {data['per_thread_qps']:<15.1f}"
        )
        print(f"           Parallel efficiency: {efficiency:.1f}%")

    print(f"\nBatch Search:         {batch_qps:>8.1f} QPS")
    print(f"                       {batch_qps / baseline_qps:>8.2f}x speedup")

    # Analysis
    print("\n" + "=" * 70)
    print("ANALYSIS")
    print("=" * 70)

    if results[8]["speedup"] >= 3.5:
        print("✅ EXCELLENT: GIL release is working correctly!")
        print("   Performance scales well with thread count.")
        if results[8]["speedup"] >= 7.0:
            print("   🚀 Near-linear scaling achieved!")
    elif results[8]["speedup"] >= 2.0:
        print("⚠️  GOOD: GIL is released, but some contention exists.")
        print("   Consider implementing lock-free architecture for better scaling.")
    else:
        print("❌ POOR: Limited multi-threading benefit detected.")
        print("   Check if GIL is actually being released.")

    print("\nNext Steps:")
    if results[8]["speedup"] < 7.0:
        print("  1. Implement Phase 1: Basic thread safety with shared_mutex")
        print("  2. Implement Phase 3: Lock-free architecture")
        print("  3. Add OpenMP to batch_search for internal parallelization")
    else:
        print("  1. Phase 2 (GIL Release) ✅ Complete")
        print("  2. Ready for Phase 3 (Lock-Free Architecture)")

    print("=" * 70)


if __name__ == "__main__":
    main()
