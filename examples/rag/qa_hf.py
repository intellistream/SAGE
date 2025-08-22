import logging
import time

from pydantic import Json

from sage.core.api.local_environment import LocalEnvironment
from sage.libs.io_utils.batch import JSONLBatch
from sage.libs.io_utils.sink import TerminalSink

from sage.libs.rag.generator import HFGenerator
from sage.libs.rag.promptor import QAPromptor
from sage.libs.rag.retriever import ChromaRetriever
from sage.common.utils.config.loader import load_config


def pipeline_run(config: dict) -> None:
    """
    创建并运行本地环境下的数据处理管道。

    Args:
        config (dict): 包含各个组件配置的字典。
    """
    # 修改JobManager实例化以使用不同的端口
    from sage.kernel import JobManager
    # 先清理可能存在的实例
    if hasattr(JobManager, 'instance') and JobManager.instance is not None:
        if hasattr(JobManager.instance, 'server') and JobManager.instance.server:
            JobManager.instance.server.shutdown()
        JobManager.instance = None
    

    env = LocalEnvironment()
    #env.set_memory(config=None)

    # 构建数据处理流程
    (env
        .from_source(JSONLBatch, config["source"])
        .map(ChromaRetriever, config["retriever"])
        .map(QAPromptor, config["promptor"])
        .map(HFGenerator, config["generator"]["local"])
        .sink(TerminalSink, config["sink"])
    )

    # 提交管道并运行一次
    env.submit()
    
    time.sleep(20)  # 等待管道运行
    env.close()

if __name__ == '__main__':
    import os
    from sage.common.utils.logging.custom_logger import CustomLogger
    # 临时启用控制台输出来调试
    # CustomLogger.disable_global_console_debug()
    config_path = os.path.join(os.path.dirname(__file__), "..", "config", "config_hf.yaml")
    config = load_config(config_path)
    pipeline_run(config)
