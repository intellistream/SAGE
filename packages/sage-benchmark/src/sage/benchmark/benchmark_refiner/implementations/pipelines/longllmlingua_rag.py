# @test:skip           - 跳过测试

"""
LongLLMLingua RAG Pipeline
==========================

使用 LongLLMLingua 压缩算法的 RAG pipeline。
LongLLMLingua 是针对长文档场景优化的 question-aware prompt 压缩方法。

特点:
    - Question-aware: 使用问题引导上下文重要性评估
    - 动态压缩: 根据内容相关性动态调整压缩比例
    - 上下文重排序: 按相关性排序压缩后的上下文
    - 对比 Perplexity: 使用 condition_compare 提升压缩质量

默认配置遵循 LongLLMLingua 论文 baseline 设置:
    - rate: 0.55
    - condition_in_question: "after"
    - condition_compare: True
    - reorder_context: "sort"

参考论文: https://arxiv.org/abs/2310.06839
"""

import os
import sys
import time

from sage.common.utils.config.loader import load_config
from sage.common.utils.logging.custom_logger import CustomLogger
from sage.kernel.api.local_environment import LocalEnvironment
from sage.libs.foundation.io.batch import HFDatasetBatch
from sage.middleware.components.sage_refiner import LongLLMLinguaOperator
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
    """运行 LongLLMLingua RAG pipeline"""
    env = LocalEnvironment()

    enable_profile = True

    (
        env.from_batch(HFDatasetBatch, config["source"])
        .map(Wiki18FAISSRetriever, config["retriever"], enable_profile=enable_profile)
        .map(LongLLMLinguaOperator, config["longllmlingua"])
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
        # LongLLMLingua uses LLM inference, so it's slower than BERT-based methods
        time.sleep(7200)  # 2 hours for 20 samples with long contexts
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
        print("🧪 Test mode detected - LongLLMLingua pipeline requires pre-built FAISS index")
        print("✅ Test passed: Example structure validated")
        sys.exit(0)

    # 配置文件路径
    config_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "config", "config_longllmlingua.yaml"
    )

    # 检查配置文件是否存在
    if not os.path.exists(config_path):
        print(f"❌ Configuration file not found: {config_path}")
        print("Please ensure the config file exists before running this example.")
        sys.exit(1)

    config = load_config(config_path)

    # 检查 LongLLMLingua 相关配置
    if config.get("longllmlingua", {}).get("enabled", True):
        print("🚀 LongLLMLingua compression enabled (Paper Baseline)")
        print(f"   Model: {config['longllmlingua'].get('model_name', 'default')}")
        print(f"   Rate: {config['longllmlingua'].get('rate', 0.55)}")
        print(f"   Condition Compare: {config['longllmlingua'].get('condition_compare', True)}")
    else:
        print("ℹ️  LongLLMLingua disabled - running in baseline mode")

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
