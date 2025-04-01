from sage.core.model.embedding_model.embedding_model import EmbeddingModel
class GeneratorModelClient:
    def __init__(self, model_name: str):
        self.model_name = model_name

    def generate(self, prompt: str) -> str:
        # TODO: Replace with actual model inference logic
        return f"[Generated from {self.model_name}]: {prompt}"


class EmbeddingModelClient:
    def __init__(self, name: str = "default",**kwargs):
        self.name = name
        self.embedding_model = EmbeddingModel(method=name,**kwargs)

    def embed(self, text: str) -> list[float]:
        # TODO: Replace with actual embedding_model logic
        return self.embedding_model.embed(text)

    def get_dim(self)->int:
        return self.embedding_model.get_dim()


def apply_generator_model(name: str) -> GeneratorModelClient:
    return GeneratorModelClient(name)


def apply_embedding_model(name: str = "default",**kwargs) -> EmbeddingModelClient:
    return EmbeddingModelClient(name,**kwargs)