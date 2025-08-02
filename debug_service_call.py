#!/usr/bin/env python3
"""
调试服务调用问题
"""

import sys
import time
import threading
from sage.core.api.local_environment import LocalEnvironment
from sage.core.function.base_function import BaseFunction

# 简单的测试服务
class TestService:
    def __init__(self):
        self.call_count = 0
    
    def test_method(self, value):
        self.call_count += 1
        print(f"[SERVICE] TestService.test_method called with value: {value}, call_count: {self.call_count}")
        return f"processed_{value}"

# 简单的测试函数
class TestFunction(BaseFunction):
    def execute(self, data):
        return data

def test_service_call():
    print("🚀 Testing simple service call...")
    
    try:
        # 创建环境并注册服务
        env = LocalEnvironment("debug_service_test")
        env.set_console_log_level("DEBUG")
        
        # 注册测试服务
        env.register_service("test_service", TestService)
        print("✅ Service registered")
        
        # 设置日志
        env.setup_logging_system("/tmp/test_logs")
        
        # 创建一个测试函数实例
        test_func = TestFunction()
        
        # 手动创建 TaskContext（模拟正常的管道执行环境）
        from sage.runtime.task_context import TaskContext
        from sage.runtime.service.service_caller import ServiceManager
        
        # 创建一个mock的graph node和transformation
        class MockGraphNode:
            def __init__(self, name):
                self.name = name
                self.parallelism = 1
                
        class MockTransformation:
            def __init__(self):
                self.function_factory = None
        
        mock_node = MockGraphNode("test_node")
        mock_transformation = MockTransformation()
        
        # 创建TaskContext
        task_ctx = TaskContext(mock_node, mock_transformation, env)
        test_func.ctx = task_ctx
        
        print("✅ TaskContext created")
        
        # 测试服务调用
        print("[TEST] About to call service...")
        try:
            result = test_func.call_service["test_service"].test_method("test_data", timeout=5.0)
            print(f"[TEST] Service call succeeded: {result}")
            return True
        except Exception as e:
            print(f"[TEST] Service call failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_service_call()
    sys.exit(0 if success else 1)
