"""RewriteAction - 查询改写策略

使用记忆体：
- MemGPT: hierarchical_memory，通过LLM改写查询以提高检索准确性

特点：
- 使用LLM重新表达查询
- 保留原始语义但优化表达
- 可配置是否替换原查询
"""

from sage.benchmark.benchmark_memory.experiment.utils import LLMGenerator

from ..base import BasePreRetrievalAction, PreRetrievalInput, PreRetrievalOutput


class RewriteAction(BasePreRetrievalAction):
    """查询改写Action

    使用LLM改写查询，以提高检索效果。
    """

    def _init_action(self) -> None:
        """初始化查询改写配置"""
        self.rewrite_prompt = self._get_config_value(
            "rewrite_prompt", required=True, context="optimize_type=rewrite"
        )

        self.replace_original = self._get_config_value("replace_original", default=False)

        self.store_optimized = self._get_config_value("store_optimized", default=True)

        # LLM生成器将由PreRetrieval主类提供
        self._llm_generator = None

    def set_llm_generator(self, generator: LLMGenerator) -> None:
        """设置LLM生成器（由PreRetrieval主类调用）"""
        self._llm_generator = generator

    def execute(self, input_data: PreRetrievalInput) -> PreRetrievalOutput:
        """改写查询

        Args:
            input_data: 输入数据

        Returns:
            包含改写查询的输出数据

        Raises:
            RuntimeError: LLM生成器未设置
        """
        if self._llm_generator is None:
            raise RuntimeError("LLM generator not set. Call set_llm_generator first.")

        question = input_data.question

        # 使用LLM改写查询
        prompt = self.rewrite_prompt.format(question=question)
        rewritten_query = self._llm_generator.generate(prompt).strip()

        # 根据配置决定最终查询
        if self.replace_original:
            final_query = rewritten_query
        else:
            final_query = question

        # 构建元数据
        metadata = {
            "original_query": question,
            "rewritten_query": rewritten_query,
            "needs_embedding": True,
        }

        # 如果配置了store_optimized，存储改写后的查询
        if self.store_optimized:
            metadata["optimized_query"] = rewritten_query

        return PreRetrievalOutput(
            query=final_query,
            query_embedding=None,  # 由外部统一生成
            metadata=metadata,
            retrieve_mode="passive",
        )
