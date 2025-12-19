"""DecomposeAction - 查询分解策略

使用场景：
- 复杂多步查询分解为子查询
- 支持LLM、规则、混合三种分解策略

特点：
- 生成多个独立的子查询
- 每个子查询可并行或顺序检索
- 支持自定义分解规则
"""

import json
import re
from typing import Any

from sage.benchmark.benchmark_memory.experiment.utils import LLMGenerator

from ..base import BasePreRetrievalAction, PreRetrievalInput, PreRetrievalOutput


class DecomposeAction(BasePreRetrievalAction):
    """查询分解Action

    将复杂查询分解为多个简单子查询，支持独立检索。
    """

    def _init_action(self) -> None:
        """初始化查询分解配置"""
        self.decompose_strategy = self._get_config_value(
            "decompose_strategy", required=True, context="action=enhancement.decompose"
        )

        self.max_sub_queries = self._get_config_value(
            "max_sub_queries", default=5, context="action=enhancement.decompose"
        )

        self.sub_query_action = self._get_config_value("sub_query_action", default="parallel")

        self.embed_sub_queries = self._get_config_value("embed_sub_queries", default=False)

        # 初始化 Embedding 生成器（用于子查询向量化）
        from sage.benchmark.benchmark_memory.experiment.utils import EmbeddingGenerator

        self._embedding_generator = EmbeddingGenerator.from_config(self.config)

        # LLM分解配置
        if self.decompose_strategy in ["llm", "hybrid"]:
            self.decompose_prompt = self._get_config_value(
                "decompose_prompt",
                default="""Break down this complex question into simpler sub-questions that can be answered independently.
Each sub-question should be self-contained and searchable.

Question: {query}

Return a JSON array of sub-questions. Example: ["sub-question 1", "sub-question 2"]
Sub-questions:""",
            )

        # 规则分解配置
        if self.decompose_strategy in ["rule", "hybrid"]:
            self.split_keywords = self._get_config_value(
                "split_keywords",
                default=["and", "or", "also", "additionally", "moreover", "furthermore", "besides"],
            )

        # LLM生成器将由PreRetrieval主类提供
        self._llm_generator = None

    def set_llm_generator(self, generator: LLMGenerator) -> None:
        """设置LLM生成器（由PreRetrieval主类调用）"""
        self._llm_generator = generator

    def execute(self, input_data: PreRetrievalInput) -> PreRetrievalOutput:
        """分解查询

        Args:
            input_data: 输入数据

        Returns:
            包含子查询列表的输出数据
        """
        question = input_data.question

        if not question:
            return PreRetrievalOutput(
                query=question,
                metadata={"sub_queries": [], "decompose_strategy": self.decompose_strategy},
            )

        # 根据策略分解查询
        sub_queries = self._decompose(question)

        # 限制子查询数量
        sub_queries = sub_queries[: self.max_sub_queries]

        # 如果没有成功分解，使用原查询
        if not sub_queries:
            sub_queries = [question]

        # 为子查询生成 embedding
        sub_query_embeddings = []
        if self._embedding_generator:
            print(f"\n🔄 开始为 {len(sub_queries)} 个子查询生成 embedding...")
            for idx, sq in enumerate(sub_queries, 1):
                try:
                    embedding = self._embedding_generator.embed(sq)
                    sub_query_embeddings.append(embedding)
                    print(f"  ✓ 子查询 {idx}: {sq[:50]}... (维度: {len(embedding)})")
                except Exception as e:
                    print(f"  ✗ 子查询 {idx} embedding 生成失败: {e}")
                    sub_query_embeddings.append(None)
        else:
            print("⚠️  未初始化 EmbeddingGenerator，子查询将无 embedding")
            sub_query_embeddings = [None] * len(sub_queries)

        # ============ DEBUG: 分解后打印 ============
        print("\n" + "=" * 80)
        print("🔍 [DecomposeAction] 查询分解结果")
        print("=" * 80)
        print(f"原始查询: {question}")
        print(f"\n分解策略: {self.decompose_strategy}")
        print(f"子查询数量: {len(sub_queries)}")
        for idx, sq in enumerate(sub_queries, 1):
            emb_status = "✓" if sub_query_embeddings[idx - 1] is not None else "✗"
            print(f"  {idx}. {emb_status} {sq}")
        print("\n" + "=" * 80)
        # ============ DEBUG END ============

        # 构建元数据
        metadata: dict[str, Any] = {
            "original_query": question,
            "sub_queries": sub_queries,
            "sub_query_embeddings": sub_query_embeddings,
            "sub_query_action": self.sub_query_action,
            "decompose_strategy": self.decompose_strategy,
            "needs_embedding": self.embed_sub_queries,
        }

        # 使用第一个子查询作为主查询，其他作为元数据
        return PreRetrievalOutput(
            query=sub_queries[0] if len(sub_queries) == 1 else question,
            query_embedding=None,
            metadata=metadata,
            retrieve_mode="active",
            retrieve_params={
                "sub_queries": sub_queries,
                "sub_query_embeddings": sub_query_embeddings,
                "action": self.sub_query_action,
            },
        )

    def _decompose(self, question: str) -> list[str]:
        """执行查询分解"""
        if self.decompose_strategy == "llm":
            return self._decompose_llm(question)
        elif self.decompose_strategy == "rule":
            return self._decompose_rule(question)
        elif self.decompose_strategy == "hybrid":
            # 先尝试规则，失败则用LLM
            sub_queries = self._decompose_rule(question)
            if len(sub_queries) <= 1:
                sub_queries = self._decompose_llm(question)
            return sub_queries
        else:
            return [question]

    def _decompose_llm(self, question: str) -> list[str]:
        """使用LLM分解查询"""
        if self._llm_generator is None:
            return [question]

        prompt = self.decompose_prompt.format(query=question)

        try:
            result = self._llm_generator.generate(prompt, max_tokens=500, temperature=0.5)

            # 尝试解析JSON数组
            try:
                match = re.search(r"\[.*?\]", result, re.DOTALL)
                if match:
                    parsed_queries = json.loads(match.group())
                    if isinstance(parsed_queries, list):
                        return [q for q in parsed_queries if isinstance(q, str) and q.strip()]
            except json.JSONDecodeError:
                pass

            # 解析失败，尝试按行解析
            lines = result.strip().split("\n")
            parsed_lines = []
            for line in lines:
                # 移除序号
                line = line.strip().lstrip("0123456789.-) ")
                # 过滤条件：
                # 1. 非空
                # 2. 不是JSON标记
                # 3. 不包含'decompose', 'break down', 'following'等说明性词汇
                # 4. 必须以疑问词开头或以问号结尾（是真正的问题）
                if (
                    line
                    and not line.startswith("[")
                    and not line.endswith("]")
                    and not any(
                        word in line.lower()
                        for word in [
                            "to decompose",
                            "break down",
                            "can break",
                            "following",
                            "sub-questions:",
                        ]
                    )
                    and (
                        line.endswith("?")
                        or any(
                            line.lower().startswith(q)
                            for q in [
                                "who",
                                "what",
                                "when",
                                "where",
                                "why",
                                "how",
                                "is",
                                "are",
                                "was",
                                "were",
                                "did",
                                "does",
                                "do",
                                "can",
                                "could",
                                "will",
                                "would",
                            ]
                        )
                    )
                ):
                    parsed_lines.append(line)

            return parsed_lines if parsed_lines else [question]

        except Exception as e:
            print(f"[WARNING] LLM decompose failed: {e}")
            return [question]

    def _decompose_rule(self, question: str) -> list[str]:
        """使用规则分解查询"""
        # 构建分词模式
        pattern = r"\b(?:" + "|".join(re.escape(kw) for kw in self.split_keywords) + r")\b"

        # 分割查询
        parts = re.split(pattern, question, flags=re.IGNORECASE)

        # 清理并过滤
        parsed_parts = [p.strip() for p in parts if p.strip()]

        # 如果成功分割（至少2个部分），返回结果
        if len(parsed_parts) > 1:
            return parsed_parts

        # 否则返回原查询
        return [question]
