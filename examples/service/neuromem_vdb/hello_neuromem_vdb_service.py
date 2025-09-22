import logging
import time

from sage.common.utils.logging.custom_logger import CustomLogger
from sage.core.api.function.batch_function import BatchFunction
from sage.core.api.function.sink_function import SinkFunction
from sage.core.api.local_environment import LocalEnvironment
from sage.core.api.service.base_service import BaseService
from sage.middleware.components.neuromem.micro_service.neuromem_vdb_service import \
    NeuroMemVDBService


class HelloBatch(BatchFunction):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 三次固定提问
        self.queries = ["人工智能", "数据库", "教育"]
        self.counter = 0
        self.max_count = len(self.queries)

    def execute(self):
        if self.counter >= self.max_count:
            return None
        query = self.queries[self.counter]
        self.counter += 1
        return query


class PrintSink(SinkFunction):
    def execute(self, data):
        logging.info(f"\n>>> 检索 Query: {data}")
        # 调用服务搜索即可
        result = self.call_service["hello_neuromem_vdb_service"].retrieve(data, topk=5)
        logging.info(">>> 检索结果:", result)


def main():
    env = LocalEnvironment("hello_neuromem_vdb_service")

    # 使用 demo_collection, 创建服务最重要的一步！！！
    env.register_service(
        "hello_neuromem_vdb_service",
        NeuroMemVDBService,
        collection_name="demo_collection",
    )

    env.from_batch(HelloBatch).sink(PrintSink)

    try:
        logging.info("Waiting for batch processing to complete...")
        env.submit()

        time.sleep(3)
    except KeyboardInterrupt:
        logging.info("停止运行")
    finally:
        logging.info("Hello Neuromem Vdb Service 批处理示例结束")


if __name__ == "__main__":
    CustomLogger.disable_global_console_debug()
    main()
