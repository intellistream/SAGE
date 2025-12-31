"""Top-K Filter - Top-K 过滤

功能: 只保留前 K 个最高分的记忆
"""

from typing import Any, Optional

from ..base import BasePostRetrievalAction, PostRetrievalInput, PostRetrievalOutput


class TopKFilterAction(BasePostRetrievalAction):
    """Top-K 过滤策略

    只保留分数最高的前 K 个记忆条目。
    """

    def _init_action(self) -> None:
        """初始化配置"""
        self.top_k = self.config.get("top_k", 10)

    def execute(
        self,
        input_data: PostRetrievalInput,
        service: Any,
        llm: Optional[Any] = None,
    ) -> PostRetrievalOutput:
        """保留 Top-K 结果

        Args:
            input_data: 输入数据
            service: 记忆服务代理（未使用）
            llm: LLM 生成器（未使用）

        Returns:
            PostRetrievalOutput: 过滤后的结果
        """
        memory_data = input_data.data.get("memory_data", [])
        items = self._convert_to_items(memory_data)

        if not items:
            return PostRetrievalOutput(memory_items=items, metadata={"action": "filter.top_k"})

        # 如果已经有分数，按分数排序后取前 K 个
        # 否则按原始顺序取前 K 个
        if any(item.score is not None for item in items):
            # 按分数降序排序
            sorted_items = sorted(items, key=lambda x: x.score or 0.0, reverse=True)
            filtered_items = sorted_items[: self.top_k]
        else:
            # 保持原始顺序
            filtered_items = items[: self.top_k]

        return PostRetrievalOutput(
            memory_items=filtered_items,
            metadata={
                "action": "filter.top_k",
                "top_k": self.top_k,
                "original_count": len(items),
                "filtered_count": len(filtered_items),
            },
        )
