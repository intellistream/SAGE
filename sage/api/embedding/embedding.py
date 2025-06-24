# sage/api/embedding.py
"""
API 层 EmbeddingModelFactory
代理 sage.core.model.embedding_model 下的 EmbeddingModel 与 MockTextEmbedder，
为上层提供统一、免直接依赖 core 的嵌入模型创建接口。
"""

from typing import Optional, Any

# 引入核心 EmbeddingModel 与 MockTextEmbedder
from sage.core.model.embedding_model.embedding_model import (
    EmbeddingModel as _CoreEmbeddingModel,
    MockTextEmbedder as _MockTextEmbedder,
)


class EmbeddingModelFactory:
    """
    提供多种嵌入模型工厂方法，避免应用层直接依赖 core 实现。
    """

    @staticmethod
    def create(
        method: str = "openai",
        model: Optional[str] = None,
        **kwargs: Any
    ) -> _CoreEmbeddingModel:
        """
        基于方法名和可选模型名称创建 Core 层 EmbeddingModel。
        :param method: 嵌入方法，例如 'openai', 'hf', 'cohere' 等，也支持 'mock'
        :param model: 对于 hf 方法，指定 transformers 模型标识；其他方法参数由 kwargs 提供
        :return: Core 层 EmbeddingModel 或 MockTextEmbedder 实例
        """
        # mock 方法：直接返回 MockTextEmbedder
        if method == "mock":
            fixed_dim = kwargs.get("fixed_dim", 128)
            name = kwargs.get("model_name", "mock-model")
            return _MockTextEmbedder(model_name=name, fixed_dim=fixed_dim)

        # default 等价于 hf
        if method == "default":
            method = "hf"
            kwargs.setdefault("model", "sentence-transformers/all-MiniLM-L6-v2")

        params = {**kwargs}
        if model:
            params["model"] = model

        return _CoreEmbeddingModel(method=method, **params)

    @staticmethod
    def mock(
        fixed_dim: int = 128,
        model_name: str = "mock-model"
    ) -> _MockTextEmbedder:
        """
        获取测试用的 MockTextEmbedder，输出固定维度、确定性随机的向量。
        :param fixed_dim: 目标向量维度
        :param model_name: 模型名称，用于随机种子
        """
        return _MockTextEmbedder(model_name=model_name, fixed_dim=fixed_dim)

    @staticmethod
    def default_hf() -> _CoreEmbeddingModel:
        """
        返回默认的 HuggingFace 嵌入模型实例，使用 all-MiniLM-L6-v2。
        """
        return EmbeddingModelFactory.create(
            method="hf",
            model="sentence-transformers/all-MiniLM-L6-v2"
        )

    @staticmethod
    def openai(
        api_key: str,
        model: Optional[str] = None
    ) -> _CoreEmbeddingModel:
        """
        使用 OpenAI API 创建嵌入模型
        :param api_key: OpenAI API Key
        :param model: OpenAI 嵌入模型名称，例如 'text-embedding-ada-002'
        """
        return EmbeddingModelFactory.create(
            method="openai",
            model=model,
            api_key=api_key
        )

    @staticmethod
    def cohere(
        api_key: str,
        model: Optional[str] = None
    ) -> _CoreEmbeddingModel:
        """
        使用 Cohere API 创建嵌入模型
        :param api_key: Cohere API Key
        :param model: Cohere 模型名称
        """
        return EmbeddingModelFactory.create(
            method="cohere",
            model=model,
            api_key=api_key
        )
