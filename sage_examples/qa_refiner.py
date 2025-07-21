import time, json
from sage_core.api.env import LocalEnvironment
from sage_utils.config_loader import load_config
from sage_core.function.map_function import MapFunction

from sage_libs.rag.retriever import DenseRetriever
from sage_plugins.longrefiner_fn.longrefiner_adapter import LongRefinerAdapter
from sage_libs.rag.promptor import QAPromptor
from sage_libs.rag.generator import get_generator_preset

from sage_common_funs.io.sink import TerminalSink
from sage_common_funs.rag.evaluate import (
    F1Evaluate, RecallEvaluate, BertRecallEvaluate, RougeLEvaluate, BRSEvaluate,
    AccuracyEvaluate, TokenCountEvaluate, LatencyEvaluate,
    ContextRecallEvaluate, CompressionRateEvaluate
)


class CustomFileSource(MapFunction):
    def __init__(self, config=None, **kwargs):
        super().__init__(**kwargs)
        self.path = config["data_path"]

    def execute(self, data=None):
        with open(self.path, "r", encoding="utf-8") as f:
            for line in f:
                item = json.loads(line)
                return {
                    "query":     item.get("question", ""),
                    "reference": item.get("reference", "")
                }
        return None


class TimeDenseRetriever(MapFunction):
    def __init__(self, config=None, **kwargs):
        super().__init__(**kwargs)
        # 先让框架创建 retriever
        self.retriever = DenseRetriever(config)
        # 再把自己的 runtime_context 注入进去
        self.retriever.runtime_context = self.runtime_context

    def execute(self, data: dict):
        start = time.time()
        # 现在 retriever.runtime_context 已可用
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
        self.refiner.runtime_context = self.runtime_context

    def execute(self, data: dict):
        start = time.time()
        query, refined = self.refiner.execute((data["query"], data["retrieved_docs"]))
        data["refine_time"]   = time.time() - start
        data["refined_docs"]  = refined
        data["query"]         = query
        return data


class TimeQAPromptor(MapFunction):
    def __init__(self, config=None, **kwargs):
        super().__init__(**kwargs)
        self.promptor = QAPromptor(config)
        self.promptor.runtime_context = self.runtime_context

    def execute(self, data: dict):
        query, prompt = self.promptor.execute((data["query"], data["refined_docs"]))
        data["prompt"] = prompt
        data["query"]  = query
        return data


class TimeGenerator(MapFunction):
    def __init__(self, config=None, **kwargs):
        super().__init__(**kwargs)
        # ———— 一行切换本地 or 远程模型 ————
        #   只需 local 或 remote，参数全在 config/generator_presets.yaml 中定义
        self.generator = get_generator_preset("local")
        # 如果要使用远程模型，改成：
        # self.generator = get_generator_preset("remote")
        self.generator.runtime_context = self.runtime_context

    def run(self, element):
        # 示例流程：调用底层 generator 生成结果
        result = self.generator.run(element)
        return result

    def execute(self, data: dict):
        start = time.time()
        query, gen = self.generator.execute((data["query"], data["prompt"]))
        data["generation_time"] = time.time() - start
        data["generated"]       = gen
        data["query"]           = query
        return data


#class ResultFormatter(MapFunction):
#    def __init__(self, config=None, **kwargs):
#        super().__init__(**kwargs)
#
#    def execute(self, data: dict):
#        return (data["query"], data["generated"])


def pipeline_run(config):
    env = LocalEnvironment()
    env.set_memory(config=None)

    (
        env
        .from_source(CustomFileSource,     config["source"])
        .map(TimeDenseRetriever,           config["retriever"])
        .map(TimeLongRefiner,              config["refiner"])
        .map(TimeQAPromptor,               config["promptor"])
        .map(TimeGenerator,                config["generator"])
        .map(F1Evaluate,                   config["evaluate"])
        .map(RecallEvaluate,               config["evaluate"])
        .map(BertRecallEvaluate,           config["evaluate"])
        .map(RougeLEvaluate,               config["evaluate"])
        .map(BRSEvaluate,                  config["evaluate"])
        .map(AccuracyEvaluate,             config["evaluate"])
        .map(TokenCountEvaluate,           config["evaluate"])
        .map(LatencyEvaluate,              config["evaluate"])
        .map(ContextRecallEvaluate,        config["evaluate"])
        .map(CompressionRateEvaluate,      config["evaluate"])
        #.map(ResultFormatter,              config["evaluate"])
        #.sink(TerminalSink,                config["sink"])
    )

    env.submit()
    env.run_once()
    time.sleep(100)
    env.close()


if __name__ == "__main__":
    config = load_config("config/config_refiner.yaml")
    pipeline_run(config)