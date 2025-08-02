#!/usr/bin/env python3
"""
最小化的服务调用调试脚本
"""
import time
import logging
from sage.core.api.local_environment import LocalEnvironment

# 设置日志级别
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s | %(levelname)s | %(name)s | %(message)s')

class SimpleService:
    """简单的测试服务"""
    def __init__(self):
        pass
    
    def hello(self, name: str):
        print(f"[SERVICE] SimpleService.hello called with name: {name}")
        return f"Hello, {name}!"

def test_simple_service_call():
    """测试简单的服务调用"""
    print("🚀 Testing Simple Service Call")
    print("=" * 50)
    
    # 创建环境
    env = LocalEnvironment("simple_test")
    
    # 注册服务
    env.register_service("simple", SimpleService)
    print("✅ Service registered: simple")
    
    # 创建简单的批处理数据
    data = ["Alice", "Bob"]
    stream = env.from_batch(data)
    
    # 创建简单的处理函数
    from sage.core.function.base_function import BaseFunction
    
    class SimpleProcessor(BaseFunction):
        def execute(self, name):
            print(f"[PROCESSOR] Processing: {name}")
            try:
                result = self.call_service["simple"].hello(name, timeout=5.0)
                print(f"[PROCESSOR] Service call result: {result}")
                return {"name": name, "result": result}
            except Exception as e:
                print(f"[PROCESSOR] Service call failed: {e}")
                return {"name": name, "error": str(e)}
    
    # 构建管道
    result_stream = stream.map(SimpleProcessor).print()
    
    # 提交并运行
    try:
        env.submit()
        print("🏃 Pipeline running...")
        time.sleep(10)
    finally:
        env.close()

if __name__ == "__main__":
    test_simple_service_call()
