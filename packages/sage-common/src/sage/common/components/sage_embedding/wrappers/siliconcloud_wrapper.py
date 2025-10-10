"""SiliconCloud (硅基流动) embedding wrapper."""

import os
from typing import Any, Dict, List, Optional

from ..base import BaseEmbedding


class SiliconCloudEmbedding(BaseEmbedding):
    """SiliconCloud (硅基流动) Embedding Wrapper

    支持通过硅基流动访问多种 embedding 模型。

    特点:
        - ✅ 国内访问快速稳定
        - ✅ 支持多种开源模型
        - ✅ 价格优势
        - ❌ 需要 API Key
        - ❌ 需要网络连接
        - 💰 按使用量计费

    支持的模型（示例）:
        - netease-youdao/bce-embedding-base_v1 (默认，768维）
        - BAAI/bge-large-zh-v1.5 (1024维，中文优化）
        - BAAI/bge-base-en-v1.5 (768维，英文）

    Args:
        model: 模型名称（默认 'netease-youdao/bce-embedding-base_v1'）
        base_url: API 地址（默认 'https://api.siliconflow.cn/v1/embeddings'）
        max_token_size: 最大 token 数（默认 512）
        api_key: API 密钥（可选，默认从环境变量 SILICONCLOUD_API_KEY 读取）

    Examples:
        >>> # 基本使用
        >>> import os
        >>> emb = SiliconCloudEmbedding(
        ...     model="netease-youdao/bce-embedding-base_v1",
        ...     api_key=os.getenv("SILICONCLOUD_API_KEY")
        ... )
        >>> vec = emb.embed("你好世界")
        >>>
        >>> # 使用 BGE 模型
        >>> emb = SiliconCloudEmbedding(
        ...     model="BAAI/bge-large-zh-v1.5",
        ...     api_key=os.getenv("SILICONCLOUD_API_KEY")
        ... )
        >>> vec = emb.embed("硅基流动提供高性价比的AI服务")
    """

    # 常见模型的维度映射
    DIMENSION_MAP = {
        "netease-youdao/bce-embedding-base_v1": 768,
        "BAAI/bge-large-zh-v1.5": 1024,
        "BAAI/bge-base-en-v1.5": 768,
        "BAAI/bge-small-en-v1.5": 384,
    }

    def __init__(
        self,
        model: str = "netease-youdao/bce-embedding-base_v1",
        base_url: str = "https://api.siliconflow.cn/v1/embeddings",
        max_token_size: int = 512,
        api_key: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """初始化 SiliconCloud Embedding

        Args:
            model: 模型名称
            base_url: API 地址
            max_token_size: 最大 token 数
            api_key: API 密钥（可选）
            **kwargs: 其他参数（保留用于扩展）

        Raises:
            ImportError: 如果未安装依赖包
            RuntimeError: 如果未提供 API Key
        """
        super().__init__(
            model=model,
            base_url=base_url,
            max_token_size=max_token_size,
            api_key=api_key,
            **kwargs,
        )

        # 检查依赖
        try:
            import requests  # noqa: F401
        except ImportError:
            raise ImportError(
                "SiliconCloud embedding 需要 requests 包。\n"
                "安装方法: pip install requests"
            )

        self._model = model
        self._base_url = base_url
        self._max_token_size = max_token_size
        self._api_key = api_key or os.getenv("SILICONCLOUD_API_KEY")
        self._kwargs = kwargs

        # 检查 API Key
        if not self._api_key:
            raise RuntimeError(
                "SiliconCloud embedding 需要 API Key。\n"
                "解决方案:\n"
                "  1. 设置环境变量: export SILICONCLOUD_API_KEY='your-key'\n"
                "  2. 传递参数: SiliconCloudEmbedding(api_key='your-key', ...)\n"
                "\n"
                "获取 API Key: https://siliconflow.cn/"
            )

        # 获取维度
        self._dim = self._infer_dimension()

    def embed(self, text: str) -> List[float]:
        """将文本转换为 embedding 向量

        Args:
            text: 输入文本

        Returns:
            embedding 向量

        Raises:
            RuntimeError: 如果 API 调用失败
        """
        try:
            import base64
            import struct

            import requests

            # 准备 API Key（添加 Bearer 前缀）
            api_key = self._api_key
            if api_key and not api_key.startswith("Bearer "):
                api_key = "Bearer " + api_key

            headers = {
                "Authorization": api_key,
                "Content-Type": "application/json",
            }

            # 截断文本
            text = text[: self._max_token_size]

            payload = {
                "model": self._model,
                "input": [text],
                "encoding_format": "base64",
            }

            response = requests.post(self._base_url, headers=headers, json=payload)
            response.raise_for_status()
            content = response.json()

            if "code" in content:
                raise ValueError(f"SiliconCloud API error: {content}")

            # 解码 base64 编码的向量
            base64_string = content["data"][0]["embedding"]
            decode_bytes = base64.b64decode(base64_string)
            n = len(decode_bytes) // 4
            float_array = struct.unpack("<" + "f" * n, decode_bytes)
            return list(float_array)

        except Exception as e:
            raise RuntimeError(
                f"SiliconCloud embedding 失败: {e}\n"
                f"模型: {self._model}\n"
                f"文本: {text[:100]}...\n"
                f"提示: 检查 API Key 是否有效，网络连接是否正常"
            ) from e

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """批量将文本转换为 embedding 向量

        当前实现为逐个调用 embed()。
        TODO: 如果 API 支持批量，可以优化。
        Issue URL: https://github.com/intellistream/SAGE/issues/912

        Args:
            texts: 输入文本列表

        Returns:
            embedding 向量列表
        """
        # TODO: 检查 SiliconCloud API 是否支持批量
        # Issue URL: https://github.com/intellistream/SAGE/issues/911
        return [self.embed(text) for text in texts]

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
            'siliconcloud'
        """
        return "siliconcloud"

    def _infer_dimension(self) -> int:
        """推断向量维度

        Returns:
            推断的维度值
        """
        # 优先使用已知的维度映射
        if self._model in self.DIMENSION_MAP:
            return self.DIMENSION_MAP[self._model]

        # 尝试通过实际调用推断
        try:
            sample = self.embed("test")
            return len(sample)
        except Exception:
            # 如果推断失败，返回默认维度
            return 768

    @classmethod
    def get_model_info(cls) -> Dict[str, Any]:
        """返回模型元信息

        Returns:
            模型信息字典
        """
        return {
            "method": "siliconcloud",
            "requires_api_key": True,
            "requires_model_download": False,
            "default_dimension": 768,
            "features": [
                "国内访问快速稳定",
                "支持多种开源模型",
                "价格优势",
            ],
        }

    def __repr__(self) -> str:
        """返回对象的字符串表示

        Returns:
            字符串表示
        """
        return f"SiliconCloudEmbedding(model='{self._model}', dim={self._dim})"
