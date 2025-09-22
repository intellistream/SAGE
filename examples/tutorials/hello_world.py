import logging

from sage.common.utils.logging.custom_logger import CustomLogger
from sage.core.api.function.batch_function import BatchFunction
from sage.core.api.function.map_function import MapFunction
from sage.core.api.function.sink_function import SinkFunction
from sage.core.api.local_environment import LocalEnvironment


# 批处理数据源：作用是生成10条"Hello, World!"字符串
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
        logging.info(data)


def main():
    env = LocalEnvironment("Hello_World")

    # 批处理源 -> map -> sink
    env.from_batch(HelloBatch).map(UpperCaseMap).sink(PrintSink)

    env.submit(autostop=True)
    logging.info("Hello World 批处理示例结束")


if __name__ == "__main__":
    # 关闭日志输出
    CustomLogger.disable_global_console_debug()
    main()
