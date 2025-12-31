"""ReinforceAction - 记忆强化

实现 MemoryBank 论文的检索强化机制:
- 被检索的记忆强度 S += 1
- 重置衰减时间 t = 0
- 更新 last_recall_date 为当前时间

用途: MemoryBank 的 Ebbinghaus 遗忘曲线需要配合检索强化使用
"""

from typing import Any, Optional

from ..base import BasePostRetrievalAction, MemoryItem, PostRetrievalInput, PostRetrievalOutput


class ReinforceAction(BasePostRetrievalAction):
    """记忆强化 Action

    在检索后更新被检索记忆的强度和时间戳。

    配置参数:
        increment (float): 强度增量 (默认 1.0)
        reset_time (bool): 是否重置时间 (默认 True)
        min_score_threshold (float): 最低分数阈值，低于此值的不强化 (默认 0.0)
    """

    def _init_action(self) -> None:
        """初始化强化参数"""
        self.increment = self.config.get("increment", 1.0)
        self.reset_time = self.config.get("reset_time", True)
        self.min_score_threshold = self.config.get("min_score_threshold", 0.0)

    def execute(
        self,
        input_data: PostRetrievalInput,
        service: Any,
        llm: Optional[Any] = None,
    ) -> PostRetrievalOutput:
        """执行记忆强化

        Args:
            input_data: 包含检索结果的输入数据
            service: 记忆服务代理（需要有 update_memory_strength 方法）
            llm: LLM 生成器（未使用）

        Returns:
            PostRetrievalOutput: 原样返回记忆条目（不改变顺序和内容）
        """
        memory_data = input_data.data.get("memory_data", [])

        # 检查 service 是否支持 update_memory_strength
        if not hasattr(service, "update_memory_strength"):
            self.logger.warning(
                f"Service {type(service).__name__} does not support update_memory_strength, "
                "skipping reinforcement"
            )
            return PostRetrievalOutput(memory_data=memory_data)

        # 统计强化信息
        reinforced_count = 0
        skipped_low_score = 0

        # 遍历所有检索结果，更新记忆强度
        for item in memory_data:
            # 检查分数阈值
            score = item.get("score", 1.0)
            if score < self.min_score_threshold:
                skipped_low_score += 1
                continue

            # 获取 entry_id
            entry_id = item.get("id")
            if not entry_id:
                self.logger.warning("Memory item missing 'id', skipping reinforcement")
                continue

            # 调用服务更新记忆强度
            try:
                service.update_memory_strength(
                    entry_id=entry_id,
                    increment=self.increment,
                    reset_time=self.reset_time,
                )
                reinforced_count += 1
            except Exception as e:
                self.logger.error(f"Failed to reinforce memory {entry_id}: {e}")

        # 日志输出
        if reinforced_count > 0 or skipped_low_score > 0:
            self.logger.info(
                f"[Reinforce] Processed {len(memory_data)} items: "
                f"{reinforced_count} reinforced, {skipped_low_score} skipped (low score)"
            )

        # 返回原始记忆数据（不改变顺序）
        return PostRetrievalOutput(
            memory_data=memory_data,
            metadata={
                "reinforced_count": reinforced_count,
                "skipped_low_score": skipped_low_score,
                "total_items": len(memory_data),
            },
        )

    def _extract_memory_items(self, memory_data: list[dict]) -> list[MemoryItem]:
        """将原始字典转换为 MemoryItem 对象

        Args:
            memory_data: 原始记忆数据列表

        Returns:
            MemoryItem 对象列表
        """
        return [
            MemoryItem(
                id=item.get("id", ""),
                text=item.get("text", ""),
                score=item.get("score", 0.0),
                metadata=item.get("metadata", {}),
            )
            for item in memory_data
        ]
