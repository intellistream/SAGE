import logging
import time
import yaml
from sage.api.env import StreamingExecutionEnvironment
from sage.lib.function.chunk import CharacterSplitter
from sage.lib.function.writer import MemoryWriter
from sage.lib.function.source import FileSource
from sage.lib.function.sink import MemWriteSink
from sage.core.neuromem.memory_manager import MemoryManager
from sage.core.neuromem.embeddingmodel import MockTextEmbedder
from sage.utils.config_loader import load_config
from sage.utils.logging_utils import configure_logging


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
    pipeline = StreamingExecutionEnvironment(name="example_pipeline")
    # 构建数据处理流程
    source_stream = pipeline.from_source(FileSource, config["source"])
    chunk_stream = source_stream.map(CharacterSplitter, config["map"])
    memwrite_stream= chunk_stream.map(MemoryWriter,config["writer"])
    sink_stream= memwrite_stream.sink(MemWriteSink,config["sink"])
    pipeline.submit(config={"is_long_running": True})
    time.sleep(100)  # 等待管道运行

if __name__ == '__main__':
    # 加载配置并初始化日志
    config = load_config('config_for_ingest.yaml')
    logging.basicConfig(level=logging.INFO)
    # 初始化内存并运行管道
    memory_init()
    pipeline_run()