# isage-eval Copilot Instructions

## Package Identity

| 属性          | 值                                           |
| ------------- | -------------------------------------------- |
| **PyPI 包名** | `isage-eval`                                 |
| **导入名**    | `sage_libs.sage_eval`                        |
| **SAGE 层级** | L3 (Algorithms & Libraries)                  |
| **版本格式**  | `0.1.x.y` (四段式)                           |
| **仓库**      | `https://github.com/intellistream/sage-eval` |

## 层级定位

### ✅ 允许的依赖

```
L3 及以下:
├── sage-common (L1)      # 基础工具、类型、配置
├── sage-platform (L2)    # 平台服务抽象
├── Python stdlib         # 标准库
├── numpy, scipy          # 科学计算
├── scikit-learn          # ML 指标
├── nltk, rouge-score     # NLP 评估
├── bert-score            # BERT 评估
└── evaluate (HF)         # HuggingFace 评估库
```

### ❌ 禁止的依赖

```
L4+ 组件 (绝对禁止):
├── sage-middleware       # ❌ 中间件层
├── isage-vdb / SageVDB   # ❌ 向量数据库
├── isage-neuromem        # ❌ 内存系统
├── FastAPI / uvicorn     # ❌ 网络服务
├── Redis / RocksDB       # ❌ 外部存储
└── vLLM / LMDeploy       # ❌ 推理引擎
```

**原则**: Eval 库提供评估指标和算法，LLM-as-Judge 通过依赖注入。

## 与 SAGE 主仓库的关系

```
┌─────────────────────────────────────────────────────────────────┐
│                  SAGE 主仓库 (sage.libs.eval)                    │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    Interface Layer                         │  │
│  │  • BaseMetric (ABC)        • BaseLLMJudge (ABC)           │  │
│  │  • BaseProfiler (ABC)      • BaseBenchmark (ABC)          │  │
│  │  • MetricType (枚举)       • MetricResult (数据类型)       │  │
│  │  • ProfileResult (数据类型)                                │  │
│  │  • create_metric(), create_judge() (工厂函数)              │  │
│  │  • create_profiler(), create_benchmark() (工厂函数)        │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              ▲                                   │
│                              │ 注册                              │
└──────────────────────────────┼──────────────────────────────────┘
                               │
┌──────────────────────────────┼──────────────────────────────────┐
│                   isage-eval (独立 PyPI 包)                      │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                 Implementation Layer                       │  │
│  │  Metrics:                                                  │  │
│  │  • AccuracyMetric, F1Metric, BLEUMetric, ROUGEMetric      │  │
│  │  • BERTScoreMetric, PerplexityMetric                      │  │
│  │  LLM Judges:                                               │  │
│  │  • FaithfulnessJudge, RelevanceJudge, CoherenceJudge      │  │
│  │  Profilers:                                                │  │
│  │  • LatencyProfiler, ThroughputProfiler, MemoryProfiler    │  │
│  │  Benchmarks:                                               │  │
│  │  • RAGBenchmark, AgentBenchmark, E2EBenchmark             │  │
│  │  • _register.py (自动注册到 SAGE 工厂)                     │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 自动注册机制

```python
# sage_libs/sage_eval/_register.py
from sage.libs.eval import (
    register_metric, register_judge,
    register_profiler, register_benchmark
)

from .metrics import AccuracyMetric, F1Metric, BLEUMetric, ROUGEMetric
from .judges import FaithfulnessJudge, RelevanceJudge
from .profilers import LatencyProfiler, MemoryProfiler
from .benchmarks import RAGBenchmark, AgentBenchmark

# 注册 Metrics
register_metric("accuracy", AccuracyMetric)
register_metric("f1", F1Metric)
register_metric("bleu", BLEUMetric)
register_metric("rouge", ROUGEMetric)

# 注册 Judges
register_judge("faithfulness", FaithfulnessJudge)
register_judge("relevance", RelevanceJudge)

# 注册 Profilers
register_profiler("latency", LatencyProfiler)
register_profiler("memory", MemoryProfiler)

