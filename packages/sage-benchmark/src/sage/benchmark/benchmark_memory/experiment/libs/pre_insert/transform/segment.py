"""TopicSegmentAction - 话题分段策略

将对话按话题分段，每个话题作为独立的记忆单元。
适用于 SeCom 等需要话题分段的记忆体。
"""

from ..base import BasePreInsertAction, PreInsertInput, PreInsertOutput


class TopicSegmentAction(BasePreInsertAction):
    """话题分段 Action

    使用场景：
    - SeCom: 按话题分段对话
    - LD-Agent: 识别对话主题切换

    分段策略：
    - simple: 简单基于关键词变化分段
    - llm: 使用 LLM 识别话题边界（推荐）
    """

    def _init_action(self) -> None:
        """初始化分段参数"""
        self.strategy = self.config.get("strategy", "simple")
        self.min_segment_length = self.config.get("min_segment_length", 3)

        # 话题关键词检测相关参数
        self.keyword_threshold = self.config.get("keyword_threshold", 0.3)

    def execute(self, input_data: PreInsertInput) -> PreInsertOutput:
        """执行话题分段

        Args:
            input_data: 包含 dialogs 的输入数据

        Returns:
            包含多个话题段的输出
        """
        # 提取对话数据
        dialogs = input_data.data.get("dialogs", [])

        # 分段
        segments = self._segment_by_topic(dialogs)

        # 创建记忆条目
        entries = []
        for i, segment in enumerate(segments):
            text = self._format_dialogue(segment)

            entry = {
                "text": text,
                "segment_text": text,
                "metadata": {
                    "action": "transform.segment",
                    "segment_index": i,
                    "total_segments": len(segments),
                    "segment_length": len(segment),
                    "strategy": self.strategy,
                },
            }
            entry = self._set_default_fields(entry)
            entry["insert_method"] = "segment_insert"
            entries.append(entry)

        return PreInsertOutput(
            memory_entries=entries,
            metadata={
                "total_segments": len(segments),
                "strategy": self.strategy,
            },
        )

    def _segment_by_topic(self, dialogs: list[dict[str, str]]) -> list[list[dict[str, str]]]:
        """按话题分段对话

        Args:
            dialogs: 对话列表

        Returns:
            分段后的对话列表（每段是一个对话列表）
        """
        if self.strategy == "llm":
            # TODO: 使用 LLM 进行话题分段
            return self._segment_by_llm(dialogs)
        else:
            # 简单策略：基于对话长度分段
            return self._segment_simple(dialogs)

    def _segment_simple(self, dialogs: list[dict[str, str]]) -> list[list[dict[str, str]]]:
        """简单分段策略

        按固定数量的对话轮次分段。

        Args:
            dialogs: 对话列表

        Returns:
            分段列表
        """
        segments = []
        current_segment = []

        for dialog in dialogs:
            current_segment.append(dialog)

            # 每 min_segment_length 轮对话作为一段
            if len(current_segment) >= self.min_segment_length:
                segments.append(current_segment)
                current_segment = []

        # 保存最后一段
        if current_segment:
            segments.append(current_segment)

        return segments if segments else [dialogs]

    def _segment_by_llm(self, dialogs: list[dict[str, str]]) -> list[list[dict[str, str]]]:
        """使用 LLM 进行话题分段

        TODO: 实现基于 LLM 的话题边界检测

        Args:
            dialogs: 对话列表

        Returns:
            分段列表
        """
        # 当前回退到简单策略
        return self._segment_simple(dialogs)
