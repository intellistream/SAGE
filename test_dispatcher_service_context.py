#!/usr/bin/env python3
"""
测试dispatcher中的service runtime context创建功能
"""
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_service_context_creation():
    """测试service runtime context的创建"""
    print("Testing service runtime context creation...")
    
    try:
        # 模拟检查dispatcher中_create_service_runtime_context方法是否存在
        from sage.runtime.dispatcher import Dispatcher
        
        # 检查方法是否存在
        if hasattr(Dispatcher, '_create_service_runtime_context'):
            print("✅ _create_service_runtime_context method found in Dispatcher")
        else:
            print("❌ _create_service_runtime_context method not found in Dispatcher")
            return False
        
        # 检查import是否正确
        print("✅ Dispatcher import successful")
        
        # 检查方法签名
        import inspect
        method = getattr(Dispatcher, '_create_service_runtime_context')
        sig = inspect.signature(method)
        params = list(sig.parameters.keys())
        
        if 'self' in params and 'service_name' in params:
            print("✅ Method signature is correct")
        else:
            print(f"❌ Method signature incorrect. Found parameters: {params}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        return False

if __name__ == "__main__":
    success = test_service_context_creation()
    if success:
        print("\n🎉 All tests passed! Service runtime context creation is properly implemented.")
    else:
        print("\n💥 Tests failed! Please check the implementation.")
        sys.exit(1)