# 注册 Benchmarks
register_benchmark("rag", RAGBenchmark)
register_benchmark("agent", AgentBenchmark)
```

## 功能模块

### 1. Metrics (评估指标)

```python
from sage.libs.eval import create_metric, MetricResult

# 准确率
metric = create_metric("accuracy")
result: MetricResult = metric.compute(
    predictions=["A", "B", "C"],
    references=["A", "B", "D"]
)
print(f"准确率: {result.value:.2%}")  # 66.67%

# F1 分数
metric = create_metric("f1", average="macro")
result = metric.compute(predictions, references)

# BLEU (机器翻译)
metric = create_metric("bleu", max_order=4)
result = metric.compute(
    predictions=["the cat sat on the mat"],
    references=[["the cat is on the mat"]]
)

# ROUGE (文本摘要)
metric = create_metric("rouge", rouge_types=["rouge1", "rouge2", "rougeL"])
result = metric.compute(summaries, reference_summaries)

# BERTScore (语义相似度)
metric = create_metric("bert_score", model="bert-base-chinese")
result = metric.compute(generated_texts, reference_texts)

# 困惑度
metric = create_metric("perplexity")
result = metric.compute(texts, model=language_model)
```

**支持的指标**:

| 指标         | 类型 | 用途           |
| ------------ | ---- | -------------- |
| `accuracy`   | 分类 | 分类准确率     |
| `f1`         | 分类 | F1 分数        |
| `precision`  | 分类 | 精确率         |
| `recall`     | 分类 | 召回率         |
| `bleu`       | 生成 | 机器翻译质量   |
| `rouge`      | 生成 | 文本摘要质量   |
| `meteor`     | 生成 | 翻译质量       |
| `bert_score` | 语义 | 语义相似度     |
| `perplexity` | LLM  | 语言模型困惑度 |

### 2. LLM-as-Judge (LLM 评估)

```python
from sage.libs.eval import create_judge

# Faithfulness Judge (事实准确性)
judge = create_judge("faithfulness", llm_client=client)
result = judge.judge(
    response="北京是中国的首都",
    context="北京，简称京，是中华人民共和国首都",
    question="中国的首都是哪里？"
)
print(f"事实准确性: {result.value:.2f}")  # 0-1 分数

# Relevance Judge (相关性)
judge = create_judge("relevance", llm_client=client)
result = judge.judge(
    response=answer,
    question=question
)

# Coherence Judge (连贯性)
judge = create_judge("coherence", llm_client=client)
result = judge.judge(response=generated_text)

# Safety Judge (安全性)
judge = create_judge("safety", llm_client=client)
result = judge.judge(response=model_output)

# 自定义评估标准
judge = create_judge("custom",
    llm_client=client,
    criteria="评估回答是否具有创意性和新颖性",
    rubric={
        5: "非常有创意",
        4: "比较有创意",
        3: "一般",
        2: "缺乏创意",
        1: "完全没有创意"
    }
)
```

### 3. Profilers (性能分析器)

```python
from sage.libs.eval import create_profiler, ProfileResult

# 延迟分析
profiler = create_profiler("latency")
with profiler.profile():
    result = model.generate(prompt)

profile: ProfileResult = profiler.get_result()
print(f"平均延迟: {profile.mean_latency_ms:.2f}ms")
print(f"P99 延迟: {profile.p99_latency_ms:.2f}ms")

# 吞吐量分析
profiler = create_profiler("throughput")
result = profiler.measure(
    func=model.generate,
    inputs=test_prompts,
    batch_size=32
)
print(f"吞吐量: {result.samples_per_second:.2f} samples/s")
print(f"Token 吞吐: {result.tokens_per_second:.2f} tokens/s")

# 内存分析
profiler = create_profiler("memory")
with profiler.profile():
    model.load()
    result = model.generate(prompt)

print(f"峰值内存: {profiler.peak_memory_mb:.2f}MB")
print(f"GPU 利用率: {profiler.avg_gpu_utilization:.1%}")
```

### 4. Benchmarks (基准测试套件)

```python
from sage.libs.eval import create_benchmark

# RAG 基准测试
benchmark = create_benchmark("rag",
    metrics=["faithfulness", "relevance", "mrr", "ndcg"],
    dataset="natural_questions"
)
results = benchmark.run(rag_pipeline)
print(benchmark.report())

