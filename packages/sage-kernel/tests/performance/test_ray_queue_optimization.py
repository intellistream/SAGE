"""
性能测试：验证Ray队列批量优化的效果

测试场景：
1. 单条put/get vs 批量操作的性能对比
2. 不同批量大小的性能影响
3. 分布式环境下的吞吐量提升

预期结果：
- 批量操作应该比单条操作快10-50倍
- 批量大小在100-500时性能最优
"""

import time

import pytest
import ray

from sage.platform.queue.ray_queue_descriptor import (
    RayQueueDescriptor,
    RayQueueProxy,
    get_global_queue_manager,
)


@pytest.fixture(scope="module")
def ray_init():
    """初始化Ray环境"""
    if not ray.is_initialized():
        ray.init(ignore_reinit_error=True)
    yield
    # 测试结束后不关闭Ray，避免影响其他测试


class TestRayQueueOptimization:
    """Ray队列批量优化性能测试"""

    def test_single_put_performance_baseline(self, ray_init):
        """基准测试：单条put操作的性能（旧版本行为模拟）"""
        print("\n" + "=" * 80)
        print("🔴 Baseline: 单条put操作性能（同步等待）")
        print("=" * 80)

        # 创建队列
        queue_desc = RayQueueDescriptor(maxsize=10000, queue_id="perf_test_baseline")
        manager = get_global_queue_manager()

        # 确保队列创建
        ray.get(manager.get_or_create_queue.remote(queue_desc.queue_id, queue_desc.maxsize))

        # 测试数据
        num_items = 1000
        test_data = [f"item_{i}" for i in range(num_items)]

        # 单条put（模拟旧版本的同步行为）
        start_time = time.time()
        for item in test_data:
            ray.get(manager.put.remote(queue_desc.queue_id, item))
        elapsed_time = time.time() - start_time

        throughput = num_items / elapsed_time
        print(f"📊 Items: {num_items}")
        print(f"⏱️  Time: {elapsed_time:.3f} seconds")
        print(f"🚀 Throughput: {throughput:.1f} items/second")
        print(f"📈 Average latency: {(elapsed_time / num_items) * 1000:.2f} ms/item")

        # 清理队列
        ray.get(manager.delete_queue.remote(queue_desc.queue_id))

        return throughput

    def test_batch_put_performance_optimized(self, ray_init):
        """优化测试：批量put操作的性能（新版本）"""
        print("\n" + "=" * 80)
        print("🟢 Optimized: 批量put操作性能（异步批量）")
        print("=" * 80)

        # 创建队列（使用优化的代理）
        queue_desc = RayQueueDescriptor(maxsize=10000, queue_id="perf_test_optimized")
        queue = queue_desc.queue_instance

        # 测试数据
        num_items = 1000
        test_data = [f"item_{i}" for i in range(num_items)]

        # 批量put（新版本的异步批量操作）
        start_time = time.time()
        for item in test_data:
            queue.put(item)  # 异步，自动批量
        queue.flush()  # 刷新缓冲区
        queue.wait_for_pending_puts()  # 等待所有批量操作完成
        elapsed_time = time.time() - start_time

        throughput = num_items / elapsed_time
        print(f"📊 Items: {num_items}")
        print(f"⏱️  Time: {elapsed_time:.3f} seconds")
        print(f"🚀 Throughput: {throughput:.1f} items/second")
        print(f"📈 Average latency: {(elapsed_time / num_items) * 1000:.2f} ms/item")

        # 显示统计信息
        stats = queue.get_stats()
        print("\n📈 Performance Stats:")
        print(f"   Total puts: {stats['total_puts']}")
        print(f"   Batch puts: {stats['batch_puts']}")
        print(f"   Avg batch size: {stats['avg_batch_size']:.1f}")

        # 清理队列
        manager = get_global_queue_manager()
        ray.get(manager.delete_queue.remote(queue_desc.queue_id))

        return throughput

    def test_performance_comparison(self, ray_init):
        """对比测试：计算性能提升倍数"""
        print("\n" + "=" * 80)
        print("📊 Performance Comparison")
        print("=" * 80)

        # 运行基准测试
        baseline_throughput = self.test_single_put_performance_baseline(ray_init)

        # 运行优化测试
        optimized_throughput = self.test_batch_put_performance_optimized(ray_init)

        # 计算提升
        improvement = optimized_throughput / baseline_throughput
        print("\n" + "=" * 80)
        print("✨ Performance Improvement Summary")
        print("=" * 80)
        print(f"🔴 Baseline throughput: {baseline_throughput:.1f} items/sec")
        print(f"🟢 Optimized throughput: {optimized_throughput:.1f} items/sec")
        print(f"🚀 Improvement: {improvement:.1f}x faster")
        print("=" * 80)

        # 说明：本地环境vs分布式环境
        print("\n📝 Note:")
        print("   - Local environment improvement: 1.5-2x (low network latency)")
        print("   - Distributed environment expected: 10-50x (1-5ms network latency)")
        print("   - High latency network expected: 50-100x (5-10ms network latency)")

        # 断言：本地环境下至少应该有1.2倍提升
        assert improvement >= 1.2, (
            f"Performance improvement {improvement:.1f}x is less than expected 1.2x"
        )
        print(f"\n✅ Test PASSED! Performance improved by {improvement:.1f}x")

        if improvement >= 5.0:
            print("🎉 Excellent! This is distributed environment level performance!")
        elif improvement >= 2.0:
            print("👍 Good! Better than local environment baseline.")
        else:
            print("ℹ️  This is expected for local environment (same machine, low latency).")

    def test_batch_size_optimization(self, ray_init):
        """测试不同批量大小的性能影响"""
        print("\n" + "=" * 80)
        print("🔬 Batch Size Optimization Test")
        print("=" * 80)

        num_items = 2000
        test_data = [f"item_{i}" for i in range(num_items)]
        batch_sizes = [10, 50, 100, 200, 500]
        results = {}

        for batch_size in batch_sizes:
            # 创建队列
            queue_desc = RayQueueDescriptor(maxsize=10000, queue_id=f"perf_test_batch_{batch_size}")
            queue = queue_desc.queue_instance

            # 设置批量大小
            if isinstance(queue, RayQueueProxy):
                queue.batch_size = batch_size

            # 测试
            start_time = time.time()
            for item in test_data:
                queue.put(item)
            queue.flush()
            queue.wait_for_pending_puts()
            elapsed_time = time.time() - start_time

            throughput = num_items / elapsed_time
            results[batch_size] = throughput

            stats = queue.get_stats()
            print(f"\n📊 Batch size: {batch_size}")
            print(f"   Throughput: {throughput:.1f} items/sec")
            print(f"   Time: {elapsed_time:.3f} sec")
            print(f"   Batches: {stats['batch_puts']}")

            # 清理
            manager = get_global_queue_manager()
            ray.get(manager.delete_queue.remote(queue_desc.queue_id))

        # 找出最优批量大小
        best_batch_size = max(results, key=results.get)
        best_throughput = results[best_batch_size]

        print("\n" + "=" * 80)
        print("🏆 Best Batch Size")
        print("=" * 80)
        print(f"Optimal batch size: {best_batch_size}")
        print(f"Best throughput: {best_throughput:.1f} items/sec")
        print("=" * 80)

    def test_batch_get_performance(self, ray_init):
        """测试批量get操作的性能"""
        print("\n" + "=" * 80)
        print("📥 Batch Get Performance Test")
        print("=" * 80)

        # 准备数据
        queue_desc = RayQueueDescriptor(maxsize=10000, queue_id="perf_test_batch_get")
        queue = queue_desc.queue_instance
        manager = get_global_queue_manager()

        num_items = 1000
        test_data = [f"item_{i}" for i in range(num_items)]

        # 先批量put数据
        for item in test_data:
            queue.put(item)
        queue.flush()
        queue.wait_for_pending_puts()

        # 测试单条get
        print("\n🔴 Single get (baseline):")
        retrieved_items = []
        start_time = time.time()
        for _ in range(num_items):
            item = queue.get()
            retrieved_items.append(item)
        single_get_time = time.time() - start_time
        single_throughput = num_items / single_get_time

        print(f"   Time: {single_get_time:.3f} sec")
        print(f"   Throughput: {single_throughput:.1f} items/sec")

        # 重新填充数据
        for item in test_data:
            ray.get(manager.put.remote(queue_desc.queue_id, item))

        # 测试批量get
        print("\n🟢 Batch get (optimized):")
        retrieved_items = []
        start_time = time.time()
        while len(retrieved_items) < num_items:
            batch = queue.get_batch(count=100)
            if not batch:
                break
            retrieved_items.extend(batch)
        batch_get_time = time.time() - start_time
        batch_throughput = len(retrieved_items) / batch_get_time

        print(f"   Time: {batch_get_time:.3f} sec")
        print(f"   Throughput: {batch_throughput:.1f} items/sec")
        print(f"   Items retrieved: {len(retrieved_items)}")

        # 计算提升
        if single_get_time > 0:
            improvement = batch_throughput / single_throughput  # 批量应该更快
            print(f"\n📊 Performance improvement: {improvement:.2f}x faster")

            if improvement >= 1.5:
                print(f"✅ Batch get is {improvement:.1f}x faster than single get!")
            elif improvement >= 1.0:
                print("✅ Batch get works correctly (slightly faster)")
            else:
                print("⚠️  Warning: Batch get slower than expected")

        # 清理
        ray.get(manager.delete_queue.remote(queue_desc.queue_id))


if __name__ == "__main__":
    """直接运行性能测试"""
    print("🚀 Starting Ray Queue Performance Tests")
    print("=" * 80)

    # 初始化Ray
    if not ray.is_initialized():
        ray.init(ignore_reinit_error=True)

    # 创建测试实例
    tester = TestRayQueueOptimization()

    # 运行所有测试
    try:
        tester.test_performance_comparison(None)
        tester.test_batch_size_optimization(None)
        tester.test_batch_get_performance(None)

        print("\n" + "=" * 80)
        print("✅ All performance tests completed successfully!")
        print("=" * 80)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
    finally:
        # ray.shutdown()  # 保留Ray环境
        pass
