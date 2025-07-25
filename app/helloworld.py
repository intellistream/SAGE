import time
import random
from sage.core.api.local_environment import LocalEnvironment
from sage.core.function.sink_function import SinkFunction
from sage.core.function.source_function import SourceFunction
from sage.core.function.map_function import MapFunction
# 简单数据源：每秒输出一条 Hello, World!
class HelloSource(SourceFunction):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.counter = 0
    def execute(self):
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
    env = LocalEnvironment("hello_world_demo")
    # 源 -> map -> sink
    env.from_source(HelloSource, delay=100).map(UpperCaseMap).sink(PrintSink)
    try:
        env.submit()
        time.sleep(5)  # 运行5秒，演示用
    except KeyboardInterrupt:
        print("停止运行")
    finally:
        print(":白色的对勾: Hello World 示例结束")
if __name__ == "__main__":
    main()
