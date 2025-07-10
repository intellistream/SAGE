import time
from sage_core.api.env import LocalEnvironment
from sage_core.api.tuple import Data
from sage_core.api.base_function import BaseFunction
from sage_common_funs.rag.generator import OpenAIGenerator
from sage_common_funs.rag.promptor import QAPromptor
from sage_common_funs.rag.evaluate import F1Evaluate
from sage_utils.config_loader import load_config
import json

class CustomFileSource(BaseFunction):
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
                return Data((question, reference))

class CustomPromptor(QAPromptor):
    def execute(self, data: Data[tuple[str, str]]) -> Data[tuple[str, list]]:
        question, reference = data.data
        prompt = [{"role":"user","content": f"Question: {question}\nAnswer:"}]
        return Data((reference, prompt))

# 生成器输出 (reference, prediction)
class ResultFormatter(BaseFunction):
    def execute(self, data: Data[tuple[str, str]]) -> Data[tuple[str, str]]:
        reference, generated = data.data
        return Data((reference, generated))

def pipeline_run(config):
    env = LocalEnvironment()
    env.set_memory(config=None)

    (env
     .from_source(CustomFileSource, config["source"])
     .map(CustomPromptor, config["promptor"])
     .map(OpenAIGenerator, config["generator"])
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
    config = load_config("config_evaluate.yaml")
    pipeline_run(config)
