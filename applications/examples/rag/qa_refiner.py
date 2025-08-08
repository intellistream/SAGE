import os
import time
import json
from sage.kernel.utils.logging.custom_logger import CustomLogger
from sage.core.api.local_environment import LocalEnvironment
from sage.kernel.utils.config.loader import load_config
from sage.lib.io_utils.batch import HFDatasetBatch
from sage.middleware.services.memory.memory_service import MemoryService

from sage.lib.rag.retriever import DenseRetriever
from sage.lib.rag.longrefiner_fn.longrefiner_adapter import LongRefinerAdapter
from sage.lib.rag.promptor import QAPromptor
from sage.lib.rag.generator import OpenAIGenerator
from sage.lib.rag.evaluate import (
    F1Evaluate, RecallEvaluate, BertRecallEvaluate, RougeLEvaluate,
    BRSEvaluate, AccuracyEvaluate, TokenCountEvaluate,
    LatencyEvaluate, ContextRecallEvaluate, CompressionRateEvaluate
)

def pipeline_run(config):
    env = LocalEnvironment()

    def memory_service_factory():
        memory_service = MemoryService()

        result = memory_service.create_collection(
            name="qa_collection",
            backend_type="VDB",
            description="Collection for QA pipeline"
        )

        if result['status'] == 'success':
            print("✅ Collection created successfully")
        else:
            print(f"❌ Failed to create collection: {result['message']}")

        return memory_service

    env.register_service("memory_service", memory_service_factory)

    enable_profile = True

    (
        env
        .from_batch(HFDatasetBatch, config["source"])
        .map(DenseRetriever, config["retriever"], enable_profile=enable_profile)
        .map(LongRefinerAdapter, config["refiner"], enable_profile=enable_profile)
        .map(QAPromptor, config["promptor"], enable_profile=enable_profile)
        .map(OpenAIGenerator, config["generator"]["vllm"], enable_profile=enable_profile)
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
        env.submit()
        time.sleep(200)
    except KeyboardInterrupt:
        print("停止运行")
    finally:
        env.close()

# ==========================================================
if __name__ == "__main__":
    CustomLogger.disable_global_console_debug()
    cfg = load_config("../../resources/config/config_refiner.yaml")
    pipeline_run(cfg)