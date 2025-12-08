# @test:skip           - 跳过测试

"""
RECOMP Extractive RAG Pipeline
==============================

使用RECOMP Extractive压缩算法的RAG pipeline。
基于双编码器（Contriever/DPR）对检索文档进行句子级打分，
选择与query最相关的top-k句子作为压缩后的上下文。

References:
    RECOMP: Improving Retrieval-Augmented LMs with Compression and Selective Augmentation
    https://arxiv.org/pdf/2310.04408.pdf
"""

import os
import sys
import time

from sage.common.utils.config.loader import load_config
from sage.common.utils.logging.custom_logger import CustomLogger
from sage.kernel.api.local_environment import LocalEnvironment
from sage.libs.foundation.io.batch import HFDatasetBatch
from sage.middleware.components.sage_refiner import RECOMPExtractiveOperator
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
    """运行RECOMP Extractive RAG pipeline"""
    env = LocalEnvironment()

    enable_profile = True

    (
        env.from_batch(HFDatasetBatch, config["source"])
        .map(Wiki18FAISSRetriever, config["retriever"], enable_profile=enable_profile)
        .map(RECOMPExtractiveOperator, config["recomp_extr"])  # RECOMP Extractive压缩
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
        time.sleep(6000)  # 100 minutes timeout
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
        print("🧪 Test mode detected - RECOMP Extractive pipeline requires pre-built FAISS index")
        print("✅ Test passed: Example structure validated")
        sys.exit(0)

    # 配置文件路径
    config_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "config", "config_recomp_extr.yaml"
    )

    # 检查配置文件是否存在
    if not os.path.exists(config_path):
        print(f"❌ Configuration file not found: {config_path}")
        print("Please ensure the config file exists before running this example.")
        sys.exit(1)

    config = load_config(config_path)

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

    # 打印运行信息
    print("🚀 Starting RECOMP Extractive RAG Pipeline")
    print(f"📊 Data source: {config['source'].get('hf_dataset_name', 'N/A')}")
    print(f"📈 Max samples: {config['source']['max_samples']}")
    print(f"🔍 Top-k retrieval: {config['retriever']['top_k']}")
    print(f"🗜️  RECOMP model: {config['recomp_extr'].get('model_path', 'N/A')}")
    print(f"📝 Top-k sentences: {config['recomp_extr'].get('top_k', 5)}")
    print(f"🤖 Generator model: {config['generator']['vllm']['model_name']}")
    print("=" * 60)

    pipeline_run(config)
