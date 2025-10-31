"""Cohere embedding wrapper."""

import os
from typing import Any

from ..base import BaseEmbedding


class CohereEmbedding(BaseEmbedding):
    """Cohere Embedding API Wrapper

    支持 Cohere 的多语言 embedding 服务。

    特点:
        - ✅ 多语言支持（100+ 语言）
        - ✅ 多种 input_type（search/classification）
        - ✅ 高质量向量
        - ✅ 原生批量支持
        - ❌ 需要 API Key
        - ❌ 需要网络连接
        - 💰 按使用量计费

    支持的模型:
        - embed-multilingual-v3.0 (默认，1024维，多语言)
        - embed-english-v3.0 (1024维，英文专用)
        - embed-multilingual-light-v3.0 (384维，轻量级)
        - embed-english-light-v3.0 (384维，英文轻量)

    Args:
        model: 模型名称（默认 'embed-multilingual-v3.0'）
        input_type: 输入类型（'search_document', 'search_query', 'classification', 'clustering'）
        api_key: API 密钥（可选，默认从环境变量 COHERE_API_KEY 读取）
        embedding_types: 返回格式（默认 ['float']）

    Examples:
        >>> # 基本使用
        >>> import os
        >>> emb = CohereEmbedding(
        ...     model="embed-multilingual-v3.0",
        ...     api_key=os.getenv("COHERE_API_KEY")
        ... )
        >>> vec = emb.embed("hello world")
        >>>
        >>> # 搜索场景（不同 input_type）
        >>> # 文档端
        >>> doc_emb = CohereEmbedding(input_type="search_document")
        >>> doc_vec = doc_emb.embed("这是一篇关于机器学习的文档")
        >>>
        >>> # 查询端
        >>> query_emb = CohereEmbedding(input_type="search_query")
        >>> query_vec = query_emb.embed("什么是机器学习")
        >>>
        >>> # 分类场景
        >>> clf_emb = CohereEmbedding(input_type="classification")
        >>> clf_vec = clf_emb.embed("这是一条正面评价")
    """

    # 模型维度映射
    DIMENSION_MAP = {
        "embed-multilingual-v3.0": 1024,
        "embed-english-v3.0": 1024,
        "embed-multilingual-light-v3.0": 384,
        "embed-english-light-v3.0": 384,
    }

    def __init__(
        self,
        model: str = "embed-multilingual-v3.0",
        input_type: str = "classification",
        api_key: str | None = None,
        embedding_types: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        """初始化 Cohere Embedding

        Args:
            model: 模型名称
            input_type: 输入类型
            api_key: API 密钥（可选）
            embedding_types: 返回格式（可选）
            **kwargs: 其他参数（保留用于扩展）

        Raises:
            ImportError: 如果未安装 cohere 包
            RuntimeError: 如果未提供 API Key
        """
        super().__init__(
            model=model,
            input_type=input_type,
            api_key=api_key,
            embedding_types=embedding_types,
            **kwargs,
        )

        # 检查依赖
        try:
            import cohere  # noqa: F401
        except ImportError:
            raise ImportError("Cohere embedding 需要 cohere 包。\n安装方法: pip install cohere")

        self._model = model
        self._input_type = input_type
        self._api_key = api_key or os.getenv("COHERE_API_KEY")
        self._embedding_types = embedding_types or ["float"]
        self._kwargs = kwargs

        # 检查 API Key
        if not self._api_key:
            raise RuntimeError(
                "Cohere embedding 需要 API Key。\n"
                "解决方案:\n"
                "  1. 设置环境变量: export COHERE_API_KEY='your-key'\n"  # pragma: allowlist secret
                "  2. 传递参数: CohereEmbedding(api_key='your-key', ...)\n"  # pragma: allowlist secret
                "\n"
                "获取 API Key: https://dashboard.cohere.com/api-keys"
            )

        # 获取维度
        self._dim = self.DIMENSION_MAP.get(model, 1024)

    def embed(self, text: str) -> list[float]:
        """将文本转换为 embedding 向量

        Args:
            text: 输入文本

        Returns:
            embedding 向量

        Raises:
            RuntimeError: 如果 API 调用失败
        """
        try:
            import cohere

            co = cohere.Client(api_key=self._api_key)
            response = co.embed(
                texts=[text],  # Cohere API 要求传入列表
                model=self._model,
                input_type=self._input_type,
                embedding_types=self._embedding_types,
            )
            return response.embeddings[0]  # pyright: ignore[reportReturnType, reportIndexIssue]
        except Exception as e:
            raise RuntimeError(
                f"Cohere embedding 失败: {e}\n"
                f"模型: {self._model}\n"
                f"输入类型: {self._input_type}\n"
                f"文本: {text[:100]}...\n"
                f"提示: 检查 API Key 是否有效，网络连接是否正常"
            ) from e

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """批量将文本转换为 embedding 向量

        Cohere API 原生支持批量操作。

        Args:
            texts: 输入文本列表

        Returns:
            embedding 向量列表
        """
        try:
            import cohere

            co = cohere.Client(api_key=self._api_key)
            response = co.embed(
                texts=texts,
                model=self._model,
                input_type=self._input_type,
                embedding_types=self._embedding_types,
            )
            return response.embeddings  # pyright: ignore[reportReturnType]
        except Exception as e:
            raise RuntimeError(
                f"Cohere 批量 embedding 失败: {e}\n"
                f"模型: {self._model}\n"
                f"输入类型: {self._input_type}\n"
                f"批量大小: {len(texts)}\n"
                f"提示: 检查 API Key 是否有效，网络连接是否正常"
            ) from e

    def get_dim(self) -> int:
        """获取向量维度

        Returns:
            维度值
        """
        return self._dim

    @property
    def method_name(self) -> str:
        """返回方法名称

        Returns:
            'cohere'
        """
        return "cohere"

    @classmethod
    def get_model_info(cls) -> dict[str, Any]:
        """返回模型元信息

        Returns:
            模型信息字典
        """
        return {
            "method": "cohere",
            "requires_api_key": True,
            "requires_model_download": False,
            "default_dimension": 1024,
            "features": [
                "多语言支持（100+ 语言）",
                "多种 input_type（search/classification）",
                "原生批量支持",
            ],
        }

    def __repr__(self) -> str:
        """返回对象的字符串表示

        Returns:
            字符串表示
        """
        return (
            f"CohereEmbedding(model='{self._model}', "
            f"input_type='{self._input_type}', dim={self._dim})"
        )
