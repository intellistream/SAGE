import logging
import time
from sage.api.env import Environment
from sage_lib_functions.io.sink import MemWriteSink
from sage_lib_functions.io.source import FileSource
from sage_lib_functions.rag.chunk import CharacterSplitter
from sage_lib_functions.rag.writer import MemoryWriter
from sage_utils.config_loader import load_config


def pipeline_run():
    env = Environment(name="example_pipeline")
    env.set_memory()

    # 构建数据处理流程
    source_stream = env.from_source(FileSource, config["source"])
    chunk_stream = source_stream.map(CharacterSplitter, config["map"])
    memwrite_stream= chunk_stream.map(MemoryWriter,config["writer"])
    sink_stream= memwrite_stream.sink(MemWriteSink,config["sink"])
    env.execute()
    time.sleep(100)  # 等待管道运行

if __name__ == '__main__':
    # 加载配置并初始化日志
    config = load_config('config_for_ingest.yaml')
    logging.basicConfig(level=logging.INFO)
    # 初始化内存并运行管道
    pipeline_run()