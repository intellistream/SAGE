import logging
import time
from dotenv import load_dotenv
import os
from sage_core.api.env import RemoteEnvironment
from sage_common_funs.io.source import FileSource
from sage_common_funs.io.sink import TerminalSink
from sage_common_funs.rag.generator import OpenAIGenerator
from sage_common_funs.rag.promptor import QAPromptor
from sage_common_funs.rag.retriever import DenseRetriever
from sage_utils.config_loader import load_config
from sage_utils.logging_utils import configure_logging

def pipeline_run():
    """创建并运行数据处理管道"""
    env = RemoteEnvironment(name="example_pipeline")
    env.set_memory(config = {"collection_name": "example_collection"})
    # 构建数据处理流程
    query_stream = env.from_source(FileSource, config["source"])
    query_and_chunks_stream = query_stream.map(DenseRetriever, config["retriever"])
    prompt_stream = query_and_chunks_stream.map(QAPromptor, config["promptor"])
    response_stream = prompt_stream.map(OpenAIGenerator, config["generator"])
    response_stream.sink(TerminalSink, config["sink"])
    # 提交管道并运行
    env.submit()
    env.run_streaming()  # 启动管道
    time.sleep(5)
    env.stop()  # 停止管道
    time.sleep(1000)

if __name__ == '__main__':
    configure_logging(level=logging.INFO)
    # 加载配置并初始化日志
    config = load_config('config_ray.yaml')
    load_dotenv(override=False)

    api_key = os.environ.get("ALIBABA_API_KEY")
    if api_key:
        config.setdefault("generator", {})["api_key"] = api_key
    pipeline_run()
