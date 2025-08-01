#!/usr/bin/env python3
"""
测试统一多态队列描述符 (QueueDescriptor) 的功能

展示以下特性：
1. 直接调用队列方法（多态接口）
2. 懒加载内部队列实例
3. 序列化支持（自动过滤不可序列化对象）
4. 跨进程传递描述符信息
"""

import json
import queue
import time
from typing import Any

# 导入我们的统一队列描述符
from sage.runtime.communication.queue_descriptor import (
    QueueDescriptor,
    register_queue_implementation,
    create_queue_pool,
    serialize_queue_pool,
    deserialize_queue_pool
)


class MockLocalQueue:
    """模拟本地队列实现"""
    def __init__(self, maxsize=0):
        self._queue = queue.Queue(maxsize=maxsize)
    
    def put(self, item: Any, block: bool = True, timeout: float = None) -> None:
        return self._queue.put(item, block, timeout)
    
    def get(self, block: bool = True, timeout: float = None) -> Any:
        return self._queue.get(block, timeout)
    
    def empty(self) -> bool:
        return self._queue.empty()
    
    def qsize(self) -> int:
        return self._queue.qsize()
    
    def full(self) -> bool:
        return self._queue.full()


class MockQueueStub:
    """模拟队列存根实现"""
    def __init__(self, descriptor):
        self.descriptor = descriptor
        maxsize = descriptor.metadata.get('maxsize', 0)
        self._queue = MockLocalQueue(maxsize)
    
    def put(self, item: Any, block: bool = True, timeout: float = None) -> None:
        print(f"[{self.descriptor.queue_type}] Putting item: {item}")
        return self._queue.put(item, block, timeout)
    
    def get(self, block: bool = True, timeout: float = None) -> Any:
        item = self._queue.get(block, timeout)
        print(f"[{self.descriptor.queue_type}] Got item: {item}")
        return item
    
    def empty(self) -> bool:
        return self._queue.empty()
    
    def qsize(self) -> int:
        return self._queue.qsize()


def test_basic_functionality():
    """测试基本功能"""
    print("=== 测试基本功能 ===")
    
    # 创建本地队列描述符
    desc = QueueDescriptor.create_local_queue("test_local", maxsize=10)
    print(f"创建队列描述符: {desc}")
    
    # 检查序列化状态
    print(f"可序列化: {desc.can_serialize}")
    print(f"已初始化: {desc.is_initialized()}")
    
    # 注册队列实现（用于回退机制）
    register_queue_implementation("local", MockQueueStub)
    
    # 直接使用队列接口（多态）
    print("\n--- 直接使用队列接口 ---")
    desc.put("Hello")
    desc.put("World")
    print(f"队列大小: {desc.qsize()}")
    print(f"队列为空: {desc.empty()}")
    
    # 获取项目
    item1 = desc.get()
    item2 = desc.get()
    print(f"获取到: {item1}, {item2}")
    print(f"队列为空: {desc.empty()}")
    
    print(f"初始化后状态: {desc.is_initialized()}")


def test_serialization():
    """测试序列化功能"""
    print("\n=== 测试序列化功能 ===")
    
    # 创建可序列化的描述符
    desc1 = QueueDescriptor.create_shm_queue("test_shm", "shared_queue_1", maxsize=100)
    print(f"原始描述符: {desc1}")
    
    # 序列化为JSON
    json_str = desc1.to_json()
    print(f"序列化结果: {json_str}")
    
    # 反序列化
    desc2 = QueueDescriptor.from_json(json_str)
    print(f"反序列化描述符: {desc2}")
    
    # 验证相等性
    print(f"描述符相等: {desc1 == desc2}")


def test_non_serializable_handling():
    """测试不可序列化对象的处理"""
    print("\n=== 测试不可序列化对象处理 ===")
    
    # 创建包含实际队列对象的本地描述符
    real_queue = MockLocalQueue(maxsize=5)
    desc = QueueDescriptor.create_local_queue("test_with_queue", queue_instance=real_queue)
    
    print(f"包含队列实例的描述符: {desc}")
    print(f"可序列化: {desc.can_serialize}")
    
    # 尝试序列化（应该失败）
    try:
        desc.to_json()
        print("❌ 序列化应该失败但成功了")
    except ValueError as e:
        print(f"✅ 预期的序列化失败: {e}")
    
    # 转换为可序列化的描述符
    serializable_desc = desc.to_serializable_descriptor()
    print(f"可序列化版本: {serializable_desc}")
    print(f"可序列化: {serializable_desc.can_serialize}")
    
    # 现在可以序列化了
    json_str = serializable_desc.to_json()
    print(f"序列化成功: {len(json_str)} 字符")


