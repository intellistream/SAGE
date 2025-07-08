import logging
import time

from sage_core.api.env import LocalEnvironment
from sage_common_funs.io.source import FileSource
from sage_common_funs.io.sink import TerminalSink
from sage_common_funs.rag.generator import HFGenerator
from sage_common_funs.rag.promptor import QAPromptor
from sage_common_funs.rag.retriever import DenseRetriever
from sage_utils.config_loader import load_config
from sage_utils.logging_utils import configure_logging


def pipeline_run(config: dict) -> None:
    """
    创建并运行本地环境下的数据处理管道。

    Args:
        config (dict): 包含各个组件配置的字典。
    """
    env = LocalEnvironment()
    env.set_memory(config=None)

    # 构建数据处理流程
    (env
        .from_source(FileSource, config["source"])
        .map(DenseRetriever, config["retriever"])
        .map(QAPromptor, config["promptor"])
        .map(HFGenerator, config["generator"])
        .sink(TerminalSink, config["sink"])
    )

    # 提交管道并运行一次
    env.submit()
    env.run_once()
    time.sleep(5)
    env.close()


if __name__ == '__main__':
    configure_logging(level=logging.INFO)
    config = load_config("config_hf.yaml")
    pipeline_run(config)
