import logging
import time
from sage.api.env import StreamingExecutionEnvironment
from sage.lib.function.promptor import QAPromptor
from sage.lib.function.generator import OpenAIGenerator
from sage.lib.function.retriever import DenseRetriever
from sage.lib.function.source import FileSource
from sage.lib.function.sink import FileSink,TerminalSink
from sage.core.neuromem.memory_manager import MemoryManager
from sage.utils.config_loader import load_config
from sage.utils.logging_utils import configure_logging
from sage.api.model.model_api import apply_embedding_model
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
    pipeline = StreamingExecutionEnvironment(name="example_pipeline")
    # 在config里指定各个节点跑在ray上边
    # 构建数据处理流程
    query_stream = pipeline.from_source(FileSource, config["source"])
    query_and_chunks_stream = query_stream.map(DenseRetriever, config["retriever"])
    prompt_stream = query_and_chunks_stream.map(QAPromptor, config["promptor"])
    response_stream = prompt_stream.map(OpenAIGenerator, config["generator"])
    response_stream.sink(TerminalSink, config["sink"])
    # 提交管道并运行
    pipeline.execute()
    time.sleep(100)  # 等待管道运行


if __name__ == '__main__':
    configure_logging(level=logging.INFO)
    # 加载配置并初始化日志
    config = load_config('config_ray.yaml')
    # 初始化内存并运行管道
    memory_init()
    pipeline_run()
