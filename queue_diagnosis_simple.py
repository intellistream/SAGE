#!/usr/bin/env python3
"""
简化的队列诊断工具
"""

import sys
import os

# 添加 SAGE 到路径
sage_root = '/home/shuhao/SAGE'
if sage_root not in sys.path:
    sys.path.insert(0, sage_root)

def test_queue_backends():
    """测试所有队列后端"""
    print("🔍 SAGE Queue System Diagnosis Report")
    print("=" * 50)
    
    # 测试环境
    print("\n🌍 Environment:")
    print(f"   • Python: {sys.version[:20]}...")
    
    # 检查 Ray
    ray_available = False
    ray_initialized = False
    try:
        import ray
        ray_available = True
        ray_initialized = ray.is_initialized()
        print(f"   • Ray Available: ✅")
        print(f"   • Ray Initialized: {'✅' if ray_initialized else '❌'}")
    except ImportError:
        print(f"   • Ray Available: ❌")
        print(f"   • Ray Initialized: ❌")
    
    # 检查 SAGE
    sage_available = False
    try:
        import sage
        sage_available = True
        print(f"   • SAGE Environment: ✅")
    except ImportError:
        print(f"   • SAGE Environment: ❌")
    
    print(f"   • Distributed Mode: {'✅' if ray_initialized else '❌'}")
    
    # 测试后端
    print(f"\n🔧 Backend Status:")
    
    backend_results = {}
    
    # 测试 Python Queue
    try:
        import queue
        test_queue = queue.Queue(maxsize=10)
        test_queue.put("test")
        result = test_queue.get()
        if result == "test":
            print(f"   • python_queue: ✅ Working 🏠")
            backend_results["python_queue"] = True
        else:
            print(f"   • python_queue: ⚠️  Available but test failed 🏠")
            backend_results["python_queue"] = False
    except Exception as e:
        print(f"   • python_queue: ❌ Error: {e} 🏠")
        backend_results["python_queue"] = False
    
    # 测试 Ray Queue
    try:
        import ray
        from ray.util.queue import Queue as RayQueue
        
        if not ray.is_initialized():
            ray.init(ignore_reinit_error=True)
        
        test_queue = RayQueue(maxsize=10)
        test_queue.put("test")
        result = test_queue.get()
        
        if result == "test":
            print(f"   • ray_queue: ✅ Working 🌐")
            backend_results["ray_queue"] = True
        else:
            print(f"   • ray_queue: ⚠️  Available but test failed 🌐")
            backend_results["ray_queue"] = False
    except ImportError:
        print(f"   • ray_queue: ❌ Ray not installed 🌐")
        backend_results["ray_queue"] = False
    except Exception as e:
        print(f"   • ray_queue: ❌ Error: {e} 🌐")
        backend_results["ray_queue"] = False
    
    # 测试 SAGE Queue
    try:
        from sage_ext.sage_queue.python.sage_queue import SageQueue
        
        test_queue = SageQueue(name="diagnostic_test", maxsize=10)
        test_queue.put("test")
        result = test_queue.get()
        test_queue.close()
        
        if result == "test":
            print(f"   • sage_queue: ✅ Working 🏠")
            backend_results["sage_queue"] = True
        else:
            print(f"   • sage_queue: ⚠️  Available but test failed 🏠")
            backend_results["sage_queue"] = False
    except ImportError as e:
        print(f"   • sage_queue: ❌ Extension not available: {e} 🏠")
        backend_results["sage_queue"] = False
    except Exception as e:
        print(f"   • sage_queue: ❌ Error: {e} 🏠")
        backend_results["sage_queue"] = False
    
    # 测试 Queue Adapter
    print(f"\n🔧 Queue Adapter Test:")
    try:
        from sage.utils.queue_adapter import create_queue, get_recommended_queue_backend
        
        backend = get_recommended_queue_backend()
        print(f"   • Recommended backend: {backend}")
        
        queue = create_queue(name='diagnostic_test')
        queue.put("adapter_test")
        result = queue.get()
        
        if result == "adapter_test":
            print(f"   • Queue adapter: ✅ Working with {backend}")
        else:
            print(f"   • Queue adapter: ⚠️  Test failed")
            
    except Exception as e:
        print(f"   • Queue adapter: ❌ Error: {e}")
    
    # 生成建议
    working_backends = [name for name, working in backend_results.items() if working]
    
    print(f"\n💡 Recommendations:")
    
    if not working_backends:
        print(f"   ❌ CRITICAL: No working queue backends found!")
        print(f"      • Install Ray: pip install ray")
        print(f"      • Build SAGE extension: cd sage_ext/sage_queue && ./build.sh")
        overall_status = "CRITICAL"
    elif len(working_backends) == 1:
        print(f"   ⚠️  Only one backend working: {working_backends[0]}")
        print(f"      • Consider installing additional backends for redundancy")
        overall_status = "LIMITED"
    else:
        print(f"   ✅ Multiple backends working: {', '.join(working_backends)}")
        overall_status = "GOOD"
    
    # 分布式建议
    if ray_initialized and "sage_queue" in working_backends:
        print(f"   ⚠️  SAGE queue doesn't support distributed environments")
        print(f"      • Will automatically fallback to Ray queue for distributed tasks")
    
    if not ray_available and sage_available:
        print(f"   💡 Install Ray for distributed support: pip install ray")
    
    print(f"\n📊 Overall Status: {overall_status}")
    print("=" * 50)
    
    return overall_status

if __name__ == "__main__":
    try:
        status = test_queue_backends()
        if status == "CRITICAL":
            sys.exit(1)
        elif status == "LIMITED":
            sys.exit(2)
        else:
            sys.exit(0)
    except Exception as e:
        print(f"❌ Diagnosis failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(3)
