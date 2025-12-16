"""ExpandAction - 查询扩展策略

使用记忆体：
- MemGPT: hierarchical_memory，通过LLM扩展查询以覆盖更多相关记忆

特点：
- 使用LLM生成多个相关查询
- 支持多种合并策略（union, intersection）
- 可配置扩展数量
"""

from sage.benchmark.benchmark_memory.experiment.utils import LLMGenerator

from ..base import BasePreRetrievalAction, PreRetrievalInput, PreRetrievalOutput


class ExpandAction(BasePreRetrievalAction):
    """查询扩展Action

    使用LLM生成多个相关查询，以扩大检索范围。
    """

    def _init_action(self) -> None:
        """初始化查询扩展配置"""
        self.expand_prompt = self._get_config_value(
            "expand_prompt", required=True, context="optimize_type=expand"
        )

        self.expand_count = self._get_config_value(
            "expand_count", required=True, context="optimize_type=expand"
        )

        self.merge_strategy = self._get_config_value("merge_strategy", default="union")

        self.replace_original = self._get_config_value("replace_original", default=False)

        self.store_optimized = self._get_config_value("store_optimized", default=True)

        # LLM生成器将由PreRetrieval主类提供
        self._llm_generator = None

    def set_llm_generator(self, generator: LLMGenerator) -> None:
        """设置LLM生成器（由PreRetrieval主类调用）"""
        self._llm_generator = generator

    def execute(self, input_data: PreRetrievalInput) -> PreRetrievalOutput:
        """扩展查询

        Args:
            input_data: 输入数据

        Returns:
            包含扩展查询的输出数据

        Raises:
            RuntimeError: LLM生成器未设置
        """
        if self._llm_generator is None:
            raise RuntimeError("LLM generator not set. Call set_llm_generator first.")

        question = input_data.question

        # 使用LLM生成扩展查询
        prompt = self.expand_prompt.format(question=question, expand_count=self.expand_count)
        response = self._llm_generator.generate(prompt)

        # 解析扩展查询（假设LLM返回换行分隔的查询列表）
        expanded_queries = [q.strip() for q in response.split("\n") if q.strip()]
        expanded_queries = expanded_queries[: self.expand_count]

        # 根据配置决定最终查询
        if self.replace_original:
            # 使用扩展查询替换原查询
            final_query = " | ".join(expanded_queries)
        else:
            # 保留原查询并添加扩展
            final_query = question

        # 构建元数据
        metadata = {
            "original_query": question,
            "expanded_queries": expanded_queries,
            "merge_strategy": self.merge_strategy,
            "needs_embedding": True,
        }

        # 如果配置了store_optimized，将扩展查询存储到metadata
        if self.store_optimized:
            metadata["optimized_queries"] = expanded_queries

        return PreRetrievalOutput(
            query=final_query,
            query_embedding=None,  # 由外部统一生成
            metadata=metadata,
            retrieve_mode="passive",
            retrieve_params={
                "multi_query": expanded_queries if not self.replace_original else None,
                "merge_strategy": self.merge_strategy,
            },
        )
