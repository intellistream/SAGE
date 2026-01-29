"""
Adaptive-RAG Pipeline - 完整的自适应 RAG 流水线

基于 SAGE 数据流引擎实现的 Adaptive-RAG Pipeline。

Pipeline 架构:
```
                              ┌─────────────────────┐
                              │   Query Classifier  │
                              │   (复杂度分类器)     │
                              └─────────┬───────────┘
                                        │
                    ┌───────────────────┼───────────────────┐
                    │                   │                   │
                    ▼                   ▼                   ▼
        ┌───────────────────┐ ┌───────────────────┐ ┌───────────────────┐
        │   No Retrieval    │ │  Single Retrieval │ │ Iterative Retr.   │
        │   (Level A)       │ │  (Level B)        │ │ (Level C/IRCoT)   │
        └─────────┬─────────┘ └─────────┬─────────┘ └─────────┬─────────┘
                  │                     │                     │
                  └───────────────────┬─┴─────────────────────┘
                                      │
                                      ▼
                              ┌───────────────────┐
                              │   Answer Merger   │
                              │   (结果合并)       │
                              └───────────────────┘
```

特性:
- 声明式 Pipeline 定义
- 支持流式和批处理
- 可配置的分类器和策略
- 完整的可观测性（日志、指标）
"""

from dataclasses import dataclass, field
from typing import Any

from .classifier import (
    ClassificationResult,
    QueryComplexityClassifier,
    QueryComplexityLevel,
    RuleBasedClassifier,
    create_classifier,
)
from .functions import (
    AdaptiveRouterFunction,
    BaseRAGStrategyFunction,
    IterativeRetrieverFunction,
    NoRetrievalFunction,
    RAGOutput,
    SingleRetrieverFunction,
)


@dataclass
class PipelineConfig:
    """Pipeline 配置"""

    # 分类器配置
    classifier_type: str = "rule"  # "rule", "llm", "t5"
    classifier_config: dict[str, Any] = field(default_factory=dict)

    # 策略配置
    no_retrieval_config: dict[str, Any] = field(default_factory=dict)
    single_retrieval_config: dict[str, Any] = field(default_factory=dict)
    iterative_retrieval_config: dict[str, Any] = field(default_factory=dict)

    # 检索器配置
    retriever_type: str = "simple"  # "simple", "chroma", "milvus"
    retriever_config: dict[str, Any] = field(default_factory=dict)

    # LLM 配置
    llm_model: str = "gpt-3.5-turbo"
    llm_base_url: str | None = None
    llm_api_key: str | None = None

    # 其他
    enable_metrics: bool = True
    enable_logging: bool = True
    batch_size: int = 1


@dataclass
class PipelineMetrics:
    """Pipeline 运行指标"""

    total_queries: int = 0
    classification_counts: dict[str, int] = field(
        default_factory=lambda: {"A": 0, "B": 0, "C": 0}
    )
    avg_latency_ms: float = 0.0
    strategy_latencies: dict[str, float] = field(
        default_factory=lambda: {"no_retrieval": 0.0, "single_retrieval": 0.0, "iterative_retrieval": 0.0}
    )
    errors: int = 0


