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
    # 构建数据处理流程
    query_stream = (env
                    .from_source(FileSource, config["source"])
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
