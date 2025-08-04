#!/usr/bin/env python3
"""
运行BaseServiceTask队列管理重构相关的测试

这个脚本运行新添加的测试，验证BaseServiceTask正确使用ServiceContext中的队列描述符。
"""

import sys
import os
import unittest

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

def run_base_service_task_tests():
    """运行BaseServiceTask队列重构测试"""
    print("🧪 Running BaseServiceTask Queue Management Refactor Tests")
    print("=" * 60)
    
    # 导入测试模块
    try:
        from sage.runtime.service.tests.test_base_service_task_queue_refactor import TestBaseServiceTaskQueueManagement
        
        # 创建测试套件
        suite = unittest.TestSuite()
        
        # 添加BaseServiceTask队列管理测试
        suite.addTest(unittest.makeSuite(TestBaseServiceTaskQueueManagement))
        
        # 运行测试
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        
        # 输出结果摘要
        print("\n" + "=" * 60)
        print("📊 Test Results Summary:")
        print(f"   Tests run: {result.testsRun}")
        print(f"   Failures: {len(result.failures)}")
        print(f"   Errors: {len(result.errors)}")
        print(f"   Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
        
        if result.failures:
            print("\n❌ Failures:")
            for test, traceback in result.failures:
                error_msg = traceback.split('AssertionError: ')[-1].split('\n')[0]
                print(f"   - {test}: {error_msg}")
        
        if result.errors:
            print("\n💥 Errors:")
            for test, traceback in result.errors:
                error_lines = traceback.split('\n')
                error_msg = error_lines[-2] if len(error_lines) > 1 else "Unknown error"
                print(f"   - {test}: {error_msg}")
        
        if result.wasSuccessful():
            print("\n✅ All tests passed! BaseServiceTask queue refactor is working correctly.")
            return True
        else:
            print("\n❌ Some tests failed. Please check the implementation.")
            return False
            
    except ImportError as e:
        print(f"❌ Failed to import test modules: {e}")
        print("Please ensure all dependencies are available.")
        return False
    except Exception as e:
        print(f"💥 Unexpected error during test execution: {e}")
        return False


def run_quick_functionality_check():
    """快速功能检查"""
    print("\n🔍 Quick Functionality Check")
    print("-" * 30)
    
    try:
        # 检查BaseServiceTask导入
        from sage.runtime.service.base_service_task import BaseServiceTask
        print("✅ BaseServiceTask import successful")
        
        # 检查ServiceContext导入
        from sage.runtime.service_context import ServiceContext
        print("✅ ServiceContext import successful")
        
        # 检查BaseQueueDescriptor导入
        from sage.runtime.communication.queue_descriptor.base_queue_descriptor import BaseQueueDescriptor
        print("✅ BaseQueueDescriptor import successful")
        
        # 检查关键方法存在
        required_methods = [
            'request_queue_descriptor',
            'request_queue', 
            'get_response_queue_descriptor',
            'get_response_queue',
            'handle_request',
            'start_running',
            'stop',
            'cleanup'
        ]
        
        for method in required_methods:
            if hasattr(BaseServiceTask, method):
                print(f"✅ Method '{method}' found")
            else:
                print(f"❌ Method '{method}' missing")
                return False
        
        # 检查抽象方法数量（应该只有2个）
        import inspect
        abstract_methods = []
        for name, method in inspect.getmembers(BaseServiceTask):
            if getattr(method, '__isabstractmethod__', False):
                abstract_methods.append(name)
        
        print(f"📋 Abstract methods: {abstract_methods}")
        expected_abstract = ['_start_service_instance', '_stop_service_instance']
        
        if set(abstract_methods) == set(expected_abstract):
            print("✅ Correct abstract methods found")
        else:
            print(f"❌ Expected abstract methods: {expected_abstract}")
            print(f"   Found abstract methods: {abstract_methods}")
            return False
        
        print("✅ All functionality checks passed!")
        return True
        
    except Exception as e:
        print(f"❌ Functionality check failed: {e}")
        return False


if __name__ == "__main__":
    print("🚀 BaseServiceTask Queue Management Refactor Test Suite")
    print("=" * 60)
    
    success = True
    
    # 运行功能检查
    if not run_quick_functionality_check():
        success = False
    
    # 运行完整测试
    if not run_base_service_task_tests():
        success = False
    
    # 最终结果
    if success:
        print("\n🎉 All checks and tests passed!")
        print("   BaseServiceTask queue refactor is ready for use.")
        sys.exit(0)
    else:
        print("\n💥 Some checks or tests failed!")
        print("   Please review the implementation before proceeding.")
        sys.exit(1)
