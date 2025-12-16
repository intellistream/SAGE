"""KeywordExtractAction - 关键词抽取策略

从文本中抽取关键词，用于索引和检索。
适用于 A-Mem 等需要关键词的记忆体。
"""

from ..base import BasePreInsertAction, PreInsertInput, PreInsertOutput


class KeywordExtractAction(BasePreInsertAction):
    """关键词抽取 Action

    使用场景：
    - A-Mem: 提取关键词建立索引
    - 通用记忆体: 关键词标注

    支持的抽取方法：
    - simple: 基于词频的简单方法
    - rake: RAKE 算法
    - textrank: TextRank 算法
    """

    def _init_action(self) -> None:
        """初始化关键词抽取工具"""
        self.method = self.config.get("method", "simple")
        self.max_keywords = self.config.get("max_keywords", 10)
        self.min_keyword_length = self.config.get("min_keyword_length", 2)

        # 停用词（简化版）
        self.stopwords = {
            "the",
            "is",
            "at",
            "which",
            "on",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "with",
            "to",
            "for",
            "of",
            "as",
            "by",
            "from",
            "that",
            "this",
            "的",
            "了",
            "在",
            "是",
            "我",
            "有",
            "和",
            "就",
            "不",
            "人",
            "都",
            "一",
        }

    def execute(self, input_data: PreInsertInput) -> PreInsertOutput:
        """执行关键词抽取

        Args:
            input_data: 包含 dialogs 的输入数据

        Returns:
            包含关键词的记忆条目
        """
        # 提取并格式化对话
        dialogs = input_data.data.get("dialogs", [])
        text = self._format_dialogue(dialogs)

        # 抽取关键词
        keywords = self._extract_keywords(text)

        # 创建记忆条目（保存原文和关键词）
        entry = {
            "text": text,
            "keywords": keywords,
            "metadata": {
                "action": "extract.keyword",
                "keyword_count": len(keywords),
                "method": self.method,
            },
        }
        entry = self._set_default_fields(entry)
        entry["insert_method"] = "keyword_insert"

        return PreInsertOutput(
            memory_entries=[entry],
            metadata={
                "keywords": keywords,
                "method": self.method,
            },
        )

    def _extract_keywords(self, text: str) -> list[str]:
        """抽取关键词

        Args:
            text: 输入文本

        Returns:
            关键词列表
        """
        if self.method == "rake":
            return self._extract_by_rake(text)
        elif self.method == "textrank":
            return self._extract_by_textrank(text)
        else:
            return self._extract_simple(text)

    def _extract_simple(self, text: str) -> list[str]:
        """简单的关键词抽取（基于词频）

        Args:
            text: 输入文本

        Returns:
            关键词列表
        """
        import re
        from collections import Counter

        # 分词（简单按空格和标点分割）
        words = re.findall(r"\b\w+\b", text.lower())

        # 过滤停用词和短词
        words = [w for w in words if w not in self.stopwords and len(w) >= self.min_keyword_length]

        # 统计词频
        word_freq = Counter(words)

        # 返回 top N
        keywords = [word for word, _ in word_freq.most_common(self.max_keywords)]

        return keywords

    def _extract_by_rake(self, text: str) -> list[str]:
        """使用 RAKE 算法抽取关键词

        TODO: 实现 RAKE 算法或集成第三方库

        Args:
            text: 输入文本

        Returns:
            关键词列表
        """
        # 当前回退到简单方法
        return self._extract_simple(text)

    def _extract_by_textrank(self, text: str) -> list[str]:
        """使用 TextRank 算法抽取关键词

        TODO: 实现 TextRank 算法或集成第三方库

        Args:
            text: 输入文本

        Returns:
            关键词列表
        """
        # 当前回退到简单方法
        return self._extract_simple(text)
