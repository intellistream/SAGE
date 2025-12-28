"""Weighted Rerank - 多因子加权重排序

使用场景: LD-Agent

功能: 综合多个因子（相似度、时间、重要性等）进行加权重排序
"""

import math
from datetime import UTC, datetime
from typing import Any, Optional

UTC = UTC

from ..base import BasePostRetrievalAction, PostRetrievalInput, PostRetrievalOutput


class WeightedRerankAction(BasePostRetrievalAction):
    """多因子加权重排序策略

    综合考虑多个因子:
    - 语义相似度
    - 时间衰减
    - 重要性分数
    - 访问频率等
    """

    def _init_action(self) -> None:
        """初始化配置"""
        self.similarity_weight = self.config.get("similarity_weight", 0.4)
        self.time_weight = self.config.get("time_weight", 0.3)
        self.importance_weight = self.config.get("importance_weight", 0.2)
        self.frequency_weight = self.config.get("frequency_weight", 0.1)
        self.time_decay_rate = self.config.get("time_decay_rate", 0.1)
        self.time_field = self.config.get("time_field", "timestamp")

    def execute(
        self,
        input_data: PostRetrievalInput,
        service: Optional[Any] = None,
        llm: Optional[Any] = None,
        embedding: Optional[Any] = None,
    ) -> PostRetrievalOutput:
        """使用多因子加权重排序

        Args:
            input_data: 输入数据
            embedding: Embedding 生成器（用于计算语义相似度）

        Returns:
            PostRetrievalOutput: 重排序后的结果
        """
        memory_data = input_data.data.get("memory_data", [])
        items = self._convert_to_items(memory_data)

        if not items:
            return PostRetrievalOutput(memory_items=items, metadata={"action": "rerank.weighted"})

        # 获取查询 embedding（用于计算相似度）
        query_embedding = input_data.data.get("query_embedding")
        if query_embedding is None and embedding is not None:
            question = input_data.data.get("question", "")
            query_embedding = embedding.generate(question)

        # 计算每个条目的综合分数
        now = datetime.now(UTC)
        scored_items = []

        for item in items:
            # 1. 语义相似度分数
            similarity_score = 0.0
            if query_embedding and item.metadata.get("embedding"):
                similarity_score = self._cosine_similarity(
                    query_embedding, item.metadata["embedding"]
                )
            elif item.score is not None:
                similarity_score = item.score

            # 2. 时间衰减分数
            time_score = 0.5  # 默认值
            timestamp = item.get_timestamp(self.time_field)
            if timestamp:
                time_diff = (now - timestamp).total_seconds() / 86400
                time_score = math.exp(-self.time_decay_rate * time_diff)

            # 3. 重要性分数
            importance_score = item.metadata.get("importance", 0.5)

            # 4. 访问频率分数
            frequency = item.metadata.get("access_count", 1)
            frequency_score = min(1.0, math.log(frequency + 1) / math.log(100))

            # 综合加权分数
            combined_score = (
                self.similarity_weight * similarity_score
                + self.time_weight * time_score
                + self.importance_weight * importance_score
                + self.frequency_weight * frequency_score
            )

            scored_items.append((item, combined_score))

        # 按综合分数降序排序
        scored_items.sort(key=lambda x: x[1], reverse=True)

        # 更新 score
        reranked_items = []
        for item, score in scored_items:
            item.score = score
            reranked_items.append(item)

        return PostRetrievalOutput(
            memory_items=reranked_items,
            metadata={
                "action": "rerank.weighted",
                "weights": {
                    "similarity": self.similarity_weight,
                    "time": self.time_weight,
                    "importance": self.importance_weight,
                    "frequency": self.frequency_weight,
                },
            },
        )

    def _cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """计算余弦相似度

        Args:
            vec1: 向量 1
            vec2: 向量 2

        Returns:
            余弦相似度 [-1, 1]
        """
        import math

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)
