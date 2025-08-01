#!/usr/bin/env python3
"""
简单的队列转换功能验证脚本
"""

import sys
import os

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_basic_functionality():
    """测试基础功能"""
    print("=== 开始基础功能测试 ===")
    
    try:
        # 导入队列描述符
        from sage.runtime.communication.queue_descriptor import QueueDescriptor
        print("✅ QueueDescriptor 导入成功")
        
        # 创建本地队列描述符
        descriptor = QueueDescriptor.create_local_queue("test_queue", maxsize=10)
        print(f"✅ 创建描述符成功: {descriptor}")
        
        # 测试序列化
        json_str = descriptor.to_json()
        print(f"✅ 序列化成功，长度: {len(json_str)}")
        
        # 测试反序列化
        restored = QueueDescriptor.from_json(json_str)
        print(f"✅ 反序列化成功: {restored.queue_id}")
        
        return True
        
    except Exception as e:
        print(f"❌ 基础功能测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_queue_stubs():
    """测试队列 Stubs"""
    print("\n=== 开始队列 Stubs 测试 ===")
    
    try:
        # 导入队列 Stubs
        from sage.runtime.communication.queue_stubs import LocalQueueStub
        print("✅ LocalQueueStub 导入成功")
        
        # 导入注册功能
        from sage.runtime.communication.queue_stubs.registry import initialize_queue_stubs
        print("✅ 注册功能导入成功")
        
        # 初始化队列类型
        count = initialize_queue_stubs()
        print(f"✅ 注册了 {count} 个队列类型")
        
        # 测试队列解析
        from sage.runtime.communication.queue_descriptor import QueueDescriptor, resolve_descriptor
        
        descriptor = QueueDescriptor.create_local_queue("stub_test")
        queue = resolve_descriptor(descriptor)
        print(f"✅ 队列解析成功: {queue}")
        
        # 测试队列操作
        queue.put("test_message")
        message = queue.get()
        print(f"✅ 队列操作成功: {message}")
        
        return True
        
    except Exception as e:
        print(f"❌ 队列 Stubs 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_conversion():
    """测试队列转换"""
    print("\n=== 开始队列转换测试 ===")
    
    try:
        from queue import Queue
        from sage.runtime.communication.queue_stubs import LocalQueueStub
        
        # 创建原始 Python Queue
        python_queue = Queue(maxsize=5)
        python_queue.put("original_data")
        
        # 从原始队列创建 Stub
        stub = LocalQueueStub.from_queue(python_queue, queue_id="conversion_test")
        print("✅ 从原始队列创建 Stub 成功")
        
        # 获取描述符
        descriptor = stub.to_descriptor()
        print(f"✅ 获取描述符成功: {descriptor.queue_id}")
        
        # 验证数据
        data = stub.get()
        print(f"✅ 数据保持完整: {data}")
        
        return True
        
    except Exception as e:
        print(f"❌ 队列转换测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主测试函数"""
    print("开始 SAGE Queue 转换系统测试\n")
    
    # 运行所有测试
    tests = [
        test_basic_functionality,
        test_queue_stubs,
        test_conversion
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print(f"\n=== 测试结果 ===")
    print(f"通过: {passed}/{total}")
    
    if passed == total:
        print("🎉 所有测试通过！")
        return 0
    else:
        print("⚠️  部分测试失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())
