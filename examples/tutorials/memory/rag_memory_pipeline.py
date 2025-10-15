# @test:allow-demo    - 允许包含demo关键字的文件运行测试
import sys

import yaml
from rag_memory_service import RAGMemoryService
from sage.common.utils.logging.custom_logger import CustomLogger
from sage.kernel.api.function.batch_function import BatchFunction
from sage.kernel.api.function.map_function import MapFunction
from sage.kernel.api.function.sink_function import SinkFunction
from sage.kernel.api.local_environment import LocalEnvironment
from sage.libs.rag.generator import OpenAIGenerator
from sage.libs.rag.promptor import QAPromptor


# 批处理数据源：遍历5个问题
class QuestionSource(BatchFunction):
    def __init__(self, config):
        super().__init__()
        self.counter = 0
        self.max = config.get("max_index")
        self.questions = config.get("questions")

    def execute(self):
        if self.counter >= self.max:
            return None
        self.counter += 1
        return self.questions[self.counter - 1]


class Retriever(MapFunction):
    def execute(self, data):
        question = data
        data = {}

        results = self.call_service("rag_memory", question, method="retrieve")
        data["question"] = question
        data["context"] = results

        return data


class Writer(MapFunction):
    def execute(self, data):
        q_and_ctx, answer = data
        question = q_and_ctx.get("question")

        self.call_service(
            "rag_memory",
            question,
            {"answer": answer, "topic": "健康-个性化"},
            method="insert",
        )
        data = {}
        data["question"] = question
        data["answer"] = answer
        return data


class PrintSink(SinkFunction):
    def execute(self, data):
        print(f"Q: {data.get('question')}\nA: {data.get('answer')}\n")


def main():
    from pathlib import Path

    # 获取配置文件的正确路径
    script_dir = Path(__file__).parent
    config_file = script_dir / "config" / "config_rag_memory_pipeline.yaml"

    if not config_file.exists():
        print(f"❌ 配置文件不存在: {config_file}")
        sys.exit(1)

    with open(config_file, "r") as f:
        config = yaml.safe_load(f)

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
