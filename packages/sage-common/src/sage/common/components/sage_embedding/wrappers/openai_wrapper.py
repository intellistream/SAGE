"""OpenAI embedding wrapper."""

import logging
import os
from typing import Any

from ..base import BaseEmbedding

# 抑制 httpx 的 INFO 日志（每次 HTTP 请求都会打印）
logging.getLogger("httpx").setLevel(logging.WARNING)


class OpenAIEmbedding(BaseEmbedding):
    """OpenAI Embedding API Wrapper

    支持 OpenAI 官方 API 以及兼容的第三方 API（如 vLLM、DeepSeek 等）。

    特点:
        - ✅ 高质量 embedding
        - ✅ 支持多种模型
        - ✅ 兼容第三方 API
        - ❌ 需要 API Key
        - ❌ 需要网络连接
        - 💰 按使用量计费

    支持的模型:
        - text-embedding-3-small (1536维，性价比高)
        - text-embedding-3-large (3072维，最高质量)
        - text-embedding-ada-002 (1536维，旧版本)

    Args:
        model: 模型名称（默认 'text-embedding-3-small'）
        api_key: API 密钥（可选，默认从环境变量 OPENAI_API_KEY 读取）
        base_url: API 端点（可选，用于兼容 API）

    Examples:
        >>> # OpenAI 官方 API
        >>> import os
        >>> emb = OpenAIEmbedding(
        ...     model="text-embedding-3-small",
        ...     api_key=os.getenv("OPENAI_API_KEY")
        ... )
        >>> vec = emb.embed("hello world")
        >>>
        >>> # 兼容 API（自定义端点）
        >>> emb = OpenAIEmbedding(
        ...     model="text-embedding-v1",
        ...     api_key=os.getenv("OPENAI_API_KEY"),
        ...     base_url=os.getenv("OPENAI_BASE_URL", "http://localhost:8090/v1")
        ... )
        >>> vec = emb.embed("你好世界")
        >>>
        >>> # vLLM 部署的模型
        >>> emb = OpenAIEmbedding(
        ...     model="BAAI/bge-base-en-v1.5",
        ...     base_url="http://localhost:8000/v1"
        ... )
    """

    # 常见模型的维度映射
    DIMENSION_MAP = {
        "text-embedding-3-small": 1536,
        "text-embedding-3-large": 3072,
        "text-embedding-ada-002": 1536,
        "text-embedding-v1": 1536,
    }

    def __init__(
        self,
        model: str = "text-embedding-3-small",
        api_key: str | None = None,
        base_url: str | None = None,
        **kwargs: Any,
    ) -> None:
        """初始化 OpenAI Embedding

        Args:
            model: 模型名称
            api_key: API 密钥（可选）
            base_url: API 端点（可选）
            **kwargs: 其他参数（保留用于扩展）

        Raises:
            RuntimeError: 如果未提供 API Key
        """
        super().__init__(model=model, api_key=api_key, base_url=base_url, **kwargs)

        self._model = model
        self._api_key = api_key or os.getenv("OPENAI_API_KEY")
        self._base_url = base_url

        # 检查 API Key
        if not self._api_key:
            raise RuntimeError(
                "OpenAI embedding 需要 API Key。\n"
                "解决方案:\n"
                "  1. 设置环境变量: export OPENAI_API_KEY='your-key'\n"  # pragma: allowlist secret
                "  2. 传递参数: OpenAIEmbedding(api_key='your-key', ...)\n"  # pragma: allowlist secret
                "\n"
                "如果使用兼容 API:\n"
                "  export OPENAI_API_KEY='your-api-key'\n"  # pragma: allowlist secret
                "  并指定 base_url 参数"
            )

        # 推断或获取维度
        self._dim = self._infer_dimension()

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
            from openai import OpenAI

            client = OpenAI(api_key=self._api_key, base_url=self._base_url)
            response = client.embeddings.create(
                model=self._model,
                input=text,
            )
            return response.data[0].embedding
        except Exception as e:
            raise RuntimeError(
                f"OpenAI embedding 失败: {e}\n"
                f"模型: {self._model}\n"
                f"文本: {text[:100]}...\n"
                f"提示: 检查 API Key 是否有效，网络连接是否正常"
            ) from e

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """批量将文本转换为 embedding 向量

        使用 OpenAI API 的批量接口（input 参数支持列表）。

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
            from openai import OpenAI

            # 设置环境变量
            if self._api_key:
                import os

                os.environ["OPENAI_API_KEY"] = self._api_key

            client = OpenAI(base_url=self._base_url)

            # OpenAI API 支持批量：input 可以是字符串列表
            response = client.embeddings.create(
                model=self._model,
                input=texts,  # 直接传入列表
            )

            # 按照原始顺序返回结果
            return [item.embedding for item in response.data]

        except Exception as e:
            raise RuntimeError(
                f"OpenAI 批量 embedding 失败: {e}\n"
                f"模型: {self._model}\n"
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
            'openai'
        """
        return "openai"

    def _infer_dimension(self) -> int:
        """推断或获取维度

        Returns:
            推断的维度值
        """
        # 优先使用已知的维度映射
        if self._model in self.DIMENSION_MAP:
            return self.DIMENSION_MAP[self._model]

        # 如果是未知模型，尝试通过实际调用推断
        try:
            sample = self.embed("test")
            return len(sample)
        except Exception:
            # 如果推断失败，返回默认维度
            return 1536

    @classmethod
    def get_model_info(cls) -> dict[str, Any]:
        """返回模型元信息

        Returns:
            模型信息字典
        """
        return {
            "method": "openai",
            "requires_api_key": True,
            "requires_model_download": False,
            "default_dimension": 1536,
        }

    def __repr__(self) -> str:
        """返回对象的字符串表示

        Returns:
            字符串表示
        """
        base_info = f"OpenAIEmbedding(model='{self._model}', dim={self._dim}"
        if self._base_url:
            base_info += f", base_url='{self._base_url}'"
        return base_info + ")"
