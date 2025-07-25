import logging
import time

from core.api.local_environment import LocalStreamEnvironment
from libs.io.source import FileSource
from libs.io.sink import TerminalSink

from libs.rag.generator import HFGenerator
from libs.rag.promptor import QAPromptor
from libs.rag.retriever import DenseRetriever
from utils.config_loader import load_config
from utils.logging_utils import configure_logging


def pipeline_run(config: dict) -> None:
    """
    创建并运行本地环境下的数据处理管道。

    Args:
        config (dict): 包含各个组件配置的字典。
    """
    env = LocalStreamEnvironment()
    env.set_memory(config=None)

    # 构建数据处理流程
    (env
        .from_source(FileSource, config["source"])
        .map(DenseRetriever, config["retriever"])
        .map(QAPromptor, config["promptor"])
        .map(HFGenerator, config["generator"]["local"])
        .sink(TerminalSink, config["sink"])
    )

    # 提交管道并运行一次
    env.submit()
    
    time.sleep(5)  # 等待管道运行
    env.close()



if __name__ == '__main__':
    configure_logging(level=logging.INFO)
    config = load_config("config_hf.yaml")
    pipeline_run(config)
