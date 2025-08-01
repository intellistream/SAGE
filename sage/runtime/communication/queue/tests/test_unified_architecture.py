"""
统一架构测试 - 测试重构后的QueueDescriptor

测试删除QueueLike Protocol后的统一队列描述符系统
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))


def test_descriptor_imports():
    """测试描述符导入"""
    try:
        from sage.runtime.communication.queue import (
            QueueDescriptor,
            resolve_descriptor
        )
        print("✓ 基础导入成功")
        return True
    except ImportError as e:
        print(f"✗ 导入失败: {e}")
        return False


def test_create_descriptors():
    """测试创建描述符"""
    try:
        from sage.runtime.communication.queue import QueueDescriptor
        
        # 测试创建本地队列描述符
        local_desc = QueueDescriptor.create_local_queue(maxsize=100)
        print(f"✓ 本地队列描述符创建成功: {local_desc}")
        
        # 测试创建共享内存队列描述符
        shm_desc = QueueDescriptor.create_shm_queue("test_shm", maxsize=200)
        print(f"✓ 共享内存队列描述符创建成功: {shm_desc}")
        
        return True
    except Exception as e:
        print(f"✗ 创建描述符失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_queue_operations():
    """测试队列操作"""
    try:
        from sage.runtime.communication.queue import QueueDescriptor
        
        # 创建本地队列
        desc = QueueDescriptor.create_local_queue(maxsize=10)
        
        # 测试队列操作
        desc.put("test_message")
        message = desc.get()
        
        print(f"✓ 队列操作成功: 发送并接收了消息 '{message}'")
        print(f"✓ 队列大小: {desc.qsize()}")
        print(f"✓ 队列是否为空: {desc.empty()}")
        
        return True
    except Exception as e:
        print(f"✗ 队列操作失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_serialization():
    """测试序列化"""
    try:
        from sage.runtime.communication.queue import QueueDescriptor
        
        # 创建可序列化的描述符
        desc = QueueDescriptor.create_local_queue(maxsize=50)
        
        # 测试序列化
        json_str = desc.to_json()
        print(f"✓ 序列化成功: {len(json_str)} 字符")
        
        # 测试反序列化
        restored_desc = QueueDescriptor.from_json(json_str)
        print(f"✓ 反序列化成功: {restored_desc}")
        
        return True
    except Exception as e:
        print(f"✗ 序列化测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("=== 统一队列描述符架构测试 ===")
    
    tests = [
        test_descriptor_imports,
        test_create_descriptors,
        test_queue_operations,
        test_serialization
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        print(f"\n--- 运行 {test.__name__} ---")
        if test():
            passed += 1
        else:
            print(f"✗ {test.__name__} 失败")
    
    print(f"\n=== 测试结果: {passed}/{total} 通过 ===")
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
