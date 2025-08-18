import time
from sage.core.api.local_environment import LocalEnvironment
from sage.core.api.remote_environment import RemoteEnvironment
from sage.libs.io_utils.source import FileSource
from sage.libs.io_utils.sink import TerminalSink
from sage.libs.rag.generator import OpenAIGenerator
from sage.libs.rag.promptor import QAPromptor
from sage.libs.rag.retriever import DenseRetriever
from sage.common.utils.config.loader import load_config


def pipeline_run():
    """创建并运行数据处理管道"""
    # env = LocalBatchEnvironment() #DEBUG and Batch -- Client 拥有后续程序的全部handler（包括JM）
    env = LocalEnvironment("JM-IP")  # Deployment to JM. -- Client 不拥有后续程序的全部handler（包括JM）

    # Batch Environment.

    query_stream = (env
                    .from_source(FileSource, config["source"]) # 处理且处理一整个file 一次。
                    # .map(DenseRetriever, config["retriever"])
                    .map(QAPromptor, config["promptor"])
                    .map(OpenAIGenerator, config["generator"]["vllm"])
                    .sink(TerminalSink, config["sink"]) # TM (JVM) --> 会打印在某一台机器的console里
                    )

    env.submit()
    time.sleep(5)

if __name__ == '__main__':
    import os
    # 加载配置
    config_path = os.path.join(os.path.dirname(__file__), "..", "config", "config.yaml")
    config = load_config(config_path)
    pipeline_run()
