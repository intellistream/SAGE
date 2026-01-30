#!/usr/bin/env python3
"""
Adaptive-RAG 使用示例

演示如何使用基于 SAGE 算子实现的 Adaptive-RAG Pipeline。

参考论文: "Adaptive-RAG: Learning to Adapt Retrieval-Augmented Large Language Models
through Question Complexity" (NAACL 2024)

运行方式:
    python -m sage.benchmark.benchmark_sage.experiments.pipelines.adaptive_rag.example
"""

from __future__ import annotations


def example_basic_usage():
    """
    示例 1: 基本用法

    展示 Adaptive-RAG Pipeline 的基本使用方式。
    """
    print("\n" + "=" * 60)
    print("示例 1: Adaptive-RAG 基本用法")
    print("=" * 60)

    from sage.benchmark.benchmark_sage.experiments.pipelines.adaptive_rag import (
        QueryComplexityClassifier,
        QueryComplexityLevel,
    )

    # 创建分类器
    classifier = QueryComplexityClassifier()

    # 测试不同复杂度的问题
    test_queries = [
        # Level A: 简单问题
        "What is machine learning?",
        "Define artificial intelligence.",
        # Level B: 中等问题
        "What are the latest developments in quantum computing?",
        "How does BERT work for NLP tasks?",
        # Level C: 复杂问题
        "Compare the economic policies of Obama and Trump and their long-term effects.",
        "What caused World War I and how did it subsequently lead to World War II?",
    ]

    print("\n问题复杂度分类结果:")
    print("-" * 60)

    for query in test_queries:
        result = classifier.classify(query)
        level_desc = {
            QueryComplexityLevel.ZERO: "A (无需检索)",
            QueryComplexityLevel.SINGLE: "B (单步检索)",
            QueryComplexityLevel.MULTI: "C (多跳检索)",
        }
        print(f"\n问题: {query[:50]}...")
        print(f"  复杂度: {level_desc[result.complexity]}")
        print(f"  置信度: {result.confidence:.2f}")
        print(f"  理由: {result.reasoning}")


def example_pipeline_run():
    """
    示例 2: Pipeline 执行

    展示完整的 Pipeline 执行流程（使用模拟 LLM）。
    """
    print("\n" + "=" * 60)
    print("示例 2: Adaptive-RAG Pipeline 执行")
    print("=" * 60)

    from sage.benchmark.benchmark_sage.experiments.pipelines.adaptive_rag import AdaptiveRAGPipeline
    from sage.benchmark.benchmark_sage.experiments.pipelines.adaptive_rag.pipeline import (
        PipelineConfig,
    )

    # 创建模拟 LLM 客户端
    class MockLLMClient:
        """模拟 LLM 客户端（用于演示）"""

        def chat(self, prompt: str) -> str:
            # 简单的模拟响应
            if "decompose" in prompt.lower() or "break down" in prompt.lower():
                return """1. What is the first concept?
2. What is the second concept?
3. How are they related?"""
            elif "answer" in prompt.lower():
                return "This is a simulated answer from the LLM."
            else:
                return "Simulated LLM response."

    # 创建 Pipeline
    config = PipelineConfig(
        classifier_type="rule",
        enable_metrics=True,
    )

    pipeline = AdaptiveRAGPipeline(config=config, llm_client=MockLLMClient())

    # 测试查询
    test_queries = [
        "What is Python?",  # Level A
        "How does TensorFlow work?",  # Level B
        "Compare PyTorch and TensorFlow and explain which is better for research vs production.",  # Level C
    ]

    print("\nPipeline 执行结果:")
    print("-" * 60)

    for query in test_queries:
        result = pipeline.run(query)
        print(f"\n问题: {query}")
        print(f"  策略: {result.strategy}")
        print(f"  分类: {result.metadata.get('classification', {}).get('level', 'N/A')}")
        print(f"  答案: {result.answer[:100]}...")
        if result.retrieved_docs:
            print(f"  检索文档数: {len(result.retrieved_docs)}")
        if result.reasoning_chain:
            print(f"  推理步数: {len(result.reasoning_chain)}")

    # 显示指标
    print("\n运行指标:")
    print("-" * 60)
    metrics = pipeline.get_metrics()
    print(f"  总查询数: {metrics['total_queries']}")
    print(f"  分类分布: {metrics['classification_distribution']}")
    print(f"  平均延迟: {metrics['avg_latency_ms']} ms")


