#!/usr/bin/env python3
"""
Ray Queue Actor 引用传递和并发测试

专门测试：
1. Ray队列在不同Actor之间的引用传递
2. Actor间的并发读写
3. Ray队列的分布式特性
4. 队列在Actor生命周期中的持久性
"""

import sys
import os
import time
import asyncio
from typing import List, Dict, Any, Optional

# 添加项目路径
sys.path.insert(0, '/api-rework')

try:
    from sage.runtime.communication.queue import (
        RayQueueDescriptor,
    )
    from sage.utils.ray_helper import ensure_ray_initialized
    print("✓ 成功导入Ray队列描述符")
except ImportError as e:
    print(f"✗ 导入失败: {e}")
    sys.exit(1)

try:
    import ray
    RAY_AVAILABLE = True
    print("✓ Ray 可用")
except ImportError:
    RAY_AVAILABLE = False
    print("✗ Ray 不可用")
    sys.exit(1)


# ============ Ray Actor 定义 ============

@ray.remote
class PersistentQueueActor:
    """持久化队列Actor - 维护队列描述符的引用"""
    
    def __init__(self, queue_desc_dict: Dict[str, Any], actor_name: str):
        """初始化Actor并建立队列连接"""
        self.actor_name = actor_name
        from sage.runtime.communication.queue import resolve_descriptor
        self.queue_desc = resolve_descriptor(queue_desc_dict)
        self.operations_count = 0
        self.last_operation_time = time.time()
        
        print(f"Actor {actor_name} initialized with queue {self.queue_desc.queue_id}")
    
    def get_queue_info(self):
        """获取队列信息"""
        return {
            "actor_name": self.actor_name,
            "queue_id": self.queue_desc.queue_id,
            "queue_type": self.queue_desc.queue_type,
            "operations_count": self.operations_count,
            "is_initialized": self.queue_desc.is_initialized(),
            "last_operation_time": self.last_operation_time
        }
    
    def put_items(self, items: List[str], delay_between_items: float = 0.0):
        """向队列放入多个项目"""
        results = []
        for item in items:
            try:
                enhanced_item = f"{self.actor_name}:{item}:{time.time()}"
                self.queue_desc.put(enhanced_item)
                results.append(f"put_success:{enhanced_item}")
                self.operations_count += 1
                self.last_operation_time = time.time()
                
                if delay_between_items > 0:
                    time.sleep(delay_between_items)
                    
            except Exception as e:
                results.append(f"put_error:{item}:{e}")
        
        return results
    
    def get_items(self, max_items: int, timeout_per_item: float = 1.0):
        """从队列获取多个项目"""
        results = []
        for i in range(max_items):
            try:
                item = self.queue_desc.get(timeout=timeout_per_item)
                results.append(f"get_success:{item}")
                self.operations_count += 1
                self.last_operation_time = time.time()
            except Exception as e:
                results.append(f"get_timeout_or_error:{e}")
                break
        
        return results
    
    def check_queue_status(self):
        """检查队列状态"""
        try:
            size = self.queue_desc.qsize()
            empty = self.queue_desc.empty()
            return {
                "size": size,
                "empty": empty,
                "operations_count": self.operations_count,
                "last_operation": self.last_operation_time
            }
        except Exception as e:
            return {"error": str(e)}
    
    def stress_test_operations(self, num_operations: int):
        """压力测试操作"""
        start_time = time.time()
        completed_ops = 0
        
        for i in range(num_operations):
            try:
                if i % 2 == 0:  # 写操作
                    item = f"stress_{self.actor_name}_{i}_{time.time()}"
                    self.queue_desc.put(item)
                else:  # 读操作
                    try:
                        item = self.queue_desc.get(timeout=0.1)
                    except:
                        # 队列空时跳过
                        pass
                completed_ops += 1
                self.operations_count += 1
            except Exception as e:
                break
        
        end_time = time.time()
        return {
            "completed_operations": completed_ops,
            "duration": end_time - start_time,
            "ops_per_second": completed_ops / (end_time - start_time) if end_time > start_time else 0
        }


