#!/usr/bin/env python3
"""
Test FAISS threading behavior to diagnose lock contention
"""

import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import faiss
import numpy as np

DIMENSION = 768
NUM_VECTORS = 10000
NUM_QUERIES = 500


def create_test_index():
    """Create a simple FAISS index for testing"""
    print(f"Creating FAISS IndexFlatIP ({NUM_VECTORS} vectors, {DIMENSION} dims)...")
    index = faiss.IndexFlatIP(DIMENSION)
    vectors = np.random.randn(NUM_VECTORS, DIMENSION).astype("float32")
    faiss.normalize_L2(vectors)
    index.add(vectors)
    print(f"✅ Index created with {index.ntotal} vectors")
    return index


def search_worker(index, query_vectors, thread_id):
    """Worker function for multi-threaded search"""
    start = time.time()
    for query in query_vectors:
        distances, indices = index.search(query.reshape(1, -1), k=10)
    duration = time.time() - start
    qps = len(query_vectors) / duration
    print(f"  Thread {thread_id}: {qps:.1f} QPS, {duration:.2f}s")
    return qps, duration


def benchmark_single_thread(index):
    """Benchmark single-threaded performance"""
    print("\n🔍 Single-threaded benchmark...")
    queries = np.random.randn(NUM_QUERIES, DIMENSION).astype("float32")
    faiss.normalize_L2(queries)

    start = time.time()
    for query in queries:
        distances, indices = index.search(query.reshape(1, -1), k=10)
    duration = time.time() - start

    qps = NUM_QUERIES / duration
    print(f"   QPS: {qps:.1f}, Time: {duration:.2f}s")
    return qps


def benchmark_multi_thread(index, num_threads):
    """Benchmark multi-threaded performance"""
    print(f"\n🔍 Multi-threaded benchmark ({num_threads} threads)...")

    # Prepare queries for each thread
    queries_per_thread = NUM_QUERIES // num_threads
    all_queries = [
        np.random.randn(queries_per_thread, DIMENSION).astype("float32")
        for _ in range(num_threads)
    ]
    for queries in all_queries:
        faiss.normalize_L2(queries)

    # Run threads
    start = time.time()
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [
            executor.submit(search_worker, index, queries, i)
            for i, queries in enumerate(all_queries)
        ]
        results = [f.result() for f in as_completed(futures)]

    total_time = time.time() - start
    total_qps = (queries_per_thread * num_threads) / total_time

    print(f"   Total QPS: {total_qps:.1f}")
    print(f"   Total time: {total_time:.2f}s")
    return total_qps


def benchmark_shared_vs_clone(index, num_threads=4):
    """Test if cloning the index helps performance"""
    print(f"\n🧪 Testing shared index vs cloned indices...")

    # Test 1: Shared index
    print("\n  Shared index:")
    shared_qps = benchmark_multi_thread(index, num_threads)

    # Test 2: Cloned indices (one per thread)
    print("\n  Cloned indices (one per thread):")
    queries_per_thread = NUM_QUERIES // num_threads
    all_queries = [
        np.random.randn(queries_per_thread, DIMENSION).astype("float32")
        for _ in range(num_threads)
    ]
    for queries in all_queries:
        faiss.normalize_L2(queries)

    # Clone the index for each thread
    cloned_indices = [faiss.clone_index(index) for _ in range(num_threads)]

    start = time.time()
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [
            executor.submit(search_worker, cloned_indices[i], queries, i)
            for i, queries in enumerate(all_queries)
        ]
        results = [f.result() for f in as_completed(futures)]

    total_time = time.time() - start
    cloned_qps = (queries_per_thread * num_threads) / total_time

    print(f"\n  Shared index QPS:  {shared_qps:.1f}")
    print(f"  Cloned indices QPS: {cloned_qps:.1f}")
    print(f"  Improvement: {(cloned_qps/shared_qps - 1) * 100:.1f}%")


def main():
    print("=" * 70)
    print("FAISS Threading Diagnosis")
    print("=" * 70)

    # Create index
    index = create_test_index()

    # Test 1: Single thread baseline
    baseline_qps = benchmark_single_thread(index)

    # Test 2: Multi-threaded scaling
    for num_threads in [2, 4, 8]:
        mt_qps = benchmark_multi_thread(index, num_threads)
        speedup = mt_qps / baseline_qps
        print(f"   Speedup: {speedup:.2f}x")

    # Test 3: Shared vs cloned indices
    benchmark_shared_vs_clone(index, num_threads=4)

    print("\n" + "=" * 70)
    print("DIAGNOSIS COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
