import logging
import yaml
from sage.api.pipeline import Pipeline
from sage.api.operator.operator_impl.retriever import SimpleRetriever
from sage.api.operator.operator_impl.promptor import QAPromptor
from sage.api.operator.operator_impl.generator import OpenAIGenerator
from sage.api.operator.operator_impl.chunk import CharacterSplitter
from sage.api.operator.operator_impl.writer import MemoryWriter
from sage.api.operator.operator_impl.source import FileSourceFunction
from sage.api.operator.operator_impl.sink import MemWriteSink,FileSink
from sage.core.neuromem.memory_manager import MemoryManager
from sage.core.neuromem.test.embeddingmodel import MockTextEmbedder
def load_config(path: str) -> dict:
    """加载YAML配置文件"""
    with open(path, 'r') as f:
        return yaml.safe_load(f)

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
    pipeline = Pipeline(name="ingest_pipeline", use_ray=False)
    # 构建数据处理流程
    source_stream = pipeline.add_source(FileSourceFunction, config_for_ingest)
    chunk_stream = source_stream.chunk(CharacterSplitter,config_for_ingest)
    memwrite_stream= chunk_stream.write_mem(MemoryWriter,config_for_ingest)
    sink_stream= memwrite_stream.sink(MemWriteSink,config_for_ingest)
    pipeline.submit(config={"is_long_running": True})

def qa_pipeline_run():
    """创建并运行数据处理管道"""
    pipeline = Pipeline(name="qa_pipeline", use_ray=False)
    # 构建数据处理流程
    query_stream = pipeline.add_source(FileSourceFunction, config_for_qa)
    query_and_chunks_stream = query_stream.retrieve(SimpleRetriever, config_for_qa)
    prompt_stream = query_and_chunks_stream.construct_prompt(QAPromptor, config_for_qa)
    response_stream = prompt_stream.generate_response(OpenAIGenerator, config_for_qa)
    response_stream.sink(FileSink, config_for_qa)
    # 提交管道并运行
    pipeline.submit(config={"is_long_running": True})

if __name__ == '__main__':
    # 加载配置并初始化日志
    config_for_ingest= load_config('./app/config_for_ingest.yaml')
    config_for_qa= load_config('./app/config_for_qa.yaml')
    logging.basicConfig(level=logging.INFO)
    # 初始化内存并运行管道
    memory_init()
    ingest_pipeline_run()
    qa_pipeline_run()