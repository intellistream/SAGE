"""
SAGE Embedding Module - Unified interface for various embedding methods.

This module provides a consistent API for different embedding providers:
- Hash-based lightweight embedding (for testing)
- Mock embedding (for unit tests)
- HuggingFace Transformer models (local, high quality)
- OpenAI and other API-based services

Quick Start:
    >>> from sage.components.sage_embedding import get_embedding_model
    >>> 
    >>> # Create an embedding model
    >>> emb = get_embedding_model("hash", dim=384)
    >>> vec = emb.embed("hello world")
    >>> 
    >>> # List available methods
    >>> from sage.components.sage_embedding import list_embedding_models
    >>> models = list_embedding_models()
    >>> for method, info in models.items():
    ...     print(f"{method}: {info['description']}")
"""

# 直接从本包的_version模块加载版本信息
try:
    from sage.middleware._version import __author__, __email__, __version__
except ImportError:
    # 备用硬编码版本
    __version__ = "0.1.4"
    __author__ = "IntelliStream Team"
    __email__ = "shuhao_zhang@hust.edu.cn"

# 新架构：统一的 embedding 接口
from .base import BaseEmbedding
from .registry import EmbeddingRegistry, ModelStatus, ModelInfo
from .factory import (
    EmbeddingFactory,
    get_embedding_model,
    list_embedding_models,
    check_model_availability,
)

# 导入所有 wrappers
from .wrappers.hash_wrapper import HashEmbedding
from .wrappers.mock_wrapper import MockEmbedding
from .wrappers.hf_wrapper import HFEmbedding
from .wrappers.openai_wrapper import OpenAIEmbedding
from .wrappers.jina_wrapper import JinaEmbedding
from .wrappers.zhipu_wrapper import ZhipuEmbedding
from .wrappers.cohere_wrapper import CohereEmbedding
from .wrappers.bedrock_wrapper import BedrockEmbedding
from .wrappers.ollama_wrapper import OllamaEmbedding
from .wrappers.siliconcloud_wrapper import SiliconCloudEmbedding
from .wrappers.nvidia_openai_wrapper import NvidiaOpenAIEmbedding


