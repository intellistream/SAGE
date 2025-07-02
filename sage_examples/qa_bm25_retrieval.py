import logging
from sage.api.env import Environment
from sage_lib import QAPromptor
from sage_lib.function.generator import OpenAIGenerator
from sage_lib.function.retriever import BM25sRetriever
from sage_lib.io.source import FileSource
from sage_lib.io.sink import TerminalSink
from sage_memory.memory_manager import MemoryManager
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
    # result=col.map("Python",index_name="bm25s_index")
    # print("检索结果:", result)


def pipeline_run():
    """创建并运行数据处理管道"""
    pipeline = Environment(name="example_pipeline")
    # 构建数据处理流程
    query_stream = pipeline.from_source(FileSource, config["source"])
    query_and_chunks_stream = query_stream.map(BM25sRetriever, config["retriever"])
    prompt_stream = query_and_chunks_stream.map(QAPromptor, config["promptor"])
    response_stream = prompt_stream.map(OpenAIGenerator, config["generator"])
    response_stream.sink(TerminalSink, config["sink"])
    # 提交管道并运行
    pipeline.execute()
    # time.sleep(100)  # 等待管道运行

if __name__ == '__main__':
    # 加载配置并初始化日志
    config = load_config('config_bm25s.yaml')
    configure_logging(level=logging.INFO)
    # 初始化内存并运行管道
    memory_init()
    pipeline_run()