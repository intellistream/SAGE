"""预插入解析器 - 负责对话格式化、三元组提取和 Embedding

参考 data_parser.py 的设计模式，将 PreInsert 中可重用的逻辑抽取出来
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sage.benchmark.benchmark_memory.experiment.utils.embedding_generator import (
        EmbeddingGenerator,
    )
    from sage.benchmark.benchmark_memory.experiment.utils.llm_generator import LLMGenerator


class PreInsertParser:
    """预插入解析器

    功能：
    1. 格式化对话内容为字符串
    2. 解析 LLM 输出的三元组
    3. 提供统一的数据处理接口

    使用示例：
        parser = PreInsertParser()
        dialogue = parser.format_dialogue(data)
        triples = parser.parse_triples(triples_text)
    """

    def __init__(self):
        """初始化解析器
        
        无需配置参数，直接使用固定的解析逻辑
        """
        pass

    def format_dialogue(self, dialogs: list[dict]) -> str:
        """格式化对话列表为字符串

        Args:
            dialogs: 对话列表，来自 dataloader.get_dialog()，格式为：
                [
                    {"speaker": "xxx", "text": "xxx", "date_time": "xxx"},
                    {"speaker": "xxx", "text": "xxx", "date_time": "xxx"}  # 可能只有1句
                ]

        Returns:
            格式化后的对话字符串，每行为 "speaker: text"

        Examples:
            >>> dialogs = [
            ...     {"speaker": "Alice", "text": "Hello", "date_time": "2023-01-01"},
            ...     {"speaker": "Bob", "text": "Hi there", "date_time": "2023-01-01"}
            ... ]
            >>> parser.format_dialogue(dialogs)
            'Alice: Hello\\nBob: Hi there'
        """
        if not dialogs:
            return ""

        lines = []
        for dialog in dialogs:
            speaker = dialog.get("speaker", "Unknown")
            text = dialog.get("text", "")
            lines.append(f"{speaker}: {text}")
        
        return "\n".join(lines)

    def parse_triples(self, triples_text: str) -> list[tuple[str, str, str]]:
        """解析 LLM 输出的三元组文本

        Args:
            triples_text: LLM 生成的三元组文本，格式如：
                (Subject, Predicate, Object)
                (Subject, Predicate, Object)
                或者 "None"

        Returns:
            三元组列表，每个三元组是 (subject, predicate, object) 的元组
            如果输入是 "None" 或解析失败，返回空列表

        Examples:
            >>> text = "(Alice, knows, Bob)\\n(Bob, likes, Python)"
            >>> parser.parse_triples(text)
            [("Alice", "knows", "Bob"), ("Bob", "likes", "Python")]

            >>> parser.parse_triples("None")
            []
        """
        triples = []

        # 如果输出是 "None"，返回空列表
        if triples_text.strip().lower() == "none":
            return triples

        # 按行分割并解析每个三元组
        lines = triples_text.strip().split("\n")
        for line in lines:
            line = line.strip()

            # 跳过空行和注释
            if not line or line.startswith("#"):
                continue

            # 解析形如 (Subject, Predicate, Object) 的格式
            if line.startswith("(") and line.endswith(")"):
                triple = self._parse_single_triple(line)
                if triple:
                    triples.append(triple)

        return triples

    def refactor_triples(self, triples: list[tuple[str, str, str]]) -> list[str]:
        """将三元组重构为自然语言描述

        Args:
            triples: 三元组列表 [(subject, predicate, object), ...]

        Returns:
            重构后的描述列表，每个三元组对应一条描述

        Examples:
            >>> triples = [("Alice", "knows", "Bob"), ("Bob", "likes", "Python")]
            >>> parser.refactor_triples(triples)
            ["Alice knows Bob", "Bob likes Python"]
        """
        descriptions = []
        for subject, predicate, obj in triples:
            # 简单拼接：主语 + 谓语 + 宾语
            description = f"{subject} {predicate} {obj}"
            descriptions.append(description)
        return descriptions

    def _parse_single_triple(self, line: str) -> tuple[str, str, str] | None:
        """解析单个三元组

        Args:
            line: 单行三元组文本，如 "(Subject, Predicate, Object)"

        Returns:
            三元组 (subject, predicate, object) 或 None（如果解析失败）
        """
        # 去掉括号
        content = line[1:-1]

        # 按逗号分割（注意可能有逗号在引号内）
        parts = [part.strip() for part in content.split(",")]

        # 必须是三个部分
        if len(parts) == 3:
            subject, predicate, obj = parts
            return (subject, predicate, obj)

        return None

    @staticmethod
    def validate_dialogue(data: dict) -> bool:
        """验证对话数据格式是否有效

        Args:
            data: 对话数据

        Returns:
            True 如果数据有效，False 否则
        """
        if not isinstance(data, dict):
            return False

        # 检查是否包含任何对话相关字段
        return any(field in data for field in PreInsertParser.DIALOGUE_FIELDS)

    @staticmethod
    def get_supported_operations() -> list[str]:
        """获取支持的操作列表

        Returns:
            支持的操作名称列表
        """
        return list(PreInsertParser.EXTRACT_OPERATIONS.keys())