# 注册所有 embedding 方法
def _register_all_methods():
    """注册所有内置的 embedding 方法"""
    
    # Hash Embedding
    EmbeddingRegistry.register(
        method="hash",
        display_name="Hash Embedding",
        description="轻量级哈希 embedding（测试用，无语义理解）",
        wrapper_class=HashEmbedding,
        requires_api_key=False,
        requires_model_download=False,
        default_dimension=384,
        example_models=["hash-384", "hash-768"],
    )
    
    # Mock Embedder
    EmbeddingRegistry.register(
        method="mock_embedder",
        display_name="Mock Embedder",
        description="随机 embedding（单元测试用）",
        wrapper_class=MockEmbedding,
        requires_api_key=False,
        requires_model_download=False,
        default_dimension=128,
        example_models=["mock-128", "mock-384"],
    )
    
    # HuggingFace Models
    EmbeddingRegistry.register(
        method="hf",
        display_name="HuggingFace Models",
        description="本地 Transformer 模型（高质量语义 embedding）",
        wrapper_class=HFEmbedding,
        requires_api_key=False,
        requires_model_download=True,
        default_dimension=None,  # 动态推断
        example_models=[
            "BAAI/bge-small-zh-v1.5",
            "BAAI/bge-base-zh-v1.5",
            "BAAI/bge-large-zh-v1.5",
            "sentence-transformers/all-MiniLM-L6-v2",
            "sentence-transformers/all-mpnet-base-v2",
        ],
    )
    
    # OpenAI Embedding
    EmbeddingRegistry.register(
        method="openai",
        display_name="OpenAI Embedding",
        description="OpenAI 官方 API（高质量，支持兼容 API）",
        wrapper_class=OpenAIEmbedding,
        requires_api_key=True,
        requires_model_download=False,
        default_dimension=1536,
        example_models=[
            "text-embedding-3-small",
            "text-embedding-3-large",
            "text-embedding-ada-002",
        ],
    )
    
    # Jina Embedding
    EmbeddingRegistry.register(
        method="jina",
        display_name="Jina AI Embedding",
        description="Jina AI 多语言 embedding（支持 late chunking）",
        wrapper_class=JinaEmbedding,
        requires_api_key=True,
        requires_model_download=False,
        default_dimension=1024,
        example_models=[
            "jina-embeddings-v3",
            "jina-embeddings-v2-base-en",
        ],
    )
    
    # Zhipu Embedding
    EmbeddingRegistry.register(
        method="zhipu",
        display_name="ZhipuAI Embedding",
        description="智谱 AI 中文 embedding（国内访问快）",
        wrapper_class=ZhipuEmbedding,
        requires_api_key=True,
        requires_model_download=False,
        default_dimension=1024,
        example_models=[
            "embedding-3",
            "embedding-2",
        ],
    )
    
    # Cohere Embedding
    EmbeddingRegistry.register(
        method="cohere",
        display_name="Cohere Embedding",
        description="Cohere 多语言 embedding（支持多种 input_type）",
        wrapper_class=CohereEmbedding,
        requires_api_key=True,
        requires_model_download=False,
        default_dimension=1024,
        example_models=[
            "embed-multilingual-v3.0",
            "embed-english-v3.0",
            "embed-multilingual-light-v3.0",
        ],
    )
    
    # AWS Bedrock Embedding
    EmbeddingRegistry.register(
        method="bedrock",
        display_name="AWS Bedrock Embedding",
        description="AWS Bedrock 托管服务（支持多种模型）",
        wrapper_class=BedrockEmbedding,
        requires_api_key=True,  # AWS 凭证
        requires_model_download=False,
        default_dimension=1024,
        example_models=[
            "amazon.titan-embed-text-v2:0",
            "amazon.titan-embed-text-v1",
            "cohere.embed-multilingual-v3",
        ],
    )
    
    # Ollama Embedding
    EmbeddingRegistry.register(
        method="ollama",
        display_name="Ollama Embedding",
        description="Ollama 本地部署（数据隐私，免费）",
        wrapper_class=OllamaEmbedding,
        requires_api_key=False,
        requires_model_download=True,
        default_dimension=768,
        example_models=[
            "nomic-embed-text",
            "mxbai-embed-large",
            "all-minilm",
        ],
    )
    
    # SiliconCloud Embedding
    EmbeddingRegistry.register(
        method="siliconcloud",
        display_name="SiliconCloud Embedding",
        description="硅基流动（国内访问快，价格优惠）",
        wrapper_class=SiliconCloudEmbedding,
        requires_api_key=True,
        requires_model_download=False,
        default_dimension=768,
        example_models=[
            "netease-youdao/bce-embedding-base_v1",
            "BAAI/bge-large-zh-v1.5",
            "BAAI/bge-base-en-v1.5",
        ],
    )
    
    # NVIDIA OpenAI Embedding
    EmbeddingRegistry.register(
        method="nvidia_openai",
        display_name="NVIDIA NIM Embedding",
        description="NVIDIA NIM（OpenAI 兼容，支持检索优化）",
        wrapper_class=NvidiaOpenAIEmbedding,
        requires_api_key=True,
        requires_model_download=False,
        default_dimension=2048,
        example_models=[
            "nvidia/llama-3.2-nv-embedqa-1b-v1",
            "nvidia/nv-embed-v1",
        ],
    )

# 执行注册
_register_all_methods()


# 向后兼容：保留旧的 EmbeddingModel 和 apply_embedding_model
from .embedding_model import EmbeddingModel, apply_embedding_model

# Service interface (新增)
from .service import EmbeddingService, EmbeddingServiceConfig


# 统一导出接口
__all__ = [
    # Service interface (新增 - 推荐用于 pipelines)
    "EmbeddingService",              # ⭐ Service 主要 API
    "EmbeddingServiceConfig",
    
    # 新架构（推荐使用 - 用于standalone）
    "BaseEmbedding",
    "EmbeddingRegistry",
    "EmbeddingFactory",
    "ModelStatus",
    "get_embedding_model",           # ⭐ 主要 API
    "list_embedding_models",         # ⭐ 模型发现
    "check_model_availability",      # ⭐ 状态检查
    
    # Wrappers（高级用途）
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
    
    # 向后兼容（旧代码仍可使用）
    "EmbeddingModel",
    "apply_embedding_model",
]
