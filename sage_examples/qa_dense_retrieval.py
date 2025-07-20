import time
from sage_core.api.env import LocalEnvironment, RemoteEnvironment
from sage_common_funs.io.source import FileSource
from sage_common_funs.io.sink import TerminalSink
from sage_libs.rag.generator import OpenAIGenerator
from sage_libs.rag.promptor import QAPromptor
from sage_libs.rag.retriever import DenseRetriever
from sage_utils.config_loader import load_config


def pipeline_run():
    """创建并运行数据处理管道"""
    # env = LocalBatchEnvironment() #DEBUG and Batch -- Client 拥有后续程序的全部handler（包括JM）
    # env = LocalStreamEnvironment() #DEBUG and Streaming
    env = RemoteBatchEnvironment("JM-IP")  # Deployment to JM. -- Client 不拥有后续程序的全部handler（包括JM）
    # env = RemoteStreamEnvironment("JM-IP")  # Deployment to JM.
    env.set_memory(config=None)
    # 构建数据处理流程
    query_stream = (env
                    .from_source(FileSource, config["source"])
                    .map(DenseRetriever, config["retriever"])
                    .map(QAPromptor, config["promptor"])
                    .map(OpenAIGenerator, config["generator"])
                    .sink(TerminalSink, config["sink"]) # TM (JVM) --> 会打印在某一台机器的console里
                    )
    try:
        env.submit()
    finally:
        env.close()

if __name__ == '__main__':
    # 加载配置
    config = load_config("config.yaml")
    pipeline_run()
