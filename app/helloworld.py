import time
from sage.core.api.local_environment import LocalEnvironment
from sage.core.function.sink_function import SinkFunction
from sage.core.function.batch_function import BatchFunction
from sage.core.function.map_function import MapFunction

# 批处理数据源：生成10条 Hello, World! 数据
class HelloBatch(BatchFunction):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.counter = 0
        self.max_count = 10  # 生成10个数据包后返回None
    
    def execute(self):
        if self.counter >= self.max_count:
            return None  # 返回None表示批处理完成
        self.counter += 1
        return f"Hello, World! #{self.counter}"

# 简单的 MapFunction，将内容转大写
class UpperCaseMap(MapFunction):
    def execute(self, data):
        return data.upper()

# 简单 SinkFunction，直接打印结果
class PrintSink(SinkFunction):
    def execute(self, data):
        print(data)
        return data

def main():
    env = LocalEnvironment("hello_world_batch_demo")
    
    # 批处理源 -> map -> sink
    env.from_batch(HelloBatch).map(UpperCaseMap).sink(PrintSink)
    
    try:
        env.submit()
        # 让主线程睡眠，让批处理自动完成并停止
        print("Waiting for batch processing to complete...")
        time.sleep(5)  # 等待5秒
    except KeyboardInterrupt:
        print("停止运行")
    finally:
        print("Hello World 批处理示例结束")

if __name__ == "__main__":
    main()
