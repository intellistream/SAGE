"""Multi Query Merge - 多查询合并

使用场景: MemGPT

功能: 执行多个相关查询并合并结果
"""

from typing import Any, Optional

from ..base import BasePostRetrievalAction, MemoryItem, PostRetrievalInput, PostRetrievalOutput


class MultiQueryMergeAction(BasePostRetrievalAction):
    """多查询合并策略

    生成多个相关查询（如改写、扩展），分别检索后合并结果。
    """

    def _init_action(self) -> None:
        """初始化配置"""
        self.num_queries = self.config.get("num_queries", 3)
        self.merge_strategy = self.config.get("merge_strategy", "union")  # union, intersection
        self.dedup = self.config.get("dedup", True)

    def execute(
        self,
        input_data: PostRetrievalInput,
        service: Any,
        llm: Optional[Any] = None,
    ) -> PostRetrievalOutput:
        """执行多查询合并

        Args:
            input_data: 输入数据
            service: 记忆服务代理
            llm: LLM 生成器（用于生成改写查询）

        Returns:
            PostRetrievalOutput: 合并后的结果
        """
        memory_data = input_data.data.get("memory_data", [])
        original_items = self._convert_to_items(memory_data)

        if service is None or llm is None:
            # 如果没有服务或 LLM，返回原始结果
            return PostRetrievalOutput(
                memory_items=original_items,
                metadata={
                    "action": "merge.multi_query",
                    "warning": "No service or LLM available",
                },
            )

        question = input_data.data.get("question", "")
        if not question:
            return PostRetrievalOutput(
                memory_items=original_items,
                metadata={"action": "merge.multi_query", "warning": "No question provided"},
            )

        # 生成多个查询变体
        queries = self._generate_queries(question, llm)

        # 对每个查询执行检索
        all_results = [original_items]  # 包含原始结果

        for query in queries:
            try:
                results = self._retrieve_with_query(query, service, input_data)
                all_results.append(results)
            except Exception:  # noqa: BLE001
                # 如果单个查询失败，跳过
                continue

        # 合并所有结果
        merged_items = self._merge_all_results(all_results)

        return PostRetrievalOutput(
            memory_items=merged_items,
            metadata={
                "action": "merge.multi_query",
                "num_queries": len(queries),
                "merge_strategy": self.merge_strategy,
                "total_results": len(merged_items),
            },
        )

    def _generate_queries(self, question: str, llm: Any) -> list[str]:
        """生成多个查询变体

        Args:
            question: 原始问题
            llm: LLM 实例

        Returns:
            查询列表（不包含原始问题）
        """
        queries = []

        # 使用 LLM 生成查询改写
        try:
            prompt = f"""Generate {self.num_queries - 1} different ways to ask the following question:

Question: {question}

Requirements:
- Each variant should have the same meaning but different wording
- Focus on different aspects or perspectives
- Keep them concise and clear

Output format (one per line):
1. [variant 1]
2. [variant 2]
..."""

            response = llm.generate(prompt)

            # 解析响应
            lines = response.strip().split("\n")
            for line in lines:
                # 去掉编号
                line = line.strip()
                if line and (line[0].isdigit() or line.startswith("-") or line.startswith("*")):
                    # 去掉前缀
                    parts = line.split(".", 1)
                    if len(parts) > 1:
                        query = parts[1].strip()
                        queries.append(query)

            # 限制数量
            queries = queries[: self.num_queries - 1]
        except Exception:  # noqa: BLE001
            # 如果生成失败，返回空列表
            pass

        return queries

    def _retrieve_with_query(
        self, query: str, service: Any, input_data: PostRetrievalInput
    ) -> list[MemoryItem]:
        """使用给定查询检索记忆

        Args:
            query: 查询文本
            service: 记忆服务
            input_data: 原始输入数据

        Returns:
            检索结果列表
        """
        # TODO: 调用服务检索
        # 需要服务提供 retrieve 方法
        # 当前简化为返回空列表
        return []

    def _merge_all_results(self, all_results: list[list[MemoryItem]]) -> list[MemoryItem]:
        """合并所有查询的结果

        Args:
            all_results: 所有查询结果的列表

        Returns:
            合并后的结果
        """
        if self.merge_strategy == "union":
            return self._merge_union(all_results)
        elif self.merge_strategy == "intersection":
            return self._merge_intersection(all_results)
        else:
            # 默认使用 union
            return self._merge_union(all_results)

    def _merge_union(self, all_results: list[list[MemoryItem]]) -> list[MemoryItem]:
        """Union 合并策略

        Args:
            all_results: 所有查询结果

        Returns:
            合并后的结果（去重）
        """
        if not self.dedup:
            # 不去重，直接拼接
            merged = []
            for results in all_results:
                merged.extend(results)
            return merged

        # 去重（基于 text）
        seen_texts = set()
        merged = []

        for results in all_results:
            for item in results:
                if item.text not in seen_texts:
                    merged.append(item)
                    seen_texts.add(item.text)

        return merged

    def _merge_intersection(self, all_results: list[list[MemoryItem]]) -> list[MemoryItem]:
        """Intersection 合并策略

        Args:
            all_results: 所有查询结果

        Returns:
            交集结果
        """
        if not all_results:
            return []

        # 提取第一个查询的文本集合
        intersection = {item.text for item in all_results[0]}

        # 与后续查询的结果求交集
        for results in all_results[1:]:
            result_texts = {item.text for item in results}
            intersection &= result_texts

        # 构建最终结果（保持第一个查询的顺序）
        merged = []
        for item in all_results[0]:
            if item.text in intersection:
                merged.append(item)

        return merged
