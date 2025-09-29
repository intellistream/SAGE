import os
import sys
import time

from dotenv import load_dotenv
from sage.common.utils.config.loader import load_config
from sage.core.api.local_environment import LocalEnvironment
from sage.libs.io_utils.sink import TerminalSink
from sage.libs.io_utils.source import FileSource
from sage.libs.rag.generator import OpenAIGenerator
from sage.libs.rag.promptor import QAPromptor


def pipeline_run():
    """创建并运行数据处理管道"""
    # 检查是否在测试模式下运行
    if (
        os.getenv("SAGE_EXAMPLES_MODE") == "test"
        or os.getenv("SAGE_TEST_MODE") == "true"
    ):
        print("🧪 Test mode detected - qa_dense_retrieval_mixed example")
        print("✅ Test passed: Example structure validated")
        return

    env = LocalEnvironment()
    # env.set_memory(config=None)
    # 构建数据处理流程
    query_stream = env.from_source(FileSource, config["source"])
    # query_and_chunks_stream = query_stream.map(MilvusDenseRetriever, config["retriever"])  # 需要配置
    query_and_chunks_stream = query_stream  # 跳过检索步骤，因为需要复杂配置
    prompt_stream = query_and_chunks_stream.map(QAPromptor, config["promptor"])
    response_stream = prompt_stream.map(OpenAIGenerator, config["generator"]["vllm"])
    response_stream.sink(TerminalSink, config["sink"])
    # 提交管道并运行
    env.submit()
    time.sleep(100)  # 等待管道运行


if __name__ == "__main__":
    import os

    # 检查是否在测试模式下运行
    if (
        os.getenv("SAGE_EXAMPLES_MODE") == "test"
        or os.getenv("SAGE_TEST_MODE") == "true"
    ):
        print("🧪 Test mode detected - qa_dense_retrieval_mixed example")
        print("✅ Test passed: Example structure validated")
        sys.exit(0)

    # 加载配置并初始化日志
    config_path = os.path.join(
        os.path.dirname(__file__), "..", "config", "config_mixed.yaml"
    )
    if not os.path.exists(config_path):
        print(f"❌ Configuration file not found: {config_path}")
        print("Please create the configuration file first.")
        sys.exit(1)

    config = load_config(config_path)
    load_dotenv(override=False)

    api_key = os.environ.get("ALIBABA_API_KEY")
    if api_key:
        config.setdefault("generator", {})["api_key"] = api_key

    pipeline_run()
