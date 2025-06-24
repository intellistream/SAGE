from token import OP
# from openai import OpenAI
# from llvm.test2 import VllmGenerator
from sage.core.model.embedding_model.embedding_model import EmbeddingModel
from sage.core.model.generator_model.generator_model import GeneratorModel


def apply_generator_model(method: str,**kwargs) -> GeneratorModel:
    """
    usage  参见sage/api/model/operator_test.py
    while name(method) = "hf", please set the param:model;
    while name(method) = "openai",if you need call other APIs which are compatible with openai,set the params:base_url,api_key,model;
    Example:operator_test.py
    """
    return GeneratorModel(method = method,**kwargs)


def apply_embedding_model(name: str = "default",**kwargs) -> EmbeddingModel:
    """
    usage  参见sage/api/model/operator_test.py
    while name(method) = "hf", please set the param:model;
    while name(method) = "openai",if you need call other APIs which are compatible with openai,set the params:base_url,api_key,model;
    while name(method) = "jina/siliconcloud/cohere",please set the params:api_key,model;
    Example:operator_test.py
    """
    return EmbeddingModel(method=name,**kwargs)