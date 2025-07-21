import time
from dotenv import load_dotenv

from sage_core.api.local_environment import LocalStreamEnvironment
from sage_libs.io.sink import TerminalSink
from sage_libs.io.source import FileSource
from sage_libs.rag.generator import OpenAIGenerator
from sage_libs.rag.promptor import QAPromptor
from sage_libs.rag.retriever import DenseRetriever
from sage_utils.config_loader import load_config


def pipeline_run(config: dict) -> None:
    """
    创建并运行数据处理管道

    Args:
        config (dict): 包含各模块配置的配置字典。
    """
    env = LocalStreamEnvironment()
    env.set_memory(config=None)

    # 构建数据处理流程
    (env
        .from_source(FileSource, config["source"])
        .map(DenseRetriever, config["retriever"])
        .map(QAPromptor, config["promptor"])
        .map(OpenAIGenerator, config["generator"])
        .sink(TerminalSink, config["sink"])
    )

    env.submit()

    time.sleep(5)  # 等待管道运行5秒

    env.close()


if __name__ == '__main__':
    load_dotenv(override=False)
    config = load_config("config.yaml")
    pipeline_run(config)
