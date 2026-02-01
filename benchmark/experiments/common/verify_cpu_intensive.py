#!/usr/bin/env python3
"""
验证CPU密集型算子的资源争用效果

对比 DelaySimulator（空循环）vs CPUIntensiveReranker（真实计算）的CPU使用率
"""

import multiprocessing as mp
import sys
import time
from pathlib import Path

import psutil

# Add common module to path
sys.path.insert(0, str(Path(__file__).parent))


def benchmark_delay_simulator(duration_sec: int = 5):
    """测试 DelaySimulator 的CPU使用率"""
    print("\n" + "=" * 60)
    print("Testing DelaySimulator (空循环模拟)")
    print("=" * 60)

    # 记录初始CPU使用率
    initial_cpu = psutil.cpu_percent(interval=1)
    print(f"Initial CPU: {initial_cpu}%")

    # 运行空循环模拟
    start = time.time()
    while time.time() - start < duration_sec:
        pass  # 空循环

    # 记录峰值CPU使用率
    peak_cpu = psutil.cpu_percent(interval=1)
    print(f"Peak CPU during simulation: {peak_cpu}%")
    print(f"Duration: {duration_sec}s")
    print(f"Result: {'❌ 几乎无CPU使用' if peak_cpu < 10 else '✅ 有CPU使用'}")

    return peak_cpu


def cpu_intensive_rerank_task(task_id: int):
    """单个CPU密集型重排序任务"""
    import numpy as np

    # 生成向量
    num_candidates = 500
    vector_dim = 1024

    query_vec = np.random.randn(vector_dim).astype(np.float32)
    query_vec = query_vec / np.linalg.norm(query_vec)

    candidate_vecs = np.random.randn(num_candidates, vector_dim).astype(np.float32)
    norms = np.linalg.norm(candidate_vecs, axis=1, keepdims=True)
    candidate_vecs = candidate_vecs / (norms + 1e-8)

    # 计算相似度
    similarities = np.dot(candidate_vecs, query_vec)

    # 排序
    top_indices = np.argsort(similarities)[::-1][:10]

    return task_id


def benchmark_cpu_intensive_reranker(duration_sec: int = 5, num_workers: int = 4):
    """测试 CPUIntensiveReranker 的CPU使用率"""
    print("\n" + "=" * 60)
    print(f"Testing CPUIntensiveReranker (真实向量计算, {num_workers} workers)")
    print("=" * 60)

    # 记录初始CPU使用率
    initial_cpu = psutil.cpu_percent(interval=1)
    print(f"Initial CPU: {initial_cpu}%")

    # 启动多进程执行CPU密集任务
    start = time.time()
    with mp.Pool(processes=num_workers) as pool:
        task_count = 0
        while time.time() - start < duration_sec:
            # 连续提交任务
            pool.apply_async(cpu_intensive_rerank_task, (task_count,))
            task_count += 1

        pool.close()
        pool.join()

    # 记录峰值CPU使用率
    peak_cpu = psutil.cpu_percent(interval=1)
    print(f"Peak CPU during computation: {peak_cpu}%")
    print(f"Duration: {duration_sec}s")
    print(f"Tasks completed: {task_count}")
    print(f"Result: {'✅ 真实CPU使用' if peak_cpu > 50 else '⚠️  CPU使用较低'}")

    return peak_cpu


def main():
    """主测试流程"""
    print("\n" + "🔬 " + "=" * 56 + " 🔬")
    print("   CPU密集型算子验证 - 资源争用效果对比")
    print("🔬 " + "=" * 56 + " 🔬")

    duration = 3  # 每个测试持续3秒
    num_workers = mp.cpu_count()

    # Test 1: DelaySimulator
    delay_cpu = benchmark_delay_simulator(duration)

    time.sleep(2)  # 等待系统恢复

    # Test 2: CPUIntensiveReranker
    intensive_cpu = benchmark_cpu_intensive_reranker(duration, num_workers)

    # 总结
    print("\n" + "=" * 60)
    print("📊 测试总结")
    print("=" * 60)
    print(
        f"DelaySimulator CPU使用率:          {delay_cpu:>6.1f}%  {'❌' if delay_cpu < 10 else '✅'}"
    )
    print(
        f"CPUIntensiveReranker CPU使用率:    {intensive_cpu:>6.1f}%  {'✅' if intensive_cpu > 50 else '⚠️'}"
    )
    print(f"CPU使用率提升:                     {intensive_cpu - delay_cpu:>6.1f}%")
    print()

    if intensive_cpu > delay_cpu * 5:
        print("✅ 验证通过: CPUIntensiveReranker产生显著的CPU资源争用")
        print("   适合用于调度器benchmark，结果更加可信。")
    else:
        print("⚠️  警告: CPU使用率提升不明显，可能需要调整参数")
        print("   建议: 增加 num_candidates 或 vector_dim")

    print("\n" + "=" * 60)
    print("💡 建议:")
    print("   - 使用 CPUIntensiveReranker 替代 DelaySimulator")
    print("   - 并发运行时会产生真实的资源竞争")
    print("   - 调度策略差异会更加明显")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    # 检查依赖
    try:
        import numpy
        import psutil
    except ImportError as e:
        print(f"❌ 缺少依赖: {e}")
        print("请安装: pip install numpy psutil")
        sys.exit(1)

    main()
