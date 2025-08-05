import time
from sage.core.api.env import LocalEnvironment
from sage.core.function.map_function import MapFunction
from sage.lib.rag.generator import OpenAIGenerator
from sage.lib.rag.promptor import QAPromptor
from sage.lib.rag.evaluate import F1Evaluate
from sage.utils.config_loader import load_config
import json

class CustomFileSource(MapFunction):
    def __init__(self, config, **kwargs):
        super().__init__(**kwargs)
        self.path = config["data_path"]

    def execute(self,data=None):
        with open(self.path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue  # 跳过空行
                item = json.loads(line)
                question = item.get("question", "")
                reference = item.get("reference", "")
                return (question, reference)

class CustomPromptor(QAPromptor):
    def execute(self, data: tuple[str, str]) -> tuple[str, list]:
        question, reference = data
        prompt = [{"role":"user","content": f"Question: {question}\nAnswer:"}]
        return (reference, prompt)

# 生成器输出 (reference, prediction)
class ResultFormatter(MapFunction):
    def execute(self, data: tuple[str, str]) -> tuple[str, str]:
        reference, generated = data
        return (reference, generated)

def pipeline_run(config):
    env = LocalEnvironment()
    env.set_memory(config=None)

    (env
     .from_source(CustomFileSource, config["source"])
     .map(CustomPromptor, config["promptor"])
     .map(OpenAIGenerator, config["generator"]["local"])
     .map(F1Evaluate, config["evaluate"])
     )
    try:
        env.submit()
        env.run_streaming()
        time.sleep(5)
        env.stop()
    finally:
        env.close()

if __name__ == "__main__":
    config = load_config("../../resources/config/config_evaluate.yaml")
    pipeline_run(config)
