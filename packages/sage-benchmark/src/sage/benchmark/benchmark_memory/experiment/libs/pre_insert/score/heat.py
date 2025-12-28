"""HeatScoreAction - 热度评分策略

计算记忆的"热度"值，用于 MemoryOS 的多层级记忆管理。
热度综合考虑访问频率、时间衰减等因素。
"""

import time

from ..base import BasePreInsertAction, PreInsertInput, PreInsertOutput


class HeatScoreAction(BasePreInsertAction):
    """热度评分 Action

    使用场景：
    - MemoryOS: 多层级记忆管理，根据热度决定存储层级
    - 通用记忆体: 热度作为优先级指标

    热度计算因素：
    - 初始热度（新记忆）
    - 内容特征（长度、关键词等）
    - 时间衰减（可选）
    """

    def _init_action(self) -> None:
        """初始化热度评分参数"""
        self.initial_heat = self.config.get("initial_heat", 1.0)
        self.heat_range = self.config.get("heat_range", [0.0, 1.0])

        # 热度计算权重
        self.length_factor = self.config.get("length_factor", 0.3)
        self.keyword_factor = self.config.get("keyword_factor", 0.4)
        self.recency_factor = self.config.get("recency_factor", 0.3)

        # 热关键词（表示高热度的词汇）
        self.hot_keywords = set(
            self.config.get(
                "hot_keywords",
                [
                    "now",
                    "today",
                    "current",
                    "urgent",
                    "active",
                    "现在",
                    "今天",
                    "当前",
                    "紧急",
                    "活跃",
                ],
            )
        )

    def execute(self, input_data: PreInsertInput) -> PreInsertOutput:
        """执行热度评分

        Args:
            input_data: 包含 dialogs 的输入数据

        Returns:
            包含热度分数的记忆条目
        """
        # 提取并格式化对话
        dialogs = input_data.data.get("dialogs", [])
        text = self._format_dialogue(dialogs)

        # 计算热度
        heat_score = self._calculate_heat(text)

        # 创建记忆条目
        entry = {
            "text": text,
            "heat": heat_score,
            "metadata": {
                "action": "score.heat",
                "initial_heat": heat_score,
                "created_at": time.time(),  # 用于后续时间衰减
            },
        }
        entry = self._set_default_fields(entry)
        entry["insert_method"] = "heat_insert"

        return PreInsertOutput(
            memory_entries=[entry],
            metadata={
                "heat_score": heat_score,
            },
        )

    def _calculate_heat(self, text: str) -> float:
        """计算热度分数

        综合考虑：
        - 文本长度（较长的对话可能更重要）
        - 热关键词（表示时效性）
        - 新鲜度（新记忆初始热度高）

        Args:
            text: 输入文本

        Returns:
            热度分数（0.0 - 1.0）
        """
        # 1. 长度因子（短文本热度略低）
        length_score = min(len(text) / 500, 1.0) * 0.8 + 0.2  # 0.2 - 1.0

        # 2. 关键词因子
        text_lower = text.lower()
        keyword_count = sum(1 for kw in self.hot_keywords if kw in text_lower)
        keyword_score = min(keyword_count / 2, 1.0)  # 最多 2 个热关键词即满分

        # 3. 新鲜度因子（新记忆默认较高热度）
        recency_score = 0.8  # 新记忆默认 0.8

        # 4. 综合得分
        heat = (
            self.length_factor * length_score
            + self.keyword_factor * keyword_score
            + self.recency_factor * recency_score
        )

        # 确保在范围内
        min_heat, max_heat = self.heat_range
        heat = max(min_heat, min(heat, max_heat))

        return round(heat, 3)
