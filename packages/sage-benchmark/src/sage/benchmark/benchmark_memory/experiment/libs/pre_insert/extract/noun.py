"""NounExtractAction - 名词抽取策略

从文本中抽取名词，用于构建索引或知识图谱。
通用的信息抽取策略。
"""

from ..base import BasePreInsertAction, PreInsertInput, PreInsertOutput


class NounExtractAction(BasePreInsertAction):
    """名词抽取 Action

    使用场景：
    - 通用记忆体: 抽取名词作为关键概念
    - 知识图谱: 名词作为节点

    支持的抽取方法：
    - spacy: 使用 spaCy POS tagging
    - simple: 简单的启发式方法
    """

    def _init_action(self) -> None:
        """初始化名词抽取工具"""
        self.method = self.config.get("method", "simple")
        self.max_nouns = self.config.get("max_nouns", 20)
        self.include_proper_nouns = self.config.get("include_proper_nouns", True)

        # 如果使用 spacy，加载模型
        if self.method == "spacy":
            try:
                import spacy

                model_name = self.config.get("spacy_model", "en_core_web_sm")
                self._nlp = spacy.load(model_name)
            except Exception:
                # 如果 spacy 不可用，回退到简单方法
                self.method = "simple"
                self._nlp = None
        else:
            self._nlp = None

    def execute(self, input_data: PreInsertInput) -> PreInsertOutput:
        """执行名词抽取

        Args:
            input_data: 包含 dialogs 的输入数据

        Returns:
            包含名词列表的记忆条目
        """
        # 提取并格式化对话
        dialogs = input_data.data.get("dialogs", [])
        text = self._format_dialogue(dialogs)

        # 抽取名词
        nouns = self._extract_nouns(text)

        # 创建记忆条目
        entry = {
            "text": text,
            "nouns": nouns,
            "metadata": {
                "action": "extract.noun",
                "noun_count": len(nouns),
                "method": self.method,
            },
        }
        entry = self._set_default_fields(entry)
        entry["insert_method"] = "noun_insert"

        return PreInsertOutput(
            memory_entries=[entry],
            metadata={
                "nouns": nouns,
                "method": self.method,
            },
        )

    def _extract_nouns(self, text: str) -> list[str]:
        """抽取名词

        Args:
            text: 输入文本

        Returns:
            名词列表
        """
        if self.method == "spacy" and self._nlp:
            return self._extract_by_spacy(text)
        else:
            return self._extract_simple(text)

    def _extract_by_spacy(self, text: str) -> list[str]:
        """使用 spaCy 抽取名词

        Args:
            text: 输入文本

        Returns:
            名词列表
        """
        doc = self._nlp(text)

        nouns = []
        for token in doc:
            # NOUN: 普通名词, PROPN: 专有名词
            if token.pos_ == "NOUN" or (self.include_proper_nouns and token.pos_ == "PROPN"):
                # 使用词元形式（lemma）
                nouns.append(token.lemma_)

        # 去重并限制数量
        unique_nouns = list(dict.fromkeys(nouns))  # 保持顺序去重
        return unique_nouns[: self.max_nouns]

    def _extract_simple(self, text: str) -> list[str]:
        """简单的名词抽取

        使用启发式规则：
        - 单词首字母大写可能是专有名词
        - 常见名词后缀（-tion, -ness, -ment 等）

        Args:
            text: 输入文本

        Returns:
            名词列表
        """
        import re

        words = re.findall(r"\b\w+\b", text)

        nouns = []

        # 名词后缀模式
        noun_suffixes = [
            "tion",
            "sion",
            "ment",
            "ness",
            "ity",
            "ty",
            "ence",
            "ance",
            "er",
            "or",
            "ist",
            "ism",
            "ship",
            "hood",
            "dom",
        ]

        for word in words:
            word_lower = word.lower()

            # 专有名词（首字母大写）
            if self.include_proper_nouns and word[0].isupper() and len(word) > 1:
                nouns.append(word)
            # 名词后缀
            elif any(word_lower.endswith(suffix) for suffix in noun_suffixes):
                nouns.append(word_lower)

        # 去重并限制数量
        unique_nouns = list(dict.fromkeys(nouns))
        return unique_nouns[: self.max_nouns]
