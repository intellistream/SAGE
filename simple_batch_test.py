#!/usr/bin/env python3
"""
简单的批处理测试
"""
import time
from sage.core.api.local_environment import LocalEnvironment
from sage.core.function.batch_function import BatchFunction
from sage.core.function.sink_function import SinkFunction
from sage.utils.custom_logger import CustomLogger

class SimpleBatch(BatchFunction):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.counter = 0
        self.max_count = 3  # 只生成3个数据包

    def execute(self):
        if self.counter >= self.max_count:
            print(f"SimpleBatch: 完成，已生成 {self.counter} 个数据包")
            return None  # 返回None表示批处理完成
        
        self.counter += 1
        result = f"Data #{self.counter}"
        print(f"SimpleBatch: 生成 {result}")
        return result

class SimpleSink(SinkFunction):
    def execute(self, data):
        print(f"SimpleSink: 接收到 {data}")
        return data

def main():
    print("=== 简单批处理测试 ===")
    
    env = LocalEnvironment("simple_batch_test")
    
    # 创建简单的批处理管道
    env.from_batch(SimpleBatch).sink(SimpleSink)
    
    try:
        print("开始批处理...")
        env.submit()
        time.sleep(5)  # 等待处理完成
    except KeyboardInterrupt:
        print("测试中断")
    finally:
        print("测试结束")

if __name__ == '__main__':
    CustomLogger.disable_global_console_debug()
    main()
