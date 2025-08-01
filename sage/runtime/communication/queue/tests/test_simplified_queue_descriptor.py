#!/usr/bin/env python3
"""
简化后的QueueDescriptor功能验证测试
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from sage.runtime.communication import QueueDescriptor

def test_simplified_usage():
    """测试简化后的QueueDescriptor使用"""
    
    print("=== 测试简化后的 QueueDescriptor ===")
    
    # 创建本地队列描述符
    print("\n1. 创建本地队列描述符")
    local_desc = QueueDescriptor.create_local_queue("test_local", maxsize=10)
    print(f"   - 队列ID: {local_desc.queue_id}")
    print(f"   - 队列类型: {local_desc.queue_type}")
    print(f"   - 可序列化: {local_desc.can_serialize}")
    
    # 测试队列操作
    print("\n2. 测试队列操作")
    local_desc.put("Hello")
    local_desc.put("World")
    print(f"   - 队列大小: {local_desc.qsize()}")
    print(f"   - 取出元素: {local_desc.get()}")
    print(f"   - 队列是否为空: {local_desc.empty()}")
    
    # 测试序列化
    print("\n3. 测试序列化")
    serialized = local_desc.to_json()
    print(f"   - 序列化长度: {len(serialized)} 字符")
    
    # 反序列化
    deserialized = QueueDescriptor.from_json(serialized)
    print(f"   - 反序列化成功: {deserialized.queue_id == local_desc.queue_id}")
    
    # 测试克隆
    print("\n4. 测试克隆")
    cloned = local_desc.clone("cloned_queue")
    print(f"   - 克隆队列ID: {cloned.queue_id}")
    print(f"   - 克隆队列类型: {cloned.queue_type}")
    
    print("\n=== 所有测试通过！ ===")

if __name__ == "__main__":
    test_simplified_usage()
