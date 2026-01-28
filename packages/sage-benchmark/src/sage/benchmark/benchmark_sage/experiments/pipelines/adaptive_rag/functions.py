"""
Adaptive-RAG Strategy Functions - 自适应 RAG 策略函数

基于 SAGE 的 MapFunction 实现三种 RAG 策略:
1. NoRetrievalFunction (A): LLM 直接回答
2. SingleRetrieverFunction (B): 单步检索 + LLM
3. IterativeRetrieverFunction (C): 多跳迭代检索 (IRCoT style)

以及自适应路由函数:
- AdaptiveRouterFunction: 根据分类结果路由到对应策略
"""

from abc import abstractmethod
from dataclasses import dataclass, field
from typing import Any

from sage.common.core import MapFunction

# 支持直接运行和模块运行两种方式
try:
    from .classifier import (
        ClassificationResult,
        QueryComplexityClassifier,
        QueryComplexityLevel,
        create_classifier,
    )
except ImportError:
    from classifier import (
        ClassificationResult,
        QueryComplexityClassifier,
        QueryComplexityLevel,
        create_classifier,
    )


@dataclass
class RAGInput:
    """RAG 输入"""

    query: str
    context: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RAGOutput:
    """RAG 输出"""

    query: str
    answer: str
    strategy: str  # 使用的策略
    retrieved_docs: list[dict[str, Any]] = field(default_factory=list)
    reasoning_chain: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseRAGStrategyFunction(MapFunction):
    """RAG 策略函数基类"""

    strategy_name: str = "base"

    def __init__(
        self,
        llm_client: Any = None,
        retriever: Any = None,
        config: dict[str, Any] | None = None,
    ):
        super().__init__()
        self.llm_client = llm_client
        self.retriever = retriever
        self.config = config or {}

    def _get_llm_client(self):
        """获取 LLM 客户端（延迟初始化）"""
        if self.llm_client is None:
            try:
                from sage.common.components.sage_llm import UnifiedInferenceClient

                self.llm_client = UnifiedInferenceClient.create()
            except ImportError:
                raise RuntimeError("LLM client not available")
        return self.llm_client

    def _get_retriever(self):
        """获取检索器（延迟初始化）"""
        if self.retriever is None:
            try:
                # 尝试使用 SAGE 的默认检索器
                from sage.middleware.operators.rag import ChromaRetriever

                self.retriever = ChromaRetriever(config=self.config.get("retriever", {}))
            except ImportError:
                # 使用简单的模拟检索器
                self.retriever = SimpleRetriever()
        return self.retriever

    @abstractmethod
    def execute(self, data: Any) -> RAGOutput:
        """执行策略"""
        pass

    def _extract_query(self, data: Any) -> str:
        """从输入数据中提取查询"""
        if isinstance(data, str):
            return data
        elif isinstance(data, dict):
            return data.get("query", data.get("question", str(data)))
        elif isinstance(data, RAGInput):
            return data.query
        else:
            return str(data)


class NoRetrievalFunction(BaseRAGStrategyFunction):
    """
    无检索策略 (Level A / ZERO)

    直接使用 LLM 回答简单问题，不进行任何检索。
    适用于:
    - 定义类问题
    - 常识类问题
    - LLM 知识库内的事实问题
    """

    strategy_name = "no_retrieval"

    PROMPT_TEMPLATE = """Answer the following question concisely and accurately.

Question: {query}

Answer:"""

    def execute(self, data: Any) -> RAGOutput:
        """直接使用 LLM 回答"""
        query = self._extract_query(data)
        llm = self._get_llm_client()

        prompt = self.PROMPT_TEMPLATE.format(query=query)

        try:
            response = llm.chat(prompt)
            answer = response if isinstance(response, str) else response.content
        except Exception as e:
            answer = f"Error generating answer: {e}"

        return RAGOutput(
            query=query,
            answer=answer.strip(),
            strategy=self.strategy_name,
            retrieved_docs=[],
            reasoning_chain=[f"Direct LLM response for simple query"],
            metadata={"prompt": prompt},
        )


