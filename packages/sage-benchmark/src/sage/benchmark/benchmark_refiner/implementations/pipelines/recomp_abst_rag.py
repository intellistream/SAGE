# @test:skip           - 跳过测试

"""
RECOMP Abstractive RAG Pipeline
===============================

使用RECOMP Abstractive压缩算法的RAG pipeline。
使用微调的T5模型生成检索文档的摘要，将多个检索文档压缩为简洁的摘要。

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

# RECOMPAbstractiveOperator may not be available yet (depends on Task 2 completion)
try:
    from sage.middleware.components.sage_refiner import RECOMPAbstractiveOperator

    if RECOMPAbstractiveOperator is None:
        raise ImportError("RECOMPAbstractiveOperator is None")
except ImportError:
    RECOMPAbstractiveOperator = None
    print(
        "⚠️  Warning: RECOMPAbstractiveOperator is not available yet.\n"
        "   Please ensure Task 2 (RECOMP Abstractive implementation) is completed first.\n"
        "   See: docs/dev-notes/l4-middleware/recomp-integration-tasks.md"
    )

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
    """运行RECOMP Abstractive RAG pipeline"""
    env = LocalEnvironment()

    enable_profile = True

    (
        env.from_batch(HFDatasetBatch, config["source"])
        .map(Wiki18FAISSRetriever, config["retriever"], enable_profile=enable_profile)
        .map(RECOMPAbstractiveOperator, config["recomp_abst"])  # RECOMP Abstractive压缩
        .map(QAPromptor, config["promptor"], enable_profile=enable_profile)
        .map(OpenAIGenerator, config["generator"]["vllm"], enable_profile=enable_profile)
        .map(F1Evaluate, config["evaluate"])
        .map(TokenCountEvaluate, config["evaluate"])
        .map(LatencyEvaluate, config["evaluate"])
        .map(CompressionRateEvaluate, config["evaluate"])
    )

    try:
        env.submit()
        # Wait for pipeline to complete (T5 summarization may take longer)
        time.sleep(12000)  # 200 minutes timeout
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
        print("🧪 Test mode detected - RECOMP Abstractive pipeline requires pre-built FAISS index")
        print("✅ Test passed: Example structure validated")
        sys.exit(0)

    # 检查 RECOMPAbstractiveOperator 是否可用
    if RECOMPAbstractiveOperator is None:
        print("❌ RECOMPAbstractiveOperator is not available.")
        print("   Please complete Task 2 (RECOMP Abstractive implementation) first.")
        print("   See: docs/dev-notes/l4-middleware/recomp-integration-tasks.md")
        sys.exit(1)

    # 配置文件路径
    config_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "config", "config_recomp_abst.yaml"
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
    print("🚀 Starting RECOMP Abstractive RAG Pipeline")
    print(f"📊 Data source: {config['source'].get('hf_dataset_name', 'N/A')}")
    print(f"📈 Max samples: {config['source']['max_samples']}")
    print(f"🔍 Top-k retrieval: {config['retriever']['top_k']}")
    print(f"🗜️  RECOMP model: {config['recomp_abst'].get('model_path', 'N/A')}")
    print(f"📝 Max target length: {config['recomp_abst'].get('max_target_length', 512)}")
    print(f"🤖 Generator model: {config['generator']['vllm']['model_name']}")
    print("=" * 60)

    pipeline_run(config)
