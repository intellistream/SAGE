class GeneratorModel:
    def __init__(self, model_name: str):
        self.model_name = model_name

    def generate(self, prompt: str) -> str:
        # TODO: Replace with actual model inference logic
        return f"[Generated from {self.model_name}]: {prompt}"


class EmbeddingModel:
    def __init__(self, model_name: str = "default"):
        self.model_name = model_name

    def embed(self, text: str) -> list[float]:
        # TODO: Replace with actual embedding logic
        return [ord(c) / 255.0 for c in text[:128]]


def apply_generator_model(name: str) -> GeneratorModel:
    return GeneratorModel(name)


def apply_embedding_model(name: str = "default") -> EmbeddingModel:
    return EmbeddingModel(name)