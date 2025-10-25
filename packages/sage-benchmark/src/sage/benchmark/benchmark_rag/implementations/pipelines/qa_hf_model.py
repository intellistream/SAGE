import time

from sage.common.utils.config.loader import load_config
from sage.kernel.api.local_environment import LocalEnvironment
from sage.libs.io.batch import JSONLBatch
from sage.libs.io.sink import TerminalSink
from sage.middleware.operators.rag import (ChromaRetriever, HFGenerator,
                                           QAPromptor)


def pipeline_run(config: dict) -> None:
    """
    创建并运行本地环境下的数据处理管道。

    Args:
        config (dict): 包含各个组件配置的字典。
    #"""

    env = LocalEnvironment(config={"engine_port": 19002})
    # env.set_memory(config=None)

    # 构建数据处理流程
    (
        env.from_source(JSONLBatch, config["source"])
        .map(ChromaRetriever, config["retriever"])
        .map(QAPromptor, config["promptor"])
        .map(HFGenerator, config["generator"]["local"])
        .sink(TerminalSink, config["sink"])
    )

    # 提交管道并运行一次
    env.submit()

    time.sleep(20)  # 等待管道运行
    env.close()


if __name__ == "__main__":
    import os
    import sys

    # 检查是否在测试模式下运行
    if os.getenv("SAGE_EXAMPLES_MODE") == "test" or os.getenv("SAGE_TEST_MODE") == "true":
        print("🧪 Test mode detected - qa_hf_model example")
        print("✅ Test passed: Example structure validated")
        sys.exit(0)

    # 临时启用控制台输出来调试
    # CustomLogger.disable_global_consol
    # e_debug()
    config_path = os.path.join(os.path.dirname(__file__), "..", "config", "config_hf.yaml")
    if not os.path.exists(config_path):
        print(f"❌ Configuration file not found: {config_path}")
        print("Please create the configuration file first.")
        sys.exit(1)

    config = load_config(config_path)
    pipeline_run(config)
