#!/usr/bin/env python
"""Performance benchmark: SageDB vs FAISS

Compares the performance of two VDB backends:
- SageDB: Self-developed C++ vector database (NOT FAISS-based)
- FAISS: Third-party Python wrapper (Facebook AI Research)

Benchmarks:
- Vector insertion (single & batch)
- Vector search (various k values)
- Memory usage
- Index building time

Note: SageDB is a fully custom C++ implementation. ANNS algorithms
will be migrated to sage-libs in the future for better modularity.
"""

import sys
import time
from pathlib import Path
from typing import Any, Callable

import numpy as np
import psutil

# Add SAGE to path
sage_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(sage_root / "packages/sage-middleware/src"))


class BenchmarkResult:
    """存储基准测试结果"""

    def __init__(self, name: str):
        self.name = name
        self.times: list[float] = []
        self.memory_usage: list[float] = []

    def add_measurement(self, time_ms: float, memory_mb: float):
        self.times.append(time_ms)
        self.memory_usage.append(memory_mb)

    @property
    def avg_time(self) -> float:
        return np.mean(self.times) if self.times else 0.0

    @property
    def std_time(self) -> float:
        return np.std(self.times) if self.times else 0.0

    @property
    def avg_memory(self) -> float:
        return np.mean(self.memory_usage) if self.memory_usage else 0.0


def measure_memory() -> float:
    """获取当前进程内存使用（MB）"""
    process = psutil.Process()
    return process.memory_info().rss / 1024 / 1024


def benchmark_operation(
    operation: Callable[[], Any], name: str, warmup: int = 1, iterations: int = 5
) -> BenchmarkResult:
    """基准测试一个操作"""
    result = BenchmarkResult(name)

    # Warmup
    for _ in range(warmup):
        operation()

    # Benchmark
    for _ in range(iterations):
        mem_before = measure_memory()
        start = time.perf_counter()

        operation()

        end = time.perf_counter()
        mem_after = measure_memory()

        time_ms = (end - start) * 1000
        memory_mb = mem_after - mem_before

        result.add_measurement(time_ms, memory_mb)

    return result


def create_test_vectors(n: int, dim: int) -> list[np.ndarray]:
    """创建测试向量"""
    return [np.random.randn(dim).astype(np.float32) for _ in range(n)]


def benchmark_backend(backend_name: str, dim: int = 128, n_vectors: int = 10000):
    """基准测试一个后端"""
    from sage.middleware.components.sage_mem.neuromem.search_engine.vdb_index import create_index

    print(f"\n{'=' * 60}")
    print(f"Benchmarking {backend_name} backend")
    print(f"{'=' * 60}")
    print(f"Dimension: {dim}, Vectors: {n_vectors}")

    # 创建索引
    config = {"name": f"test_{backend_name.lower()}", "dim": dim, "backend_type": backend_name}

    index = create_index(config)

    # 准备测试数据
    vectors = create_test_vectors(n_vectors, dim)
    vector_ids = [f"vec_{i}" for i in range(n_vectors)]
    query_vectors = create_test_vectors(100, dim)  # 100 queries

    results = {}

    # 1. 单个插入基准
    print("\n1️⃣  Single insert benchmark...")
    test_vectors = vectors[:100]  # 只测试前100个
    test_ids = vector_ids[:100]

    def single_insert():
        for vec, vid in zip(test_vectors, test_ids):
            index.insert(vec, f"{vid}_single")

    results["single_insert"] = benchmark_operation(
        single_insert, "Single Insert (100 vectors)", warmup=0, iterations=1
    )

    # 2. 批量插入基准
    print("2️⃣  Batch insert benchmark...")
    batch_vectors = vectors
    batch_ids = vector_ids

    def batch_insert():
        index.batch_insert(batch_vectors, batch_ids)

    results["batch_insert"] = benchmark_operation(
        batch_insert, f"Batch Insert ({n_vectors} vectors)", warmup=0, iterations=1
    )

    # 3. 搜索基准 (不同 k 值)
    for k in [1, 5, 10, 50]:
        print(f"3️⃣  Search benchmark (k={k})...")

        def search_k():
            for query in query_vectors:
                index.search(query, topk=k)

        results[f"search_k{k}"] = benchmark_operation(
            search_k, f"Search (k={k}, 100 queries)", warmup=1, iterations=3
        )

    # 4. 内存占用
    mem_usage = measure_memory()
    print(f"\n4️⃣  Memory usage: {mem_usage:.2f} MB")

    return results


def print_comparison_table(faiss_results: dict, sagedb_results: dict):
    """打印对比表格"""
    print("\n" + "=" * 80)
    print("Performance Comparison: FAISS vs SageDB")
    print("=" * 80)

    # 表头
    print(f"\n{'Operation':<30} {'FAISS (ms)':<15} {'SageDB (ms)':<15} {'Speedup':<10}")
    print("-" * 80)

    # 对比每个操作
    for op_name in faiss_results.keys():
        faiss_result = faiss_results[op_name]
        sagedb_result = sagedb_results.get(op_name)

        if sagedb_result:
            faiss_time = faiss_result.avg_time
            sagedb_time = sagedb_result.avg_time
            speedup = faiss_time / sagedb_time if sagedb_time > 0 else 0.0

            speedup_str = f"{speedup:.2f}x" if speedup > 0 else "N/A"
            if speedup > 1.0:
                speedup_str = f"🚀 {speedup_str}"
            elif speedup < 1.0 and speedup > 0:
                speedup_str = f"🐢 {speedup_str}"

            print(
                f"{faiss_result.name:<30} "
                f"{faiss_time:>12.2f} ±{faiss_result.std_time:>5.2f}  "
                f"{sagedb_time:>12.2f} ±{sagedb_result.std_time:>5.2f}  "
                f"{speedup_str:<10}"
            )


def main():
    """主函数"""
    print("=" * 80)
    print("VDB Backend Performance Benchmark")
    print("=" * 80)
    print("\nComparing FAISS vs SageDB performance...")
    print("This may take a few minutes...\n")

    # 测试参数
    dim = 128
    n_vectors = 5000  # 减少到 5000 以加快测试

    try:
        # 基准测试 FAISS
        faiss_results = benchmark_backend("FAISS", dim, n_vectors)

        # 基准测试 SageDB
        sagedb_results = benchmark_backend("SageDB", dim, n_vectors)

        # 打印对比
        print_comparison_table(faiss_results, sagedb_results)

        # 总结
        print("\n" + "=" * 80)
        print("Summary")
        print("=" * 80)

        # 计算平均加速比
        speedups = []
        for op_name in faiss_results.keys():
            faiss_time = faiss_results[op_name].avg_time
            sagedb_time = sagedb_results[op_name].avg_time
            if sagedb_time > 0:
                speedups.append(faiss_time / sagedb_time)

        avg_speedup = np.mean(speedups) if speedups else 0.0

        print(f"\nAverage speedup: {avg_speedup:.2f}x")

        if avg_speedup > 1.1:
            print("✅ SageDB is faster overall")
            print("💡 Recommendation: Use SageDB for production workloads")
        elif avg_speedup < 0.9:
            print("✅ FAISS is faster overall")
            print("💡 Recommendation: FAISS may be better for your workload")
        else:
            print("⚖️  Performance is similar")
            print("💡 Recommendation: Choose based on other factors (ease of use, features)")

        print("\n✅ Benchmark completed successfully!")

    except Exception as e:
        print(f"\n❌ Benchmark failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
