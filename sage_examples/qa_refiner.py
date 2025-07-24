import os
import time, json
from sage_core.api.local_environment import LocalEnvironment
from sage_libs.rag.evaluate import F1Evaluate, BertRecallEvaluate, RougeLEvaluate, BRSEvaluate, RecallEvaluate, \
    AccuracyEvaluate, TokenCountEvaluate, LatencyEvaluate, ContextRecallEvaluate, CompressionRateEvaluate
from sage_utils.clients.generator_model import apply_generator_model
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
class CustomFileSource(SourceFunction):
    """
    支持两种数据源：
      type = "local" -> 从本地 JSONL 读取 question + golden_answers 列表
      type = "hf"    -> 调用 HF datasets.load_dataset 读取 question + golden_answers 列表
    统一输出每条:
      { "query": str, "references": List[str] }
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
                    "query": ex.get("question", ""),
                    "references": ex.get("golden_answers") or []
                }
    def execute(self):
        if self._iter is None:
            self.logger.debug(f"Initializing data source: {self.source_type}")
            print(f"[CustomFileSource] mode={self.source_type}, path={getattr(self, 'path', self.hf_name)}")
            self._iter = self._build_iter()
        try:
            self.logger.debug("Fetching next data item from source")
            data = next(self._iter)
            self.logger.debug(f"Yielding data: {data}")
            return data
        except StopIteration:
            return None
class TimeDenseRetriever(MapFunction):
    def __init__(self, config=None, **kwargs):
        super().__init__(**kwargs)
        self.retriever = DenseRetriever(config)
    def execute(self, data: dict):
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
class TimeGenerator(MapFunction):
    def __init__(self, config=None, **kwargs):
        super().__init__(**kwargs)
        self.config = config
        self.model = apply_generator_model(
            method=self.config["method"],
            model_name=self.config["model_name"],
            base_url=self.config["base_url"],
            api_key=self.config["api_key"] or os.getenv("ALIBABA_API_KEY"),
            seed=42  # Hardcoded seed for reproducibility
        )
        self.num = 1
    def execute(self, data: dict):
        start = time.time()
        response = self.model.generate(data["prompt"])
        data["generation_time"] = time.time() - start
        data["generated"] = response
        data["query"] = data["query"]
        return data
def pipeline_run(config):
    env = LocalEnvironment()
    # env.set_memory(config=None)
    (
        env
        .from_source(CustomFileSource, config["source"])
        .map(TimeDenseRetriever, config["retriever"])
        .map(TimeLongRefiner, config["refiner"])
        .map(TimeQAPromptor, config["promptor"])
        .map(TimeGenerator, config["generator"]["vllm"])  ## ———— 一行切换本地, vllm or 远程模型 ————
        .map(F1Evaluate, config["evaluate"])
        .map(RecallEvaluate, config["evaluate"])
        # .map(BertRecallEvaluate, config["evaluate"])
        .map(RougeLEvaluate, config["evaluate"])
        .map(BRSEvaluate, config["evaluate"])
        .map(AccuracyEvaluate, config["evaluate"])
        .map(TokenCountEvaluate, config["evaluate"])
        .map(LatencyEvaluate, config["evaluate"])
        .map(ContextRecallEvaluate, config["evaluate"])
        .map(CompressionRateEvaluate, config["evaluate"])
    )
    env.submit()
    time.sleep(100)
    env.close()
if __name__ == "__main__":
    config = load_config("config/config_refiner.yaml")
    pipeline_run(config)