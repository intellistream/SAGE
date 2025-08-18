import time
from dotenv import load_dotenv

from sage.core.api.local_environment import LocalEnvironment
from sage.libs.io_utils.source import FileSource
from sage.libs.io_utils.sink import TerminalSink

from sage.libs.rag.generator import OpenAIGeneratorWithHistory
from sage.libs.rag.promptor import QAPromptor
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
        .map(QAPromptor, config["promptor"])
        .map(OpenAIGeneratorWithHistory, config["generator"]["vllm"])
        .sink(TerminalSink, config["sink"])
    )

    env.submit()
    
    time.sleep(5)  # 等待管道运行
    env.close()


if __name__ == '__main__':
    import os
    load_dotenv(override=False)
    config_path = os.path.join(os.path.dirname(__file__), "..", "config", "config.yaml")
    config = load_config(config_path)
    pipeline_run(config)
