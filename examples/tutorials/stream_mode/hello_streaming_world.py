import logging
from sage.common.utils.logging.custom_logger import CustomLogger
from sage.core.api.function.map_function import MapFunction
from sage.core.api.function.sink_function import SinkFunction
from sage.core.api.function.source_function import SourceFunction
from sage.core.api.local_environment import LocalEnvironment


# 流式数据源：从BatchFunction变成SourceFunction
class HelloStreaming(SourceFunction):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.counter = 0

    def execute(self):
        self.counter += 1
        return f"Hello, Streaming World! #{self.counter}"


class UpperCaseMap(MapFunction):
    def execute(self, data):
        return data.upper()


class PrintSink(SinkFunction):
    def execute(self, data):
        logging.info(data)


def main():
    env = LocalEnvironment("hello_streaming_world")

    # 流式源，从 from_batch 变成 from_source
    env.from_source(HelloStreaming).map(UpperCaseMap).sink(PrintSink)

    try:
        logging.info("Waiting for streaming processing to complete...")
        env.submit()

        # 暂停主程序，因为在LocalEnvironment下，流式处理是异步的
        from time import sleep

        sleep(1)

    except KeyboardInterrupt:
        logging.info("停止运行")
    finally:
        logging.info("Hello Streaming World 流式处理示例结束")


if __name__ == "__main__":
    # 关闭日志输出
    CustomLogger.disable_global_console_debug()
    main()
