#!/usr/bin/env python3
"""
统一多态队列描述符使用示例

演示 UnifiedQueueDescriptor 的主要特性:
1. 多态接口 - 统一的队列操作方法
2. 懒加载 - 按需初始化队列实例
3. 序列化支持 - 跨进程传递描述符
4. 类型安全 - 自动处理不可序列化对象
"""

import json
import time
import pickle
from typing import List

from sage.runtime.communication.queue_descriptor import (
    UnifiedQueueDescriptor,
    QueueDescriptor,  # 向后兼容别名
    register_queue_implementation,
    create_queue_pool,
    serialize_queue_pool,
    deserialize_queue_pool
)


def example_1_polymorphic_interface():
    """示例1: 多态接口 - 统一的队列操作"""
    print("📚 示例1: 多态接口")
    print("-" * 40)
    
    # 创建不同类型的队列描述符
    queues = [
        UnifiedQueueDescriptor.create_local_queue("demo_local", maxsize=5),
        UnifiedQueueDescriptor.create_shm_queue("shared_mem", "demo_shm", maxsize=10),
        UnifiedQueueDescriptor.create_ray_actor_queue("worker_actor", "demo_ray"),
        UnifiedQueueDescriptor.create_rpc_queue("localhost", 8080, "demo_rpc"),
        UnifiedQueueDescriptor.create_sage_queue("demo_sage", maxsize=20)
    ]
    
    # 统一的多态操作
    for queue in queues:
        print(f"\n处理队列: {queue}")
        
        # 所有队列都实现相同的接口
        print(f"  - 初始状态: 空={queue.empty()}, 大小={queue.qsize()}")
        
        # 无需关心具体类型，统一调用put/get方法
        try:
            queue.put(f"Hello from {queue.queue_type}")
            queue.put(f"Message {time.time()}")
            
            print(f"  - 添加后: 空={queue.empty()}, 大小={queue.qsize()}")
            
            item = queue.get()
            print(f"  - 获取项目: {item}")
            print(f"  - 获取后: 空={queue.empty()}, 大小={queue.qsize()}")
            
        except Exception as e:
            print(f"  - 操作失败: {e}")


def example_2_lazy_loading():
    """示例2: 懒加载 - 按需初始化"""
    print("\n\n🔄 示例2: 懒加载机制")
    print("-" * 40)
    
    # 创建队列描述符（此时不会创建实际队列）
    desc = UnifiedQueueDescriptor.create_ray_queue("lazy_demo")
    print(f"创建描述符: {desc}")
    print(f"已初始化: {desc.is_initialized()}")  # False
    
    # 第一次使用时才会初始化队列
    print("\n第一次使用...")
    desc.put("First item")
    print(f"使用后已初始化: {desc.is_initialized()}")  # True
    
    # 可以清除缓存强制重新初始化
    print("\n清除缓存...")
    desc.clear_cache()
    print(f"清除后已初始化: {desc.is_initialized()}")  # False
    
    # 再次使用会重新初始化
    print("再次使用...")
    size = desc.qsize()
    print(f"队列大小: {size}")
    print(f"重新初始化: {desc.is_initialized()}")  # True


def example_3_serialization():
    """示例3: 序列化支持 - 跨进程传递"""
    print("\n\n💾 示例3: 序列化支持")
    print("-" * 40)
    
    # 创建可序列化的描述符
    original = UnifiedQueueDescriptor.create_shm_queue(
        "demo_shared", "serialization_demo", 
        maxsize=100
    )
    
    print(f"原始描述符: {original}")
    print(f"可序列化: {original.can_serialize}")
    
    # JSON序列化
    print("\n--- JSON序列化 ---")
    json_str = original.to_json()
    print(f"JSON长度: {len(json_str)} 字符")
    print(f"JSON内容: {json_str}")
    
    # 反序列化
    restored = UnifiedQueueDescriptor.from_json(json_str)
    print(f"恢复的描述符: {restored}")
    print(f"描述符相等: {original == restored}")
    
    # Pickle序列化 (用于更复杂的跨进程场景)
    print("\n--- Pickle序列化 ---")
    pickled_data = pickle.dumps(original.to_dict())
    unpickled_dict = pickle.loads(pickled_data)
    restored_from_pickle = UnifiedQueueDescriptor.from_dict(unpickled_dict)
    print(f"Pickle恢复: {restored_from_pickle}")


def example_4_non_serializable_handling():
    """示例4: 不可序列化对象处理"""
    print("\n\n🚫 示例4: 不可序列化对象处理")
    print("-" * 40)
    
    # 模拟一个不可序列化的队列对象
    class MockQueue:
        def __init__(self):
            self.items = []
        def put(self, item): self.items.append(item)
        def get(self): return self.items.pop(0) if self.items else None
        def empty(self): return len(self.items) == 0
        def qsize(self): return len(self.items)
    
    # 创建包含实际队列对象的描述符（不可序列化）
    real_queue = MockQueue()
    desc_with_queue = UnifiedQueueDescriptor.create_local_queue(
        "non_serializable_demo",
        queue_instance=real_queue
    )
    
    print(f"包含队列实例的描述符: {desc_with_queue}")
    print(f"可序列化: {desc_with_queue.can_serialize}")
    
    # 尝试序列化会失败
    try:
        desc_with_queue.to_json()
        print("❌ 意外成功序列化")
    except ValueError as e:
        print(f"✅ 预期的序列化失败: {e}")
    
    # 转换为可序列化版本
    print("\n转换为可序列化版本...")
    serializable_version = desc_with_queue.to_serializable_descriptor()
    print(f"可序列化版本: {serializable_version}")
    print(f"现在可序列化: {serializable_version.can_serialize}")
    
    # 现在可以成功序列化
    json_data = serializable_version.to_json()
    print(f"序列化成功: {len(json_data)} 字符")