class AdaptiveRAGPipeline:
    """
    Adaptive-RAG Pipeline

    完整的自适应 RAG 流水线，支持:
    - 问题复杂度分类
    - 策略路由
    - 多种 RAG 策略执行
    - 结果汇总

    基本用法:
    ```python
    pipeline = AdaptiveRAGPipeline()
    result = pipeline.run("What is the capital of France?")
    print(result.answer)
    ```

    高级用法:
    ```python
    config = PipelineConfig(
        classifier_type="llm",
        retriever_type="milvus",
        llm_model="gpt-4",
    )
    pipeline = AdaptiveRAGPipeline(config)

    # 批量处理
    results = pipeline.batch_run([
        "What is AI?",
        "Compare Python and Java",
        "What causes climate change and its effects?"
    ])
    ```

    与 SAGE 数据流集成:
    ```python
    from sage.kernel import StreamExecutionEnvironment

    env = StreamExecutionEnvironment.get_execution_environment()

    # 创建 Pipeline
    pipeline = AdaptiveRAGPipeline()

    # 使用 SAGE 算子
    queries = env.from_source(query_source)
    results = queries.map(pipeline.as_function())
    results.add_sink(result_sink)

    env.execute("adaptive-rag-pipeline")
    ```
    """

    def __init__(
        self,
        config: PipelineConfig | None = None,
        llm_client: Any = None,
        retriever: Any = None,
    ):
        self.config = config or PipelineConfig()
        self.llm_client = llm_client
        self.retriever = retriever
        self.metrics = PipelineMetrics()

        # 初始化组件
        self._classifier = None
        self._strategies: dict[QueryComplexityLevel, BaseRAGStrategyFunction] = {}
        self._router = None

    @property
    def classifier(self):
        """获取分类器（延迟初始化）"""
        if self._classifier is None:
            self._classifier = create_classifier(
                self.config.classifier_type, **self.config.classifier_config
            )
        return self._classifier

    def _get_strategy(self, level: QueryComplexityLevel) -> BaseRAGStrategyFunction:
        """获取对应策略"""
        if level not in self._strategies:
            if level == QueryComplexityLevel.ZERO:
                self._strategies[level] = NoRetrievalFunction(
                    llm_client=self.llm_client,
                    config=self.config.no_retrieval_config,
                )
            elif level == QueryComplexityLevel.SINGLE:
                self._strategies[level] = SingleRetrieverFunction(
                    llm_client=self.llm_client,
                    retriever=self.retriever,
                    config=self.config.single_retrieval_config,
                )
            else:
                self._strategies[level] = IterativeRetrieverFunction(
                    llm_client=self.llm_client,
                    retriever=self.retriever,
                    config=self.config.iterative_retrieval_config,
                )
        return self._strategies[level]

    def classify(self, query: str) -> ClassificationResult:
        """对查询进行复杂度分类"""
        return self.classifier.classify(query)

    def run(self, query: str) -> RAGOutput:
        """
        执行单个查询

        Args:
            query: 用户查询

        Returns:
            RAGOutput 包含答案和元数据
        """
        import time

        start_time = time.time()

        try:
            # 1. 分类
            classification = self.classify(query)
            self.metrics.classification_counts[classification.complexity.value] += 1

            # 2. 获取策略
            strategy = self._get_strategy(classification.complexity)

            # 3. 执行
            result = strategy.execute(query)

            # 4. 添加分类信息
            result.metadata["classification"] = {
                "level": classification.complexity.value,
                "level_name": classification.complexity.name,
                "confidence": classification.confidence,
                "reasoning": classification.reasoning,
            }

            # 更新指标
            self.metrics.total_queries += 1
            latency = (time.time() - start_time) * 1000
            self._update_latency(result.strategy, latency)

            return result

        except Exception as e:
            self.metrics.errors += 1
            return RAGOutput(
                query=query,
                answer=f"Pipeline error: {e}",
                strategy="error",
                metadata={"error": str(e)},
            )

    def batch_run(self, queries: list[str]) -> list[RAGOutput]:
        """
        批量执行查询

        Args:
            queries: 查询列表

        Returns:
            RAGOutput 列表
        """
        results = []
        for query in queries:
            result = self.run(query)
            results.append(result)
        return results

    def _update_latency(self, strategy: str, latency_ms: float):
        """更新延迟指标"""
        if strategy in self.metrics.strategy_latencies:
            old_avg = self.metrics.strategy_latencies[strategy]
            count = self.metrics.classification_counts.get(
                {"no_retrieval": "A", "single_retrieval": "B", "iterative_retrieval": "C"}.get(
                    strategy, "B"
                ),
                1,
            )
            self.metrics.strategy_latencies[strategy] = (old_avg * (count - 1) + latency_ms) / count

        # 更新总体延迟
        old_total = self.metrics.avg_latency_ms
        self.metrics.avg_latency_ms = (
            old_total * (self.metrics.total_queries - 1) + latency_ms
        ) / self.metrics.total_queries

    def get_metrics(self) -> dict[str, Any]:
        """获取运行指标"""
        return {
            "total_queries": self.metrics.total_queries,
            "classification_distribution": self.metrics.classification_counts,
            "avg_latency_ms": round(self.metrics.avg_latency_ms, 2),
            "strategy_latencies": {
                k: round(v, 2) for k, v in self.metrics.strategy_latencies.items()
            },
            "errors": self.metrics.errors,
            "error_rate": (
                round(self.metrics.errors / max(1, self.metrics.total_queries) * 100, 2)
            ),
        }

    def reset_metrics(self):
        """重置指标"""
        self.metrics = PipelineMetrics()

    def as_function(self) -> AdaptiveRouterFunction:
        """
        返回可用于 SAGE 数据流的 MapFunction

        用法:
        ```python
        env = StreamExecutionEnvironment.get_execution_environment()
        queries = env.from_source(query_source)
        results = queries.map(pipeline.as_function())
        ```
        """
        if self._router is None:
            self._router = AdaptiveRouterFunction(
                classifier_type=self.config.classifier_type,
                classifier_config=self.config.classifier_config,
                llm_client=self.llm_client,
                retriever=self.retriever,
                strategy_config={
                    "no_retrieval": self.config.no_retrieval_config,
                    "single_retrieval": self.config.single_retrieval_config,
                    "iterative_retrieval": self.config.iterative_retrieval_config,
                },
            )
        return self._router


# 便捷函数
def create_adaptive_rag_pipeline(
    classifier_type: str = "rule",
    llm_client: Any = None,
    retriever: Any = None,
    **kwargs,
) -> AdaptiveRAGPipeline:
    """
    创建 Adaptive-RAG Pipeline 的便捷函数

    Args:
        classifier_type: 分类器类型 ("rule", "llm", "t5")
        llm_client: LLM 客户端
        retriever: 检索器
        **kwargs: 其他配置参数

    Returns:
        AdaptiveRAGPipeline 实例
    """
    config = PipelineConfig(classifier_type=classifier_type, **kwargs)
    return AdaptiveRAGPipeline(config=config, llm_client=llm_client, retriever=retriever)


# SAGE 数据流集成
def build_sage_pipeline(
    env,  # StreamExecutionEnvironment
    source,
    pipeline_config: PipelineConfig | None = None,
    llm_client: Any = None,
    retriever: Any = None,
):
    """
    构建基于 SAGE 数据流的 Adaptive-RAG Pipeline

    Args:
        env: SAGE StreamExecutionEnvironment
        source: 数据源
        pipeline_config: Pipeline 配置
        llm_client: LLM 客户端
        retriever: 检索器

    Returns:
        DataStream 结果流

    用法:
    ```python
    from sage.kernel import StreamExecutionEnvironment
    from sage.benchmark.benchmark_sage.experiments.pipelines.adaptive_rag import build_sage_pipeline

    env = StreamExecutionEnvironment.get_execution_environment()
    source = env.from_collection(["What is AI?", "Compare X and Y"])

    results = build_sage_pipeline(env, source)
    results.print()

    env.execute("adaptive-rag")
    ```
    """
    pipeline = AdaptiveRAGPipeline(
        config=pipeline_config or PipelineConfig(),
        llm_client=llm_client,
        retriever=retriever,
    )

    # 使用 map 算子应用 Adaptive-RAG 路由函数
    return source.map(pipeline.as_function())
