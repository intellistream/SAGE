from sage.core.model.embedding_model import EmbeddingModel
class GeneratorModelClient:
    def __init__(self, model_name: str):
        self.model_name = model_name

    def generate(self, prompt: str) -> str:
        # TODO: Replace with actual model inference logic
        return f"[Generated from {self.model_name}]: {prompt}"


class EmbeddingModelClient(EmbeddingModel):
    def __init__(self, method, **kwargs):
        # self.model_name = model_name
        self.method = method
        super().__init__(method, **kwargs)

    def embed(self, text: str) -> list[float]:
        # TODO: Replace with actual embedding_model logic
        return super().embed(text)


def apply_generator_model(name: str) -> GeneratorModel:
    return GeneratorModelClient(name)


def apply_embedding_model(name: str = "default", **kwargs) -> EmbeddingModel:
    return EmbeddingModelClient(name, **kwargs)
