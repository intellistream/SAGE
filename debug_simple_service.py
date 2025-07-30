#!/usr/bin/env python3

"""
最简单的服务调用调试脚本
直接测试CoMap中的服务调用是否工作
"""

import time
import sys
import os

# 添加项目根目录到 sys.path
sys.path.insert(0, '/home/shuhao/SAGE')

from sage.core.api.local_environment import LocalEnvironment
from sage.core.function.source_function import SourceFunction
from sage.core.function.comap_function import BaseCoMapFunction
from sage.core.function.sink_function import SinkFunction


class SimpleTestService:
    """最简单的测试服务"""
    
    def hello(self, name: str) -> str:
        return f"Hello {name}!"


class SimpleDataSource(SourceFunction):
    """简单数据源"""
    
    def __init__(self, ctx=None, **kwargs):
        super().__init__(ctx=ctx, **kwargs)
        self.counter = 0
        self.data = ["test1", "test2"]
    
    def execute(self):
        if self.counter >= len(self.data):
            return None
        
        data = self.data[self.counter]
        self.counter += 1
        print(f"[DEBUG] SimpleDataSource generated: {data}")
        return data


class SimpleCoMapFunction(BaseCoMapFunction):
    """简单CoMap函数"""
    
    def __init__(self, ctx=None, **kwargs):
        super().__init__(ctx=ctx, **kwargs)
        self.processed = 0
    
    def map0(self, data):
        """处理Stream 0"""
        print(f"[DEBUG] CoMap.map0 called with: {data}")
        self.processed += 1
        
        # 尝试进行最简单的服务调用
        print(f"[DEBUG] About to call service...")
        try:
            result = self.call_service["test_service"].hello(data)
            print(f"[DEBUG] Service call succeeded: {result}")
            
            return {
                "stream": 0,
                "data": data,
                "service_result": result,
                "processed_count": self.processed
            }
        except Exception as e:
            print(f"[DEBUG] Service call failed: {e}")
            import traceback
            traceback.print_exc()
            return {
                "stream": 0,
                "data": data,
                "error": str(e),
                "processed_count": self.processed
            }
    
    def map1(self, data):
        """处理Stream 1"""
        print(f"[DEBUG] CoMap.map1 called with: {data}")
        return {
            "stream": 1,
            "data": data,
            "processed_count": self.processed
        }


class SimpleCollectorSink(SinkFunction):
    """简单收集器"""
    
    results = []
    
    def __init__(self, ctx=None, **kwargs):
        super().__init__(ctx=ctx, **kwargs)
    
    def execute(self, data):
        print(f"[DEBUG] Sink received: {data}")
        SimpleCollectorSink.results.append(data)
        return data


def test_simple_comap_service():
    print("🧪 Testing Simple CoMap Service Call")
    print("=" * 50)
    
    # 清理之前的结果
    SimpleCollectorSink.results.clear()
    
    # 创建环境
    env = LocalEnvironment("simple_test")
    
    # 注册服务
    env.register_service("test_service", SimpleTestService)
    print("✅ Service registered")
    
    # 创建数据源（只用一个流）
    stream1 = env.from_source(SimpleDataSource, delay=0.1)
    stream2 = env.from_source(SimpleDataSource, delay=0.1)  # 空流，只是为了满足CoMap需要
    
    # 构建管道
    result = (
        stream1
        .connect(stream2)
        .comap(SimpleCoMapFunction)
        .sink(SimpleCollectorSink)
    )
    
    print("📊 Pipeline created")
    
    try:
        # 提交管道
        env.submit()
        print("🏃 Pipeline running...")
        
        # 等待处理
        time.sleep(3)
        
    finally:
        env.close()
    
    # 检查结果
    print(f"\n📋 Results: {len(SimpleCollectorSink.results)}")
    for i, result in enumerate(SimpleCollectorSink.results):
        print(f"  {i+1}: {result}")
    
    return len(SimpleCollectorSink.results) > 0


if __name__ == "__main__":
    success = test_simple_comap_service()
    if success:
        print("\n✅ Test PASSED")
    else:
        print("\n❌ Test FAILED")
        sys.exit(1)
