import logging
import time

from sage.api.env import LocalEnvironment
from sage_common_funs.io.sink import TerminalSink
from sage_common_funs.rag.generator import OpenAIGenerator
from sage_common_funs.rag.manual_source import ManualSource
from sage_common_funs.rag.promptor import QAPromptor
from sage_common_funs.rag.retriever import DenseRetriever
from sage_memory.memory_manager import MemoryManager
from sage_utils.config_loader import load_config
from sage_utils.logging_utils import configure_logging
from sage_utils.embedding_methods.embedding_api import apply_embedding_model


def memory_init():
    """初始化内存管理器并创建测试集合"""
    manager = MemoryManager()
    embedding_model = apply_embedding_model("hf", model="sentence-transformers/all-MiniLM-L6-v2")
    col = manager.create_collection(
        name="vdb_test",
        backend_type="VDB",
        embedding_model=embedding_model,
        dim=embedding_model.get_dim(),
        description="test vdb collection",
        as_ray_actor=True
    )
    col.add_metadata_field("owner")
    col.add_metadata_field("show_type")
    texts = [
        ("hello world", {"owner": "ruicheng", "show_type": "text"}),
        ("你好，世界", {"owner": "Jun", "show_type": "text"}),
        ("こんにちは、世界", {"owner": "Lei", "show_type": "img"}),
    ]
    for text, metadata in texts:
        col.insert(text, metadata)
    col.create_index(index_name="vdb_index")
    config["retriever"]["ltm_collection"] = col._collection





def pipeline_run():
    """创建并运行数据处理管道"""
    pipeline = LocalEnvironment()
    # 构建数据处理流程
    manual_source = ManualSource(config["source"])
    query_stream = pipeline.from_source(manual_source)
    query_and_chunks_stream = query_stream.map(DenseRetriever, config["retriever"])
    prompt_stream = query_and_chunks_stream.map(QAPromptor, config["promptor"])
    response_stream = prompt_stream.map(OpenAIGenerator, config["generator"])
    response_stream.sink(TerminalSink, config["sink"])
    # 提交管道并运行
    pipeline.submit_mixed(config={"is_long_running":True})
    manual_source.push("What is the capital of France?")
    manual_source.push("What is the capital of Japan?")
    manual_source.push("What is the capital of China?")
    time.sleep(100)  # 等待管道运行


if __name__ == '__main__':
    configure_logging(level=logging.INFO)
    # 加载配置并初始化日志
    config = load_config('./config_instance.yaml')
    # 初始化内存并运行管道
    memory_init()
    pipeline_run()
