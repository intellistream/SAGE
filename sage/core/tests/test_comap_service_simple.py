"""
CoMap函数服务调用测试 - 简化版本
专注测试核心功能：CoMap函数中使用服务调用语法糖
"""

import time
import pytest
from sage.core.api.local_environment import LocalEnvironment
from sage.core.function.source_function import SourceFunction
from sage.core.function.comap_function import BaseCoMapFunction
from sage.core.function.sink_function import SinkFunction


# 简单的测试服务（改名避免pytest收集警告）
class MockTestService:
    def __init__(self):
        self.data = {}
        self.call_count = 0
    
    def store(self, key, value):
        self.call_count += 1
        self.data[key] = value
        return f"stored_{key}"
    
    def retrieve(self, key):
        self.call_count += 1
        return self.data.get(key, f"default_{key}")


# 测试数据源
class SimpleSource(SourceFunction):
    def __init__(self, ctx=None, data_list=None, **kwargs):
        super().__init__(ctx=ctx, **kwargs)
        self.data_list = data_list or [1, 2, 3]
        self.counter = 0
    
    def execute(self):
        if self.counter >= len(self.data_list):
            return None
        data = self.data_list[self.counter]
        self.counter += 1
        return data


# 测试CoMap函数
class ServiceCallCoMapFunction(BaseCoMapFunction):
    """测试CoMap函数中的服务调用"""
    
    def __init__(self, ctx=None, **kwargs):
        super().__init__(ctx=ctx, **kwargs)
        self.results = []
    
    def map0(self, data):
        """Stream 0: 使用同步服务调用"""
        # 同步调用服务
        store_result = self.call_service["test_service"].store(f"key_{data}", f"value_{data}")
        retrieve_result = self.call_service["test_service"].retrieve(f"key_{data}")
        
        result = {
            "stream": 0,
            "data": data,
            "store_result": store_result,
            "retrieve_result": retrieve_result
        }
        self.results.append(result)
        return result
    
    def map1(self, data):
        """Stream 1: 使用异步服务调用"""
        # 异步调用服务
        store_future = self.call_service_async["test_service"].store(f"async_key_{data}", f"async_value_{data}")
        retrieve_future = self.call_service_async["test_service"].retrieve(f"async_key_{data}")
        
        # 获取异步结果
        store_result = store_future.result(timeout=2.0)
        retrieve_result = retrieve_future.result(timeout=2.0)
        
        result = {
            "stream": 1,
            "data": data,
            "store_result": store_result,
            "retrieve_result": retrieve_result
        }
        self.results.append(result)
        return result


# 收集结果的Sink
class CollectorSink(SinkFunction):
    results = []
    
    def __init__(self, ctx=None, **kwargs):
        super().__init__(ctx=ctx, **kwargs)
    
    def execute(self, data):
        CollectorSink.results.append(data)
        return data
    
    @classmethod
    def clear(cls):
        cls.results.clear()


class TestCoMapServiceCalls:
    """测试CoMap函数中的服务调用功能"""
    
    def setup_method(self):
        """每个测试方法前的清理"""
        CollectorSink.clear()
    
    def test_comap_service_calls_basic(self):
        """测试CoMap函数中基本的服务调用功能"""
        # 创建环境并注册服务
        env = LocalEnvironment("comap_service_basic_test")
        env.register_service("test_service", MockTestService)
        
        # 创建数据源
        source1 = env.from_source(SimpleSource, data_list=[10, 20])
        source2 = env.from_source(SimpleSource, data_list=[100, 200])
        
        # 构建CoMap管道
        result = (source1
                 .connect(source2)
                 .comap(ServiceCallCoMapFunction)
                 .sink(CollectorSink))
        
        try:
            # 运行管道
            env.submit()
            time.sleep(3)  # 等待处理完成
        finally:
            env.close()
        
        # 验证结果
        results = CollectorSink.results
        assert len(results) > 0, "No results collected"
        
        # 验证Stream 0的结果
        stream0_results = [r for r in results if r.get("stream") == 0]
        assert len(stream0_results) > 0, "No Stream 0 results"
        
        # 验证Stream 1的结果
        stream1_results = [r for r in results if r.get("stream") == 1]
        assert len(stream1_results) > 0, "No Stream 1 results"
        
        # 验证服务调用结果
        for result in stream0_results:
            assert "store_result" in result, "Missing store_result in Stream 0"
            assert "retrieve_result" in result, "Missing retrieve_result in Stream 0"
            assert result["store_result"].startswith("stored_"), "Invalid store result format"
        
        for result in stream1_results:
            assert "store_result" in result, "Missing store_result in Stream 1"
            assert "retrieve_result" in result, "Missing retrieve_result in Stream 1"
            assert result["store_result"].startswith("stored_"), "Invalid store result format"
        
        print(f"✅ Test passed: {len(stream0_results)} Stream 0 results, {len(stream1_results)} Stream 1 results")
    
    def test_comap_service_state_isolation(self):
        """测试CoMap中服务调用的状态隔离"""
        env = LocalEnvironment("comap_isolation_test")
        env.register_service("test_service", MockTestService)
        
        source1 = env.from_source(SimpleSource, data_list=[1])
        source2 = env.from_source(SimpleSource, data_list=[2])
        
        result = (source1
                 .connect(source2)
                 .comap(ServiceCallCoMapFunction)
                 .sink(CollectorSink))
        
        try:
            env.submit()
            time.sleep(2)
        finally:
            env.close()
        
        results = CollectorSink.results
        assert len(results) >= 2, f"Expected at least 2 results, got {len(results)}"
        
        # 验证不同流的数据被正确处理
        stream_0_count = len([r for r in results if r.get("stream") == 0])
        stream_1_count = len([r for r in results if r.get("stream") == 1])
        
        assert stream_0_count > 0, "Stream 0 not processed"
        assert stream_1_count > 0, "Stream 1 not processed"
        
        print(f"✅ State isolation test passed: Stream 0: {stream_0_count}, Stream 1: {stream_1_count}")


def test_standalone_comap_service_integration():
    """独立运行的CoMap服务集成测试"""
    print("\n🚀 Running CoMap Service Integration Test")
    
    test_instance = TestCoMapServiceCalls()
    test_instance.setup_method()
    
    try:
        test_instance.test_comap_service_calls_basic()
        test_instance.setup_method()  # 清理
        test_instance.test_comap_service_state_isolation()
        
        print("🎉 All CoMap service integration tests passed!")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        pytest.fail(f"CoMap service integration test failed: {e}")


if __name__ == "__main__":
    success = test_standalone_comap_service_integration()
    if not success:
        exit(1)