def example_5_queue_pools():
    """示例5: 队列池管理"""
    print("\n\n🏊 示例5: 队列池管理")
    print("-" * 40)
    
    # 定义队列池配置
    pool_config = [
        {"type": "local", "maxsize": 10, "queue_id": "worker_1"},
        {"type": "shm", "shm_name": "shared_pool", "maxsize": 50, "queue_id": "shared_1"},
        {"type": "ray_actor", "actor_name": "processor", "maxsize": 20, "queue_id": "ray_1"},
        {"type": "sage_queue", "maxsize": 100, "namespace": "production", "queue_id": "sage_1"}
    ]
    
    # 创建队列池
    pool = create_queue_pool(pool_config, "demo_pool")
    print(f"创建队列池，包含 {len(pool)} 个队列:")
    for name, queue_desc in pool.items():
        print(f"  - {name}: {queue_desc}")
    
    # 序列化整个队列池
    print(f"\n序列化队列池...")
    pool_json = serialize_queue_pool(pool)
    print(f"序列化结果: {len(pool_json)} 字符")
    
    # 反序列化队列池
    print("反序列化队列池...")
    restored_pool = deserialize_queue_pool(pool_json)
    print(f"恢复的队列池，包含 {len(restored_pool)} 个队列:")
    for name, queue_desc in restored_pool.items():
        print(f"  - {name}: {queue_desc}")


def example_6_advanced_features():
    """示例6: 高级特性"""
    print("\n\n⚡ 示例6: 高级特性")
    print("-" * 40)
    
    # 克隆描述符
    original = UnifiedQueueDescriptor.create_sage_queue(
        "advanced_demo",
        maxsize=200,
        auto_cleanup=True,
        namespace="testing"
    )
    
    cloned = original.clone("cloned_demo")
    print(f"原始: {original}")
    print(f"克隆: {cloned}")
    print(f"相等性: {original == cloned}")  # False (不同ID)
    
    # 元数据访问
    print(f"\n原始队列元数据:")
    for key, value in original.metadata.items():
        print(f"  {key}: {value}")
    
    # 向后兼容性
    print(f"\n向后兼容性测试:")
    old_style = QueueDescriptor("compat_test", "local", {"maxsize": 5})
    print(f"QueueDescriptor别名工作: {isinstance(old_style, UnifiedQueueDescriptor)}")
    
    # 队列状态检查
    print(f"\n队列状态:")
    print(f"  - 类型: {original.queue_type}")
    print(f"  - ID: {original.queue_id}")
    print(f"  - 创建时间: {time.ctime(original.created_timestamp)}")
    print(f"  - 可序列化: {original.can_serialize}")
    print(f"  - 已初始化: {original.is_initialized()}")


def main():
    """主演示函数"""
    print("🎯 统一多态队列描述符使用示例")
    print("=" * 60)
    
    # 注册模拟队列实现（用于演示）
    class DemoQueueStub:
        def __init__(self, descriptor):
            self.desc = descriptor
            self.items = []
        
        def put(self, item, block=True, timeout=None): 
            print(f"  📥 [{self.desc.queue_type}] 放入: {item}")
            self.items.append(item)
        
        def get(self, block=True, timeout=None): 
            if self.items:
                item = self.items.pop(0)
                print(f"  📤 [{self.desc.queue_type}] 取出: {item}")
                return item
            return None
        
        def empty(self): 
            return len(self.items) == 0
        
        def qsize(self): 
            return len(self.items)
        
        def put_nowait(self, item):
            return self.put(item, block=False)
        
        def get_nowait(self):
            return self.get(block=False)
        
        def full(self):
            maxsize = self.desc.metadata.get('maxsize', 0)
            if maxsize <= 0:
                return False
            return len(self.items) >= maxsize
    
    # 注册各种队列类型的模拟实现
    queue_types = ["local", "shm", "ray_actor", "ray_queue", "rpc", "sage_queue"]
    for qt in queue_types:
        register_queue_implementation(qt, DemoQueueStub)
    
    try:
        # 运行所有示例
        example_1_polymorphic_interface()
        example_2_lazy_loading()
        example_3_serialization()
        example_4_non_serializable_handling()
        example_5_queue_pools()
        example_6_advanced_features()
        
        print(f"\n{'=' * 60}")
        print("🎉 所有示例运行完成！")
        print("\n主要特性总结:")
        print("✅ 多态接口 - 统一的队列操作方法")
        print("✅ 懒加载 - 按需初始化队列实例")
        print("✅ 序列化支持 - 安全的跨进程传递")
        print("✅ 类型安全 - 自动处理不可序列化对象")
        print("✅ 队列池 - 批量管理多个队列")
        print("✅ 向后兼容 - 保持原有API接口")
        
    except Exception as e:
        print(f"\n❌ 示例运行出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
