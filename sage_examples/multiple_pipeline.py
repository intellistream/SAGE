import logging
from sage.api.env import Environment
from sage_lib.function.retriever import DenseRetriever
from sage_lib import QAPromptor
from sage_lib.function.generator import OpenAIGenerator
from sage_lib.function.chunk import CharacterSplitter
from sage_lib.function.writer import MemoryWriter
from sage_lib.io.source import FileSource
from sage_lib.io.sink import MemWriteSink,FileSink
from sage_memory.memory_manager import MemoryManager
from sage_memory.embeddingmodel import MockTextEmbedder

from sage_utils.config_loader import load_config


def memory_init():
    """初始化内存管理器并创建测试集合"""
    default_model = MockTextEmbedder(fixed_dim=128)
    manager = MemoryManager()
    col = manager.create_collection(
        name="vdb_test",
        backend_type="VDB",
        embedding_model=default_model,
        dim=128,
        description="operator_test vdb collection",
        as_ray_actor=False,
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
    config_for_ingest["writer"]["ltm_collection"] = col
    config_for_qa["retriever"]["ltm_collection"] = col
def ingest_pipeline_run():
    pipeline = Environment(name="ingest_pipeline")
    # 构建数据处理流程
    source_stream = pipeline.from_source(FileSource, config_for_ingest["source"])
    chunk_stream = source_stream.map(CharacterSplitter,config_for_ingest["chunk"])
    memwrite_stream= chunk_stream.map(MemoryWriter,config_for_ingest["writer"])
    sink_stream= memwrite_stream.sink(MemWriteSink,config_for_ingest["sink"])
    pipeline.execute()

def qa_pipeline_run():
    """创建并运行数据处理管道"""
    pipeline = Environment(name="qa_pipeline")
    # 构建数据处理流程
    query_stream = pipeline.from_source(FileSource, config_for_qa["source"])
    query_and_chunks_stream = query_stream.map(DenseRetriever, config_for_qa["retriever"])
    prompt_stream = query_and_chunks_stream.map(QAPromptor, config_for_qa["promptor"])
    response_stream = prompt_stream.map(OpenAIGenerator, config_for_qa["generator"])
    response_stream.sink(FileSink, config_for_qa["sink"])
    # 提交管道并运行
    pipeline.execute()

if __name__ == '__main__':
    # 加载配置并初始化日志
    config_for_ingest= load_config('config_for_ingest.yaml')
    config_for_qa= load_config('config_for_qa.yaml')
    logging.basicConfig(level=logging.INFO)
    # 初始化内存并运行管道
    memory_init()
    ingest_pipeline_run()
    qa_pipeline_run()