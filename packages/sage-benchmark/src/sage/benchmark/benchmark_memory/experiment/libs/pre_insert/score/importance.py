"""ImportanceScoreAction - 重要性评分策略

为记忆条目评估重要性分数，用于优先级排序和遗忘决策。
适用于 LD-Agent, Generative Agents 等需要重要性评分的记忆体。
"""

from ..base import BasePreInsertAction, PreInsertInput, PreInsertOutput


class ImportanceScoreAction(BasePreInsertAction):
    """重要性评分 Action

    使用场景：
    - LD-Agent: 评估对话重要性
    - Generative Agents: Reflection 机制需要重要性分数

    评分方法：
    - rule_based: 基于规则的启发式评分
    - llm: 使用 LLM 评估重要性（推荐）
    """

    def _init_action(self) -> None:
        """初始化评分参数"""
        self.method = self.config.get("method", "rule_based")
        self.score_range = self.config.get("score_range", [0, 10])

        # 规则评分的权重配置
        self.length_weight = self.config.get("length_weight", 0.3)
        self.keyword_weight = self.config.get("keyword_weight", 0.4)
        self.recency_weight = self.config.get("recency_weight", 0.3)

        # 重要关键词列表（简化版）
        self.important_keywords = set(
            self.config.get(
                "important_keywords",
                [
                    "urgent",
                    "important",
                    "critical",
                    "remember",
                    "note",
                    "紧急",
                    "重要",
                    "关键",
                    "记住",
                    "注意",
                ],
            )
        )

    def execute(self, input_data: PreInsertInput) -> PreInsertOutput:
        """执行重要性评分

        Args:
            input_data: 包含 dialogs 的输入数据

        Returns:
            包含重要性分数的记忆条目
        """
        # 提取并格式化对话
        dialogs = input_data.data.get("dialogs", [])
        text = self._format_dialogue(dialogs)

        # 计算重要性分数
        importance_score = self._calculate_importance(text)

        # 创建记忆条目
        entry = {
            "text": text,
            "importance": importance_score,
            "metadata": {
                "action": "score.importance",
                "score_method": self.method,
                "score_range": self.score_range,
            },
        }
        entry = self._set_default_fields(entry)
        entry["insert_method"] = "importance_insert"

        return PreInsertOutput(
            memory_entries=[entry],
            metadata={
                "importance_score": importance_score,
                "method": self.method,
            },
        )

    def _calculate_importance(self, text: str) -> float:
        """计算重要性分数

        Args:
            text: 输入文本

        Returns:
            重要性分数（归一化到 score_range）
        """
        if self.method == "llm":
            return self._score_by_llm(text)
        else:
            return self._score_by_rule(text)

    def _score_by_rule(self, text: str) -> float:
        """基于规则的评分

        综合考虑：
        - 文本长度（越长可能越重要）
        - 重要关键词出现次数
        - 其他启发式特征

        Args:
            text: 输入文本

        Returns:
            重要性分数
        """
        # 1. 长度因子（归一化到 0-1）
        length_score = min(len(text) / 1000, 1.0)

        # 2. 关键词因子
        text_lower = text.lower()
        keyword_count = sum(1 for kw in self.important_keywords if kw in text_lower)
        keyword_score = min(keyword_count / 3, 1.0)  # 最多 3 个关键词即满分

        # 3. 综合得分
        raw_score = (
            self.length_weight * length_score
            + self.keyword_weight * keyword_score
            + self.recency_weight * 0.5  # 新记忆默认中等重要性
        )

        # 映射到目标范围
        min_score, max_score = self.score_range
        final_score = min_score + raw_score * (max_score - min_score)

        return round(final_score, 2)

    def _score_by_llm(self, text: str) -> float:
        """使用 LLM 评估重要性

        TODO: 集成 LLM 调用

        Prompt 示例：
        "Rate the importance of the following conversation on a scale of 0-10,
        where 0 is trivial and 10 is critical:\n\n{text}\n\nImportance:"

        Args:
            text: 输入文本

        Returns:
            重要性分数
        """
        # 当前回退到规则方法
        return self._score_by_rule(text)
