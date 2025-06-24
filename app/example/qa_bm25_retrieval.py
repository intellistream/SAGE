import logging
import time
from unittest import result
import yaml
from sage.api.pipeline import Pipeline
from sage.api.operator.operator_impl.promptor import QAPromptor
from sage.api.operator.operator_impl.generator import OpenAIGenerator
from sage.api.operator.operator_impl.retriever import BM25sRetriever
from sage.api.operator.operator_impl.source import FileSource
from sage.api.operator.operator_impl.sink import FileSink, TerminalSink
from sage.core.neuromem.memory_manager import MemoryManager
from sage.core.neuromem.test.embeddingmodel import MockTextEmbedder
from sage.utils.config_loader import load_config
from sage.utils.logging_utils import configure_logging

def memory_init():
    """初始化内存管理器并创建测试集合"""
    # default_model = MockTextEmbedder(fixed_dim=128)
    manager = MemoryManager()

    col = manager.create_collection(
        name="bm25_test",
        backend_type="KV",

        description="test vdb collection",
        as_ray_actor=False
    )
    ids = ["a", "b", "c"]
    texts = [
        "The quick brown fox jumps over the lazy dog.",
        "Hello world! This is a test document.",
        "Python is a great programming language."
    ]
    for i, text in enumerate(texts):
        col.insert(text)
    col.create_index(index_name="bm25s_index")
    config["retriever"]["bm25s_collection"] = col
    # result=col.retrieve("Python",index_name="bm25s_index")
    # print("检索结果:", result)


def pipeline_run():
    """创建并运行数据处理管道"""
    pipeline = Pipeline(name="example_pipeline", use_ray=False)
    # 构建数据处理流程
    query_stream = pipeline.add_source(FileSource, config)
    query_and_chunks_stream = query_stream.retrieve(BM25sRetriever, config)
    prompt_stream = query_and_chunks_stream.construct_prompt(QAPromptor, config)
    response_stream = prompt_stream.generate_response(OpenAIGenerator, config)
    response_stream.sink(TerminalSink, config)
    # 提交管道并运行
    pipeline.submit(config={"is_long_running": False})
    # time.sleep(100)  # 等待管道运行

if __name__ == '__main__':
    # 加载配置并初始化日志
    config = load_config('config_bm25s.yaml')
    configure_logging(level=logging.INFO)
    # 初始化内存并运行管道
    memory_init()
    pipeline_run()