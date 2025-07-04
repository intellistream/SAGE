import logging
import time
from sage_core.api.env import LocalEnvironment
from sage_common_funs.io.sink import MemWriteSink
from sage_common_funs.io.source import FileSource
from sage_common_funs.rag.chunk import CharacterSplitter
from sage_common_funs.rag.writer import MemoryWriter
from sage_utils.config_loader import load_config


def pipeline_run():
    env = LocalEnvironment(name="example_pipeline")
    env.set_memory()

    # 构建数据处理流程
    source_stream = env.from_source(FileSource, config["source"])
    chunk_stream = source_stream.map(CharacterSplitter, config["map"])
    memwrite_stream= chunk_stream.map(MemoryWriter,config["writer"])
    sink_stream= memwrite_stream.sink(MemWriteSink,config["sink"])
    env.submit()
    env.run_streaming()  # 启动管道
    time.sleep(100)  # 等待管道运行

if __name__ == '__main__':
    # 加载配置并初始化日志
    config = load_config('config_for_ingest.yaml')
    logging.basicConfig(level=logging.INFO)
    # 初始化内存并运行管道
    pipeline_run()