@ray.remote
class QueueCoordinatorActor:
    """队列协调器Actor - 管理多个队列操作"""
    
    def __init__(self):
        self.managed_queues = {}
        self.coordination_log = []
    
    def register_queue(self, queue_name: str, queue_desc_dict: Dict[str, Any]):
        """注册一个队列"""
        from sage.runtime.communication.queue import resolve_descriptor
        queue_desc = resolve_descriptor(queue_desc_dict)
        self.managed_queues[queue_name] = queue_desc
        self.coordination_log.append(f"registered_queue:{queue_name}")
        return f"Queue {queue_name} registered"
    
    def coordinate_batch_operation(self, queue_name: str, operation: str, items: List[str]):
        """协调批量操作"""
        if queue_name not in self.managed_queues:
            return f"Queue {queue_name} not found"
        
        queue_desc = self.managed_queues[queue_name]
        results = []
        
        if operation == "put_batch":
            for item in items:
                try:
                    queue_desc.put(f"coordinator:{item}:{time.time()}")
                    results.append(f"success:{item}")
                except Exception as e:
                    results.append(f"error:{item}:{e}")
        
        elif operation == "get_batch":
            for i in range(len(items)):  # items作为计数使用
                try:
                    item = queue_desc.get(timeout=1.0)
                    results.append(f"success:{item}")
                except Exception as e:
                    results.append(f"timeout:{e}")
                    break
        
        self.coordination_log.append(f"coordinated:{operation}:{queue_name}:{len(results)}")
        return results
    
    def get_coordination_summary(self):
        """获取协调摘要"""
        queue_summaries = {}
        for name, queue_desc in self.managed_queues.items():
            try:
                queue_summaries[name] = {
                    "queue_id": queue_desc.queue_id,
                    "size": queue_desc.qsize(),
                    "empty": queue_desc.empty()
                }
            except Exception as e:
                queue_summaries[name] = {"error": str(e)}
        
        return {
            "managed_queues": queue_summaries,
            "coordination_log": self.coordination_log[-10:]  # 最近10条记录
        }


# ============ 测试类 ============

