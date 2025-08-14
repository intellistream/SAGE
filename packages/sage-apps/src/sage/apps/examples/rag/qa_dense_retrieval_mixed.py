import logging
import time
from dotenv import load_dotenv
import os
from sage.core.api.local_environment import LocalEnvironment
from sage.apps.libs.io_utils.source import FileSource
from sage.apps.libs.io_utils.sink import TerminalSink
from sage.apps.libs.rag.generator import OpenAIGenerator
from sage.apps.libs.rag.promptor import QAPromptor
from sage.apps.libs.rag.retriever import DenseRetriever
from sage.common.utils.config.loader import load_config

def pipeline_run():
    """创建并运行数据处理管道"""
    env = LocalEnvironment()
    #env.set_memory(config=None)
    # 构建数据处理流程
    query_stream = env.from_source(FileSource, config["source"])
    query_and_chunks_stream = query_stream.map(DenseRetriever, config["retriever"])
    prompt_stream = query_and_chunks_stream.map(QAPromptor, config["promptor"])
    response_stream = prompt_stream.map(OpenAIGenerator, config["generator"]["vllm"])
    response_stream.sink(TerminalSink, config["sink"])
    # 提交管道并运行
    env.submit()
    time.sleep(100)  # 等待管道运行


if __name__ == '__main__':
    # 加载配置并初始化日志
    config = load_config('config_mixed.yaml')
    load_dotenv(override=False)

    api_key = os.environ.get("ALIBABA_API_KEY")
    if api_key:
        config.setdefault("generator", {})["api_key"] = api_key

    pipeline_run()