def example_custom_classifier():
    """
    示例 3: 自定义分类器

    展示如何创建和使用自定义分类器。
    """
    print("\n" + "=" * 60)
    print("示例 3: 自定义分类器")
    print("=" * 60)

    from sage.benchmark.benchmark_sage.experiments.pipelines.adaptive_rag.classifier import (
        BaseClassifier,
        ClassificationResult,
        QueryComplexityLevel,
    )

    class KeywordCountClassifier(BaseClassifier):
        """基于关键词数量的简单分类器"""

        def classify(self, query: str) -> ClassificationResult:
            # 简单规则：根据问句长度和关键词判断
            word_count = len(query.split())
            has_compare = any(w in query.lower() for w in ["compare", "difference", "between"])
            has_complex = any(w in query.lower() for w in ["why", "how", "explain", "cause"])

            if word_count < 6 and not has_compare and not has_complex:
                complexity = QueryComplexityLevel.ZERO
            elif has_compare or (has_complex and word_count > 15):
                complexity = QueryComplexityLevel.MULTI
            else:
                complexity = QueryComplexityLevel.SINGLE

            return ClassificationResult(
                query=query,
                complexity=complexity,
                confidence=0.7,
                reasoning=f"Word count: {word_count}, compare: {has_compare}, complex: {has_complex}",
            )

    # 使用自定义分类器
    classifier = KeywordCountClassifier()

    test_queries = [
        "What is AI?",
        "How does machine learning work in practice?",
        "Compare neural networks and decision trees and explain the trade-offs.",
    ]

    print("\n自定义分类器结果:")
    for query in test_queries:
        result = classifier.classify(query)
        print(f"\n问题: {query}")
        print(f"  复杂度: {result.complexity.value} ({result.complexity.name})")
        print(f"  理由: {result.reasoning}")


def example_strategy_functions():
    """
    示例 4: 单独使用策略函数

    展示如何单独使用各个 RAG 策略函数。
    """
    print("\n" + "=" * 60)
    print("示例 4: 策略函数独立使用")
    print("=" * 60)

    from sage.benchmark.benchmark_sage.experiments.pipelines.adaptive_rag.functions import (
        IterativeRetrieverFunction,
        NoRetrievalFunction,
        SimpleRetriever,
        SingleRetrieverFunction,
    )

    # 模拟 LLM
    class MockLLM:
        def chat(self, prompt):
            return "This is a mock LLM response for demonstration."

    llm = MockLLM()

    # 创建模拟检索器
    retriever = SimpleRetriever(
        documents=[
            {"content": "Machine learning is a type of AI that learns from data.", "id": "1"},
            {"content": "Deep learning uses neural networks with multiple layers.", "id": "2"},
            {
                "content": "Natural language processing enables computers to understand text.",
                "id": "3",
            },
        ]
    )

    print("\n1. NoRetrievalFunction (Level A):")
    print("-" * 40)
    no_ret = NoRetrievalFunction(llm_client=llm)
    result = no_ret.execute("What is machine learning?")
    print(f"  策略: {result.strategy}")
    print(f"  答案: {result.answer}")
    print(f"  检索文档数: {len(result.retrieved_docs)}")

    print("\n2. SingleRetrieverFunction (Level B):")
    print("-" * 40)
    single_ret = SingleRetrieverFunction(llm_client=llm, retriever=retriever)
    result = single_ret.execute("Explain neural networks")
    print(f"  策略: {result.strategy}")
    print(f"  答案: {result.answer}")
    print(f"  检索文档数: {len(result.retrieved_docs)}")
    if result.retrieved_docs:
        print(f"  首个文档: {result.retrieved_docs[0]['content'][:50]}...")

    print("\n3. IterativeRetrieverFunction (Level C):")
    print("-" * 40)
    iter_ret = IterativeRetrieverFunction(llm_client=llm, retriever=retriever, max_iterations=2)
    result = iter_ret.execute(
        "Compare machine learning and deep learning and explain their relationship"
    )
    print(f"  策略: {result.strategy}")
    print(f"  答案: {result.answer}")
    print(f"  检索文档数: {len(result.retrieved_docs)}")
    print(f"  推理步骤: {len(result.reasoning_chain)}")
    for i, step in enumerate(result.reasoning_chain[:3]):
        print(f"    Step {i + 1}: {step[:60]}...")


