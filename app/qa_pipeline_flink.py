# app/custom_pipeline.py

import logging
import time

from sage.utils.config_loader import load_config
from sage.utils.logging_utils import configure_logging

from sage.api.memory.manager import MemoryManager
from sage.api.embedding.embedding import EmbeddingModelFactory

from sage.api.execution.env import StreamingExecutionEnvironment

# 从 API 层导入内置 Function 类
from sage.api.function import (
    FileSource,
    SimpleRetriever,
    QAPromptor,
    OpenAIGenerator,
    FileSink
)
# 引入 Function 基类，便于自定义
from sage.api.function.base import Function


class MyMapFunction(Function):
    """
    自定义业务 Function：在检索前给 query 加个前缀示例
    """
    def open(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.prefix = self.config.get("custom_prefix", ">> ")

    def process(self, record):
        # record 为单条输入（FileSource 输出的字符串）
        modified = self.prefix + record
        self.logger.info(f"MyMapFunction modified record: {modified}")
        return modified  # 下游会收到这个字符串

    def close(self):
        self.logger.info("MyMapFunction closed.")


def build_and_run_pipeline(config: dict):
    """
    完整示例：自定义 MapFunction + 内置算子
    """
    # 1. 初始化 Memory
    mgr = MemoryManager()
    embedder = EmbeddingModelFactory.mock(fixed_dim=128)
    col = mgr.create_collection(
        name="vdb_test",
        backend_type="VDB",
        embedding_model=embedder,
        dim=128,
        description="demo vdb"
    )
    # 将底层 collection 传给检索算子
    config["retriever"]["ltm_collection"] = col._collection

    # 2. 创建 Flink‐style 流式执行环境
    env = StreamingExecutionEnvironment(
        job_name="custom_job",
        config=config,
        use_ray=True,
    )

    # 3. 构建数据流
    ds = env.from_source(FileSource)         # 读取文件，每条记录是字符串
    ds = ds.map(MyMapFunction)               # 自定义映射：加前缀
    ds = ds.map(SimpleRetriever)             # 检索，输出 (query, chunks)
    ds = ds.map(QAPromptor)                  # 构建 prompt
    ds = ds.map(OpenAIGenerator)             # 调用生成器
    ds = ds.sink(FileSink)                   # 写入文件

    # 4. 提交并执行
    env.execute()

    # 保持进程存活以便观察
    time.sleep(100)


if __name__ == "__main__":
    configure_logging(level=logging.INFO)
    cfg = load_config("config/config_for_qa.yaml")
    build_and_run_pipeline(cfg)
