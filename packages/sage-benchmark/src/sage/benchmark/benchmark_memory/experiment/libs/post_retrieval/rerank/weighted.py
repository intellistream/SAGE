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
    - 话题重叠 (keyword_jaccard)
    """

    def _init_action(self) -> None:
        """初始化配置"""
        # 支持新格式: factors 列表
        factors = self.config.get("factors", [])
        if factors:
            # 使用 factors 列表配置
            self.factors = factors
            self._parse_factors(factors)
        else:
            # 向后兼容: 使用旧的独立参数
            self.similarity_weight = self.config.get("similarity_weight", 0.4)
            self.time_weight = self.config.get("time_weight", 0.3)
            self.importance_weight = self.config.get("importance_weight", 0.2)
            self.frequency_weight = self.config.get("frequency_weight", 0.1)
            self.time_decay_rate = self.config.get("time_decay_rate", 0.1)
            self.factors = None

        self.time_field = self.config.get("time_field", "timestamp")
        self.embedding: Optional[Any] = None

    def _parse_factors(self, factors: list[dict]) -> None:
        """解析 factors 列表配置

        Args:
            factors: 因子配置列表，格式:
                [{name, weight, source?, decay_type?, decay_rate?}, ...]
        """
        self.factor_weights = {}
        self.factor_sources = {}
        self.factor_decay_configs = {}

        for factor in factors:
            name = factor.get("name")
            weight = float(factor.get("weight", 0.0))
            source = factor.get("source", "default")

            self.factor_weights[name] = weight
            self.factor_sources[name] = source

            # 解析衰减配置
            if "decay_type" in factor:
                self.factor_decay_configs[name] = {
                    "type": factor.get("decay_type"),
                    "rate": float(factor.get("decay_rate", 0.1)),
                }

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
        """使用多因子加权重排序

        Args:
            input_data: 输入数据
            service: 记忆服务代理（未使用）
            llm: LLM 生成器（未使用）

        Returns:
            PostRetrievalOutput: 重排序后的结果
        """
        memory_data = input_data.data.get("memory_data", [])
        items = self._convert_to_items(memory_data)

        if not items:
            return PostRetrievalOutput(memory_items=items, metadata={"action": "rerank.weighted"})

        # 使用新的 factors 配置或旧的独立参数
        if self.factors:
            scored_items = self._score_with_factors(items, input_data)
        else:
            scored_items = self._score_legacy(items, input_data)

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
                "weights": self.factor_weights
                if self.factors
                else {
                    "similarity": self.similarity_weight,
                    "time": self.time_weight,
                    "importance": self.importance_weight,
                    "frequency": self.frequency_weight,
                },
            },
        )

    def _score_with_factors(self, items, input_data: PostRetrievalInput) -> list:
        """使用 factors 列表配置计算分数

        Args:
            items: 记忆条目列表
            input_data: 输入数据

        Returns:
            (item, score) 元组列表
        """
        # 获取查询关键词（用于 keyword_jaccard）
        query_keywords = input_data.data.get("extracted_keywords", [])

        # 获取查询 embedding（用于 embedding_similarity）
        query_embedding = input_data.data.get("query_embedding")
        if query_embedding is None and self.embedding is not None:
            question = input_data.data.get("question", "")
            query_embedding = self.embedding.generate(question)

        now = datetime.now(UTC)
        scored_items = []

        for item in items:
            combined_score = 0.0

            for factor_name, weight in self.factor_weights.items():
                factor_score = self._calculate_factor_score(
                    factor_name, item, input_data, query_keywords, query_embedding, now
                )
                combined_score += weight * factor_score

            scored_items.append((item, combined_score))

        return scored_items

    def _calculate_factor_score(
        self,
        factor_name: str,
        item,
        input_data: PostRetrievalInput,
        query_keywords: list,
        query_embedding,
        now: datetime,
    ) -> float:
        """计算单个因子的分数

        Args:
            factor_name: 因子名称 (relevance, recency, topic_overlap 等)
            item: 记忆条目
            input_data: 输入数据
            query_keywords: 查询关键词列表
            query_embedding: 查询向量
            now: 当前时间

        Returns:
            因子分数 [0, 1]
        """
        source = self.factor_sources.get(factor_name, "default")

        # 1. relevance / embedding_similarity
        if factor_name == "relevance" or source == "embedding_similarity":
            if query_embedding and item.metadata.get("embedding"):
                return self._cosine_similarity(query_embedding, item.metadata["embedding"])
            elif item.score is not None:
                return item.score
            return 0.5

        # 2. recency / time decay
        elif factor_name == "recency":
            timestamp = item.get_timestamp(self.time_field)
            if not timestamp:
                return 0.5

            # 应用时间衰减
            decay_config = self.factor_decay_configs.get(factor_name, {})
            decay_type = decay_config.get("type", "exponential")
            decay_rate = decay_config.get("rate", 0.1)

            if decay_type == "exponential":
                # LD-Agent 格式: exp(-decay_rate * time_diff_seconds)
                time_diff_seconds = (now - timestamp).total_seconds()
                return math.exp(-decay_rate * time_diff_seconds)
            else:
                # 默认按天衰减
                time_diff_days = (now - timestamp).total_seconds() / 86400
                return math.exp(-decay_rate * time_diff_days)

        # 3. topic_overlap / keyword_jaccard
        elif factor_name == "topic_overlap" or source == "keyword_jaccard":
            return self._calculate_keyword_jaccard(query_keywords, item)

        # 4. importance
        elif factor_name == "importance":
            return item.metadata.get("importance", 0.5)

        # 5. frequency
        elif factor_name == "frequency":
            frequency = item.metadata.get("access_count", 1)
            return min(1.0, math.log(frequency + 1) / math.log(100))

        # 默认值
        return 0.5

    def _calculate_keyword_jaccard(self, query_keywords: list, item) -> float:
        """计算 keyword Jaccard 相似度（LD-Agent 实现）

        Args:
            query_keywords: 查询关键词列表
            item: 记忆条目

        Returns:
            Jaccard 相似度 [0, 1]

        LD-Agent 公式:
            overlap_score = 0.5 * (overlap / len(query_kw)) + 0.5 * (overlap / len(memory_kw))
        """
        if not query_keywords:
            return 0.0

        # 从 metadata 或 PreRetrieval 结果获取记忆的关键词
        memory_keywords = item.metadata.get("keywords", [])
        if not memory_keywords:
            # 如果没有预提取,尝试简单分词
            memory_keywords = item.text.lower().split()

        if not memory_keywords:
            return 0.0

        # 转换为集合并计算交集
        query_set = {kw.lower() for kw in query_keywords}
        memory_set = {kw.lower() for kw in memory_keywords}
        overlap_count = len(query_set & memory_set)

        if overlap_count == 0:
            return 0.0

        # LD-Agent 的 Jaccard 变体: 平均相对重叠
        score = 0.5 * (overlap_count / len(query_set)) + 0.5 * (overlap_count / len(memory_set))
        return score

    def _score_legacy(self, items, input_data: PostRetrievalInput) -> list:
        """使用旧的独立参数计算分数（向后兼容）

        Args:
            items: 记忆条目列表
            input_data: 输入数据

        Returns:
            (item, score) 元组列表
        """
        # 获取查询 embedding（用于计算相似度）
        query_embedding = input_data.data.get("query_embedding")
        if query_embedding is None and self.embedding is not None:
            question = input_data.data.get("question", "")
            query_embedding = self.embedding.generate(question)

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

        return scored_items

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
