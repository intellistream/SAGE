"""Mock embedding wrapper (migrated from mockembedder.py)."""

import random
from typing import Any

from ..base import BaseEmbedding


class MockEmbedding(BaseEmbedding):
    """Mock Embedding（用于测试）

    生成随机向量，主要用于单元测试和快速原型验证。
    不提供任何语义信息，每次调用都生成不同的随机向量。

    特点:
        - ✅ 无需下载模型
        - ✅ 无需 API Key
        - ✅ 速度极快
        - ❌ 完全随机，无任何语义

    适用场景:
        - 单元测试
        - 性能测试
        - 快速功能验证

    Args:
        fixed_dim: 向量维度（默认 128）
        seed: 随机种子（可选，设置后可复现）

    Examples:
        >>> # 基本用法
        >>> emb = MockEmbedding(fixed_dim=128)
        >>> vec = emb.embed("test")
        >>> len(vec)
        128
        >>>
        >>> # 使用固定种子（可复现）
        >>> emb = MockEmbedding(fixed_dim=128, seed=42)
        >>> vec1 = emb.embed("hello")
        >>>
        >>> emb2 = MockEmbedding(fixed_dim=128, seed=42)
        >>> vec2 = emb2.embed("hello")
        >>> vec1 == vec2
        True
    """

    def __init__(self, fixed_dim: int = 128, seed: int | None = None, **kwargs: Any) -> None:
        """初始化 Mock Embedding

        Args:
            fixed_dim: 向量维度
            seed: 随机种子（可选）
            **kwargs: 其他参数（兼容性）
        """
        super().__init__(fixed_dim=fixed_dim, seed=seed, **kwargs)
        self._dim = max(64, int(fixed_dim))
        self._seed = seed
        if seed is not None:
            random.seed(seed)

    def embed(self, text: str) -> list[float]:
        """生成随机 embedding 向量

        Args:
            text: 输入文本（实际不使用，保持接口一致）

        Returns:
            随机生成的向量

        Note:
            - 如果设置了 seed，相同文本会生成相同向量
            - 如果未设置 seed，每次调用生成不同向量
        """
        if self._seed is not None:
            # 使用文本作为种子的一部分，保证相同文本生成相同向量
            text_seed = hash(text) % (2**32)
            rng = random.Random(self._seed + text_seed)
            return [rng.random() for _ in range(self._dim)]
        else:
            # 完全随机
            return [random.random() for _ in range(self._dim)]

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
            'mockembedder'
        """
        return "mockembedder"

    @classmethod
    def get_model_info(cls) -> dict[str, Any]:
        """返回模型元信息

        Returns:
            模型信息字典
        """
        return {
            "method": "mockembedder",
            "requires_api_key": False,
            "requires_model_download": False,
            "default_dimension": 128,
        }