def test_lazy_loading():
    """测试懒加载功能"""
    print("\n=== 测试懒加载功能 ===")
    
    # 注册队列实现
    register_queue_implementation("ray_actor", MockQueueStub)
    
    # 创建Ray Actor队列描述符（懒加载）
    desc = QueueDescriptor.create_ray_actor_queue("test_actor", "ray_queue_1")
    print(f"创建懒加载描述符: {desc}")
    print(f"已初始化: {desc.is_initialized()}")
    
    # 第一次使用时才初始化
    print("\n--- 第一次使用队列 ---")
    desc.put("Lazy Item")
    print(f"使用后已初始化: {desc.is_initialized()}")
    
    # 清除缓存
    desc.clear_cache()
    print(f"清除缓存后已初始化: {desc.is_initialized()}")
    
    # 再次使用会重新初始化
    size = desc.qsize()
    print(f"再次使用后队列大小: {size}")
    print(f"重新初始化: {desc.is_initialized()}")


def test_queue_pool():
    """测试队列池功能"""
    print("\n=== 测试队列池功能 ===")
    
    # 定义队列配置
    queue_configs = [
        {"type": "local", "maxsize": 10},
        {"type": "shm", "shm_name": "shared_queue", "maxsize": 100},
        {"type": "ray_actor", "actor_name": "worker_actor", "maxsize": 50},
    ]
    
    # 创建队列池
    pool = create_queue_pool(queue_configs, "test_pool")
    print(f"创建队列池，包含 {len(pool)} 个队列:")
    for queue_id, desc in pool.items():
        print(f"  - {queue_id}: {desc}")
    
    # 序列化队列池
    pool_json = serialize_queue_pool(pool)
    print(f"\n序列化队列池: {len(pool_json)} 字符")
    
    # 反序列化队列池
    restored_pool = deserialize_queue_pool(pool_json)
    print(f"恢复队列池，包含 {len(restored_pool)} 个队列:")
    for queue_id, desc in restored_pool.items():
        print(f"  - {queue_id}: {desc}")


def test_polymorphic_usage():
    """测试多态使用"""
    print("\n=== 测试多态使用 ===")
    
    # 注册不同类型的队列实现
    register_queue_implementation("shm", MockQueueStub)
    register_queue_implementation("rpc", MockQueueStub)
    
    # 创建不同类型的队列描述符
    queues = [
        QueueDescriptor.create_local_queue("poly_local"),
        QueueDescriptor.create_shm_queue("test_shm", "poly_shm"),
        QueueDescriptor.create_rpc_queue("localhost", 8080, "poly_rpc")
    ]
    
    # 多态使用 - 所有队列都实现了相同的接口
    print("--- 多态操作不同类型的队列 ---")
    for i, q in enumerate(queues):
        print(f"\n操作 {q.queue_type} 队列:")
        q.put(f"Message_{i}")
        q.put(f"Data_{i}")
        
        print(f"  队列大小: {q.qsize()}")
        print(f"  获取项目: {q.get()}")
        print(f"  剩余大小: {q.qsize()}")


def test_cloning():
    """测试克隆功能"""
    print("\n=== 测试克隆功能 ===")
    
    # 创建原始描述符
    original = QueueDescriptor.create_sage_queue(
        "original_sage",
        maxsize=200,
        auto_cleanup=True,
        namespace="test_ns"
    )
    print(f"原始描述符: {original}")
    
    # 克隆描述符
    cloned = original.clone("cloned_sage")
    print(f"克隆描述符: {cloned}")
    
    # 验证克隆结果
    print(f"ID相同: {original.queue_id == cloned.queue_id}")
    print(f"类型相同: {original.queue_type == cloned.queue_type}")
    print(f"元数据相同: {original.metadata == cloned.metadata}")
    print(f"克隆版本可序列化: {cloned.can_serialize}")


def main():
    """主测试函数"""
    print("🚀 统一多态队列描述符测试")
    print("=" * 50)
    
    try:
        test_basic_functionality()
        test_serialization()
        test_non_serializable_handling()
        test_lazy_loading()
        test_queue_pool()
        test_polymorphic_usage()
        test_cloning()
        
        print("\n" + "=" * 50)
        print("✅ 所有测试完成！")
        
    except Exception as e:
        print(f"\n❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
