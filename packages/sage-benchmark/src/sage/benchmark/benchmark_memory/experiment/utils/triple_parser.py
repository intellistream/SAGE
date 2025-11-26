"""三元组解析器 - 解析和重构三元组

可被多个模块复用，如 PreInsert、知识图谱模块等。
"""

from __future__ import annotations

import re


class TripleParser:
    """三元组解析器

    功能：
    - 解析 LLM 输出的三元组文本
    - 将三元组重构为自然语言描述

    使用示例：
        parser = TripleParser()
        triples = parser.parse("(Alice, knows, Bob)")
        descriptions = parser.refactor(triples)
    """

    def parse(self, triples_text: str) -> list[tuple[str, str, str]]:
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
            >>> parser = TripleParser()
            >>> parser.parse("(Alice, knows, Bob)\\n(Bob, likes, Python)")
            [("Alice", "knows", "Bob"), ("Bob", "likes", "Python")]

            >>> parser.parse("None")
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

            # 移除行首的编号格式，如 "(1) "、"(2) "、"1. "、"1) " 等
            line = re.sub(r'^\(\d+\)\s*', '', line)  # (1) 格式
            line = re.sub(r'^\d+\.\s*', '', line)    # 1. 格式
            line = re.sub(r'^\d+\)\s*', '', line)    # 1) 格式
            line = line.strip()

            # 解析形如 (Subject, Predicate, Object) 的格式
            if line.startswith("(") and line.endswith(")"):
                triple = self._parse_single(line)
                if triple:
                    triples.append(triple)

        return triples

    def refactor(self, triples: list[tuple[str, str, str]]) -> list[str]:
        """将三元组重构为自然语言描述

        Args:
            triples: 三元组列表 [(subject, predicate, object), ...]

        Returns:
            重构后的描述列表，每个三元组对应一条描述

        Examples:
            >>> parser = TripleParser()
            >>> triples = [("Alice", "knows", "Bob"), ("Bob", "likes", "Python")]
            >>> parser.refactor(triples)
            ["Alice knows Bob", "Bob likes Python"]
        """
        descriptions = []
        for subject, predicate, obj in triples:
            # 简单拼接：主语 + 谓语 + 宾语
            description = f"{subject} {predicate} {obj}"
            descriptions.append(description)
        return descriptions

    def parse_and_refactor(self, triples_text: str) -> tuple[list[tuple[str, str, str]], list[str]]:
        """解析三元组并同时生成重构描述

        Args:
            triples_text: LLM 生成的三元组文本

        Returns:
            (triples, descriptions) 元组：
            - triples: 三元组列表
            - descriptions: 重构后的描述列表

        Examples:
            >>> parser = TripleParser()
            >>> triples, descs = parser.parse_and_refactor("(Alice, knows, Bob)")
            >>> triples
            [("Alice", "knows", "Bob")]
            >>> descs
            ["Alice knows Bob"]
        """
        triples = self.parse(triples_text)
        descriptions = self.refactor(triples)
        return triples, descriptions

    def deduplicate(
        self, 
        triples: list[tuple[str, str, str]], 
        descriptions: list[str]
    ) -> tuple[list[tuple[str, str, str]], list[str]]:
        """基于描述去重三元组

        Args:
            triples: 三元组列表
            descriptions: 对应的描述列表

        Returns:
            (unique_triples, unique_descriptions) 去重后的结果

        Examples:
            >>> parser = TripleParser()
            >>> triples = [("A", "knows", "B"), ("A", "knows", "B")]
            >>> descs = ["A knows B", "A knows B"]
            >>> parser.deduplicate(triples, descs)
            ([("A", "knows", "B")], ["A knows B"])
        """
        seen = set()
        unique_triples = []
        unique_descriptions = []

        for triple, desc in zip(triples, descriptions):
            if desc not in seen:
                seen.add(desc)
                unique_triples.append(triple)
                unique_descriptions.append(desc)

        return unique_triples, unique_descriptions

    def _parse_single(self, line: str) -> tuple[str, str, str] | None:
        """解析单个三元组

        Args:
            line: 单行三元组文本，如 "(Subject, Predicate, Object)"

        Returns:
            三元组 (subject, predicate, object) 或 None（如果解析失败）
        """
        # 去掉括号
        content = line[1:-1]

        # 按逗号分割（注意：简单分割，不处理引号内的逗号）
        parts = [part.strip() for part in content.split(",")]

        # 必须是三个部分
        if len(parts) == 3:
            subject, predicate, obj = parts
            return (subject, predicate, obj)

        return None
