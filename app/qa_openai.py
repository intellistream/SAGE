import time
from dotenv import load_dotenv

from sage.core.api.local_environment import LocalEnvironment
from sage.lib.io.sink import TerminalSink
from sage.lib.io.source import FileSource
from sage.lib.rag.generator import OpenAIGenerator
from sage.lib.rag.promptor import QAPromptor
from sage.lib.rag.retriever import DenseRetriever
from sage.utils.config_loader import load_config


def pipeline_run(config: dict) -> None:
    """
    创建并运行数据处理管道

    Args:
        config (dict): 包含各模块配置的配置字典。
    """
    env = LocalEnvironment()
    #env.set_memory(config=None)

    # 构建数据处理流程
    (env
        .from_source(FileSource, config["source"])
        .map(DenseRetriever, config["retriever"])
        .map(QAPromptor, config["promptor"])
        .map(OpenAIGenerator, config["generator"]["vllm"])
        .sink(TerminalSink, config["sink"])
    )

    env.submit()
    time.sleep(5)  # 等待管道运行5秒
    env.close()


if __name__ == '__main__':
    load_dotenv(override=False)
    config = load_config("config.yaml")
    pipeline_run(config)
