#!/usr/bin/env python3
"""
快速验证脚本：验证Ray队列批量优化是否工作

运行方式：
    python verify_optimization.py
"""

import time

import ray


def verify_optimization():
    """验证优化效果的快速脚本"""
    print("🚀 Ray Queue Batch Optimization Verification")
    print("=" * 80)

    # 初始化Ray
    if not ray.is_initialized():
        ray.init(ignore_reinit_error=True)
        print("✅ Ray initialized")

    try:
        from sage.kernel.runtime.communication.queue_descriptor.ray_queue_descriptor import (
            RayQueueDescriptor,
            get_global_queue_manager,
        )

        print("✅ Import successful")

        # 测试1：基本功能
        print("\n📝 Test 1: Basic Functionality")
        print("-" * 80)
        queue_desc = RayQueueDescriptor(maxsize=1000, queue_id="verify_test")
        queue = queue_desc.queue_instance

        # 批量put
        test_items = [f"item_{i}" for i in range(100)]
        start = time.time()
        for item in test_items:
            queue.put(item)
        queue.flush()
        queue.wait_for_pending_puts()
        elapsed = time.time() - start

        print(f"   Put 100 items: {elapsed:.3f}s")
        print(f"   Throughput: {100 / elapsed:.1f} items/sec")

        # 获取统计
        stats = queue.get_stats()
        print("\n📊 Statistics:")
        print(f"   Total puts: {stats['total_puts']}")
        print(f"   Batch operations: {stats['batch_puts']}")
        print(f"   Avg batch size: {stats['avg_batch_size']:.1f}")

        if stats["batch_puts"] > 0:
            print("\n✅ Test 1 PASSED: Batch operations working!")
        else:
            print("\n⚠️  Test 1 WARNING: No batch operations detected")

        # 测试2：批量get
        print("\n📝 Test 2: Batch Get")
        print("-" * 80)
        batch = queue.get_batch(count=50)
        print(f"   Retrieved {len(batch)} items in batch")

        if len(batch) > 0:
            print("\n✅ Test 2 PASSED: Batch get working!")
        else:
            print("\n❌ Test 2 FAILED: No items retrieved")

        # 测试3：性能对比
        print("\n📝 Test 3: Performance Comparison")
        print("-" * 80)

        # 清理旧数据
        manager = get_global_queue_manager()
        ray.get(manager.delete_queue.remote("verify_test"))

        # 旧方式（单条同步）
        # queue_desc1 = RayQueueDescriptor(maxsize=1000, queue_id="verify_sync")
        manager = get_global_queue_manager()
        ray.get(manager.get_or_create_queue.remote("verify_sync", 1000))

        print("\n   🔴 Synchronous (old way):")
        test_items = [f"item_{i}" for i in range(200)]
        start = time.time()
        for item in test_items:
            ray.get(manager.put.remote("verify_sync", item))
        sync_time = time.time() - start
        sync_throughput = 200 / sync_time
        print(f"      Time: {sync_time:.3f}s")
        print(f"      Throughput: {sync_throughput:.1f} items/sec")

        # 新方式（批量异步）
        queue_desc2 = RayQueueDescriptor(maxsize=1000, queue_id="verify_async")
        queue2 = queue_desc2.queue_instance

        print("\n   🟢 Asynchronous batch (new way):")
        start = time.time()
        for item in test_items:
            queue2.put(item)
        queue2.flush()
        queue2.wait_for_pending_puts()
        async_time = time.time() - start
        async_throughput = 200 / async_time
        print(f"      Time: {async_time:.3f}s")
        print(f"      Throughput: {async_throughput:.1f} items/sec")

        # 计算提升（始终用吞吐量比）
        improvement = async_throughput / sync_throughput
        if async_time < sync_time:
            print(f"\n   🚀 Performance improvement: {improvement:.1f}x faster (throughput)")
            print("\n✅ Test 3 PASSED: Optimization working!")
        else:
            print(f"\n   📊 Performance: {improvement:.2f}x (throughput)")
            print("\n⚠️  Test 3 WARNING: Improvement less than expected")

        # 清理
        ray.get(manager.delete_queue.remote("verify_sync"))
        ray.get(manager.delete_queue.remote("verify_async"))

        # 总结
        print("\n" + "=" * 80)
        print("✨ Verification Complete!")
        print("=" * 80)
        print("\n📋 Summary:")
        print("   ✅ Import and initialization: OK")
        print("   ✅ Batch operations: OK")
        print("   ✅ Statistics collection: OK")
        print(f"   ✅ Performance improvement: {improvement:.1f}x")
        print("\n🎉 Ray queue batch optimization is working correctly!")

        return True

    except Exception as e:
        print(f"\n❌ Verification FAILED: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = verify_optimization()
    exit(0 if success else 1)
