import time
import json
import yaml

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

    def run(self):
        # 在开始时打印一次，确认走的分支和路径
        print(f"[CustomFileSource] mode={self.source_type}, path={getattr(self, 'path', self.hf_name)}")
        if self.source_type == "local":
            with open(self.path, "r", encoding="utf-8") as f:
                for line in f:
                    item = json.loads(line)
                    golds = item.get("golden_answers") or []
                    yield {
                        "query":      item.get("question", ""),
                        "references": golds
                    }

        elif self.source_type == "hf":
            from datasets import load_dataset
            ds = load_dataset(self.hf_name, self.hf_config, split=self.hf_split)
            for ex in ds:
                golds = ex.get("golden_answers") or ex.get("answers") or []
                yield {
                    "query":      ex.get("question", ""),
                    "references": golds
                }

        else:
            # 不会走到这里
            raise RuntimeError(f"Unknown source.type {self.source_type}")


class TimeDenseRetriever(MapFunction):
    def __init__(self, config=None, **kwargs):
        super().__init__(**kwargs)
        self.retriever = DenseRetriever(config)
        self.retriever.ctx = self.ctx

    def execute(self, data: dict):
        start = time.time()
        query, chunks = self.retriever.execute(data["query"])
        data["retrieval_time"] = time.time() - start
        data["retrieved_docs"] = [
            c["text"] if isinstance(c, dict) else c
            for c in chunks
        ]
        data["query"] = query
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
        self.generator = OpenAIGenerator(config, self.ctx)
        self.generator.ctx = self.ctx

    def execute(self, data: dict):
        start = time.time()
        query, gen = self.generator.execute((data["query"], data["prompt"]))
        data["generation_time"] = time.time() - start
        data["generated"]       = gen
        data["query"]           = query
        return data


def pipeline_run(config):
    env = LocalEnvironment("111")
    # env.set_memory(config=None)

    (
        env
        .from_source(CustomFileSource, config["source"])
        .map(TimeDenseRetriever, config["retriever"])
        .map(TimeLongRefiner, config["refiner"])
        .map(TimeQAPromptor, config["promptor"])
        .map(TimeGenerator, config["generator"]["local"])  ## ———— 一行切换本地, vllm or 远程模型 ————
        .map(F1Evaluate, config["evaluate"])
        .map(RecallEvaluate, config["evaluate"])
        .map(BertRecallEvaluate, config["evaluate"])
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