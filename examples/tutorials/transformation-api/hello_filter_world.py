# 此例意在说明 Fileter 算子的使用
import logging

from sage.common.utils.logging.custom_logger import CustomLogger
from sage.core.api.function.batch_function import BatchFunction
from sage.core.api.function.filter_function import FilterFunction
from sage.core.api.function.map_function import MapFunction
from sage.core.api.function.sink_function import SinkFunction
from sage.core.api.local_environment import LocalEnvironment


class HelloBatch(BatchFunction):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.counter = 0
        self.max_count = 10

    def execute(self):
        if self.counter >= self.max_count:
            return None
        self.counter += 1
        return f"Hello, World! #{self.counter}"


class UpperCaseMap(MapFunction):
    def execute(self, data):
        return data.upper()


class PrintSink(SinkFunction):
    def execute(self, data):
        logging.info(data)


# 过滤器示例，过滤所有偶数结尾的数据
class Oddpicker(FilterFunction):
    def execute(self, data):
        if int(data[-1]) % 2 != 0:
            return data
        else:
            return None


def main():
    env = LocalEnvironment("Hello_Filter_World")

    env.from_batch(HelloBatch).map(UpperCaseMap).filter(Oddpicker).sink(PrintSink)

    env.submit(autostop=True)
    logging.info("Hello Filter World 示例结束")


if __name__ == "__main__":
    # 关闭日志输出
    CustomLogger.disable_global_console_debug()
    main()
