"""SAGE Embedding Module - Unified interface for various embedding methods.

Layer: L1 (Foundation - Common Components)

This module provides a consistent API for different embedding providers:
- Hash-based lightweight embedding (for testing)
- Mock embedding (for unit tests)
- HuggingFace Transformer models (local, high quality)
- OpenAI and other API-based services

IMPORTANT: For LLM + Embedding combined usage, use UnifiedInferenceClient from
sage.llm instead. This module is for embedding-only scenarios.

Quick Start:
    >>> from sage.common.components.sage_embedding import get_embedding_model
    >>>
    >>> # Create an embedding model
    >>> emb = get_embedding_model("hash", dim=384)
    >>> vec = emb.embed("hello world")
    >>>
    >>> # For combined LLM + Embedding, use UnifiedInferenceClient:
    >>> from sage.llm import UnifiedInferenceClient
    >>> client = UnifiedInferenceClient.create()
    >>> vectors = client.embed(["text1", "text2"])

Architecture:
    This is a L1 foundation component used by higher layers (L2-L6).
    It must NOT import from sage.kernel, sage.middleware, sage.libs, or sage.apps.
"""

# L1 components should not depend on higher layers
# Version information is maintained locally to avoid circular dependencies
__version__ = "0.1.4"
__author__ = "IntelliStream Team"
__email__ = "shuhao_zhang@hust.edu.cn"

# Core embedding interfaces
from .base import BaseEmbedding
from .factory import (
    EmbeddingFactory,
    check_model_availability,
    get_embedding_model,
    list_embedding_models,
)
from .protocols import (
    EmbeddingClientAdapter,
    EmbeddingProtocol,
    adapt_embedding_client,
)
from .registry import EmbeddingRegistry, ModelInfo, ModelStatus

# 只导入轻量级的 wrappers，其他使用延迟导入
from .wrappers.hash_wrapper import HashEmbedding
from .wrappers.mock_wrapper import MockEmbedding

# 重量级 wrappers 使用延迟导入，避免在模块加载时加载大型依赖
# 这些会在 _register_all_methods() 中按需导入


# 注册所有 embedding 方法
def _register_all_methods():
    """注册所有内置的 embedding 方法

    使用延迟导入 wrapper_class，通过传递字符串路径而不是类对象。
    这样可以避免在模块加载时就导入所有重量级依赖。
    """

    # Hash Embedding - 轻量级，直接导入
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

    # Mock Embedder - 轻量级，直接导入
    EmbeddingRegistry.register(
        method="mockembedder",
        display_name="Mock Embedder",
        description="随机 embedding（单元测试用）",
        wrapper_class=MockEmbedding,
        requires_api_key=False,
        requires_model_download=False,
        default_dimension=128,
        example_models=["mock-128", "mock-384"],
    )

    # 以下使用字符串路径进行延迟注册，避免导入重量级依赖
    # 实际导入会在 EmbeddingFactory.create() 时进行

    # HuggingFace Models
    EmbeddingRegistry.register(
        method="hf",
        display_name="HuggingFace Models",
        description="本地 Transformer 模型（高质量语义 embedding）",
        wrapper_class="sage.common.components.sage_embedding.wrappers.hf_wrapper:HFEmbedding",
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
        wrapper_class="sage.common.components.sage_embedding.wrappers.openai_wrapper:OpenAIEmbedding",
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
        wrapper_class="sage.common.components.sage_embedding.wrappers.jina_wrapper:JinaEmbedding",
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
        wrapper_class="sage.common.components.sage_embedding.wrappers.zhipu_wrapper:ZhipuEmbedding",
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
        wrapper_class="sage.common.components.sage_embedding.wrappers.cohere_wrapper:CohereEmbedding",
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
        wrapper_class="sage.common.components.sage_embedding.wrappers.bedrock_wrapper:BedrockEmbedding",
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
        wrapper_class="sage.common.components.sage_embedding.wrappers.ollama_wrapper:OllamaEmbedding",
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
        wrapper_class="sage.common.components.sage_embedding.wrappers.siliconcloud_wrapper:SiliconCloudEmbedding",
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
        wrapper_class="sage.common.components.sage_embedding.wrappers.nvidia_openai_wrapper:NvidiaOpenAIEmbedding",
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
from .embedding_model import (
    EmbeddingModel,  # noqa: E402
    apply_embedding_model,
)

# Service interface (新增)
from .service import EmbeddingService, EmbeddingServiceConfig  # noqa: E402

# 统一导出接口
__all__ = [
    # Service interface (推荐用于 pipelines)
    "EmbeddingService",  # ⭐ Service 主要 API
    "EmbeddingServiceConfig",
    # Core embedding interfaces
    "BaseEmbedding",
    "EmbeddingRegistry",
    "EmbeddingFactory",
    "ModelStatus",
    "ModelInfo",
    "get_embedding_model",  # ⭐ 主要 API
    "list_embedding_models",  # ⭐ 模型发现
    "check_model_availability",  # ⭐ 状态检查
    # Protocol adapters
    "EmbeddingProtocol",
    "EmbeddingClientAdapter",
    "adapt_embedding_client",
    # Lightweight wrappers (直接导入)
    "HashEmbedding",
    "MockEmbedding",
    # Note: Heavy wrappers (HF, OpenAI, Jina, etc.) use lazy loading
    # They are available via get_embedding_model() but not directly imported
    # 向后兼容（旧代码仍可使用）
    "EmbeddingModel",
    "apply_embedding_model",
]
