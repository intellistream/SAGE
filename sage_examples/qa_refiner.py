import os
import time
import json

from sage_core.api.local_environment import LocalEnvironment
from sage_utils.config_loader import load_config
from sage_core.function.source_function import SourceFunction
from sage_core.function.map_function import MapFunction

from sage_libs.rag.retriever import DenseRetriever
from sage_plugins.longrefiner_fn.longrefiner_adapter import LongRefinerAdapter
from sage_libs.rag.promptor import QAPromptor
from sage_libs.rag.generator import OpenAIGenerator
from sage_libs.rag.evaluate import (
    F1Evaluate, RecallEvaluate, BertRecallEvaluate, RougeLEvaluate,
    BRSEvaluate, AccuracyEvaluate, TokenCountEvaluate,
    LatencyEvaluate, ContextRecallEvaluate, CompressionRateEvaluate
)

# ==========================================================
# Source
# ==========================================================
class CustomFileSource(SourceFunction):
    """
    支持两种数据源:
      • local  -> 本地 JSONL, 每行含 question+golden_answers
      • hf     -> HuggingFace dataset
    输出统一:
        {"query": str, "references": List[str]}
    """

    def __init__(self, config=None, **kwargs):
        super().__init__(config=config, **kwargs)
        self.source_type = config.get("type", "local")
        if self.source_type == "local":
            self.path = config["data_path"]
        elif self.source_type == "hf":
            self.hf_name   = config["hf_dataset_name"]
            self.hf_config = config.get("hf_dataset_config")
            self.hf_split  = config.get("hf_split", "train")
        else:
            raise ValueError(f"Unsupported source.type: {self.source_type}")
        self._iter = None

    # ------------------------------------------------------
    def _build_iter(self):
        if self.source_type == "local":
            with open(self.path, "r", encoding="utf-8") as f:
                for line in f:
                    item = json.loads(line)
                    yield {
                        "query":      item.get("question", ""),
                        "references": item.get("golden_answers") or []
                    }
        else:  # hf
            from datasets import load_dataset
            ds = load_dataset(self.hf_name, self.hf_config,
                              split=self.hf_split, streaming=True)
            for ex in ds:
                yield {
                    "query":      ex.get("question", ""),
                    "references": ex.get("golden_answers") or []
                }

    # ------------------------------------------------------
    def execute(self):
        if self._iter is None:
            self.logger.debug(f"Initializing data source: {self.source_type}")
            src_info = getattr(self, 'path', getattr(self, 'hf_name', ''))
            print(f"[CustomFileSource] mode={self.source_type}, path={src_info}")
            self._iter = self._build_iter()

        try:
            data = next(self._iter)
            self.logger.debug(f"Yielding data: {data}")
            return data
        except StopIteration:
            return None

# ==========================================================
# Retriever
# ==========================================================
class TimeDenseRetriever(MapFunction):
    def __init__(self, config=None, **kwargs):
        super().__init__(**kwargs)
        self.retriever = DenseRetriever(config)

    def execute(self, data: dict):
        # 框架未自动注入 ctx 时手动补全
        if getattr(self.retriever, "ctx", None) is None and self.ctx is not None:
            self.retriever.ctx = self.ctx

        start = time.time()
        chunks = list(self.retriever.execute(data["query"]))
        data["retrieval_time"] = time.time() - start
        data["retrieved_docs"] = [
            c["text"] if isinstance(c, dict) else c
            for c in chunks
        ]
        return data

# ==========================================================
# Long Refiner
# ==========================================================
class TimeLongRefiner(MapFunction):
    def __init__(self, config=None, **kwargs):
        super().__init__(**kwargs)
        self.refiner = LongRefinerAdapter(config)
        self.refiner.ctx = self.ctx

    def execute(self, data: dict):
        start = time.time()
        query, refined = self.refiner.execute((data["query"], data["retrieved_docs"]))
        data["refine_time"]  = time.time() - start
        data["refined_docs"] = refined
        data["query"]        = query
        return data

# ==========================================================
# Promptor
# ==========================================================
class TimeQAPromptor(MapFunction):
    def __init__(self, config=None, **kwargs):
        super().__init__(**kwargs)
        self.promptor = QAPromptor(config)
        self.promptor.ctx = self.ctx

    def execute(self, data: dict):
        query, prompt = self.promptor.execute((data["query"], data["refined_docs"]))
        data["prompt"] = prompt
        data["query"]  = query
        return data

# ==========================================================
# Generator
# ==========================================================
class TimeGenerator(MapFunction):
    """
    把耗时统计叠加在 OpenAIGenerator 之上，保持
    qa_refiner 字典 I/O 与下游 Evaluate 兼容。
    """

    def __init__(self, config: dict = None, **kwargs):
        super().__init__(**kwargs)
        # 新 OpenAIGenerator 只需“子配置”即可
        self.generator = OpenAIGenerator(config)

    def execute(self, data: dict):
        start = time.time()

        # OpenAIGenerator 期望 [user_query, prompt] 或 [prompt]
        user_query = data["query"]
        prompt     = data["prompt"]
        generated  = self.generator.execute([user_query, prompt])[1]

        data["generated"]       = generated
        data["generation_time"] = time.time() - start
        return data

# ==========================================================
# Pipeline
# ==========================================================
def pipeline_run(config):
    env = LocalEnvironment()

    (
        env
        .from_source(CustomFileSource, config["source"])
        .map(TimeDenseRetriever,       config["retriever"])
        .map(TimeLongRefiner,          config["refiner"])
        .map(TimeQAPromptor,           config["promptor"])
        # —— 切换本地 / vllm / 远程端点，只需改 YAML 即可 ——
        .map(TimeGenerator,            config["generator"]["vllm"])
        .map(F1Evaluate,               config["evaluate"])
        .map(RecallEvaluate,           config["evaluate"])
        # .map(BertRecallEvaluate,     config["evaluate"])
        .map(RougeLEvaluate,           config["evaluate"])
        .map(BRSEvaluate,              config["evaluate"])
        .map(AccuracyEvaluate,         config["evaluate"])
        .map(TokenCountEvaluate,       config["evaluate"])
        .map(LatencyEvaluate,          config["evaluate"])
        .map(ContextRecallEvaluate,    config["evaluate"])
        .map(CompressionRateEvaluate,  config["evaluate"])
    )

    env.submit()
    # 等待任务完成；视需要调整
    time.sleep(100)
    env.close()

# ==========================================================
if __name__ == "__main__":
    cfg = load_config("config/config_refiner.yaml")
    pipeline_run(cfg)
