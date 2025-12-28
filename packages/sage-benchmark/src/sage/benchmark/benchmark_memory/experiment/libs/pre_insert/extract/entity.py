"""EntityExtractAction - 实体抽取策略

从文本中抽取命名实体（人名、地名、组织等）。
适用于 Mem0, Mem0ᵍ 等需要实体识别的记忆体。
"""

from ..base import BasePreInsertAction, PreInsertInput, PreInsertOutput


class EntityExtractAction(BasePreInsertAction):
    """实体抽取 Action

    使用场景：
    - Mem0: 抽取实体建立知识图谱
    - Mem0ᵍ: 基于实体的记忆索引

    支持的抽取方法：
    - spacy: 使用 spaCy NER
    - simple: 简单的启发式方法
    """

    def _init_action(self) -> None:
        """初始化实体抽取工具"""
        self.method = self.config.get("method", "simple")
        self.entity_types = self.config.get(
            "entity_types", ["PERSON", "ORG", "GPE", "LOC", "DATE", "TIME"]
        )

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
        """执行实体抽取

        Args:
            input_data: 包含 dialogs 的输入数据

        Returns:
            包含实体信息的记忆条目
        """
        # 提取并格式化对话
        dialogs = input_data.data.get("dialogs", [])
        text = self._format_dialogue(dialogs)

        # 抽取实体
        entities = self._extract_entities(text)

        # 创建记忆条目
        entry = {
            "text": text,
            "entities": entities,
            "metadata": {
                "action": "extract.entity",
                "entity_count": len(entities),
                "method": self.method,
                "entity_types": self.entity_types,
            },
        }
        entry = self._set_default_fields(entry)
        entry["insert_method"] = "entity_insert"

        return PreInsertOutput(
            memory_entries=[entry],
            metadata={
                "entities": entities,
                "method": self.method,
            },
        )

    def _extract_entities(self, text: str) -> list[dict[str, str]]:
        """抽取实体

        Args:
            text: 输入文本

        Returns:
            实体列表，每个实体包含 text, type, start, end
        """
        if self.method == "spacy" and self._nlp:
            return self._extract_by_spacy(text)
        else:
            return self._extract_simple(text)

    def _extract_by_spacy(self, text: str) -> list[dict[str, str]]:
        """使用 spaCy 抽取实体

        Args:
            text: 输入文本

        Returns:
            实体列表
        """
        doc = self._nlp(text)

        entities = []
        for ent in doc.ents:
            if ent.label_ in self.entity_types:
                entities.append(
                    {
                        "text": ent.text,
                        "type": ent.label_,
                        "start": ent.start_char,
                        "end": ent.end_char,
                    }
                )

        return entities

    def _extract_simple(self, text: str) -> list[dict[str, str]]:
        """简单的实体抽取（基于启发式规则）

        识别大写开头的词作为可能的实体。

        Args:
            text: 输入文本

        Returns:
            实体列表
        """
        import re

        # 匹配连续大写单词（可能是人名、地名等）
        pattern = r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b"
        matches = re.finditer(pattern, text)

        entities = []
        for match in matches:
            entities.append(
                {
                    "text": match.group(),
                    "type": "UNKNOWN",  # 简单方法无法判断类型
                    "start": match.start(),
                    "end": match.end(),
                }
            )

        # 去重
        seen = set()
        unique_entities = []
        for ent in entities:
            if ent["text"] not in seen:
                seen.add(ent["text"])
                unique_entities.append(ent)

        return unique_entities