# Agent 基准测试
benchmark = create_benchmark("agent",
    metrics=["task_success", "tool_accuracy", "efficiency"],
    tasks=["web_search", "calculation", "code_generation"]
)
results = benchmark.run(agent)

# 端到端基准测试
benchmark = create_benchmark("e2e",
    metrics=["quality", "latency", "cost"],
    test_cases=test_cases
)
results = benchmark.run(pipeline)
```

### 5. Retrieval Metrics (检索指标)

```python
from sage.libs.eval import create_metric

# MRR (Mean Reciprocal Rank)
metric = create_metric("mrr")
result = metric.compute(
    predictions=ranked_results,
    references=ground_truth
)

# NDCG (Normalized Discounted Cumulative Gain)
metric = create_metric("ndcg", k=10)
result = metric.compute(predictions, references)

# MAP (Mean Average Precision)
metric = create_metric("map")
result = metric.compute(predictions, references)

# Hit Rate
metric = create_metric("hit_rate", k=5)
result = metric.compute(predictions, references)
```

## 目录结构

```
sage-eval/                          # 独立仓库根目录
├── pyproject.toml                  # 包配置 (name = "isage-eval")
├── README.md
├── COPILOT_INSTRUCTIONS.md         # 本文件
├── LICENSE
├── src/
│   └── sage_libs/                  # 命名空间包
│       └── sage_eval/
│           ├── __init__.py         # 主入口
│           ├── _version.py         # 版本信息
│           ├── _register.py        # 自动注册
│           ├── metrics/            # 评估指标实现
│           │   ├── __init__.py
│           │   ├── classification.py  # Accuracy, F1, Precision, Recall
│           │   ├── generation.py      # BLEU, ROUGE, METEOR
│           │   ├── semantic.py        # BERTScore, Similarity
│           │   ├── retrieval.py       # MRR, NDCG, MAP, HitRate
│           │   └── language_model.py  # Perplexity
│           ├── judges/             # LLM-as-Judge 实现
│           │   ├── __init__.py
│           │   ├── faithfulness.py
│           │   ├── relevance.py
│           │   ├── coherence.py
│           │   ├── safety.py
│           │   └── custom.py
│           ├── profilers/          # 性能分析器实现
│           │   ├── __init__.py
│           │   ├── latency.py
│           │   ├── throughput.py
│           │   └── memory.py
│           └── benchmarks/         # 基准测试实现
│               ├── __init__.py
│               ├── rag.py
│               ├── agent.py
│               └── e2e.py
├── tests/
│   ├── conftest.py
│   ├── test_metrics.py
│   ├── test_judges.py
│   ├── test_profilers.py
│   └── test_benchmarks.py
└── examples/
    ├── evaluate_rag.py
    ├── llm_judge.py
    └── benchmark_pipeline.py
```

## 常见问题修复指南

### 1. LLM Judge 注入

```python
# ❌ 错误：Judge 内部创建 LLM 客户端
class FaithfulnessJudge(BaseLLMJudge):
    def __init__(self):
        from sage.llm import UnifiedInferenceClient
        self.llm = UnifiedInferenceClient.create()  # ❌ 隐式依赖

# ✅ 正确：通过依赖注入
class FaithfulnessJudge(BaseLLMJudge):
    def __init__(self, llm_client: LLMClientProtocol):
        self.llm = llm_client

# 使用时
judge = create_judge("faithfulness", llm_client=client)
```

### 2. 批量评估效率

```python
# ❌ 问题：逐条评估太慢
for pred, ref in zip(predictions, references):
    result = metric.compute([pred], [ref])  # 每次只评估一条

# ✅ 修复：批量评估
result = metric.compute(predictions, references)  # 一次评估所有

# 或使用 batch 方法
result = metric.compute_batch(
    predictions, references,
    batch_size=64
)
```

### 3. Profiler 上下文管理

```python
# ❌ 问题：忘记结束 profiling
profiler.start()
model.generate(prompt)
# 忘记 profiler.stop()

