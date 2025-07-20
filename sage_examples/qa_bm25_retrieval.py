
import logging

from sage_core.environment.base_environment import LocalEnvironment
from sage_common_funs.io.sink import TerminalSink
from sage_common_funs.io.source import FileSource
from sage_libs.rag.generator import OpenAIGenerator
from sage_libs.rag.promptor import QAPromptor
from sage_libs.rag.retriever import BM25sRetriever
from sage_utils.config_loader import load_config
from sage_utils.logging_utils import configure_logging


def pipeline_run():
    """创建并运行数据处理管道"""
    env = LocalEnvironment()
    env.set_memory(config=None)
    # 构建数据处理流程
    query_stream = env.from_source(FileSource, config["source"])
    query_and_chunks_stream = query_stream.map(BM25sRetriever, config["retriever"])
    prompt_stream = query_and_chunks_stream.map(QAPromptor, config["promptor"])
    response_stream = prompt_stream.map(OpenAIGenerator, config["generator"])
    response_stream.sink(TerminalSink, config["sink"])
    # 提交管道并运行
    env.submit()
    env.run_streaming()  # 启动管道

    # time.sleep(100)  # 等待管道运行

if __name__ == '__main__':
    # 加载配置并初始化日志
    config = load_config('config_bm25s.yaml')
    configure_logging(level=logging.INFO)
    # 初始化内存并运行管道
    pipeline_run()