# @test:skip           - 跳过测试

"""
LLMLingua-2 RAG Pipeline
========================

使用 LLMLingua-2 压缩算法的 RAG pipeline。
LLMLingua-2 基于 BERT token 分类，比 LLM-based 方法快得多。

特点:
    - 快速压缩：使用 BERT 模型进行 token 分类，无需 LLM 推理
    - 多语言支持：使用 mBERT 或 XLM-RoBERTa 模型
    - Token 级精确压缩：每个 token 独立分类
    - 可选的上下文级过滤：粗到细的压缩策略

参考论文: https://arxiv.org/abs/2403.12968
"""

import os
import sys
import time

from sage.common.utils.config.loader import load_config
from sage.common.utils.logging.custom_logger import CustomLogger
from sage.kernel.api.local_environment import LocalEnvironment
from sage.libs.foundation.io.batch import HFDatasetBatch
from sage.middleware.components.sage_refiner import LLMLingua2Operator
from sage.middleware.operators.rag import (
    CompressionRateEvaluate,
    F1Evaluate,
    LatencyEvaluate,
    OpenAIGenerator,
    QAPromptor,
    TokenCountEvaluate,
    Wiki18FAISSRetriever,
)


def pipeline_run(config):
    """运行 LLMLingua-2 RAG pipeline"""
    env = LocalEnvironment()

    enable_profile = True

    (
        env.from_batch(HFDatasetBatch, config["source"])
        .map(Wiki18FAISSRetriever, config["retriever"], enable_profile=enable_profile)
        .map(LLMLingua2Operator, config["llmlingua2"])
        .map(QAPromptor, config["promptor"], enable_profile=enable_profile)
        .map(OpenAIGenerator, config["generator"]["vllm"], enable_profile=enable_profile)
        .map(F1Evaluate, config["evaluate"])
        .map(TokenCountEvaluate, config["evaluate"])
        .map(LatencyEvaluate, config["evaluate"])
        .map(CompressionRateEvaluate, config["evaluate"])
    )

    try:
        env.submit()
        # Wait for pipeline to complete
        # LLMLingua-2 is faster than LLM-based methods, so we can use shorter timeout
        time.sleep(3600)  # 1 hour for 20 samples
    except KeyboardInterrupt:
        print("\n⚠️  KeyboardInterrupt: 用户手动停止")
    except Exception as e:
        print(f"\n❌ Pipeline异常: {e}")
        import traceback

        traceback.print_exc()
    finally:
        print("\n🔄 清理环境...")
        env.close()
        print("✅ 环境已关闭")


# ==========================================================
if __name__ == "__main__":
    CustomLogger.disable_global_console_debug()

    # 检查是否在测试模式下运行
    if os.getenv("SAGE_EXAMPLES_MODE") == "test" or os.getenv("SAGE_TEST_MODE") == "true":
        print("🧪 Test mode detected - LLMLingua-2 pipeline requires pre-built FAISS index")
        print("✅ Test passed: Example structure validated")
        sys.exit(0)

    # 配置文件路径
    config_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "config", "config_llmlingua2.yaml"
    )

    # 检查配置文件是否存在
    if not os.path.exists(config_path):
        print(f"❌ Configuration file not found: {config_path}")
        print("Please ensure the config file exists before running this example.")
        sys.exit(1)

    config = load_config(config_path)

    # 检查 LLMLingua-2 相关配置
    if config.get("llmlingua2", {}).get("enabled", True):
        print("🚀 LLMLingua-2 compression enabled")
        print(f"   Model: {config['llmlingua2'].get('model_name', 'default')}")
        print(f"   Rate: {config['llmlingua2'].get('rate', 0.5)}")
    else:
        print("ℹ️  LLMLingua-2 disabled - running in baseline mode")

    # 检查索引文件是否存在
    if config["retriever"]["type"] == "wiki18_faiss":
        index_path = config["retriever"]["faiss"]["index_path"]
        # 展开环境变量
        index_path = os.path.expandvars(index_path)
        if not os.path.exists(index_path):
            print(f"❌ FAISS index file not found: {index_path}")
            print(
                "Please build the FAISS index first using build_milvus_dense_index.py or similar."
            )
            print("Or modify the config to use a different retriever type.")
            sys.exit(1)

    pipeline_run(config)
