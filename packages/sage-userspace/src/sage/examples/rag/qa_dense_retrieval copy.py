from dotenv import load_dotenv
import os, time
from sage.kernel.api.local_environment import LocalEnvironment
from sage.kernel.api.remote_environment import RemoteEnvironment
from sage.lib.io_utils.source import FileSource
from sage.lib.io_utils.sink import TerminalSink
from sage.lib.rag.generator import OpenAIGenerator
from sage.lib.rag.promptor import QAPromptor
from sage.lib.rag.retriever import DenseRetriever
from sage.kernel.utils.config.loader import load_config



def pipeline_run():
    """创建并运行数据处理管道"""
    env = LocalEnvironment()
    env.set_memory(config=None)
    # 构建数据处理流程
    query_stream = (env
                    .from_source(FileSource, config["source"])
                    .map(DenseRetriever, config["retriever"])
                    .map(QAPromptor, config["promptor"])
                    .map(OpenAIGenerator, config["generator"]["local"])
                    .sink(TerminalSink, config["sink"])
                    )
    env.submit()
    time.sleep(15)  # 等待管道运行

if __name__ == '__main__':
    # 加载配置
    config = load_config("../../resources/config/config.yaml")
    pipeline_run()