def example_batch_processing():
    """
    示例 5: 批量处理

    展示如何批量处理多个查询。
    """
    print("\n" + "=" * 60)
    print("示例 5: 批量处理")
    print("=" * 60)

    from sage.benchmark.benchmark_sage.experiments.pipelines.adaptive_rag import AdaptiveRAGPipeline

    class MockLLM:
        def chat(self, prompt):
            return "Mock response for batch processing demo."

    pipeline = AdaptiveRAGPipeline(llm_client=MockLLM())

    queries = [
        "What is Python?",
        "How does Git work?",
        "Compare Java and Python for web development.",
        "What are the effects of climate change on agriculture?",
        "Define machine learning.",
    ]

    print(f"\n批量处理 {len(queries)} 个查询...")
    results = pipeline.batch_run(queries)

    print("\n结果汇总:")
    print("-" * 60)

    for i, (query, result) in enumerate(zip(queries, results)):
        classification = result.metadata.get("classification", {})
        print(f"\n{i + 1}. {query[:40]}...")
        print(f"   Level: {classification.get('level', 'N/A')} | 策略: {result.strategy}")

    print("\n总体指标:")
    metrics = pipeline.get_metrics()
    print(
        f"  分类分布: A={metrics['classification_distribution']['A']}, "
        f"B={metrics['classification_distribution']['B']}, "
        f"C={metrics['classification_distribution']['C']}"
    )


def example_sage_integration():
    """
    示例 6: SAGE 数据流集成

    展示如何将 Adaptive-RAG 集成到 SAGE 数据流 Pipeline 中。
    (这是一个概念性示例，展示集成方式)
    """
    print("\n" + "=" * 60)
    print("示例 6: SAGE 数据流集成 (概念性)")
    print("=" * 60)

    print("""
Adaptive-RAG 可以无缝集成到 SAGE 数据流系统中:

```python
from sage.kernel import StreamExecutionEnvironment
from sage.benchmark.benchmark_sage.experiments.pipelines.adaptive_rag import (
    AdaptiveRAGPipeline, build_sage_pipeline
)

# 1. 创建 SAGE 执行环境
env = StreamExecutionEnvironment.get_execution_environment()

# 2. 定义数据源
query_source = env.from_collection([
    "What is AI?",
    "Compare Python and Java",
    "Explain the causes and effects of World War II"
])

# 3. 使用 Adaptive-RAG Pipeline
pipeline = AdaptiveRAGPipeline(
    classifier_type="rule",
    llm_client=my_llm_client,
    retriever=my_retriever,
)

# 方式 1: 直接使用 as_function()
results = query_source.map(pipeline.as_function())

# 方式 2: 使用便捷函数
results = build_sage_pipeline(env, query_source)

# 4. 添加 Sink
results.add_sink(my_sink)

# 5. 执行
env.execute("adaptive-rag-pipeline")
```

关键特性:
- MapFunction 兼容: AdaptiveRouterFunction 继承自 MapFunction
- 流式处理: 支持实时查询处理
- 批处理: 支持批量查询
- 可观测性: 集成 SAGE 的日志和指标系统
- 容错: 支持 checkpoint 和恢复
""")


def main():
    """运行所有示例"""
    print("\n" + "=" * 60)
    print("Adaptive-RAG 示例程序")
    print("基于 SAGE 算子系统的自适应 RAG Pipeline 实现")
    print("=" * 60)

    try:
        example_basic_usage()
    except Exception as e:
        print(f"\n示例 1 出错: {e}")

    try:
        example_pipeline_run()
    except Exception as e:
        print(f"\n示例 2 出错: {e}")

    try:
        example_custom_classifier()
    except Exception as e:
        print(f"\n示例 3 出错: {e}")

    try:
        example_strategy_functions()
    except Exception as e:
        print(f"\n示例 4 出错: {e}")

    try:
        example_batch_processing()
    except Exception as e:
        print(f"\n示例 5 出错: {e}")

    try:
        example_sage_integration()
    except Exception as e:
        print(f"\n示例 6 出错: {e}")

    print("\n" + "=" * 60)
    print("所有示例执行完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
