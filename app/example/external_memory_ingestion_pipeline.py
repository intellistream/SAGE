import logging
import time
import yaml
from sage.api.pipeline import Pipeline
from sage.api.operator.operator_impl.chunk import CharacterSplitter
from sage.api.operator.operator_impl.writer import MemoryWriter
from sage.api.operator.operator_impl.source import FileSource
from sage.api.operator.operator_impl.sink import MemWriteSink
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
    config["writer"]["ltm_collection"] = col

def pipeline_run(): 
    pipeline = Pipeline(name="example_pipeline", use_ray=False)
    # 构建数据处理流程
    source_stream = pipeline.add_source(FileSource, config)
    chunk_stream = source_stream.chunk(CharacterSplitter,config)
    memwrite_stream= chunk_stream.write_mem(MemoryWriter,config)
    sink_stream= memwrite_stream.sink(MemWriteSink,config)
    pipeline.submit(config={"is_long_running": True})
    time.sleep(100)  # 等待管道运行

if __name__ == '__main__':
    # 加载配置并初始化日志
    config = load_config('./app/config_for_ingest.yaml')
    logging.basicConfig(level=logging.INFO)
    # 初始化内存并运行管道
    memory_init()
    pipeline_run()