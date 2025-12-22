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
        # Embedding生成器将由operator通过set_embedding_generator传入
        self._embedding_generator = None

    def set_llm_generator(self, generator: LLMGenerator) -> None:
        """设置LLM生成器（由PreRetrieval主类调用）"""
        self._llm_generator = generator

    def set_embedding_generator(self, generator) -> None:
        """设置Embedding生成器（由PreRetrieval主类调用）"""
        self._embedding_generator = generator

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

        # 解析扩展查询（过滤掉说明文字和格式标记）
        lines = response.split("\n")
        expanded_queries = []
        for line in lines:
            line = line.strip()
            # 跳过空行、代码块标记、说明性文字
            if not line:
                continue
            if line.startswith("```"):
                continue
            if line in ["[", "]", "{", "}"]:
                continue
            # 过滤说明性文字（不以问号结尾的长句）
            if any(
                keyword in line.lower()
                for keyword in [
                    "related queries",
                    "here are",
                    "this query explores",
                    "this focuses on",
                    "query explores",
                    "query focuses",
                ]
            ):
                continue
            # 移除列表编号和格式标记
            import re

            line = re.sub(r"^[\d\-\*]+[\.)\]\s]+", "", line)  # 1. 2) 3] - *
            line = re.sub(
                r"^\*\*Query\s+\d+:?\s*[\"\']?", "", line, flags=re.IGNORECASE
            )  # **Query 1: "
            line = re.sub(r"[\"\']\*\*$", "", line)  # 结尾的 "**
            line = re.sub(r'^["\']|["\']$', "", line)  # 引号
            line = line.strip()

            # 只保留长度 > 15 且以问号结尾的有效查询
            if line and len(line) > 15 and line.endswith("?"):
                expanded_queries.append(line)

        expanded_queries = expanded_queries[: self.expand_count]

        # 添加调试输出
        print("\n📝 LLM 扩展查询生成:")
        print(f"  原始查询: {question}")
        print(f"  LLM 响应长度: {len(response)} 字符")
        print(f"  解析出 {len(expanded_queries)} 个扩展查询:")
        for idx, eq in enumerate(expanded_queries, 1):
            print(f"    {idx}. {eq}")

        # 根据配置决定最终查询
        if self.replace_original:
            # 使用扩展查询替换原查询
            final_query = " | ".join(expanded_queries) if expanded_queries else question
            queries_for_retrieval = expanded_queries if expanded_queries else [question]
        else:
            # 保留原查询并添加扩展
            final_query = question
            # 将原查询作为第一个查询，扩展查询跟在后面
            queries_for_retrieval = (
                [question] + expanded_queries if expanded_queries else [question]
            )

        # 为所有查询批量生成 embedding（包括原查询）
        all_embeddings = []
        if (
            queries_for_retrieval
            and self._embedding_generator
            and self._embedding_generator.is_available()
        ):
            print(f"\n🔄 开始批量生成 {len(queries_for_retrieval)} 个查询的 embedding...")
            try:
                all_embeddings = self._embedding_generator.embed_batch(queries_for_retrieval)
                if all_embeddings:
                    for idx, (eq, emb) in enumerate(zip(queries_for_retrieval, all_embeddings), 1):
                        query_type = (
                            "原始查询"
                            if (not self.replace_original and idx == 1)
                            else f"扩展查询 {idx if self.replace_original else idx - 1}"
                        )
                        if emb:
                            print(f"  ✓ {query_type}: {eq[:50]}... (维度: {len(emb)})")
                        else:
                            print(f"  ✗ {query_type}: embedding 生成失败")
                else:
                    print("  ⚠️  embed_batch 返回 None")
                    all_embeddings = [None] * len(queries_for_retrieval)
            except Exception as e:
                print(f"  ✗ 批量 embedding 生成失败: {e}")
                import traceback

                traceback.print_exc()
                all_embeddings = [None] * len(queries_for_retrieval)
        else:
            if not self._embedding_generator:
                print("⚠️  未初始化 EmbeddingGenerator，查询将无 embedding")
            elif not self._embedding_generator.is_available():
                print("⚠️  EmbeddingGenerator 不可用，查询将无 embedding")
            all_embeddings = [None] * len(queries_for_retrieval)

        # 构建元数据
        metadata = {
            "original_query": question,
            "expanded_queries": expanded_queries,
            "all_queries": queries_for_retrieval,
            "all_embeddings": all_embeddings,
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
                "multi_query": queries_for_retrieval if len(queries_for_retrieval) > 1 else None,
                "expanded_embeddings": all_embeddings,
                "merge_strategy": self.merge_strategy,
            },
        )
