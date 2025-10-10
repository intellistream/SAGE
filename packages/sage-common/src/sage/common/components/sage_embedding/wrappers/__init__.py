"""Wrapper classes for various embedding providers.

This module uses lazy imports to avoid loading heavy dependencies
(transformers, torch, etc.) until they are actually needed.
"""

from typing import TYPE_CHECKING

# 轻量级的 wrapper 可以直接导入
from .hash_wrapper import HashEmbedding
from .mock_wrapper import MockEmbedding

# 重量级的 wrapper 使用延迟导入，避免在模块加载时就加载大型依赖
if TYPE_CHECKING:
    from .bedrock_wrapper import BedrockEmbedding
    from .cohere_wrapper import CohereEmbedding
    from .hf_wrapper import HFEmbedding
    from .jina_wrapper import JinaEmbedding
    from .nvidia_openai_wrapper import NvidiaOpenAIEmbedding
    from .ollama_wrapper import OllamaEmbedding
    from .openai_wrapper import OpenAIEmbedding
    from .siliconcloud_wrapper import SiliconCloudEmbedding
    from .zhipu_wrapper import ZhipuEmbedding

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


def __getattr__(name: str):
    """延迟导入重量级 wrapper，只在实际使用时才加载依赖"""
    if name == "HFEmbedding":
        from .hf_wrapper import HFEmbedding

        return HFEmbedding
    elif name == "OpenAIEmbedding":
        from .openai_wrapper import OpenAIEmbedding

        return OpenAIEmbedding
    elif name == "JinaEmbedding":
        from .jina_wrapper import JinaEmbedding

        return JinaEmbedding
    elif name == "ZhipuEmbedding":
        from .zhipu_wrapper import ZhipuEmbedding

        return ZhipuEmbedding
    elif name == "CohereEmbedding":
        from .cohere_wrapper import CohereEmbedding

        return CohereEmbedding
    elif name == "BedrockEmbedding":
        from .bedrock_wrapper import BedrockEmbedding

        return BedrockEmbedding
    elif name == "OllamaEmbedding":
        from .ollama_wrapper import OllamaEmbedding

        return OllamaEmbedding
    elif name == "SiliconCloudEmbedding":
        from .siliconcloud_wrapper import SiliconCloudEmbedding

        return SiliconCloudEmbedding
    elif name == "NvidiaOpenAIEmbedding":
        from .nvidia_openai_wrapper import NvidiaOpenAIEmbedding

        return NvidiaOpenAIEmbedding
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
