"""Jina AI embedding wrapper."""

import os
from typing import Any

from ..base import BaseEmbedding
from ..jina import jina_embed_sync  # 复用现有实现


class JinaEmbedding(BaseEmbedding):
    """Jina AI Embedding API Wrapper

    支持 Jina AI 的多语言、多模态 embedding 服务。

    特点:
        - ✅ 多语言支持（100+ 语言）
        - ✅ 长文本处理（8192 tokens）
        - ✅ Late Chunking 技术
        - ✅ 可调维度（32-1024）
        - ❌ 需要 API Key
        - ❌ 需要网络连接
        - 💰 按使用量计费

    支持的模型:
        - jina-embeddings-v3 (默认，多语言，可调维度)
        - jina-embeddings-v2-base-en (英文专用)
        - jina-clip-v1 (多模态：文本+图像)

    Args:
        model: 模型名称（默认 'jina-embeddings-v3'）
        dimensions: embedding 维度（默认 1024，范围 32-1024）
        late_chunking: 是否启用 late chunking（默认 False）
        api_key: API 密钥（可选，默认从环境变量 JINA_API_KEY 读取）
        base_url: API 端点（可选，用于自托管）

    Examples:
        >>> # 基本使用
        >>> import os
        >>> emb = JinaEmbedding(
        ...     model="jina-embeddings-v3",
        ...     api_key=os.getenv("JINA_API_KEY")
        ... )
        >>> vec = emb.embed("hello world")
        >>>
        >>> # 自定义维度（降维节省成本）
        >>> emb = JinaEmbedding(
        ...     dimensions=256,
        ...     api_key=os.getenv("JINA_API_KEY")
        ... )
        >>> vec = emb.embed("你好世界")
        >>> assert len(vec) == 256
        >>>
        >>> # Late Chunking（长文本处理）
        >>> emb = JinaEmbedding(
        ...     late_chunking=True,
        ...     api_key=os.getenv("JINA_API_KEY")
        ... )
        >>> long_text = "..." * 1000
        >>> vec = emb.embed(long_text)
    """

    def __init__(
        self,
        model: str = "jina-embeddings-v3",
        dimensions: int = 1024,
        late_chunking: bool = False,
        api_key: str | None = None,
        base_url: str | None = None,
        **kwargs: Any,
    ) -> None:
        """初始化 Jina Embedding

        Args:
            model: 模型名称
            dimensions: embedding 维度（32-1024）
            late_chunking: 是否启用 late chunking
            api_key: API 密钥（可选）
            base_url: API 端点（可选）
            **kwargs: 其他参数（保留用于扩展）

        Raises:
            RuntimeError: 如果未提供 API Key
            ValueError: 如果维度超出范围
        """
        super().__init__(
            model=model,
            dimensions=dimensions,
            late_chunking=late_chunking,
            api_key=api_key,
            base_url=base_url,
            **kwargs,
        )

        self._model = model
        self._dimensions = dimensions
        self._late_chunking = late_chunking
        self._api_key = api_key or os.getenv("JINA_API_KEY")
        self._base_url = base_url

        # 检查 API Key
        if not self._api_key:
            raise RuntimeError(
                "Jina embedding 需要 API Key。\n"  # pragma: allowlist secret
                "解决方案:\n"
                "  1. 设置环境变量: export JINA_API_KEY='your-key'\n"  # pragma: allowlist secret
                "  2. 传递参数: JinaEmbedding(api_key='your-key', ...)\n"  # pragma: allowlist secret
                "\n"
                "获取 API Key: https://jina.ai/embeddings/"  # pragma: allowlist secret
            )

        # 检查维度范围
        if not (32 <= dimensions <= 1024):
            raise ValueError(
                f"Jina embedding 维度必须在 32-1024 范围内，当前值: {dimensions}\n"
                "提示: 更小的维度可以降低成本，但可能影响精度"
            )

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
            return jina_embed_sync(
                text=text,
                dimensions=self._dimensions,
                late_chunking=self._late_chunking,
                base_url=self._base_url,
                api_key=self._api_key,
                model=self._model,
            )
        except Exception as e:
            raise RuntimeError(
                f"Jina embedding 失败: {e}\n"
                f"模型: {self._model}\n"
                f"维度: {self._dimensions}\n"
                f"文本: {text[:100]}...\n"
                f"提示: 检查 API Key 是否有效，网络连接是否正常"
            ) from e

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """批量将文本转换为 embedding 向量

        使用 Jina API 的批量接口（input 参数支持列表）。

        Args:
            texts: 输入文本列表

        Returns:
            embedding 向量列表

        Raises:
            RuntimeError: 如果 API 调用失败
        """
        if not texts:
            return []

        try:
            import requests

            # 准备 API Key (guaranteed to be non-None after __init__ validation)
            api_key = self._api_key
            assert api_key is not None  # Help mypy understand this can't be None
            if not api_key.startswith("Bearer "):
                api_key = "Bearer " + api_key  # pragma: allowlist secret

            headers = {
                "Authorization": api_key,  # pragma: allowlist secret
                "Content-Type": "application/json",
            }

            url = self._base_url or "https://api.jina.ai/v1/embeddings"

            payload = {
                "model": self._model,
                "normalized": True,
                "embedding_type": "float",
                "dimensions": self._dimensions,
                "late_chunking": self._late_chunking,
                "input": texts,  # 直接传入列表
            }

            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

            # 按照原始顺序返回结果
            return [item["embedding"] for item in data["data"]]

        except Exception as e:
            raise RuntimeError(
                f"Jina 批量 embedding 失败: {e}\n"
                f"模型: {self._model}\n"
                f"维度: {self._dimensions}\n"
                f"批量大小: {len(texts)}\n"
                f"提示: 检查 API Key 是否有效，网络连接是否正常"
            ) from e

    def get_dim(self) -> int:
        """获取向量维度

        Returns:
            维度值
        """
        return self._dimensions

    @property
    def method_name(self) -> str:
        """返回方法名称

        Returns:
            'jina'
        """
        return "jina"

    @classmethod
    def get_model_info(cls) -> dict[str, Any]:
        """返回模型元信息

        Returns:
            模型信息字典
        """
        return {
            "method": "jina",
            "requires_api_key": True,
            "requires_model_download": False,
            "default_dimension": 1024,
            "features": [
                "多语言支持（100+ 语言）",
                "长文本处理（8192 tokens）",
                "可调维度（32-1024）",
                "Late Chunking",
            ],
        }

    def __repr__(self) -> str:
        """返回对象的字符串表示

        Returns:
            字符串表示
        """
        base_info = f"JinaEmbedding(model='{self._model}', dim={self._dimensions}"
        if self._late_chunking:
            base_info += ", late_chunking=True"
        if self._base_url:
            base_info += f", base_url='{self._base_url}'"
        return base_info + ")"
