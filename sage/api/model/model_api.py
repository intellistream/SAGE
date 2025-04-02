from token import OP
# from openai import OpenAI
# from llvm.test2 import VllmGenerator
from sage.core.model.generator_model.generator_model import OpenAIClient,VLLMGenerator
class GeneratorModelClient:
    def __init__(self, method: str, model_name: str, **kwargs):
        if method=="openai":
            self.model=OpenAIClient(model_name,**kwargs)
        elif method=="vllm":
            self.model=VLLMGenerator(model_name,**kwargs)
        else:
            raise ValueError("this method isn't supported")


    def generate(self, prompt: str, **kwargs):

        response=self.model.generate(prompt, **kwargs)

        return response


class EmbeddingModelClient:
    def __init__(self, model_name: str = "default"):
        self.model_name = model_name

    def embed(self, text: str) -> list[float]:
        # TODO: Replace with actual embedding_model logic
        return [ord(c) / 255.0 for c in text[:128]]


def apply_generator_model(method: str,name: str,**kwargs) -> GeneratorModelClient:
    return GeneratorModelClient(method,name,**kwargs)


def apply_embedding_model(name: str = "default") -> EmbeddingModelClient:
    return EmbeddingModelClient(name)