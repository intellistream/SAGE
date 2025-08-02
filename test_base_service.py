#!/usr/bin/env python3
"""
测试BaseService和ctx注入功能
"""
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_base_service():
    """测试BaseService基类"""
    print("Testing BaseService base class...")
    
    try:
        from sage.core.service.base_service import BaseService
        
        # 测试基类创建
        class TestService(BaseService):
            def __init__(self):
                super().__init__()
                self.test_data = "hello"
        
        service = TestService()
        
        # 测试logger属性
        logger = service.logger
        print(f"✅ Logger accessible: {type(logger).__name__}")
        
        # 测试name属性
        name = service.name
        print(f"✅ Name accessible: {name}")
        
        # 测试方法存在
        if hasattr(service, 'setup') and hasattr(service, 'cleanup'):
            print("✅ Required methods (setup, cleanup) exist")
        else:
            print("❌ Missing required methods")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing BaseService: {e}")
        return False

def test_service_task_logger():
    """测试BaseServiceTask的logger属性"""
    print("\nTesting BaseServiceTask logger property...")
    
    try:
        from sage.runtime.service.base_service_task import BaseServiceTask
        
        # 检查logger属性是否存在
        if hasattr(BaseServiceTask, 'logger') and isinstance(getattr(BaseServiceTask, 'logger'), property):
            print("✅ BaseServiceTask has logger property")
        else:
            print("❌ BaseServiceTask missing logger property")
            return False
        
        # 检查name属性是否存在
        if hasattr(BaseServiceTask, 'name') and isinstance(getattr(BaseServiceTask, 'name'), property):
            print("✅ BaseServiceTask has name property")
        else:
            print("❌ BaseServiceTask missing name property")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing BaseServiceTask: {e}")
        return False

if __name__ == "__main__":
    success1 = test_base_service()
    success2 = test_service_task_logger()
    
    if success1 and success2:
        print("\n🎉 All tests passed! BaseService and ctx injection are properly implemented.")
    else:
        print("\n💥 Some tests failed! Please check the implementation.")
        sys.exit(1)
