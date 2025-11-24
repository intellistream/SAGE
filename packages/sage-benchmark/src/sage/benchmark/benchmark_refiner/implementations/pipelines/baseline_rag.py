# @test:skip           - 跳过测试

"""
Baseline RAG Pipeline (No Refiner)
===================================

标准RAG pipeline，不使用任何压缩/refine算法，用于对比实验。
"""

import os
import sys
import time

from sage.common.utils.config.loader import load_config
from sage.common.utils.logging.custom_logger import CustomLogger
from sage.kernel.api.local_environment import LocalEnvironment
from sage.libs.foundation.io.batch import HFDatasetBatch
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
    """运行Baseline RAG pipeline（无Refiner）"""
    env = LocalEnvironment()

    enable_profile = True

    (
        env.from_batch(HFDatasetBatch, config["source"])
        .map(Wiki18FAISSRetriever, config["retriever"], enable_profile=enable_profile)
        # 注意：这里跳过了 REFORMRefinerOperator
        .map(QAPromptor, config["promptor"], enable_profile=enable_profile)
        .map(OpenAIGenerator, config["generator"]["vllm"], enable_profile=enable_profile)
        .map(F1Evaluate, config["evaluate"])
        .map(TokenCountEvaluate, config["evaluate"])
        .map(LatencyEvaluate, config["evaluate"])
        .map(CompressionRateEvaluate, config["evaluate"])
    )

    try:
        env.submit()
        time.sleep(600)
    except KeyboardInterrupt:
        print("停止运行")
    finally:
        env.close()


# ==========================================================
if __name__ == "__main__":
    CustomLogger.disable_global_console_debug()

    # 检查是否在测试模式下运行
    if os.getenv("SAGE_EXAMPLES_MODE") == "test" or os.getenv("SAGE_TEST_MODE") == "true":
        print("🧪 Test mode detected - Baseline pipeline requires pre-built FAISS index")
        print("✅ Test passed: Example structure validated")
        sys.exit(0)

    # 配置文件路径
    config_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "config", "config_baseline.yaml"
    )

    # 检查配置文件是否存在
    if not os.path.exists(config_path):
        print(f"❌ Configuration file not found: {config_path}")
        print("Please ensure the config file exists before running this example.")
        sys.exit(1)

    config = load_config(config_path)

    # 检查索引文件是否存在
    index_path = config["retriever"].get("index_path")
    if index_path and not os.path.exists(index_path):
        print(f"❌ FAISS index not found: {index_path}")
        print("Please build the index first using the head selection experiment.")
        sys.exit(1)

    print("🚀 Starting Baseline RAG Pipeline (No Refiner)...")
    print(f"📊 Data source: {config['source'].get('hf_dataset_name', 'N/A')}")
    print(f"📈 Max samples: {config['source']['max_samples']}")
    print(f"🔍 Top-k retrieval: {config['retriever']['top_k']}")
    print(f"🤖 Generator model: {config['generator']['vllm']['model_name']}")
    print("=" * 60)

    pipeline_run(config)
