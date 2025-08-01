"""
Test New Queue Descriptor Architecture - 测试新的队列描述符架构
"""

import sys
import os

# 将当前目录添加到Python路径中
sys.path.insert(0, '/api-rework')

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
        from sage.runtime.communication.descriptors import create_queue_descriptor
        
        # 测试创建本地队列描述符
        local_desc = create_queue_descriptor('local', maxsize=100)
        print(f"✓ 本地队列描述符创建成功: {local_desc}")
        
        # 测试创建可序列化本地队列描述符
        ser_desc = create_queue_descriptor('serializable_local', maxsize=200)
        print(f"✓ 可序列化本地队列描述符创建成功: {ser_desc}")
        
        return True
    except Exception as e:
        print(f"✗ 创建描述符失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_list_types():
    """测试列出支持的类型"""
    try:
        from sage.runtime.communication.descriptors import list_supported_queue_types
        
        types = list_supported_queue_types()
        print(f"✓ 支持的队列类型: {types}")
        return True
    except Exception as e:
        print(f"✗ 列出类型失败: {e}")
        return False


def test_descriptor_info():
    """测试获取描述符信息"""
    try:
        from sage.runtime.communication.descriptors import get_descriptor_info
        
        info = get_descriptor_info()
        print(f"✓ 描述符系统信息: {info}")
        return True
    except Exception as e:
        print(f"✗ 获取信息失败: {e}")
        return False


def run_all_tests():
    """运行所有测试"""
    print("=== 新队列描述符架构测试 ===\n")
    
    tests = [
        ("导入测试", test_descriptor_imports),
        ("创建描述符测试", test_create_descriptors),
        ("列出类型测试", test_list_types),
        ("描述符信息测试", test_descriptor_info)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        try:
            if test_func():
                passed += 1
                print(f"{test_name}: PASSED")
            else:
                print(f"{test_name}: FAILED")
        except Exception as e:
            print(f"{test_name}: ERROR - {e}")
    
    print(f"\n=== 测试结果: {passed}/{total} 通过 ===")
    return passed == total


if __name__ == "__main__":
    run_all_tests()
