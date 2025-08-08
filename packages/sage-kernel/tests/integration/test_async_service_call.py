#!/usr/bin/env python3
"""
测试 BaseRuntimeContext 的异步服务调用功能
"""
import sys
import os
import time
import tempfile
from concurrent.futures import Future, TimeoutError

# 设置路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'packages', 'sage-kernel', 'src'))

from sage.core.api import LocalEnvironment
from sage.core.api.function.base_function import BaseFunction
from sage.core.api.service.base_service import BaseService
from sage.core.api.function.sink_function import SinkFunction
from sage.core.operator.batch_operator import BatchOperator

print("=== Testing BaseRuntimeContext async service call functionality ===")

class TestAsyncService(BaseService):
    """测试异步服务"""
    
    def __init__(self):
        super().__init__()
        self._data = {}
    
    def store_data(self, key: str, value: str, delay: float = 0.1) -> str:
        """存储数据，模拟一些处理时间"""
        self.logger.info(f"TestAsyncService: Storing {key}={value} with {delay}s delay")
        time.sleep(delay)  # 模拟处理时间
        self._data[key] = value
        result = f"stored_{key}_{value}"
        self.logger.info(f"TestAsyncService: Storage completed, result: {result}")
        return result
    
    def get_data(self, key: str) -> str:
        """获取数据"""
        result = self._data.get(key, f"not_found_{key}")
        self.logger.info(f"TestAsyncService: Retrieved {key} -> {result}")
        return result

class AsyncTestFunction(BaseFunction):
    """测试异步调用的函数"""
    
    def execute(self, data: dict):
        key = data['key']
        value = data['value']
        
        self.logger.info(f"AsyncTestFunction: Testing async calls for {key}={value}")
        
        # 测试1: 基本异步调用
        self.logger.info("Test 1: Basic async call with future.result()")
        future1 = self.call_service_async["test_async_service"].store_data(key, value, 0.2)
        self.logger.info(f"Future created: {future1}")
        
        # 检查 Future 对象类型
        if not isinstance(future1, Future):
            raise TypeError(f"Expected Future object, got {type(future1)}")
        
        # 阻塞等待结果
        result1 = future1.result(timeout=5.0)
        self.logger.info(f"Async call result: {result1}")
        
        # 测试2: 非阻塞检查
        self.logger.info("Test 2: Non-blocking async call with done() check")
        future2 = self.call_service_async["test_async_service"].get_data(key)
        
        # 等待一下让调用完成
        time.sleep(0.1)
        
        if future2.done():
            result2 = future2.result()
            self.logger.info(f"Non-blocking result: {result2}")
        else:
            # 如果还没完成，阻塞等待
            result2 = future2.result(timeout=5.0)
            self.logger.info(f"Blocking result: {result2}")
        
        # 测试3: 超时测试
        self.logger.info("Test 3: Timeout test")
        future3 = self.call_service_async["test_async_service"].store_data(f"{key}_timeout", f"{value}_timeout", 0.05)
        try:
            result3 = future3.result(timeout=3.0)  # 应该足够完成
            self.logger.info(f"Timeout test passed: {result3}")
        except TimeoutError:
            self.logger.error("Unexpected timeout!")
            raise
        
        return {
            'async_test_passed': True,
            'key': key,
            'value': value,
            'result1': result1,
            'result2': result2,
            'result3': result3,
            'future_types_check': f"Future1: {type(future1)}, Future2: {type(future2)}, Future3: {type(future3)}"
        }

# 结果收集
test_results = []

class TestResultCollector(SinkFunction):
    """收集测试结果"""
    
    def execute(self, data):
        self.logger.info(f"TestResultCollector: {data}")
        test_results.append(data)
        return data

def test_async_service_calls():
    """测试异步服务调用"""
    
    # 创建环境
    env = LocalEnvironment()
    
    # 注册服务
    env.register_service("test_async_service", TestAsyncService)
    
    # 创建测试数据
    test_data = [
        {"key": "async_key_1", "value": "async_value_1"},
        {"key": "async_key_2", "value": "async_value_2"}
    ]
    
    # 创建数据流
    data_stream = env.from_batch(test_data)
    
    # 创建处理管道
    result_stream = (
        data_stream
        .map(AsyncTestFunction)
        .sink(TestResultCollector, parallelism=1)
    )
    
    print("🚀 Starting async test pipeline execution...")
    
    # 启动环境
    env.submit()
    
    # 让管道运行一段时间
    time.sleep(8)
    
    return test_results

if __name__ == "__main__":
    try:
        print("🚀 Running async service call tests...")
        results = test_async_service_calls()
        
        print("\n📊 Test Results:")
        if len(results) == 2:
            all_passed = all(r.get('async_test_passed', False) for r in results)
            if all_passed:
                print(f"✅ All async tests PASSED! ({len(results)}/2)")
                for i, result in enumerate(results, 1):
                    print(f"   Test {i}: {result['key']} -> {result['result1']}")
                    print(f"            Future types: {result['future_types_check']}")
            else:
                print("❌ Some async tests FAILED!")
                for result in results:
                    print(f"   {result}")
        else:
            print(f"⚠️  Unexpected number of results: {len(results)} (expected 2)")
            for result in results:
                print(f"   {result}")
                
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
