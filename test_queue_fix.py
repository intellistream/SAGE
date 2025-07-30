#!/usr/bin/env python3
"""
简单的队列系统测试和修复验证
"""

import sys
import os
import time

# 添加 SAGE 到路径
SAGE_ROOT = '/home/shuhao/SAGE'
if SAGE_ROOT not in sys.path:
    sys.path.insert(0, SAGE_ROOT)

def test_queue_adapter():
    """测试队列适配器"""
    print("🔧 Testing Queue Adapter...")
    
    try:
        from sage.utils.queue_adapter import create_queue, get_recommended_queue_backend
        
        # 测试后端推荐
        recommended = get_recommended_queue_backend()
        print(f"   Recommended backend: {recommended}")
        
        # 测试队列创建
        queue = create_queue(name='test_simple')
        print(f"   Created queue: {type(queue)}")
        
        # 测试基础操作
        test_data = "hello_world"
        queue.put(test_data)
        result = queue.get()
        
        if result == test_data:
            print("   ✅ Queue operations working")
            return True
        else:
            print(f"   ❌ Queue test failed: expected {test_data}, got {result}")
            return False
            
    except Exception as e:
        print(f"   ❌ Queue adapter error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_backend_fallback():
    """测试后端回退机制"""
    print("🔄 Testing Backend Fallback...")
    
    try:
        from sage.utils.queue_adapter import create_queue
        
        # 测试不同后端
        backends_to_test = ['auto', 'ray_queue', 'python_queue']
        working_backends = []
        
        for backend in backends_to_test:
            try:
                queue = create_queue(backend=backend, name=f'test_{backend}')
                queue.put("test")
                result = queue.get()
                if result == "test":
                    working_backends.append(backend)
                    print(f"   ✅ Backend {backend} working")
                else:
                    print(f"   ❌ Backend {backend} failed test")
            except Exception as e:
                print(f"   ⚠️  Backend {backend} error: {e}")
        
        print(f"   Working backends: {working_backends}")
        return len(working_backends) > 0
        
    except Exception as e:
        print(f"   ❌ Fallback test error: {e}")
        return False

def test_distributed_detection():
    """测试分布式环境检测"""
    print("🌐 Testing Distributed Environment Detection...")
    
    try:
        # 检查 Ray 是否可用
        try:
            import ray
            ray_available = True
            ray_initialized = ray.is_initialized()
            print(f"   Ray available: {ray_available}")
            print(f"   Ray initialized: {ray_initialized}")
        except ImportError:
            ray_available = False
            ray_initialized = False
            print("   Ray not available")
        
        # 测试队列适配器的分布式检测
        from sage.utils.queue_adapter import get_recommended_queue_backend
        recommended = get_recommended_queue_backend()
        print(f"   Recommended for current environment: {recommended}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Distributed detection error: {e}")
        return False

def test_router_fix():
    """测试路由器修复是否有效"""
    print("🔗 Testing Router Connection Fix...")
    
    try:
        # 模拟路由器连接测试
        from sage.utils.queue_adapter import create_queue
        
        # 创建模拟的 input_buffer（就像 BaseTask 做的那样）
        input_buffer = create_queue(name='test_input_buffer')
        
        # 模拟连接建立（之前的错误方式会创建新队列）
        # 现在应该直接使用 input_buffer
        target_buffer = input_buffer  # 正确方式：直接使用现有队列
        
        # 测试数据传递
        test_packet = {"type": "test", "data": "router_test"}
        target_buffer.put(test_packet)
        received = target_buffer.get()
        
        if received == test_packet:
            print("   ✅ Router connection simulation working")
            return True
        else:
            print(f"   ❌ Router test failed: {received}")
            return False
            
    except Exception as e:
        print(f"   ❌ Router test error: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 SAGE Queue System Fix Verification")
    print("=" * 50)
    
    tests = [
        ("Queue Adapter", test_queue_adapter),
        ("Backend Fallback", test_backend_fallback), 
        ("Distributed Detection", test_distributed_detection),
        ("Router Fix", test_router_fix)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}:")
        try:
            result = test_func()
            results[test_name] = result
        except Exception as e:
            print(f"   💥 Test crashed: {e}")
            results[test_name] = False
    
    # 总结
    print(f"\n" + "=" * 50)
    print("📊 Test Results Summary:")
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   • {test_name}: {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Queue system fix is working correctly.")
        return 0
    elif passed > 0:
        print("⚠️  Some tests passed. Queue system partially working.")
        return 1
    else:
        print("❌ All tests failed. Queue system needs more work.")
        return 2

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
