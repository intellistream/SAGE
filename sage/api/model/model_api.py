from sage.core.model.embedding_model.embedding_model import EmbeddingModel
class GeneratorModelClient:
    def __init__(self, model_name: str):
        self.model_name = model_name

    def generate(self, prompt: str) -> str:
        # TODO: Replace with actual model inference logic
        return f"[Generated from {self.model_name}]: {prompt}"





def apply_generator_model(name: str) -> GeneratorModelClient:
    return GeneratorModelClient(name)


def apply_embedding_model(name: str = "default",**kwargs) -> EmbeddingModel:
    """
    usage  参见sage/api/model/test.py
    while name(method) = "hf", please set the param:model;
    while name(method) = "openai",if you need call other APIs which are compatible with openai,set the params:base_url,api_key,model;
    while name(method) = "jina/siliconcloud/cohere",please set the params:api_key,model;
    Example:test.py
    """
    return EmbeddingModel(method=name,**kwargs)

