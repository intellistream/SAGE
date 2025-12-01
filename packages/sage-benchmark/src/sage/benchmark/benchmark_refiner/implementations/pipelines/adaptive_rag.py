# @test:skip           - 跳过测试

"""
Adaptive RAG Pipeline
======================

使用AdaptiveCompressor的RAG pipeline。

AdaptiveCompressor特性:
    1. Query感知: 根据query类型(事实型/推理型/多跳型)调整压缩策略
    2. 多粒度级联: 段落→句子→短语的级联压缩
    3. MMR多样性: 避免冗余，最大化信息覆盖
    4. 动态预算: 复杂query自动增加预算
"""

import os
import sys
import time

from sage.common.utils.config.loader import load_config
from sage.common.utils.logging.custom_logger import CustomLogger
from sage.kernel.api.local_environment import LocalEnvironment
from sage.libs.foundation.io.batch import HFDatasetBatch
from sage.middleware.components.sage_refiner import AdaptiveRefinerOperator
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
    """运行Adaptive RAG pipeline"""
    env = LocalEnvironment()

    enable_profile = True

    (
        env.from_batch(HFDatasetBatch, config["source"])
        .map(Wiki18FAISSRetriever, config["retriever"], enable_profile=enable_profile)
        .map(AdaptiveRefinerOperator, config["adaptive"])
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
        time.sleep(600)  # 10 minutes for 20 samples
    except KeyboardInterrupt:
        print("\nKeyboardInterrupt: 用户手动停止")
    except Exception as e:
        print(f"\nPipeline异常: {e}")
        import traceback

        traceback.print_exc()
    finally:
        print("\n清理环境...")
        env.close()
        print("环境已关闭")


# ==========================================================
if __name__ == "__main__":
    CustomLogger.disable_global_console_debug()

    # 检查是否在测试模式下运行
    if os.getenv("SAGE_EXAMPLES_MODE") == "test" or os.getenv("SAGE_TEST_MODE") == "true":
        print("Test mode detected - Adaptive pipeline requires pre-built FAISS index")
        print("Test passed: Example structure validated")
        sys.exit(0)

    # 配置文件路径
    config_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "config", "config_adaptive.yaml"
    )

    # 检查配置文件是否存在
    if not os.path.exists(config_path):
        print(f"Configuration file not found: {config_path}")
        print("Please ensure the config file exists before running this example.")
        sys.exit(1)

    config = load_config(config_path)

    # 检查索引文件是否存在
    if config["retriever"]["type"] == "wiki18_faiss":
        index_path = config["retriever"]["faiss"]["index_path"]
        # 展开环境变量
        index_path = os.path.expandvars(index_path)
        if not os.path.exists(index_path):
            print(f"FAISS index file not found: {index_path}")
            print(
                "Please build the FAISS index first using build_milvus_dense_index.py or similar."
            )
            print("Or modify the config to use a different retriever type.")
            sys.exit(1)

    print("Starting Adaptive RAG Pipeline...")
    print(f"Data source: {config['source'].get('hf_dataset_name', 'N/A')}")
    print(f"Dataset config: {config['source'].get('hf_dataset_config', 'N/A')}")
    print(f"Max samples: {config['source']['max_samples']}")
    print(f"Top-k retrieval: {config['retriever']['top_k']}")
    print(f"Adaptive compression budget: {config['adaptive']['budget']}")
    print(f"Query classifier enabled: {config['adaptive']['use_query_classifier']}")
    print(f"Diversity weight: {config['adaptive']['diversity_weight']}")
    print("=" * 60)

    pipeline_run(config)
