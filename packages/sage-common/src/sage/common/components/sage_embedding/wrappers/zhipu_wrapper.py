"""ZhipuAI (智谱清言) embedding wrapper."""

import os
from typing import Any

from ..base import BaseEmbedding


class ZhipuEmbedding(BaseEmbedding):
    """ZhipuAI Embedding API Wrapper

    支持智谱 AI 的中文 embedding 服务。

    特点:
        - ✅ 中文优化
        - ✅ 高质量向量
        - ✅ 国内访问稳定
        - ❌ 需要 API Key
        - ❌ 需要网络连接
        - 💰 按使用量计费

    支持的模型:
        - embedding-3 (默认，1024维，最新版本)
        - embedding-2 (512维，旧版本)

    Args:
        model: 模型名称（默认 'embedding-3'）
        api_key: API 密钥（可选，默认从环境变量 ZHIPU_API_KEY 读取）

    Examples:
        >>> # 基本使用
        >>> import os
        >>> emb = ZhipuEmbedding(
        ...     model="embedding-3",
        ...     api_key=os.getenv("ZHIPU_API_KEY")  # pragma: allowlist secret
        ... )
        >>> vec = emb.embed("你好世界")
        >>>
        >>> # 使用环境变量
        >>> # export ZHIPU_API_KEY='your-key'  # pragma: allowlist secret
        >>> emb = ZhipuEmbedding()
        >>> vec = emb.embed("智谱清言是一个强大的中文模型")
    """

    # 模型维度映射
    DIMENSION_MAP = {
        "embedding-3": 1024,
        "embedding-2": 512,
    }

    def __init__(
        self, model: str = "embedding-3", api_key: str | None = None, **kwargs: Any
    ) -> None:
        """初始化 Zhipu Embedding

        Args:
            model: 模型名称
            api_key: API 密钥（可选）
            **kwargs: 其他参数（传递给 ZhipuAI client）

        Raises:
            ImportError: 如果未安装 zhipuai 包
            RuntimeError: 如果未提供 API Key
        """
        super().__init__(model=model, api_key=api_key, **kwargs)

        # 检查依赖
        try:
            from zhipuai import ZhipuAI  # noqa: F401
        except ImportError:
            raise ImportError("Zhipu embedding 需要 zhipuai 包。\n安装方法: pip install zhipuai")

        self._model = model
        self._api_key = api_key or os.getenv("ZHIPU_API_KEY")
        self._kwargs = kwargs

        # 检查 API Key
        if not self._api_key:
            raise RuntimeError(
                "Zhipu embedding 需要 API Key。\n"
                "解决方案:\n"
                "  1. 设置环境变量: export ZHIPU_API_KEY='your-key'\n"  # pragma: allowlist secret
                "  2. 传递参数: ZhipuEmbedding(api_key='your-key', ...)\n"  # pragma: allowlist secret
                "\n"
                "获取 API Key: https://open.bigmodel.cn/"
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
            from zhipuai import ZhipuAI

            client = ZhipuAI(api_key=self._api_key)
            response = client.embeddings.create(model=self._model, input=[text], **self._kwargs)
            return response.data[0].embedding
        except Exception as e:
            raise RuntimeError(
                f"Zhipu embedding 失败: {e}\n"
                f"模型: {self._model}\n"
                f"文本: {text[:100]}...\n"
                f"提示: 检查 API Key 是否有效，网络连接是否正常"
            ) from e

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """批量将文本转换为 embedding 向量

        使用 ZhipuAI API 的批量接口（input 参数支持列表）。

        Args:
            texts: 输入文本列表

        Returns:
            embedding 向量列表
        """
        try:
            from zhipuai import ZhipuAI

            client = ZhipuAI(api_key=self._api_key)
            response = client.embeddings.create(
                model=self._model,
                input=texts,
                **self._kwargs,  # 直接传入列表
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            raise RuntimeError(
                f"Zhipu 批量 embedding 失败: {e}\n"
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
            'zhipu'
        """
        return "zhipu"

    @classmethod
    def get_model_info(cls) -> dict[str, Any]:
        """返回模型元信息

        Returns:
            模型信息字典
        """
        return {
            "method": "zhipu",
            "requires_api_key": True,
            "requires_model_download": False,
            "default_dimension": 1024,
            "features": [
                "中文优化",
                "高质量向量",
                "国内访问稳定",
            ],
        }

    def __repr__(self) -> str:
        """返回对象的字符串表示

        Returns:
            字符串表示
        """
        return f"ZhipuEmbedding(model='{self._model}', dim={self._dim})"
