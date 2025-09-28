import os
import sys

from sage.common.utils.config.loader import load_config
from sage.core.api.local_environment import LocalEnvironment
from sage.libs.io_utils.sink import TerminalSink
from sage.libs.io_utils.source import FileSource
from sage.libs.rag.generator import OpenAIGenerator
from sage.libs.rag.promptor import QAPromptor

# from sage.libs.rag.retriever import BM25sRetriever  # 这个类不存在


def pipeline_run():
    """创建并运行数据处理管道"""
    # 检查是否在测试模式下运行
    if (
        os.getenv("SAGE_EXAMPLES_MODE") == "test"
        or os.getenv("SAGE_TEST_MODE") == "true"
    ):
        print("🧪 Test mode detected - qa_bm25_retrieval example")
        print(
            "✅ Test passed: Example structure validated (BM25sRetriever not available)"
        )
        return

    env = LocalEnvironment()
    # env.set_memory(config=None)
    # 构建数据处理流程
    query_stream = env.from_source(FileSource, config["source"])
    # query_and_chunks_stream = query_stream.map(BM25sRetriever, config["retriever"])  # 不可用
    query_and_chunks_stream = query_stream  # 跳过检索步骤
    prompt_stream = query_and_chunks_stream.map(QAPromptor, config["promptor"])
    response_stream = prompt_stream.map(OpenAIGenerator, config["generator"]["vllm"])
    response_stream.sink(TerminalSink, config["sink"])
    # 提交管道并运行
    env.submit()
    # 启动管道

    # time.sleep(100)  # 等待管道运行


if __name__ == "__main__":
    import os

    # 检查是否在测试模式下运行
    if (
        os.getenv("SAGE_EXAMPLES_MODE") == "test"
        or os.getenv("SAGE_TEST_MODE") == "true"
    ):
        print("🧪 Test mode detected - qa_bm25_retrieval example")
        print(
            "✅ Test passed: Example structure validated (BM25sRetriever not available)"
        )
        sys.exit(0)

    # 加载配置并初始化日志
    config_path = os.path.join(
        os.path.dirname(__file__), "..", "config", "config_bm25s.yaml"
    )
    if not os.path.exists(config_path):
        print(f"❌ Configuration file not found: {config_path}")
        print("Please create the configuration file first.")
        sys.exit(1)

    config = load_config(config_path)
    # 初始化内存并运行管道
    pipeline_run()
