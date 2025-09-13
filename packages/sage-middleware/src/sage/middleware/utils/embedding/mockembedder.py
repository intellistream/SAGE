import hashlib
from typing import Optional

import torch


class MockTextEmbedder:
    def __init__(self, model_name: str = "mock-model", fixed_dim: int = 128):
        """Mock 模型，输出固定维度的随机张量（但相同文本输出一致）"""
        self.fixed_dim = fixed_dim
        # 用模型名作为随机种子的一部分，确保不同实例行为一致
        self.seed = int(hashlib.sha256(model_name.encode()).hexdigest()[:8], 16)
        # 添加 method_name 属性以兼容 MemoryManager
        self.method_name = "mockembedder"

    def encode(
        self, text: str, max_length: int = 512, stride: Optional[int] = None
    ) -> torch.Tensor:
        """生成固定维度的伪嵌入（相同文本输出相同）"""
        if not text.strip():
            return torch.zeros(self.fixed_dim)

        # 根据文本内容生成确定性随机数
        text_seed = self.seed + int(hashlib.sha256(text.encode()).hexdigest()[:8], 16)
        torch.manual_seed(text_seed)

        # 生成随机向量（与原有代码维度逻辑一致）
        if stride is None or len(text.split()) <= max_length:
            return self._embed_single()
        else:
            return self._embed_with_sliding_window()

    def _embed_single(self) -> torch.Tensor:
        """模拟单文本嵌入"""
        embedding = torch.randn(384)  # 模拟原始模型的中间维度
        return self._adjust_dimension(embedding)

    def _embed_with_sliding_window(self) -> torch.Tensor:
        """模拟长文本滑动窗口嵌入"""
        embeddings = torch.stack([torch.randn(384) for _ in range(3)])  # 模拟3个窗口
        return self._adjust_dimension(embeddings.mean(dim=0))

    def _adjust_dimension(self, embedding: torch.Tensor) -> torch.Tensor:
        """保持与原代码一致的维度调整逻辑"""
        if embedding.size(0) > self.fixed_dim:
            return embedding[: self.fixed_dim]
        elif embedding.size(0) < self.fixed_dim:
            padding = torch.zeros(self.fixed_dim - embedding.size(0))
            return torch.cat((embedding, padding))
        return embedding
