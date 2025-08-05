#!/usr/bin/env python3
"""
SAGE Queue 快速验证测试
用于快速检查基本功能是否正常工作
"""

import sys
import os
import time

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_import():
    """测试模块导入"""
    try:
        from sage.extensions.sage_queue.python.sage_queue import SageQueue
        print("✅ 模块导入成功")
        return True
    except Exception as e:
        print(f"❌ 模块导入失败: {e}")
        return False

def test_queue_creation():
    """测试队列创建"""
    try:
        from sage.extensions.sage_queue.python.sage_queue import SageQueue
        queue = SageQueue(f"quick_test_{int(time.time() * 1000)}", maxsize=1024)
        queue.close()
        print("✅ 队列创建成功")
        return True
    except Exception as e:
        print(f"❌ 队列创建失败: {e}")
        return False

def test_basic_operations():
    """测试基本操作"""
    try:
        from sage.extensions.sage_queue.python.sage_queue import SageQueue
        queue = SageQueue(f"quick_ops_{int(time.time() * 1000)}", maxsize=1024)
        
        # 测试 put/get
        test_data = "Quick test message"
        queue.put(test_data)
        result = queue.get()
        
        if result == test_data:
            print("✅ 基本 put/get 操作成功")
            success = True
        else:
            print(f"❌ 数据不匹配: 期望 '{test_data}', 得到 '{result}'")
            success = False
        
        queue.close()
        return success
    except Exception as e:
        print(f"❌ 基本操作失败: {e}")
        return False

def test_queue_states():
    """测试队列状态"""
    try:
        from sage.extensions.sage_queue.python.sage_queue import SageQueue
        queue = SageQueue(f"quick_state_{int(time.time() * 1000)}", maxsize=1024)
        
        # 测试空队列
        if not queue.empty():
            print("❌ 新队列应该为空")
            return False
        
        if queue.qsize() != 0:
            print(f"❌ 新队列大小应该为0，实际为 {queue.qsize()}")
            return False
        
        # 添加项目后测试
        queue.put("test")
        if queue.empty():
            print("❌ 添加项目后队列不应该为空")
            return False
        
        if queue.qsize() != 1:
            print(f"❌ 添加一个项目后大小应该为1，实际为 {queue.qsize()}")
            return False
        
        queue.close()
        print("✅ 队列状态检查成功")
        return True
    except Exception as e:
        print(f"❌ 队列状态检查失败: {e}")
        return False

def test_serialization():
    """测试序列化功能"""
    try:
        from sage.extensions.sage_queue.python.sage_queue import SageQueue
        queue = SageQueue(f"quick_serial_{int(time.time() * 1000)}", maxsize=1024)
        
        # 测试复杂数据类型
        test_data = {
            "string": "test",
            "number": 42,
            "list": [1, 2, 3],
            "nested": {"key": "value"}
        }
        
        queue.put(test_data)
        result = queue.get()
        
        if result == test_data:
            print("✅ 复杂数据序列化成功")
            success = True
        else:
            print(f"❌ 序列化数据不匹配")
            success = False
        
        queue.close()
        return success
    except Exception as e:
        print(f"❌ 序列化测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🔍 SAGE Queue 快速验证测试")
    print("=" * 40)
    
    tests = [
        ("模块导入", test_import),
        ("队列创建", test_queue_creation),
        ("基本操作", test_basic_operations),
        ("队列状态", test_queue_states),
        ("数据序列化", test_serialization),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 测试: {test_name}")
        if test_func():
            passed += 1
        else:
            print(f"⚠️  {test_name} 测试失败")
    
    print("\n" + "=" * 40)
    print(f"📊 测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有快速验证测试通过！")
        return 0
    else:
        print("❌ 部分测试失败，请检查问题")
        return 1

if __name__ == '__main__':
    exit(main())
