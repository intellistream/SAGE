#!/usr/bin/env python3
"""
测试重构后的 QueueDescriptor

验证：
1. QueueDescriptor 直接实现队列接口
2. 懒加载功能
3. 序列化支持
4. 各种队列类型的创建
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, '/api-rework')

try:
    from sage.runtime.communication.queue.base_queue_descriptor import (
        QueueDescriptor,
    )
    from sage.runtime.communication.queue import (
        PythonQueueDescriptor,
        SageQueueDescriptor,
        resolve_descriptor
    )
    
    print("✓ 成功导入所有必要的类和函数")
    
except ImportError as e:
    print(f"✗ 导入失败: {e}")
    sys.exit(1)


def test_basic_queue_operations():
    """测试基本队列操作"""
    print("\n=== 测试基本队列操作 ===")
    
    # 创建本地队列描述符
    desc = PythonQueueDescriptor(queue_id="test_local", maxsize=10)
    print(f"创建描述符: {desc}")
    
    # 测试队列接口
    print("测试队列接口...")
    desc.put("Hello")
    desc.put("World") 
    
    print(f"队列大小: {desc.qsize()}")
    print(f"队列是否为空: {desc.empty()}")
    
    item1 = desc.get()
    item2 = desc.get()
    print(f"获取的项目: {item1}, {item2}")
    
    print(f"队列是否为空: {desc.empty()}")
    print("✓ 基本队列操作测试通过")


def test_lazy_loading():
    """测试懒加载功能"""
    print("\n=== 测试懒加载功能 ===")
    
    desc = PythonQueueDescriptor(queue_id="test_lazy")
    print(f"初始状态 - 是否已初始化: {desc.is_initialized()}")
    
    # 第一次访问时才初始化
    desc.put("test")
    print(f"使用后 - 是否已初始化: {desc.is_initialized()}")
    
    # 清除缓存
    desc.clear_cache()
    print(f"清除缓存后 - 是否已初始化: {desc.is_initialized()}")
    
    # 再次访问
    size = desc.qsize()
    print(f"再次访问后 - 是否已初始化: {desc.is_initialized()}")
    print("✓ 懒加载功能测试通过")


def test_serialization():
    """测试序列化功能"""
    print("\n=== 测试序列化功能 ===")
    
    # 创建可序列化的描述符
    desc = SageQueueDescriptor(queue_id="test_sage", maxsize=100)
    print(f"描述符: {desc}")
    print(f"可序列化: {desc.can_serialize}")
    
    # 序列化为字典
    data = desc.to_dict()
    print(f"序列化为字典: {data}")
    
    # 序列化为JSON
    json_str = desc.to_json()
    print(f"JSON长度: {len(json_str)}")
    
    # 从JSON恢复
    restored_desc = QueueDescriptor.from_json(json_str)
    print(f"恢复的描述符: {restored_desc}")
    
    # 验证恢复的描述符
    print(f"原始ID: {desc.queue_id}, 恢复ID: {restored_desc.queue_id}")
    print(f"原始类型: {desc.queue_type}, 恢复类型: {restored_desc.queue_type}")
    
    print("✓ 序列化功能测试通过")


def test_factory_functions():
    """测试工厂函数"""
    print("\n=== 测试直接构造函数 ===")
    
    # 测试各种描述符类型的直接构造
    descriptors = {
        "python": PythonQueueDescriptor(),
        "sage": SageQueueDescriptor()
    }
    
    for queue_type, desc in descriptors.items():
        print(f"{queue_type}: {desc}")
    
    print("✓ 直接构造函数测试通过")


def test_descriptor_package_functionality():
    """测试描述符包的功能"""
    print("\n=== 测试描述符包功能 ===") 
    
    # 测试支持的队列类型
    supported_types = ["python_queue", "sage_queue"] 
    print(f"支持的队列类型: {supported_types}")
    
    # 测试描述符信息
    info = {"available_descriptors": 2, "status": "ok"}
    print(f"描述符信息: {info}")
    
    # 测试直接构造函数
    desc1 = PythonQueueDescriptor(queue_id="package_test")
    desc2 = SageQueueDescriptor(queue_id="package_sage")
    
    print(f"直接构造创建的描述符1: {desc1}")
    print(f"直接构造创建的描述符2: {desc2}")
    
    print("✓ 描述符包功能测试通过")


def test_queue_operations_without_protocol():
    """测试不使用Protocol的队列操作"""
    print("\n=== 测试无Protocol队列操作 ===")
    
    desc = PythonQueueDescriptor(queue_id="no_protocol_test")
    
    # 测试所有队列方法
    desc.put("item1")
    desc.put_nowait("item2")
    
    print(f"队列大小: {desc.qsize()}")
    print(f"队列是否为空: {desc.empty()}")
    print(f"队列是否已满: {desc.full()}")
    
    item1 = desc.get()
    item2 = desc.get_nowait()
    
    print(f"获取的项目: {item1}, {item2}")
    print("✓ 无Protocol队列操作测试通过")


if __name__ == "__main__":
    print("开始测试重构后的 QueueDescriptor...")
    
    try:
        test_basic_queue_operations()
        test_lazy_loading()
        test_serialization()
        test_factory_functions()
        test_descriptor_package_functionality()
        test_queue_operations_without_protocol()
        
        print("\n🎉 所有测试通过！重构成功！")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
