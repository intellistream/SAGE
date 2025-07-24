import time
from sage_core.api.env import LocalEnvironment
from sage_common_funs.io.source import FileSource
from sage_common_funs.io.sink import TerminalSink
from sage_libs.rag.generator import OpenAIGenerator
from sage_libs.rag.promptor import QAPromptor
from sage_libs.rag.retriever import DenseRetriever
from sage_utils.config_loader import load_config


def pipeline_run():
    """创建并运行数据处理管道"""
    env = LocalEnvironment()
    env.set_memory(config=None)

    # # 大数据处理流 -- sage.flow
    # data_stream = (env
    #                 .from_source(KafaSource, config["source"])
    #                 .map(FilterOperator, config["filter"])
    #                 .map(IVTOPK,config["kafka"])
    #                 .map(MemoryWriter, config["kafka"])    # 存放关键信息
    #                 )

    # 目标：大量的非结构化数据流涌入之后，flow 能按照用户定义的逻辑去高速的执行并提取关键信息 (high throughput, low latency)
    # 多维信息流融合，新闻、微博、小红书、twitter、用户对话、环境噪音。
    # 大数据处理流 -- sage.flow
    data_stream = (env
                    .from_source(KafaSource, config["source"])
                    .map(Embedding, config["embedding"]) #libtorch.
                    .map(FilterOperator, config["filter"])
                    .map(IVTOPK,config["kafka"])
                    )

    # 数据通信协议between flow engine and sage engine
    # 数据序列化处理 protobuf
    # 大模型推理流
    query_stream = (data_stream
        # env
                    # .from_source(FileSource, config["source"])
                    #.join(data_stream)
                    .map(DenseRetriever, config["retriever"])
                    .map(QAPromptor, config["promptor"])
                    .map(OpenAIGenerator, config["generator"])
                    .sink(TerminalSink, config["sink"])
                    )
    try:
        env.submit()
        env.run_once()  # 启动管道
        time.sleep(15)  # 等待管道运行
        env.stop()
    finally:
        env.close()

if __name__ == '__main__':
    # 加载配置
    config = load_config("config.yaml")
    pipeline_run()
