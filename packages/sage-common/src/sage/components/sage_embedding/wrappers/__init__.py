"""Wrapper classes for various embedding providers."""

from .hash_wrapper import HashEmbedding
from .mock_wrapper import MockEmbedding
from .hf_wrapper import HFEmbedding
from .openai_wrapper import OpenAIEmbedding
from .jina_wrapper import JinaEmbedding
from .zhipu_wrapper import ZhipuEmbedding
from .cohere_wrapper import CohereEmbedding
from .bedrock_wrapper import BedrockEmbedding
from .ollama_wrapper import OllamaEmbedding
from .siliconcloud_wrapper import SiliconCloudEmbedding
from .nvidia_openai_wrapper import NvidiaOpenAIEmbedding

__all__ = [
    "HashEmbedding",
    "MockEmbedding",
    "HFEmbedding",
    "OpenAIEmbedding",
    "JinaEmbedding",
    "ZhipuEmbedding",
    "CohereEmbedding",
    "BedrockEmbedding",
    "OllamaEmbedding",
    "SiliconCloudEmbedding",
    "NvidiaOpenAIEmbedding",
]
