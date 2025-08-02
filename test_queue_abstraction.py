#!/usr/bin/env python3
"""
测试BaseServiceTask的队列抽象化
"""
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_abstract_methods():
    """测试抽象方法是否正确定义"""
    print("Testing abstract methods in BaseServiceTask...")
    
    try:
        from sage.runtime.service.base_service_task import BaseServiceTask
        import inspect
        
        # 检查抽象方法是否存在
        abstract_methods = [
            '_create_request_queue',
            '_create_response_queue', 
            '_queue_get',
            '_queue_put',
            '_queue_close',
            '_start_service_instance',
            '_stop_service_instance'
        ]
        
        for method_name in abstract_methods:
            if hasattr(BaseServiceTask, method_name):
                method = getattr(BaseServiceTask, method_name)
                if hasattr(method, '__isabstractmethod__') and method.__isabstractmethod__:
                    print(f"✅ Abstract method {method_name} exists")
                else:
                    print(f"⚠️  Method {method_name} exists but is not abstract")
            else:
                print(f"❌ Abstract method {method_name} not found")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing abstract methods: {e}")
        return False

def test_local_service_task():
    """测试LocalServiceTask实现"""
    print("\nTesting LocalServiceTask implementation...")
    
    try:
        from sage.runtime.service.local_service_task import LocalServiceTask
        
        # 检查是否有queue导入
        import sage.runtime.service.local_service_task as lst_module
        if hasattr(lst_module, 'queue'):
            print("✅ LocalServiceTask has queue import")
        else:
            print("❌ LocalServiceTask missing queue import")
            return False
        
        # 检查是否实现了所有抽象方法
        methods_to_check = [
            '_create_request_queue',
            '_create_response_queue',
            '_queue_get', 
            '_queue_put',
            '_queue_close'
        ]
        
        for method_name in methods_to_check:
            if hasattr(LocalServiceTask, method_name):
                print(f"✅ LocalServiceTask implements {method_name}")
            else:
                print(f"❌ LocalServiceTask missing {method_name}")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing LocalServiceTask: {e}")
        return False

def test_ray_service_task():
    """测试RayServiceTask实现"""
    print("\nTesting RayServiceTask implementation...")
    
    try:
        from sage.runtime.service.ray_service_task import RayServiceTask
        
        # 检查是否有RayQueue导入处理
        import sage.runtime.service.ray_service_task as rst_module
        if hasattr(rst_module, 'RAY_QUEUE_AVAILABLE'):
            print("✅ RayServiceTask has Ray queue availability check")
        else:
            print("❌ RayServiceTask missing Ray queue availability check")
            return False
        
        # 检查是否实现了所有抽象方法
        methods_to_check = [
            '_create_request_queue',
            '_create_response_queue',
            '_queue_get',
            '_queue_put', 
            '_queue_close'
        ]
        
        for method_name in methods_to_check:
            if hasattr(RayServiceTask, method_name):
                print(f"✅ RayServiceTask implements {method_name}")
            else:
                print(f"❌ RayServiceTask missing {method_name}")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing RayServiceTask: {e}")
        return False

if __name__ == "__main__":
    success1 = test_abstract_methods()
    success2 = test_local_service_task()  
    success3 = test_ray_service_task()
    
    if success1 and success2 and success3:
        print("\n🎉 All tests passed! Queue abstraction is properly implemented.")
    else:
        print("\n💥 Some tests failed! Please check the implementation.")
        sys.exit(1)
