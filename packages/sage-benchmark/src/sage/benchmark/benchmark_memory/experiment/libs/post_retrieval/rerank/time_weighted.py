"""Time Weighted Rerank - 时间加权重排序

使用场景: LD-Agent

功能: 结合时间衰减因子重新排序记忆，越新的记忆权重越高
"""

import math
from datetime import UTC, datetime
from typing import Any, Optional

UTC = UTC

from ..base import BasePostRetrievalAction, PostRetrievalInput, PostRetrievalOutput


class TimeWeightedRerankAction(BasePostRetrievalAction):
    """时间加权重排序策略

    使用时间衰减因子调整记忆分数，越新的记忆权重越高。
    """

    def _init_action(self) -> None:
        """初始化配置"""
        self.decay_rate = self.config.get("time_decay_rate", 0.1)
        self.time_field = self.config.get("time_field", "timestamp")
        self.time_weight = self.config.get("time_weight", 0.5)  # 时间因子权重
        self.score_weight = self.config.get("score_weight", 0.5)  # 原始分数权重

    def execute(
        self,
        input_data: PostRetrievalInput,
        service: Optional[Any] = None,
        llm: Optional[Any] = None,
        embedding: Optional[Any] = None,
    ) -> PostRetrievalOutput:
        """使用时间衰减重排序

        Args:
            input_data: 输入数据

        Returns:
            PostRetrievalOutput: 重排序后的结果
        """
        memory_data = input_data.data.get("memory_data", [])
        items = self._convert_to_items(memory_data)

        if not items:
            return PostRetrievalOutput(
                memory_items=items, metadata={"action": "rerank.time_weighted"}
            )

        # 计算时间衰减分数
        now = datetime.now(UTC)
        scored_items = []

        for item in items:
            timestamp = item.get_timestamp(self.time_field)

            if timestamp:
                # 计算时间差（天数）
                time_diff = (now - timestamp).total_seconds() / 86400
                decay_factor = math.exp(-self.decay_rate * time_diff)
            else:
                # 如果没有时间戳，使用默认衰减因子 0.5
                decay_factor = 0.5

            # 组合原始分数和时间衰减
            original_score = item.score or 1.0
            combined_score = self.score_weight * original_score + self.time_weight * decay_factor

            scored_items.append((item, combined_score))

        # 按组合分数降序排序
        scored_items.sort(key=lambda x: x[1], reverse=True)

        # 更新 score
        reranked_items = []
        for item, score in scored_items:
            item.score = score
            reranked_items.append(item)

        return PostRetrievalOutput(
            memory_items=reranked_items,
            metadata={
                "action": "rerank.time_weighted",
                "decay_rate": self.decay_rate,
                "time_weight": self.time_weight,
                "score_weight": self.score_weight,
            },
        )
