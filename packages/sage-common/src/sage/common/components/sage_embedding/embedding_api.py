import os

# flake8: noqa: E402
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
from sage.common.components.sage_embedding.embedding_model import EmbeddingModel


def apply_embedding_model(name: str = "default", **kwargs) -> EmbeddingModel:
    """
    usage  参见sage/api/model/operator_test.py
    while name(method) = "hf", please set the param:model;
    while name(method) = "openai",if you need call other APIs which are compatible with openai,set the params:base_url,api_key,model;
    while name(method) = "jina/siliconcloud/cohere",please set the params:api_key,model;
    Example:operator_test.py
    """
    return EmbeddingModel(method=name, **kwargs)