class SingleRetrieverFunction(BaseRAGStrategyFunction):
    """
    单步检索策略 (Level B / SINGLE)

    执行一次检索，然后基于检索结果生成回答。
    适用于:
    - 需要最新信息的问题
    - 特定领域知识问题
    - 需要事实支撑的问题
    """

    strategy_name = "single_retrieval"

    PROMPT_TEMPLATE = """Answer the question based on the provided context.

Context:
{context}

Question: {query}

Answer based on the context above:"""

    def __init__(
        self,
        llm_client: Any = None,
        retriever: Any = None,
        config: dict[str, Any] | None = None,
        top_k: int = 5,
    ):
        super().__init__(llm_client, retriever, config)
        self.top_k = top_k

    def execute(self, data: Any) -> RAGOutput:
        """单步检索并回答"""
        query = self._extract_query(data)
        retriever = self._get_retriever()
        llm = self._get_llm_client()

        # 检索相关文档
        try:
            docs = retriever.retrieve(query, top_k=self.top_k)
            if isinstance(docs, list):
                retrieved_docs = [
                    {"content": d.get("content", str(d)), "score": d.get("score", 0.0)}
                    if isinstance(d, dict)
                    else {"content": str(d), "score": 0.0}
                    for d in docs
                ]
            else:
                retrieved_docs = [{"content": str(docs), "score": 0.0}]
        except Exception as e:
            retrieved_docs = []
            self.logger.warning(f"Retrieval failed: {e}")

        # 构建上下文
        context = "\n\n".join([f"[Doc {i+1}]: {d['content']}" for i, d in enumerate(retrieved_docs)])
        if not context:
            context = "No relevant documents found."

        # 生成回答
        prompt = self.PROMPT_TEMPLATE.format(context=context, query=query)

        try:
            response = llm.chat(prompt)
            answer = response if isinstance(response, str) else response.content
        except Exception as e:
            answer = f"Error generating answer: {e}"

        return RAGOutput(
            query=query,
            answer=answer.strip(),
            strategy=self.strategy_name,
            retrieved_docs=retrieved_docs,
            reasoning_chain=[
                f"Retrieved {len(retrieved_docs)} documents",
                "Generated answer based on retrieved context",
            ],
            metadata={"prompt": prompt, "top_k": self.top_k},
        )


class IterativeRetrieverFunction(BaseRAGStrategyFunction):
    """
    多跳迭代检索策略 (Level C / MULTI)

    使用 IRCoT (Interleaving Retrieval with Chain-of-Thought) 风格的迭代检索。

    流程:
    1. 分解问题为子问题
    2. 对每个子问题进行检索
    3. 基于检索结果和推理链进行下一步
    4. 汇总所有信息生成最终答案

    适用于:
    - 多实体比较问题
    - 需要推理链的复杂问题
    - 多跳问答
    """

    strategy_name = "iterative_retrieval"

    DECOMPOSITION_PROMPT = """Break down this complex question into simpler sub-questions.

Question: {query}

List 2-4 sub-questions that need to be answered to fully answer the main question:
1."""

    COT_PROMPT = """Based on the context and previous reasoning, continue answering.

Original Question: {query}

Previous Context and Reasoning:
{previous_reasoning}

New Retrieved Information:
{new_context}

Current Sub-question: {sub_question}

Continue reasoning (be concise):"""

    FINAL_PROMPT = """Synthesize all the information to answer the original question.

Original Question: {query}

Collected Information and Reasoning:
{reasoning_chain}

Final Answer:"""

    def __init__(
        self,
        llm_client: Any = None,
        retriever: Any = None,
        config: dict[str, Any] | None = None,
        max_iterations: int = 3,
        top_k_per_step: int = 3,
    ):
        super().__init__(llm_client, retriever, config)
        self.max_iterations = max_iterations
        self.top_k_per_step = top_k_per_step

    def execute(self, data: Any) -> RAGOutput:
        """多跳迭代检索并回答"""
        query = self._extract_query(data)
        retriever = self._get_retriever()
        llm = self._get_llm_client()

        all_docs = []
        reasoning_chain = []

        # Step 1: 分解问题
        sub_questions = self._decompose_question(query, llm)
        reasoning_chain.append(f"Decomposed into {len(sub_questions)} sub-questions")

        # Step 2: 迭代检索和推理
        previous_reasoning = ""
        for i, sub_q in enumerate(sub_questions[: self.max_iterations]):
            # 检索
            try:
                docs = retriever.retrieve(sub_q, top_k=self.top_k_per_step)
                step_docs = self._normalize_docs(docs)
                all_docs.extend(step_docs)
            except Exception as e:
                step_docs = []
                self.logger.warning(f"Retrieval failed for sub-question {i+1}: {e}")

            # 构建上下文
            new_context = "\n".join([f"- {d['content'][:500]}" for d in step_docs])
            if not new_context:
                new_context = "No relevant information found."

            # 推理
            cot_prompt = self.COT_PROMPT.format(
                query=query,
                previous_reasoning=previous_reasoning or "None yet.",
                new_context=new_context,
                sub_question=sub_q,
            )

            try:
                step_reasoning = llm.chat(cot_prompt)
                step_reasoning = step_reasoning if isinstance(step_reasoning, str) else step_reasoning.content
                reasoning_chain.append(f"Step {i+1} ({sub_q}): {step_reasoning.strip()}")
                previous_reasoning += f"\n\nStep {i+1}: {step_reasoning.strip()}"
            except Exception as e:
                reasoning_chain.append(f"Step {i+1} error: {e}")

        # Step 3: 生成最终答案
        final_prompt = self.FINAL_PROMPT.format(
            query=query, reasoning_chain="\n".join(reasoning_chain)
        )

        try:
            response = llm.chat(final_prompt)
            answer = response if isinstance(response, str) else response.content
        except Exception as e:
            answer = f"Error generating final answer: {e}"

        return RAGOutput(
            query=query,
            answer=answer.strip(),
            strategy=self.strategy_name,
            retrieved_docs=all_docs,
            reasoning_chain=reasoning_chain,
            metadata={
                "sub_questions": sub_questions,
                "iterations": min(len(sub_questions), self.max_iterations),
            },
        )

    def _decompose_question(self, query: str, llm: Any) -> list[str]:
        """分解复杂问题为子问题"""
        prompt = self.DECOMPOSITION_PROMPT.format(query=query)

        try:
            response = llm.chat(prompt)
            response_text = response if isinstance(response, str) else response.content

            # 解析子问题
            lines = response_text.strip().split("\n")
            sub_questions = []
            for line in lines:
                line = line.strip()
                # 移除数字前缀
                if line and line[0].isdigit():
                    line = line.lstrip("0123456789.):- ")
                if line and len(line) > 5:
                    sub_questions.append(line)

            # 确保至少有一个子问题
            if not sub_questions:
                sub_questions = [query]

            return sub_questions[:4]  # 最多4个子问题
        except Exception:
            return [query]  # 降级：使用原问题

    def _normalize_docs(self, docs: Any) -> list[dict[str, Any]]:
        """标准化文档格式"""
        if not docs:
            return []

        if isinstance(docs, list):
            return [
                {"content": d.get("content", str(d)), "score": d.get("score", 0.0)}
                if isinstance(d, dict)
                else {"content": str(d), "score": 0.0}
                for d in docs
            ]
        return [{"content": str(docs), "score": 0.0}]


