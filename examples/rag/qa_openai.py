import time
from dotenv import load_dotenv

from sage.core.api.local_environment import LocalEnvironment
from sage.libs.io_utils.sink import TerminalSink
from sage.libs.io_utils.source import FileSource
from sage.libs.rag.generator import OpenAIGenerator
from sage.libs.rag.promptor import QAPromptor
from sage.libs.rag.retriever import DenseRetriever
from sage.common.utils.config.loader import load_config


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
    config = load_config("../config/config.yaml")
    pipeline_run(config)
