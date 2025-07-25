from sage.libs.io.source import FileSource
from sage.libs.io.sink import TerminalSink
from draft.remote_environment import RemoteBatchEnvironment
from sage.libs.rag.generator import OpenAIGenerator
from sage.libs.rag.promptor import QAPromptor
from sage.libs.rag.retriever import DenseRetriever
from sage.utils.config_loader import load_config


def pipeline_run():
    """创建并运行数据处理管道"""
    # env = LocalBatchEnvironment() #DEBUG and Batch -- Client 拥有后续程序的全部handler（包括JM）
    env = RemoteBatchEnvironment("JM-IP")  # Deployment to JM. -- Client 不拥有后续程序的全部handler（包括JM）

    # Batch Environment.

    query_stream = (env
                    .process(FileSource, config["source"]) # 处理且处理一整个file 一次。
                    .map(DenseRetriever, config["retriever"])
                    .map(QAPromptor, config["promptor"])
                    .map(OpenAIGenerator, config["generator"]["local"])
                    .sink(TerminalSink, config["sink"]) # TM (JVM) --> 会打印在某一台机器的console里
                    )

    # Streaming Environment.
    env.set_memory(config=None)
    # env = LocalEnvironment() #DEBUG and Streaming
    # env = RemoteStreamEnvironment("JM-IP")  # Deployment to JM.

    # 构建数据处理流程
    query_stream = (env
                    .from_source(FileSource, config["source"])
                    .map(DenseRetriever, config["retriever"])
                    .map(QAPromptor, config["promptor"])
                    .map(OpenAIGenerator, config["generator"]["local"])
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
