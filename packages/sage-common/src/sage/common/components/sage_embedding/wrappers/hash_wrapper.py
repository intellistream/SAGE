"""Hash-based lightweight embedding (migrated from sage chat)."""

import hashlib
import re
from typing import Any

from ..base import BaseEmbedding


class HashEmbedding(BaseEmbedding):
    """基于哈希的轻量级 Embedding

    使用 SHA256 哈希将文本 tokens 映射到固定维度的向量空间。
    主要用于快速测试和演示，不提供语义理解能力。

    特点:
        - ✅ 无需下载模型
        - ✅ 无需 GPU
        - ✅ 速度极快
        - ❌ 无语义理解（只能精确匹配关键词）

    适用场景:
        - 快速原型开发
        - 功能测试
        - 不需要语义理解的场景

    Args:
        dim: 向量维度（默认 384）

    Examples:
        >>> emb = HashEmbedding(dim=384)
        >>> vec = emb.embed("hello world")
        >>> len(vec)
        384
        >>>
        >>> # 相同文本产生相同向量
        >>> vec1 = emb.embed("test")
        >>> vec2 = emb.embed("test")
        >>> vec1 == vec2
        True
        >>>
        >>> # 批量处理
        >>> vecs = emb.embed_batch(["hello", "world"])
        >>> len(vecs)
        2
    """

    def __init__(self, dim: int = 384, **kwargs: Any) -> None:
        """初始化 Hash Embedding

        Args:
            dim: 向量维度（最小 64）
            **kwargs: 其他参数（兼容性）
        """
        super().__init__(dim=dim, **kwargs)
        self._dim = max(64, int(dim))

    def embed(self, text: str) -> list[float]:
        """将文本转换为哈希向量

        算法:
            1. 分词（提取字母数字和中文字符）
            2. 对每个 token 计算 SHA256 哈希
            3. 将哈希值映射到向量空间
            4. L2 归一化

        Args:
            text: 输入文本

        Returns:
            归一化的 embedding 向量
        """
        if not text:
            return [0.0] * self._dim

        vector = [0.0] * self._dim

        # 分词：提取字母数字和中文字符
        tokens = re.findall(r"[\w\u4e00-\u9fa5]+", text.lower())
        if not tokens:
            tokens = [text.lower()]

        # 对每个 token 哈希
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()

            # 将哈希值的每 4 字节映射到向量的一个位置
            for offset in range(0, len(digest), 4):
                chunk = digest[offset : offset + 4]
                if len(chunk) < 4:
                    chunk = chunk.ljust(4, b"\0")
                idx = int.from_bytes(chunk, "little") % self._dim
                vector[idx] += 1.0

        # L2 归一化
        norm = sum(v * v for v in vector) ** 0.5 or 1.0
        return [v / norm for v in vector]

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
            'hash'
        """
        return "hash"

    @classmethod
    def get_model_info(cls) -> dict[str, Any]:
        """返回模型元信息

        Returns:
            模型信息字典
        """
        return {
            "method": "hash",
            "requires_api_key": False,
            "requires_model_download": False,
            "default_dimension": 384,
        }
