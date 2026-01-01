"""Semantic Rerank - 语义重排序

使用场景: TiM

功能: 使用 embedding 计算查询和记忆条目的语义相似度，重新排序
"""

from typing import Any, Optional

from ..base import BasePostRetrievalAction, PostRetrievalInput, PostRetrievalOutput


class SemanticRerankAction(BasePostRetrievalAction):
    """语义重排序策略

    使用查询和记忆条目的 embedding 计算相似度，重新排序结果。
    """

    def _init_action(self) -> None:
        """初始化配置"""
        self.similarity_metric = self.config.get("similarity_metric", "cosine")
        self.embedding: Optional[Any] = None

    def set_embedding_generator(self, embedding_generator: Any) -> None:
        """设置 embedding 生成器

        Args:
            embedding_generator: Embedding 生成器实例
        """
        self.embedding = embedding_generator

    def execute(
        self,
        input_data: PostRetrievalInput,
        service: Any,
        llm: Optional[Any] = None,
    ) -> PostRetrievalOutput:
        """使用语义相似度重排序

        Args:
            input_data: 输入数据（包含 question 和 memory_data）
            service: 记忆服务代理（未使用）
            llm: LLM 生成器（未使用）

        Returns:
            PostRetrievalOutput: 重排序后的结果
        """
        memory_data = input_data.data.get("memory_data", [])
        items = self._convert_to_items(memory_data)

        if not items:
            return PostRetrievalOutput(memory_items=items, metadata={"action": "rerank.semantic"})

        # 获取查询 embedding
        query_embedding = input_data.data.get("query_embedding")
        if query_embedding is None and self.embedding is not None:
            question = input_data.data.get("question", "")
            query_embedding = self.embedding.generate(question)

        if query_embedding is None:
            # 如果没有查询 embedding，退化为保持原序
            return PostRetrievalOutput(
                memory_items=items,
                metadata={"action": "rerank.semantic", "warning": "No query embedding available"},
            )

        # 计算相似度并重排序
        scored_items = []
        for item in items:
            item_embedding = item.metadata.get("embedding")
            if item_embedding is not None:
                similarity = self._compute_similarity(query_embedding, item_embedding)
                scored_items.append((item, similarity))
            else:
                # 如果条目没有 embedding，使用原始 score 或 0
                scored_items.append((item, item.score or 0.0))

        # 按相似度降序排序
        scored_items.sort(key=lambda x: x[1], reverse=True)

        # 更新 score 为新的相似度
        reranked_items = []
        for item, similarity in scored_items:
            item.score = similarity
            reranked_items.append(item)

        return PostRetrievalOutput(
            memory_items=reranked_items,
            metadata={"action": "rerank.semantic", "similarity_metric": self.similarity_metric},
        )

    def _compute_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """计算两个向量的相似度

        Args:
            vec1: 向量 1
            vec2: 向量 2

        Returns:
            相似度分数
        """
        if self.similarity_metric == "cosine":
            return self._cosine_similarity(vec1, vec2)
        elif self.similarity_metric == "dot":
            return sum(a * b for a, b in zip(vec1, vec2))
        else:
            # 默认使用余弦相似度
            return self._cosine_similarity(vec1, vec2)

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
