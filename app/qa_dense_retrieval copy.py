from dotenv import load_dotenv
import os, time
from sage.core.api.env import LocalEnvironment, RemoteEnvironment
from sage.libs.io.source import FileSource
from sage.libs.io.sink import TerminalSink
from sage.libs.rag.generator import OpenAIGenerator
from sage.libs.rag.promptor import QAPromptor
from sage.libs.rag.retriever import DenseRetriever
from sage.utils.config_loader import load_config
from sage.utils.logging_utils import configure_logging



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
    config = load_config("config.yaml")
    pipeline_run()