class AdaptiveRouterFunction(MapFunction):
    """
    自适应路由函数

    根据问题复杂度自动路由到对应的 RAG 策略。

    这是 Adaptive-RAG 的核心组件，实现了:
    1. 问题复杂度分类
    2. 策略选择
    3. 策略执行

    用法:
        router = AdaptiveRouterFunction(
            classifier_type="rule",  # 或 "llm", "t5"
            llm_client=my_llm,
            retriever=my_retriever,
        )
        result = router.execute("What is the relationship between X and Y?")
    """

    def __init__(
        self,
        classifier_type: str = "rule",
        classifier_config: dict[str, Any] | None = None,
        llm_client: Any = None,
        retriever: Any = None,
        strategy_config: dict[str, Any] | None = None,
    ):
        super().__init__()
        self.classifier_type = classifier_type
        self.classifier_config = classifier_config or {}
        self.llm_client = llm_client
        self.retriever = retriever
        self.strategy_config = strategy_config or {}

        # 延迟初始化
        self._classifier = None
        self._strategies: dict[QueryComplexityLevel, BaseRAGStrategyFunction] = {}

    def _get_classifier(self):
        """获取分类器"""
        if self._classifier is None:
            self._classifier = create_classifier(self.classifier_type, **self.classifier_config)
        return self._classifier

    def _get_strategy(self, level: QueryComplexityLevel) -> BaseRAGStrategyFunction:
        """获取对应复杂度的策略"""
        if level not in self._strategies:
            if level == QueryComplexityLevel.ZERO:
                self._strategies[level] = NoRetrievalFunction(
                    llm_client=self.llm_client,
                    config=self.strategy_config,
                )
            elif level == QueryComplexityLevel.SINGLE:
                self._strategies[level] = SingleRetrieverFunction(
                    llm_client=self.llm_client,
                    retriever=self.retriever,
                    config=self.strategy_config,
                )
            else:  # MULTI
                self._strategies[level] = IterativeRetrieverFunction(
                    llm_client=self.llm_client,
                    retriever=self.retriever,
                    config=self.strategy_config,
                )
        return self._strategies[level]

    def execute(self, data: Any) -> RAGOutput:
        """自适应路由执行"""
        # 提取查询
        if isinstance(data, str):
            query = data
        elif isinstance(data, dict):
            query = data.get("query", data.get("question", str(data)))
        else:
            query = str(data)

        # 分类
        classifier = self._get_classifier()
        classification = classifier.classify(query)

        # 获取策略
        strategy = self._get_strategy(classification.complexity)

        # 执行
        result = strategy.execute(data)

        # 添加分类信息到元数据
        result.metadata["classification"] = {
            "level": classification.complexity.value,
            "confidence": classification.confidence,
            "reasoning": classification.reasoning,
        }

        return result


# 简单检索器实现（用于测试和演示）
class SimpleRetriever:
    """简单的模拟检索器"""

    def __init__(self, documents: list[dict[str, Any]] | None = None):
        self.documents = documents or [
            {"content": "Machine learning is a subset of artificial intelligence.", "id": "1"},
            {"content": "Deep learning uses neural networks with many layers.", "id": "2"},
            {"content": "Python is a popular programming language for ML.", "id": "3"},
        ]

    def retrieve(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """简单的关键词匹配检索"""
        query_words = set(query.lower().split())
        scored_docs = []

        for doc in self.documents:
            content_words = set(doc["content"].lower().split())
            overlap = len(query_words & content_words)
            if overlap > 0:
                scored_docs.append({**doc, "score": overlap / len(query_words)})

        # 按分数排序
        scored_docs.sort(key=lambda x: x["score"], reverse=True)
        return scored_docs[:top_k]
