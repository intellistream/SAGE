
import logging

from sage.core.api.local_environment import LocalEnvironment
from sage.libs.io_utils.sink import TerminalSink
from sage.libs.io_utils.source import FileSource
from sage.libs.rag.generator import OpenAIGenerator
from sage.libs.rag.promptor import QAPromptor
from sage.libs.rag.retriever import BM25sRetriever
from sage.common.utils.config.loader import load_config


def pipeline_run():
    """创建并运行数据处理管道"""
    env = LocalEnvironment()
    # 构建数据处理流程
    query_stream = env.from_source(FileSource, config["source"])
    query_and_chunks_stream = query_stream.map(BM25sRetriever, config["retriever"])
    prompt_stream = query_and_chunks_stream.map(QAPromptor, config["promptor"])
    response_stream = prompt_stream.map(OpenAIGenerator, config["generator"]["vllm"])
    response_stream.sink(TerminalSink, config["sink"])
    # 提交管道并运行
    env.submit()
      # 启动管道

    # time.sleep(100)  # 等待管道运行

if __name__ == '__main__':
    import os
    # 加载配置并初始化日志
    config_path = os.path.join(os.path.dirname(__file__), "..", "config", "config_bm25s.yaml")
    config = load_config(config_path)
    # 初始化内存并运行管道
    pipeline_run()