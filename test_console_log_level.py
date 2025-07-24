#!/usr/bin/env python3
"""
测试console日志等级设置功能
"""

from sage_core.environment.base_environment import BaseEnvironment
from sage_core.api.local_environment import LocalEnvironment
from sage_core.function.source_function import SourceFunction
from sage_core.function.map_function import MapFunction
from sage_core.function.sink_function import SinkFunction
import time

# 创建测试用的函数类
class TestSourceFunction(SourceFunction):
    """测试数据源，产生一系列数字"""
    def __init__(self, ctx=None, **kwargs):
        super().__init__(ctx, **kwargs)
        self.count = 0
        self.max_count = kwargs.get('max_count', 5)
    
    def execute(self):
        if self.count < self.max_count:
            data = f"数据_{self.count}"
            self.logger.debug(f"[DEBUG] 生成数据: {data}")
            self.logger.info(f"[INFO] 生成数据: {data}")
            self.logger.warning(f"[WARNING] 生成数据: {data}")
            self.logger.error(f"[ERROR] 生成数据: {data}")
            self.count += 1
            return data
        else:
            # 返回停止信号
            from sage_core.function.source_function import StopSignal
            return StopSignal("TestSource")

class TestMapFunction(MapFunction):
    """测试映射函数，对数据进行转换"""
    def execute(self, data):
        result = f"处理后的_{data}"
        self.logger.debug(f"[DEBUG] 数据转换: {data} -> {result}")
        self.logger.info(f"[INFO] 数据转换: {data} -> {result}")
        self.logger.warning(f"[WARNING] 数据转换: {data} -> {result}")
        self.logger.error(f"[ERROR] 数据转换: {data} -> {result}")
        return result

class TestSinkFunction(SinkFunction):
    """测试汇聚函数，输出数据"""
    def execute(self, data):
        self.logger.debug(f"[DEBUG] 输出数据: {data}")
        self.logger.info(f"[INFO] 输出数据: {data}")
        self.logger.warning(f"[WARNING] 输出数据: {data}")
        self.logger.error(f"[ERROR] 输出数据: {data}")
        print(f"最终输出: {data}")

def test_console_log_level_basic():
    """测试基本的控制台日志等级设置"""
    
    print("=== 测试基本console日志等级设置功能 ===")
    
    # 测试1: 创建本地环境
    env = LocalEnvironment("test_env")
    print(f"1. 默认console日志等级: {env.console_log_level}")
    
    # 测试2: 设置不同的日志等级
    print("\n2. 测试设置不同日志等级:")
    
    valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR"]
    for level in valid_levels:
        env.set_console_log_level(level)
        print(f"   设置为 {level}: {env.console_log_level}")
    
    # 测试3: 测试无效日志等级
    print("\n3. 测试无效日志等级:")
    try:
        env.set_console_log_level("INVALID")
        print("   ERROR: 应该抛出异常!")
    except ValueError as e:
        print(f"   正确: {e}")
    
    # 测试4: 测试大小写不敏感
    print("\n4. 测试大小写处理:")
    env.set_console_log_level("debug")
    print(f"   设置 'debug' -> {env.console_log_level}")
    env.set_console_log_level("Warning")
    print(f"   设置 'Warning' -> {env.console_log_level}")
    
    print("\n=== 基本测试完成 ===")

def test_pipeline_console_log_level():
    """测试流水线中算子的console日志等级"""
    
    print("\n=== 测试流水线中算子的console日志等级 ===")
    
    # 测试不同日志等级
    log_levels = ["DEBUG", "INFO", "WARNING", "ERROR"]
    
    for level in log_levels:
        print(f"\n--- 测试日志等级: {level} ---")
        
        # 创建环境并设置日志等级
        env = LocalEnvironment(f"pipeline_test_{level.lower()}")
        env.set_console_log_level(level)
        print(f"环境日志等级设置为: {env.console_log_level}")
        
        try:
            # 构建流水线
            (env
             .from_source(TestSourceFunction, max_count=2)
             .map(TestMapFunction)
             .sink(TestSinkFunction)
            )
            
            # 提交并运行
            print(f"提交流水线...")
            env.submit()
            
            # 等待一段时间让流水线运行
            print(f"等待流水线运行...")
            time.sleep(3)
            
            print(f"--- {level} 日志等级测试完成 ---")
            
        except Exception as e:
            print(f"流水线运行出错: {e}")
            import traceback
            traceback.print_exc()
        
        # 清理
        try:
            env.stop()
        except:
            pass

if __name__ == "__main__":
    # 先测试基本功能
    test_console_log_level_basic()
    
    # 再测试流水线功能
    test_pipeline_console_log_level()
