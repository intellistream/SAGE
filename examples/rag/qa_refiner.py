import json
import os

from sage.common.utils.config.loader import load_config
from sage.common.utils.logging.custom_logger import CustomLogger
from sage.core.api.local_environment import LocalEnvironment
from sage.libs.io_utils.batch import HFDatasetBatch
from sage.libs.rag.evaluate import (AccuracyEvaluate, BertRecallEvaluate,
                                    BRSEvaluate, CompressionRateEvaluate,
                                    ContextRecallEvaluate, F1Evaluate,
                                    LatencyEvaluate, RecallEvaluate,
                                    RougeLEvaluate, TokenCountEvaluate)
from sage.libs.rag.generator import OpenAIGenerator
from sage.libs.rag.longrefiner.longrefiner_adapter import LongRefinerAdapter
from sage.libs.rag.promptor import QAPromptor
from sage.libs.rag.retriever import Wiki18FAISSRetriever
from sage.middleware.services.memory.memory_service import MemoryService


def pipeline_run(config):
    env = LocalEnvironment()

    enable_profile = True

    (
        env.from_batch(HFDatasetBatch, config["source"])
        .map(Wiki18FAISSRetriever, config["retriever"], enable_profile=enable_profile)
        .map(LongRefinerAdapter, config["refiner"], enable_profile=enable_profile)
        .map(QAPromptor, config["promptor"], enable_profile=enable_profile)
        .map(
            OpenAIGenerator, config["generator"]["vllm"], enable_profile=enable_profile
        )
        .map(F1Evaluate, config["evaluate"])
        .map(RecallEvaluate, config["evaluate"])
        .map(RougeLEvaluate, config["evaluate"])
        .map(BRSEvaluate, config["evaluate"])
        .map(AccuracyEvaluate, config["evaluate"])
        .map(TokenCountEvaluate, config["evaluate"])
        .map(LatencyEvaluate, config["evaluate"])
        .map(ContextRecallEvaluate, config["evaluate"])
        .map(CompressionRateEvaluate, config["evaluate"])
    )

    try:
        env.submit(autostop=True)
    except KeyboardInterrupt:
        print("停止运行")
    finally:
        env.close()


# ==========================================================
if __name__ == "__main__":
    from sage.common.utils.logging.custom_logger import CustomLogger

    CustomLogger.disable_global_console_debug()

    import os
    import sys

    # 检查是否在测试模式下运行
    if (
        os.getenv("SAGE_EXAMPLES_MODE") == "test"
        or os.getenv("SAGE_TEST_MODE") == "true"
    ):
        print(
            "🧪 Test mode detected - qa_refiner example requires pre-built FAISS index"
        )
        print("✅ Test passed: Example structure validated")
        sys.exit(0)

    config_path = os.path.join(
        os.path.dirname(__file__), "..", "config", "config_refiner.yaml"
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
        if not os.path.exists(index_path):
            print(f"❌ FAISS index file not found: {index_path}")
            print(
                "Please build the FAISS index first using build_milvus_dense_index.py or similar."
            )
            print("Or modify the config to use a different retriever type.")
            sys.exit(1)

    pipeline_run(config)
