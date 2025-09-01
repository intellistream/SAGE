import os
import time
import json
from sage.common.utils.logging.custom_logger import CustomLogger
from sage.core.api.local_environment import LocalEnvironment
from sage.common.utils.config.loader import load_config
from sage.libs.io_utils.batch import HFDatasetBatch
from sage.middleware.components.neuromem.memory_service import MemoryService

from sage.libs.rag.retriever import ChromaRetriever
from sage.libs.rag.longrefiner.longrefiner_adapter import LongRefinerAdapter
from sage.libs.rag.promptor import QAPromptor
from sage.libs.rag.generator import OpenAIGenerator
from sage.libs.rag.evaluate import (
    F1Evaluate, RecallEvaluate, BertRecallEvaluate, RougeLEvaluate,
    BRSEvaluate, AccuracyEvaluate, TokenCountEvaluate,
    LatencyEvaluate, ContextRecallEvaluate, CompressionRateEvaluate
)

def pipeline_run(config):
    env = LocalEnvironment()

    enable_profile = True

    (
        env
        .from_batch(HFDatasetBatch, config["source"])
        .map(ChromaRetriever, config["retriever"], enable_profile=enable_profile)
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
    # from sage.common.utils.logging.custom_logger import CustomLogger
    # CustomLogger.disable_global_console_debug()
    
    import os
    config_path = os.path.join(os.path.dirname(__file__), "..", "config", "config_refiner.yaml")
    config = load_config(config_path)
    pipeline_run(config)