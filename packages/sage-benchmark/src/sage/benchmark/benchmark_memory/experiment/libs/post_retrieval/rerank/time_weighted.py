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
        self.top_k = self.config.get("top_k", -1)  # 返回前 k 个结果，-1 表示全部返回

        # MemoryBank: 记忆强化配置
        self.enable_reinforcement = self.config.get("enable_reinforcement", False)
        self.reinforcement_increment = self.config.get("reinforcement_increment", 1.0)
        self.reinforcement_reset_time = self.config.get("reinforcement_reset_time", True)

    def execute(
        self,
        input_data: PostRetrievalInput,
        service: Any,
        llm: Optional[Any] = None,
    ) -> PostRetrievalOutput:
        """使用时间衰减重排序

        Args:
            input_data: 输入数据
            service: 记忆服务代理（用于记忆强化）
            llm: LLM 生成器（未使用）

        Returns:
            PostRetrievalOutput: 重排序后的结果
        """
        memory_data = input_data.data.get("memory_data", [])
        items = self._convert_to_items(memory_data)

        if not items:
            return PostRetrievalOutput(
                memory_items=items, metadata={"action": "rerank.time_weighted"}
            )

        # MemoryBank: 记忆强化 (在重排序之前执行)
        reinforced_count = 0
        if self.enable_reinforcement and service and hasattr(service, "update_memory_strength"):
            for item in items:
                entry_id = item.metadata.get("entry_id")
                if entry_id:
                    try:
                        success = service.update_memory_strength(
                            entry_id=entry_id,
                            increment=self.reinforcement_increment,
                            reset_time=self.reinforcement_reset_time,
                        )
                        if success:
                            reinforced_count += 1
                    except Exception as e:
                        self.logger.debug(f"Failed to reinforce memory {entry_id}: {e}")

        # 计算时间衰减分数并重排序
        now = datetime.now(UTC)

        for item in items:
            timestamp = item.get_timestamp(self.time_field)

            if timestamp:
                # 计算时间差（天数）
                time_diff = (now - timestamp).total_seconds() / 86400
                decay_factor = math.exp(-self.decay_rate * time_diff)
            else:
                # 没有时间戳，使用默认衰减因子 1.0
                decay_factor = 1.0

            # 计算加权分数
            item.score = self.score_weight * item.score + self.time_weight * decay_factor

        # 按加权分数排序
        items.sort(key=lambda x: x.score, reverse=True)

        # 截取 top_k
        if self.top_k > 0:
            items = items[: self.top_k]

        metadata = {
            "action": "rerank.time_weighted",
            "decay_rate": self.decay_rate,
            "time_weight": self.time_weight,
            "score_weight": self.score_weight,
        }

        # 添加记忆强化统计
        if self.enable_reinforcement:
            metadata["reinforced_count"] = reinforced_count
            metadata["reinforcement_enabled"] = True

        return PostRetrievalOutput(
            memory_items=items,
            metadata=metadata,
        )
