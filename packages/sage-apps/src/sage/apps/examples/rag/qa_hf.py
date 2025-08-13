import logging
import time

from sage.core.api.local_environment import LocalEnvironment
from sage.apps.libs.io_utils.source import FileSource
from sage.apps.libs.io_utils.sink import TerminalSink

from sage.apps.libs.rag.generator import HFGenerator
from sage.apps.libs.rag.promptor import QAPromptor
from sage.apps.libs.rag.retriever import DenseRetriever
from sage.common.utils.config.loader import load_config


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
        .map(HFGenerator, config["generator"]["vllm"])
        .sink(TerminalSink, config["sink"])
    )

    # 提交管道并运行一次
    env.submit()
    
    time.sleep(5)  # 等待管道运行
    env.close()



if __name__ == '__main__':
    config = load_config("../config/config_hf.yaml")
    pipeline_run(config)
