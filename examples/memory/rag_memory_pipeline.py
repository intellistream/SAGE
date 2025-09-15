import time

import yaml
from rag_memory_service import RAGMemoryService
from sage.common.utils.logging.custom_logger import CustomLogger
from sage.core.api.function.batch_function import BatchFunction
from sage.core.api.function.map_function import MapFunction
from sage.core.api.function.sink_function import SinkFunction
from sage.core.api.local_environment import LocalEnvironment
from sage.core.communication.metronome import create_metronome
from sage.libs.rag.generator import OpenAIGenerator
from sage.libs.rag.promptor import QAPromptor

metronome = create_metronome("sync_metronome")


# 批处理数据源：遍历5个问题
class QuestionSource(BatchFunction):
    use_metronome = True

    def __init__(self, config):
        super().__init__()
        self.counter = 0
        self.max = config.get("max_index")
        self.questions = config.get("questions")
        self.metronome = metronome

    def execute(self):
        if self.counter >= self.max:
            return None
        self.counter += 1
        return self.questions[self.counter - 1]


class Retriever(MapFunction):
    def execute(self, data):
        question = data
        data = {}

        results = self.call_service["rag_memory"].retrieve(question)
        data["question"] = question
        data["context"] = results

        return data


class Writer(MapFunction):
    def execute(self, data):
        q_and_ctx, answer = data
        question = q_and_ctx.get("question")

        self.call_service["rag_memory"].insert(
            question, {"answer": answer, "topic": "健康-个性化"}
        )
        data = {}
        data["question"] = question
        data["answer"] = answer
        return data


class PrintSink(SinkFunction):
    use_metronome = True

    def __init__(self):
        super().__init__()
        self.metronome = metronome

    def execute(self, data):
        print(f"Q: {data.get('question')}\nA: {data.get('answer')}\n")


def main():

    with open("examples/config/config_rag_memory_pipeline.yaml", "r") as f:
        config = yaml.safe_load(f)

    metronome.release_once()
    env = LocalEnvironment("rag_memory_pipeline")

    env.register_service("rag_memory", RAGMemoryService, config["rag_config"])

    (
        env.from_batch(QuestionSource, config["source"])
        .map(Retriever)
        .map(QAPromptor, config["promptor"])
        .map(OpenAIGenerator, config["generator"]["vllm"])
        .map(Writer)
        .sink(PrintSink)
    )

    env.submit(autostop=True)


if __name__ == "__main__":
    CustomLogger.disable_global_console_debug()
    main()
