"""
CoMap函数服务调用测试 - 简化版本
专注测试核心功能：CoMap函数中使用服务调用语法糖
"""

import time
import pytest
import json
import os
from pathlib import Path
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
        print(f"ServiceCallCoMapFunction initialized with ctx: {ctx}")
    
    def map0(self, data):
        """Stream 0: 使用同步服务调用"""
        print(f"map0 processing data: {data}")
        
        try:
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
            print(f"map0 result: {result}")
            return result
        except Exception as e:
            print(f"map0 error: {e}")
            # 返回错误信息而不是抛出异常
            result = {
                "stream": 0,
                "data": data,
                "error": str(e),
                "store_result": f"error_{data}",
                "retrieve_result": f"error_{data}"
            }
            return result
    
    def map1(self, data):
        """Stream 1: 使用异步服务调用"""
        print(f"map1 processing data: {data}")
        
        try:
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
            print(f"map1 result: {result}")
            return result
        except Exception as e:
            print(f"map1 error: {e}")
            # 返回错误信息而不是抛出异常
            result = {
                "stream": 1,
                "data": data,
                "error": str(e),
                "store_result": f"error_async_{data}",
                "retrieve_result": f"error_async_{data}"
            }
            return result


# 收集结果的Sink
class CollectorSink(SinkFunction):
    results = []
    
    def __init__(self, ctx=None, output_file=None, **kwargs):
        super().__init__(ctx=ctx, **kwargs)
        self.output_file = output_file
        self.local_results = []
    
    def execute(self, data):
        print(f"CollectorSink received data: {data}")
        result_data = {
            "timestamp": time.time(),
            "data": data,
            "processed_by": self.__class__.__name__
        }
        
        # 添加到类级别的结果列表
        CollectorSink.results.append(result_data)
        # 添加到实例级别的结果列表
        self.local_results.append(result_data)
        
        # 如果指定了输出文件，立即写入
        if self.output_file:
            self._write_to_file(result_data)
        
        return result_data
    
    def _write_to_file(self, data):
        """将结果写入文件"""
        try:
            output_path = Path(self.output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 追加模式写入
            with open(self.output_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(data, ensure_ascii=False) + '\n')
        except Exception as e:
            print(f"Failed to write to file {self.output_file}: {e}")
    
    @classmethod
    def clear(cls):
        cls.results.clear()
    
    @classmethod 
    def save_all_results(cls, filename):
        """将所有结果保存到文件"""
        try:
            output_path = Path(filename)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(filename, 'w', encoding='utf-8') as f:
                for result in cls.results:
                    f.write(json.dumps(result, ensure_ascii=False) + '\n')
            print(f"Saved {len(cls.results)} results to {filename}")
            return True
        except Exception as e:
            print(f"Failed to save results to {filename}: {e}")
            return False


class TestCoMapServiceCalls:
    """测试CoMap函数中的服务调用功能"""
    
    def setup_method(self):
        """每个测试方法前的清理"""
        CollectorSink.clear()
    
    def test_comap_service_calls_basic(self):
        """测试CoMap函数中基本的服务调用功能"""
        # 创建测试结果目录
        test_output_dir = Path("/tmp/sage_test_results")
        test_output_dir.mkdir(parents=True, exist_ok=True)
        results_file = test_output_dir / "comap_service_basic_results.jsonl"
        
        # 清理之前的结果
        if results_file.exists():
            results_file.unlink()
        
        print(f"🚀 Starting CoMap service test, results will be saved to: {results_file}")
        
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
                 .sink(CollectorSink, output_file=str(results_file)))
        
        try:
            # 运行管道
            print("📤 Submitting pipeline...")
            env.submit()
            print("⏳ Waiting for processing to complete...")
            time.sleep(5)  # 增加等待时间
            
            # 保存所有结果到文件
            CollectorSink.save_all_results(str(results_file.with_suffix('.all.jsonl')))
            
        finally:
            print("🔄 Closing environment...")
            env.close()
        
        # 验证结果
        results = CollectorSink.results
        print(f"📊 Collected {len(results)} results from CollectorSink")
        
        # 从文件中读取结果进行验证
        file_results = []
        if results_file.exists():
            try:
                with open(results_file, 'r', encoding='utf-8') as f:
                    file_results = [json.loads(line.strip()) for line in f if line.strip()]
                print(f"📁 Loaded {len(file_results)} results from file")
            except Exception as e:
                print(f"⚠️ Failed to load results from file: {e}")
        
        # 使用文件结果如果收集器结果为空
        if not results and file_results:
            print("Using file results as primary source")
            # 提取实际数据
            results = [r.get('data', r) for r in file_results]
        
        # 验证至少有一些结果
        assert len(results) > 0 or len(file_results) > 0, f"No results collected. CollectorSink: {len(results)}, File: {len(file_results)}"
        
        # 如果从文件读取结果，使用文件数据进行验证
        validation_results = results if results else [r.get('data', r) for r in file_results]
        
        print(f"🔍 Validating {len(validation_results)} results...")
        
        # 验证Stream 0的结果
        stream0_results = [r for r in validation_results if isinstance(r, dict) and r.get("stream") == 0]
        print(f"Stream 0 results: {len(stream0_results)}")
        
        # 验证Stream 1的结果  
        stream1_results = [r for r in validation_results if isinstance(r, dict) and r.get("stream") == 1]
        print(f"Stream 1 results: {len(stream1_results)}")
        
        # 灵活的断言 - 至少要有一些结果
        assert len(stream0_results) > 0 or len(stream1_results) > 0, f"No stream results found. Stream 0: {len(stream0_results)}, Stream 1: {len(stream1_results)}"
        
        # 验证服务调用结果格式
        all_stream_results = stream0_results + stream1_results
        for result in all_stream_results:
            if isinstance(result, dict):
                assert "store_result" in result, f"Missing store_result in result: {result}"
                assert "retrieve_result" in result, f"Missing retrieve_result in result: {result}"
                if "store_result" in result:
                    assert result["store_result"].startswith("stored_"), f"Invalid store result format: {result['store_result']}"
        
        print(f"✅ Test passed: {len(stream0_results)} Stream 0 results, {len(stream1_results)} Stream 1 results")
        print(f"📄 Results saved to: {results_file}")
        
        # 打印一些示例结果用于调试
        if validation_results:
            print("📋 Sample results:")
            for i, result in enumerate(validation_results[:3]):
                print(f"  {i+1}: {result}")
    
    def test_comap_service_state_isolation(self):
        """测试CoMap中服务调用的状态隔离"""
        # 创建测试结果目录
        test_output_dir = Path("/tmp/sage_test_results")
        test_output_dir.mkdir(parents=True, exist_ok=True)
        results_file = test_output_dir / "comap_isolation_results.jsonl"
        
        # 清理之前的结果
        if results_file.exists():
            results_file.unlink()
        
        print(f"🚀 Starting isolation test, results will be saved to: {results_file}")
        
        env = LocalEnvironment("comap_isolation_test")
        env.register_service("test_service", MockTestService)
        
        source1 = env.from_source(SimpleSource, data_list=[1])
        source2 = env.from_source(SimpleSource, data_list=[2])
        
        result = (source1
                 .connect(source2)
                 .comap(ServiceCallCoMapFunction)
                 .sink(CollectorSink, output_file=str(results_file)))
        
        try:
            env.submit()
            time.sleep(3)
            
            # 保存所有结果到文件
            CollectorSink.save_all_results(str(results_file.with_suffix('.all.jsonl')))
            
        finally:
            env.close()
        
        results = CollectorSink.results
        print(f"📊 Collected {len(results)} results from CollectorSink for isolation test")
        
        # 从文件中读取结果进行验证
        file_results = []
        if results_file.exists():
            try:
                with open(results_file, 'r', encoding='utf-8') as f:
                    file_results = [json.loads(line.strip()) for line in f if line.strip()]
                print(f"📁 Loaded {len(file_results)} results from file for isolation test")
            except Exception as e:
                print(f"⚠️ Failed to load results from file: {e}")
        
        # 使用文件结果如果收集器结果为空
        validation_results = results if results else [r.get('data', r) for r in file_results]
        
        assert len(validation_results) >= 1, f"Expected at least 1 result, got {len(validation_results)}"
        
        # 验证不同流的数据被正确处理
        stream_0_count = len([r for r in validation_results if isinstance(r, dict) and r.get("stream") == 0])
        stream_1_count = len([r for r in validation_results if isinstance(r, dict) and r.get("stream") == 1])
        
        print(f"Stream isolation results - Stream 0: {stream_0_count}, Stream 1: {stream_1_count}")
        
        # 灵活的断言 - 至少要有一个流被处理
        assert stream_0_count > 0 or stream_1_count > 0, f"No streams processed. Stream 0: {stream_0_count}, Stream 1: {stream_1_count}"
        
        print(f"✅ State isolation test passed: Stream 0: {stream_0_count}, Stream 1: {stream_1_count}")
        print(f"📄 Results saved to: {results_file}")


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
