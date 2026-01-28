#!/usr/bin/env python3
"""
Quick Local Test for Workload 2
================================

Tests Workload 2 in local mode (without distributed execution).
"""

import sys
sys.path.insert(0, ".")

from distributed_workloads.workload_config import get_config
from distributed_workloads.workload_pipelines import build_and_run_workload

def main():
    print("=" * 80)
    print("Workload 2 - Local Mode Test")
    print("=" * 80)
    
    config = get_config('workload_2')
    config.use_remote = False  # 本地模式，不使用Ray
    config.num_tasks = 10
    config.query_qps = 2.0
    config.keyby_parallelism = 2  # 降低并行度
    
    print(f"Configuration:")
    print(f"  - Use Remote: {config.use_remote}")
    print(f"  - Num Tasks: {config.num_tasks}")
    print(f"  - QPS: {config.query_qps}")
    print(f"  - Parallelism: {config.keyby_parallelism}")
    print()
    
    try:
        build_and_run_workload('workload_2', config)
        print("\n✅ Test completed successfully!")
        return 0
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
