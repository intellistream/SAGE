import logging
import time
from sage.api.pipeline import Pipeline
from sage.api.operator.operator_impl.promptor import QAPromptor
from sage.api.operator.operator_impl.generator import OpenAIGenerator
from sage.api.operator.operator_impl.retriever import DenseRetriever
from sage.api.operator.operator_impl.source import FileSource
from sage.api.operator.operator_impl.sink import TerminalSink
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
        as_ray_actor=False
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
    pipeline = Pipeline(name="example_pipeline")
    # 构建数据处理流程
    query_stream = (pipeline
        .add_source(FileSource, config["source"])
        .retrieve(DenseRetriever, config["retriever"])
        .construct_prompt(QAPromptor, config["promptor"])
        .generate_response(OpenAIGenerator, config["generator"])
        .sink(TerminalSink, config["sink"])
    )
    pipeline.submit(config={"is_long_running":False})
    # time.sleep(100)  # 等待管道运行


if __name__ == '__main__':
    configure_logging(level=logging.INFO)
    # 加载配置并初始化日志
    config = load_config('config.yaml')
    # 初始化内存并运行管道
    memory_init()
    pipeline_run()
