"""Threshold Filter - 阈值过滤

功能: 根据分数阈值过滤低分记忆
"""

from typing import Any, Optional

from ..base import BasePostRetrievalAction, PostRetrievalInput, PostRetrievalOutput


class ThresholdFilterAction(BasePostRetrievalAction):
    """阈值过滤策略

    过滤掉分数低于阈值的记忆条目。
    """

    def _init_action(self) -> None:
        """初始化配置"""
        self.threshold = self.config.get("threshold", 0.5)
        self.score_field = self.config.get("score_field", "score")

    def execute(
        self,
        input_data: PostRetrievalInput,
        service: Optional[Any] = None,
        llm: Optional[Any] = None,
        embedding: Optional[Any] = None,
    ) -> PostRetrievalOutput:
        """根据阈值过滤结果

        Args:
            input_data: 输入数据

        Returns:
            PostRetrievalOutput: 过滤后的结果
        """
        memory_data = input_data.data.get("memory_data", [])
        items = self._convert_to_items(memory_data)

        if not items:
            return PostRetrievalOutput(memory_items=items, metadata={"action": "filter.threshold"})

        # 过滤低于阈值的条目
        filtered_items = []
        for item in items:
            score = item.score
            if score is None:
                # 如果没有分数，尝试从 metadata 获取
                score = item.metadata.get(self.score_field)

            if score is not None and score >= self.threshold:
                filtered_items.append(item)

        return PostRetrievalOutput(
            memory_items=filtered_items,
            metadata={
                "action": "filter.threshold",
                "threshold": self.threshold,
                "original_count": len(items),
                "filtered_count": len(filtered_items),
            },
        )
