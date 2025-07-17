import time
from dotenv import load_dotenv

from sage_core.api.env import LocalEnvironment
from sage_common_funs.io.source import FileSource
from sage_common_funs.io.sink import TerminalSink
from sage_libs.rag import OpenAIGeneratorWithHistory
from sage_libs.rag.promptor import QAPromptor
from sage_utils.config_loader import load_config


def pipeline_run(config: dict) -> None:
    """
    创建并运行数据处理管道

    Args:
        config (dict): 包含各模块配置的配置字典。
    """
    env = LocalEnvironment()
    env.set_memory(config=None)

    # 构建数据处理流程
    (env
        .from_source(FileSource, config["source"])
        .map(QAPromptor, config["promptor"])
        .map(OpenAIGeneratorWithHistory, config["generator"])
        .sink(TerminalSink, config["sink"])
    )

    env.submit()
    env.run_streaming()
    time.sleep(5)  # 等待管道运行
    env.close()


if __name__ == '__main__':
    load_dotenv(override=False)
    config = load_config("config.yaml")
    pipeline_run(config)
