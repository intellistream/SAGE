#!/usr/bin/env python3
"""
测试 Cache Miss Profiling 功能

使用方法:
    python test_cache_profiling.py
"""

import os
import sys

import numpy as np

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bench.cache_profiler import CacheProfiler, check_perf_availability


def test_basic_profiling():
    """测试基本的 cache profiling 功能"""
    print("\n" + "=" * 80)
    print("测试 1: 基本 Cache Profiling 功能")
    print("=" * 80)

    # 检查可用性
    is_available, message = check_perf_availability()
    print(f"\n{message}\n")

    if not is_available:
        print("✗ Perf 不可用，跳过测试")
        return False

    # 创建 profiler
    profiler = CacheProfiler()

    # 启动监测
    if not profiler.start():
        print("✗ 启动 profiler 失败")
        return False

    print("✓ Profiler 已启动")

    # 模拟一些计算密集型操作（产生 cache miss）
    print("  执行工作负载...")

    # 创建大数组进行矩阵运算（会产生大量 cache miss）
    size = 10000
    data = np.random.rand(size, 128).astype(np.float32)
    result = np.dot(data, data.T)

    # 再做一些随机访问（更多 cache miss）
    indices = np.random.randint(0, size, size=5000)
    _ = data[indices]

    print("  工作负载完成")

    # 停止监测
    stats = profiler.stop()

    if stats is None:
        print("✗ 获取统计数据失败")
        return False

    print("✓ Profiler 已停止\n")

    # 显示结果
    print("Cache Miss 统计:")
    print(f"  监测时长: {stats.duration_seconds:.2f} 秒")
    print(f"  Cache misses: {stats.cache_misses:,}")
    print(f"  Cache references: {stats.cache_references:,}")
    print(f"  Cache miss rate: {stats.cache_miss_rate:.2%}")
    print(f"  L1 D-cache loads: {stats.l1_dcache_loads:,}")
    print(f"  L1 D-cache load misses: {stats.l1_dcache_load_misses:,}")
    print(f"  LLC loads: {stats.llc_loads:,}")
    print(f"  LLC load misses: {stats.llc_load_misses:,}")
    print(f"  Instructions: {stats.instructions:,}")
    print(f"  Cycles: {stats.cycles:,}")

    # 验证数据
    if stats.cache_misses == 0 and stats.cache_references == 0:
        print("\n⚠️  警告: Cache 统计数据全为 0，可能是以下原因:")
        print("  1. 在虚拟机或容器中运行（不支持硬件性能计数器）")
        print("  2. perf 权限配置不正确")
        print("  3. 工作负载太轻，采样数据不足")
        return False

    print("\n✓ 测试通过")
    return True


def test_context_manager():
    """测试上下文管理器用法"""
    print("\n" + "=" * 80)
    print("测试 2: 上下文管理器用法")
    print("=" * 80 + "\n")

    is_available, _ = check_perf_availability()
    if not is_available:
        print("✗ Perf 不可用，跳过测试")
        return False

    try:
        with CacheProfiler() as profiler:
            print("✓ 进入上下文管理器")

            # 执行一些工作
            data = np.random.rand(5000, 64).astype(np.float32)
            _ = np.dot(data, data.T)

            print("✓ 工作负载完成")

        print("✓ 退出上下文管理器（自动停止）")
        print("✓ 测试通过")
        return True

    except Exception as e:
        print(f"✗ 测试失败: {e}")
        return False


def test_multiple_rounds():
    """测试多轮监测"""
    print("\n" + "=" * 80)
    print("测试 3: 多轮监测")
    print("=" * 80 + "\n")

    is_available, _ = check_perf_availability()
    if not is_available:
        print("✗ Perf 不可用，跳过测试")
        return False

    profiler = CacheProfiler()
    all_stats = []

    for round_idx in range(3):
        print(f"第 {round_idx + 1} 轮监测:")

        if not profiler.start():
            print("  ✗ 启动失败")
            return False

        # 不同大小的工作负载
        size = 1000 * (round_idx + 1)
        data = np.random.rand(size, 32).astype(np.float32)
        _ = np.dot(data, data.T)

        stats = profiler.stop()
        if stats:
            all_stats.append(stats)
            print(f"  Cache misses: {stats.cache_misses:,}")
            print(f"  Cache miss rate: {stats.cache_miss_rate:.2%}")
        else:
            print("  ✗ 获取统计失败")
            return False

    print(f"\n✓ 完成 {len(all_stats)} 轮监测")

    # 验证趋势（工作负载越大，cache miss 应该越多）
    if len(all_stats) >= 2:
        if all_stats[0].cache_misses > 0 and all_stats[-1].cache_misses > all_stats[0].cache_misses:
            print("✓ Cache miss 趋势符合预期")
        else:
            print("⚠️  警告: Cache miss 趋势不符合预期，可能是环境问题")

    print("✓ 测试通过")
    return True


def main():
    """运行所有测试"""
    print("\n" + "=" * 80)
    print("Cache Miss Profiling 功能测试")
    print("=" * 80)

    tests = [
        ("基本功能测试", test_basic_profiling),
        ("上下文管理器测试", test_context_manager),
        ("多轮监测测试", test_multiple_rounds),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ {name} 异常: {e}")
            import traceback

            traceback.print_exc()
            results.append((name, False))

    # 总结
    print("\n" + "=" * 80)
    print("测试总结")
    print("=" * 80)

    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{status}: {name}")

    passed = sum(1 for _, r in results if r)
    total = len(results)
    print(f"\n总计: {passed}/{total} 测试通过")

    if passed == total:
        print("\n🎉 所有测试通过!")
        return 0
    else:
        print("\n⚠️  部分测试失败，请检查 perf 配置")
        return 1


if __name__ == "__main__":
    sys.exit(main())
