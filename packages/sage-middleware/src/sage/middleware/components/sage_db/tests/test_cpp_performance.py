#!/usr/bin/env python3
"""
Direct C++ performance test - bypassing Python entirely
"""

import os
import sys

# Add parent directory to path to find _sage_db.so
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import _sage_db
import numpy as np

DIMENSION = 768
NUM_VECTORS = 10000
NUM_QUERIES = 500


def create_database():
    """Create and populate a SageDB database"""
    print(f"Creating SageDB ({NUM_VECTORS} vectors, {DIMENSION} dims)...")

    config = _sage_db.DatabaseConfig()
    config.dimension = DIMENSION
    config.index_type = _sage_db.IndexType.FLAT  # Correct enum value

    db = _sage_db.SageDB(config)

    # Add vectors
    vectors = np.random.randn(NUM_VECTORS, DIMENSION).astype("float32")
    for vec in vectors:
        vec = vec / np.linalg.norm(vec)  # Normalize
        db.add(vec.tolist(), {})

    print(f"✅ Database ready with {NUM_VECTORS} vectors")
    return db


def search_worker(db, queries, worker_id):
    """Worker function for multi-threaded search"""
    print(f"  Worker {worker_id} starting with {len(queries)} queries...")
    start = time.time()

    for query in queries:
        results = db.search(query.tolist(), k=10)

    duration = time.time() - start
    qps = len(queries) / duration
    print(f"  Worker {worker_id}: {qps:.1f} QPS, {duration:.2f}s")
    return qps, duration


def benchmark_single_thread(db, num_queries=NUM_QUERIES):
    """Single-threaded baseline"""
    print(f"\n🔍 Single-threaded benchmark ({num_queries} queries)...")

    queries = np.random.randn(num_queries, DIMENSION).astype("float32")
    for i in range(len(queries)):
        queries[i] = queries[i] / np.linalg.norm(queries[i])

    start = time.time()
    for query in queries:
        results = db.search(query.tolist(), k=10)
    duration = time.time() - start

    qps = num_queries / duration
    print(f"   QPS: {qps:.1f}, Time: {duration:.2f}s")
    return qps


def benchmark_multi_thread(db, num_threads, queries_per_thread=NUM_QUERIES):
    """Multi-threaded benchmark"""
    print(
        f"\n🔍 Multi-threaded benchmark ({num_threads} threads, {queries_per_thread} queries each)..."
    )

    # Prepare queries for each thread
    all_queries = []
    for _ in range(num_threads):
        queries = np.random.randn(queries_per_thread, DIMENSION).astype("float32")
        for i in range(len(queries)):
            queries[i] = queries[i] / np.linalg.norm(queries[i])
        all_queries.append(queries)

    # Run threads
    start = time.time()
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [
            executor.submit(search_worker, db, queries, i)
            for i, queries in enumerate(all_queries)
        ]
        results = [f.result() for f in as_completed(futures)]

    total_time = time.time() - start
    total_queries = queries_per_thread * num_threads
    total_qps = total_queries / total_time

    print(f"   Total QPS: {total_qps:.1f}")
    print(f"   Total time: {total_time:.2f}s")
    print(f"   Speedup: {total_qps / baseline_qps:.2f}x")
    return total_qps


def profile_lock_contention(db):
    """Profile lock contention by testing different thread counts"""
    print("\n📊 Lock Contention Profile")
    print("=" * 70)

    results = {}
    for num_threads in [1, 2, 4, 8]:
        qps = benchmark_multi_thread(db, num_threads, queries_per_thread=250)
        results[num_threads] = qps

    print("\n" + "=" * 70)
    print("RESULTS SUMMARY")
    print("=" * 70)
    print(f"{'Threads':<10} {'QPS':<15} {'Speedup':<15} {'Efficiency':<15}")
    print("-" * 70)

    baseline = results[1]
    for threads, qps in results.items():
        speedup = qps / baseline
        efficiency = (speedup / threads) * 100
        print(f"{threads:<10} {qps:<15.1f} {speedup:<15.2f}x {efficiency:<15.1f}%")

    return results


if __name__ == "__main__":
    print("=" * 70)
    print("SageDB C++ Direct Performance Test")
    print("=" * 70)

    # Create database
    db = create_database()

    # Baseline
    baseline_qps = benchmark_single_thread(db)

    # Profile lock contention
    profile_lock_contention(db)

    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)