# ✅ 修复：使用上下文管理器
with profiler.profile() as p:
    model.generate(prompt)
result = profiler.get_result()  # 自动停止
```

### 4. 指标类型匹配

```python
# ❌ 问题：用错指标类型
metric = create_metric("bleu")
result = metric.compute(
    predictions=["A", "B", "C"],  # 分类标签
    references=["A", "B", "D"]
)  # BLEU 不适用于分类

# ✅ 修复：选择正确的指标
metric = create_metric("accuracy")  # 分类用 accuracy
result = metric.compute(predictions, references)
```

### 5. 多指标聚合

```python
# ❌ 问题：手动管理多个指标
accuracy = AccuracyMetric().compute(preds, refs)
f1 = F1Metric().compute(preds, refs)
bleu = BLEUMetric().compute(preds, refs)

# ✅ 修复：使用 MetricSuite
from sage_libs.sage_eval import MetricSuite

suite = MetricSuite(metrics=["accuracy", "f1", "bleu"])
results = suite.compute(predictions, references)
for name, result in results.items():
    print(f"{name}: {result.value:.4f}")
```

## 关键设计原则

### 1. 指标无状态

指标计算应该是无状态的：

```python
# ✅ 好：无状态计算
class AccuracyMetric(BaseMetric):
    def compute(self, predictions, references) -> MetricResult:
        # 纯函数计算
        correct = sum(p == r for p, r in zip(predictions, references))
        return MetricResult(name="accuracy", value=correct / len(predictions))
```

### 2. 结果标准化

所有指标返回统一格式：

```python
@dataclass
class MetricResult:
    name: str           # 指标名称
    value: float        # 指标值 (归一化到 0-1 或合理范围)
    metric_type: MetricType
    confidence_interval: Optional[tuple[float, float]] = None
    sample_size: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
```

### 3. LLM 客户端抽象

Judge 使用协议而不是具体类型：

```python
class LLMClientProtocol(Protocol):
    def chat(self, messages: list[dict]) -> str: ...

class FaithfulnessJudge:
    def __init__(self, llm_client: LLMClientProtocol):
        # 接受任何符合协议的客户端
        self.llm = llm_client
```

### 4. 流式支持

大数据集支持流式计算：

```python
class StreamingMetric(BaseMetric):
    def supports_streaming(self) -> bool:
        return True

    def update(self, prediction: Any, reference: Any) -> None:
        """增量更新"""
        self._total += 1
        self._correct += (prediction == reference)

    def finalize(self) -> MetricResult:
        """完成计算"""
        return MetricResult(
            name=self.name,
            value=self._correct / self._total
        )
```

### 5. 可解释性

复杂指标提供详细解释：

```python
class FaithfulnessJudge(BaseLLMJudge):
    def judge(self, response, context, **kwargs) -> MetricResult:
        # 不仅返回分数，还返回解释
        return MetricResult(
            name="faithfulness",
            value=0.85,
            metadata={
                "explanation": "回答基本准确，但缺少部分细节",
                "supported_claims": ["北京是首都"],
                "unsupported_claims": [],
                "evidence": "根据上下文第2段..."
            }
        )
```

## 测试规范

```bash
# 运行单元测试
pytest tests/ -v

# 运行需要 LLM 的测试（使用 mock）
pytest tests/ -v -m "not llm_required"

# 运行完整测试（包括 LLM Judge）
SAGE_TEST_LLM_ENABLED=1 pytest tests/ -v
```

## 与其他 L3 库的协作

```python
# isage-eval + isage-rag 协作
from sage_libs.sage_eval import create_benchmark
from sage_libs.sage_rag import DenseRetriever

# 创建 RAG pipeline
retriever = DenseRetriever(...)
rag_pipeline = ...

# 使用 RAG 基准测试
benchmark = create_benchmark("rag",
    metrics=["faithfulness", "relevance", "mrr"]
)
results = benchmark.run(rag_pipeline)
```

## 发布流程

```bash
# 使用 sage-pypi-publisher
cd /path/to/sage-pypi-publisher
./publish.sh sage-eval --auto-bump patch

# 或手动指定版本
./publish.sh sage-eval --version 0.1.0.1
```