class TestRayQueueActorCommunication:
    """Ray队列Actor通信测试"""
    
    def setup_method(self):
        """测试设置"""
        ensure_ray_initialized()
        
        # 创建测试队列
        self.test_queue = RayQueueDescriptor(queue_id="test_ray_actor_comm", maxsize=1000)
        self.queue_dict = self.test_queue.to_dict()
    
    def tearDown(self):
        """测试清理"""
        # Ray会自动清理Actor，但我们可以显式关闭
        pass
    
    def test_basic_actor_queue_operations(self):
        """测试基础Actor队列操作"""
        print("\n=== 测试基础Actor队列操作 ===")
        
        # 创建两个Actor
        producer_actor = PersistentQueueActor.remote(self.queue_dict, "producer")
        consumer_actor = PersistentQueueActor.remote(self.queue_dict, "consumer")
        
        # 生产者放入数据
        items_to_produce = ["item1", "item2", "item3", "item4", "item5"]
        produce_result = ray.get(producer_actor.put_items.remote(items_to_produce))
        print(f"生产结果: {len(produce_result)} 项目")
        
        # 添加小延迟确保数据已写入
        time.sleep(0.1)
        
        # 检查队列状态
        producer_status = ray.get(producer_actor.check_queue_status.remote())
        print(f"生产后队列状态: {producer_status}")
        
        # 消费者获取数据
        consume_result = ray.get(consumer_actor.get_items.remote(len(items_to_produce), timeout_per_item=2.0))
        print(f"消费结果: {len(consume_result)} 项目")
        
        # 统计成功获取的项目数
        successful_gets = [r for r in consume_result if r.startswith("get_success")]
        print(f"成功获取的项目数: {len(successful_gets)}")
        
        # 检查Actor状态
        producer_info = ray.get(producer_actor.get_queue_info.remote())
        consumer_info = ray.get(consumer_actor.get_queue_info.remote())
        
        print(f"生产者状态: {producer_info}")
        print(f"消费者状态: {consumer_info}")
        
        # 验证断言
        assert producer_info['operations_count'] == len(items_to_produce), f"生产者应该执行了{len(items_to_produce)}次操作"
        assert len(successful_gets) > 0, f"消费者应该成功获取了一些项目，但实际获取了{len(successful_gets)}个"
        
        # 打印成功获取的项目
        for item in successful_gets:
            print(f"  成功获取: {item}")
        
        print("✓ 基础Actor队列操作测试通过")
    
    def test_multiple_actors_concurrent_access(self):
        """测试多个Actor并发访问同一队列"""
        print("\n=== 测试多Actor并发访问 ===")
        
        # 创建多个生产者和消费者Actor
        num_producers = 3
        num_consumers = 2
        items_per_producer = 8
        
        producers = []
        consumers = []
        
        # 创建生产者Actor
        for i in range(num_producers):
            actor = PersistentQueueActor.remote(self.queue_dict, f"producer_{i}")
            producers.append(actor)
        
        # 创建消费者Actor
        for i in range(num_consumers):
            actor = PersistentQueueActor.remote(self.queue_dict, f"consumer_{i}")
            consumers.append(actor)
        
        print(f"创建了 {num_producers} 个生产者Actor和 {num_consumers} 个消费者Actor")
        
        # 并发生产
        producer_futures = []
        for i, producer in enumerate(producers):
            items = [f"batch_{i}_item_{j}" for j in range(items_per_producer)]
            future = producer.put_items.remote(items, delay_between_items=0.01)
            producer_futures.append(future)
        
        # 等待生产完成
        producer_results = ray.get(producer_futures)
        total_produced = sum(len(result) for result in producer_results)
        print(f"总共生产: {total_produced} 项目")
        
        # 并发消费
        consumer_futures = []
        expected_per_consumer = total_produced // num_consumers
        for consumer in consumers:
            future = consumer.get_items.remote(expected_per_consumer, timeout_per_item=2.0)
            consumer_futures.append(future)
        
        # 等待消费完成
        consumer_results = ray.get(consumer_futures)
        total_consumed = sum(len([r for r in result if r.startswith("get_success")]) for result in consumer_results)
        print(f"总共消费: {total_consumed} 项目")
        
        # 检查最终状态
        queue_status_futures = [actor.check_queue_status.remote() for actor in producers + consumers]
        queue_statuses = ray.get(queue_status_futures)
        
        print("Actor队列状态:")
        for i, status in enumerate(queue_statuses):
            actor_type = "producer" if i < num_producers else "consumer"
            actor_id = i if i < num_producers else i - num_producers
            print(f"  {actor_type}_{actor_id}: {status}")
        
        assert total_produced > 0, "应该生产了一些项目"
        assert total_consumed > 0, "应该消费了一些项目"
        
        print("✓ 多Actor并发访问测试通过")
    
    def test_queue_coordinator_pattern(self):
        """测试队列协调器模式"""
        print("\n=== 测试队列协调器模式 ===")
        
        # 创建协调器
        coordinator = QueueCoordinatorActor.remote()
        
        # 注册队列
        register_result = ray.get(coordinator.register_queue.remote("main_queue", self.queue_dict))
        print(f"队列注册结果: {register_result}")
        
        # 通过协调器进行批量写入
        items_to_write = ["coord_item1", "coord_item2", "coord_item3", "coord_item4"]
        batch_put_result = ray.get(coordinator.coordinate_batch_operation.remote(
            "main_queue", "put_batch", items_to_write
        ))
        print(f"批量写入结果: {len(batch_put_result)} 项目")
        
        # 通过协调器进行批量读取
        batch_get_result = ray.get(coordinator.coordinate_batch_operation.remote(
            "main_queue", "get_batch", [""] * len(items_to_write)  # 占位符
        ))
        print(f"批量读取结果: {len(batch_get_result)} 项目")
        
        # 获取协调摘要
        summary = ray.get(coordinator.get_coordination_summary.remote())
        print(f"协调摘要: {summary}")
        
        assert len(batch_put_result) == len(items_to_write), "所有项目应该被写入"
        assert len(batch_get_result) > 0, "应该读取了一些项目"
        
        print("✓ 队列协调器模式测试通过")
    
    def test_actor_lifecycle_and_queue_persistence(self):
        """测试Actor生命周期和队列持久性"""
        print("\n=== 测试Actor生命周期和队列持久性 ===")
        
        # 第一阶段：创建Actor并写入数据
        phase1_actor = PersistentQueueActor.remote(self.queue_dict, "phase1_actor")
        phase1_items = ["persistent_item1", "persistent_item2", "persistent_item3"]
        
        put_result = ray.get(phase1_actor.put_items.remote(phase1_items))
        print(f"阶段1写入结果: {len(put_result)} 项目")
        
        # 获取Actor信息
        phase1_info = ray.get(phase1_actor.get_queue_info.remote())
        print(f"阶段1 Actor信息: {phase1_info}")
        
        # 第二阶段：创建新Actor并读取数据（模拟Actor重启）
        phase2_actor = PersistentQueueActor.remote(self.queue_dict, "phase2_actor")
        
        get_result = ray.get(phase2_actor.get_items.remote(len(phase1_items)))
        successful_gets = [r for r in get_result if r.startswith("get_success")]
        print(f"阶段2读取结果: {len(successful_gets)} 项目")
        
        # 验证数据持久性
        for item in successful_gets:
            print(f"  读取到: {item}")
        
        assert len(successful_gets) > 0, "新Actor应该能读取到之前写入的数据"
        
        print("✓ Actor生命周期和队列持久性测试通过")
    
    def test_concurrent_stress_with_actors(self):
        """Actor并发压力测试"""
        print("\n=== Actor并发压力测试 ===")
        
        num_actors = 5
        operations_per_actor = 100
        
        # 创建多个Actor进行压力测试
        stress_actors = []
        for i in range(num_actors):
            actor = PersistentQueueActor.remote(self.queue_dict, f"stress_actor_{i}")
            stress_actors.append(actor)
        
        print(f"创建 {num_actors} 个Actor，每个执行 {operations_per_actor} 个操作")
        
        # 启动压力测试
        start_time = time.time()
        stress_futures = []
        for actor in stress_actors:
            future = actor.stress_test_operations.remote(operations_per_actor)
            stress_futures.append(future)
        
        # 等待完成
        stress_results = ray.get(stress_futures)
        end_time = time.time()
        
        # 分析结果
        total_operations = sum(result['completed_operations'] for result in stress_results)
        total_duration = end_time - start_time
        overall_ops_per_sec = total_operations / total_duration if total_duration > 0 else 0
        
        print(f"压力测试结果:")
        print(f"  总操作数: {total_operations}")
        print(f"  总耗时: {total_duration:.2f}秒")
        print(f"  整体操作/秒: {overall_ops_per_sec:.2f}")
        
        for i, result in enumerate(stress_results):
            print(f"  Actor {i}: {result['completed_operations']} 操作, "
                  f"{result['ops_per_second']:.2f} ops/sec")
        
        assert total_operations > 0, "应该完成一些操作"
        
        print("✓ Actor并发压力测试通过")


def run_ray_actor_tests():
    """运行Ray Actor测试"""
    if not RAY_AVAILABLE:
        print("Ray不可用，跳过Ray Actor测试")
        return False
    
    print("开始运行Ray队列Actor通信测试...")
    
    test_suite = TestRayQueueActorCommunication()
    
    try:
        # 设置测试环境
        test_suite.setUp()
        
        # 运行所有测试
        test_suite.test_basic_actor_queue_operations()
        test_suite.test_multiple_actors_concurrent_access()
        test_suite.test_queue_coordinator_pattern()
        test_suite.test_actor_lifecycle_and_queue_persistence()
        test_suite.test_concurrent_stress_with_actors()
        
        # 清理测试环境
        test_suite.tearDown()
        
        print("\n🎉 所有Ray Actor测试通过！")
        return True
        
    except Exception as e:
        print(f"\n❌ Ray Actor测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # 确保Ray清理
        if ray.is_initialized():
            ray.shutdown()


if __name__ == "__main__":
    success = run_ray_actor_tests()
    if not success:
        sys.exit(1)
