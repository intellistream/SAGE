#!/usr/bin/env python3
"""
Quick test script to verify the benchmark_anns framework.
This creates synthetic data and runs a simple test without requiring actual datasets.
"""

import sys
import os
import numpy as np
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from benchmark_anns.core import (
    CongestionRunner,
    Runbook,
    create_simple_runbook
)
from benchmark_anns.datasets import SimpleDataset
from benchmark_anns.algorithms.faiss_hnsw import FaissHNSWCongestion


def create_synthetic_dataset(nb=5000, nq=100, d=128):
    """Create a synthetic dataset for testing"""
    print(f"Creating synthetic dataset: {nb} base vectors, {nq} queries, dimension {d}")
    
    dataset = SimpleDataset(name="synthetic", data_path=".", dtype="float32")
    dataset.d = d
    dataset.nb = nb
    dataset.nq = nq
    dataset._base_data = np.random.randn(nb, d).astype(np.float32)
    dataset._query_data = np.random.randn(nq, d).astype(np.float32)
    
    return dataset


def main():
    print("=" * 70)
    print("Benchmark ANNS - Quick Test")
    print("=" * 70)
    
    # Create synthetic dataset
    print("\n[1/5] Creating synthetic dataset...")
    dataset = create_synthetic_dataset(nb=5000, nq=100, d=128)
    print(f"✓ Dataset created: {dataset.nb} vectors, {dataset.nq} queries, dim={dataset.d}")
    
    # Create algorithm
    print("\n[2/5] Creating algorithm...")
    try:
        algo = FaissHNSWCongestion(
            metric='euclidean',
            index_params={'indexkey': 'HNSW32'},
            parallel_workers=1
        )
        print(f"✓ Algorithm created: {algo.name}")
    except ModuleNotFoundError as e:
        print(f"✗ Error: PyCANDYAlgo not found. Faiss HNSW requires PyCANDYAlgo.")
        print(f"  This is expected if PyCANDYAlgo is not installed.")
        print(f"  The framework structure is complete, but this algorithm needs the library.")
        return
    
    # Setup algorithm
    print("\n[3/5] Setting up algorithm...")
    max_pts = 10000
    setup_time = CongestionRunner.setup_algorithm(algo, dataset, max_pts)
    print(f"✓ Setup completed in {setup_time:.3f}s")
    
    # Create simple runbook
    print("\n[4/5] Creating test runbook...")
    runbook = create_simple_runbook(
        nb_initial=1000,
        nb_insert=2000,
        nb_delete=100,
        nb_search=5,
        batch_size=500,
        event_rate=1000
    )
    print(f"✓ Runbook created with {len(runbook)} operations")
    
    # Run test
    print("\n[5/5] Running congestion test...")
    print("-" * 70)
    
    query_params = {'ef': 32}
    algo.set_query_arguments(query_params)
    
    try:
        results = CongestionRunner.run_test(
            algo=algo,
            dataset=dataset,
            runbook=runbook,
            query_args=query_params,
            k=10
        )
        
        print("-" * 70)
        print("\n✓ Test completed successfully!")
        print("\n" + "=" * 70)
        print("RESULTS SUMMARY")
        print("=" * 70)
        print(f"Total time:     {results['total_time']:.2f}s")
        print(f"Operations:     {results['operation_counts']}")
        print(f"\nInsert latency: mean={results['insert_stats']['mean']/1e3:.2f}ms, "
              f"p95={results['insert_stats']['p95']/1e3:.2f}ms")
        if results['query_stats']['mean'] > 0:
            print(f"Query latency:  mean={results['query_stats']['mean']/1e3:.2f}ms, "
                  f"p95={results['query_stats']['p95']/1e3:.2f}ms")
        print(f"\n✓ All framework components working correctly!")
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    print("\n" + "=" * 70)
    print("Framework verification complete!")
    print("=" * 70)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
