# 高级教程

深入学习 SAGE 的高级特性和最佳实践，构建生产级的流式 AI 应用。

## 📚 本章内容

本章节涵盖 SAGE 的高级主题，适合已经掌握基础知识的开发者。

### [分布式 Pipeline](distributed-pipeline.md)

构建可扩展的分布式流式处理应用：

- 🌐 **分布式环境配置** - Ray 集群配置和资源管理
- 📊 **并行处理** - 多节点并行数据处理
- ⚡ **性能优化** - 资源分配和调度优化
- 🔄 **跨节点通信** - 高效的数据交换机制

**适合场景**：大规模数据处理、高并发推理、多 GPU 训练

👉 [查看详情](distributed-pipeline.md)

### [自定义算子](custom-operators.md)

创建可复用的自定义算子和组件：

- 🛠️ **算子基类** - MapFunction、FilterFunction、SinkFunction
- 🔧 **状态管理** - 有状态算子的实现模式
- 🎯 **生命周期** - open、map/filter、close 方法详解
- 🔌 **最佳实践** - 异常处理、资源管理、日志记录

**适合场景**：业务定制化需求、特殊数据处理逻辑、算法封装

👉 [查看详情](custom-operators.md)

### [复杂工作流](complex-workflows.md)

构建复杂的多阶段流式工作流：

- 🌲 **多分支 Pipeline** - 数据流的分支和合并
- 🔗 **流连接（Join）** - 多数据流的关联处理
- 🔄 **迭代处理** - 循环处理直到满足条件
- 📊 **聚合与窗口** - 时间窗口和聚合操作

**适合场景**：复杂业务逻辑、多模态数据处理、实时分析

👉 [查看详情](complex-workflows.md)

### [高级 RAG 技术](advanced-rag.md)

构建企业级的检索增强生成系统：

- 🗂️ **多源检索** - 从多个知识库并行检索
- 🎯 **分层检索** - 粗粒度 + 细粒度两阶段检索
- 📈 **重排序（Re-ranking）** - 提升检索精度
- 🧠 **混合检索** - 向量检索 + 关键词检索

**适合场景**：知识问答系统、文档分析、智能客服

👉 [查看详情](advanced-rag.md)

### [性能调优](performance-tuning.md)

优化 SAGE 应用的性能和资源使用：

- 📊 **性能分析** - Profiling 和瓶颈定位
- 💾 **内存优化** - 内存使用监控和优化策略
- 🔢 **批处理优化** - 批量处理提升吞吐量
- ⚡ **GPU 加速** - GPU 资源管理和优化

**适合场景**：生产环境部署、高负载场景、成本优化

👉 [查看详情](performance-tuning.md)

### [容错与可靠性](fault-tolerance.md)

构建高可用的容错系统：

- 💾 **检查点（Checkpointing）** - 状态持久化和恢复
- 🔄 **重试机制** - 智能重试和指数退避
- 🛡️ **异常处理** - 优雅降级和错误隔离
- 📊 **监控告警** - 系统健康监控

**适合场景**：生产环境、长时间运行任务、关键业务系统

👉 [查看详情](fault-tolerance.md)

## 🎯 学习路径

=== "分布式系统开发者"

```
1. [分布式 Pipeline](distributed-pipeline.md) - 理解分布式架构
2. [性能调优](performance-tuning.md) - 优化系统性能
3. [容错与可靠性](fault-tolerance.md) - 构建高可用系统
```

=== "算法工程师"

```
1. [自定义算子](custom-operators.md) - 封装算法逻辑
2. [复杂工作流](complex-workflows.md) - 构建算法 Pipeline
3. [性能调优](performance-tuning.md) - 优化推理性能
```

=== "AI 应用开发者"

```
1. [高级 RAG 技术](advanced-rag.md) - 构建智能问答
2. [复杂工作流](complex-workflows.md) - 多模态处理
3. [容错与可靠性](fault-tolerance.md) - 保障服务质量
```

## 🔍 快速参考

### 常见高级场景

| 场景               | 推荐教程                                   | 关键技术             |
| ------------------ | ------------------------------------------ | -------------------- |
| **大规模数据处理** | [分布式 Pipeline](distributed-pipeline.md) | Ray 集群、并行度配置 |
| **实时推荐系统**   | [复杂工作流](complex-workflows.md)         | 流连接、窗口聚合     |
| **智能客服**       | [高级 RAG](advanced-rag.md)                | 多源检索、重排序     |
| **业务定制化**     | [自定义算子](custom-operators.md)          | 算子开发、状态管理   |
| **性能瓶颈**       | [性能调优](performance-tuning.md)          | Profiling、批处理    |
| **生产部署**       | [容错与可靠性](fault-tolerance.md)         | 检查点、监控告警     |

### 核心概念对照

| SAGE 概念      | Apache Flink 类比 | Spark Streaming 类比 |
| -------------- | ----------------- | -------------------- |
| MapFunction    | MapFunction       | map()                |
| FilterFunction | FilterFunction    | filter()             |
| Checkpoint     | Savepoint         | Checkpoint           |
| Parallelism    | Parallelism       | Partitions           |
| Window         | Window            | Window               |

## 📖 前置知识

在学习本章内容前，建议您已经掌握：

- ✅ [快速入门](../../getting-started/quickstart.md) - SAGE 基础使用
- ✅ [基础教程](../basic/streaming-101.md) - 流式处理概念
- ✅ [Kernel 用户指南](../../guides/packages/sage-kernel/README.md) - 执行引擎原理
- ✅ Python 异步编程基础

## 💡 最佳实践提示

### 开发阶段

- 🔍 **小数据测试** - 先用小数据集验证逻辑正确性
- 📊 **逐步扩展** - 逐步增加并行度和数据规模
- 🐛 **详细日志** - 添加充分的日志便于调试

### 生产部署

- 🛡️ **容错设计** - 添加检查点和重试机制
- 📈 **监控指标** - 监控吞吐量、延迟、资源使用
- 🔄 **灰度发布** - 逐步切换流量到新版本

### 性能优化

- ⚡ **批量处理** - 合并小请求减少网络开销
- 💾 **内存管理** - 及时释放大对象，避免 OOM
- 🎯 **资源配置** - 根据负载合理分配 CPU/GPU

## 🚀 下一步

完成高级教程后，您可以：

<div class="grid cards" markdown>

- :material-rocket-launch:{ .lg .middle } **部署应用**

  ______________________________________________________________________

  将 SAGE 应用部署到生产环境

  [:octicons-arrow-right-24: 部署指南](../../guides/deployment/index.md)

- :material-code-braces:{ .lg .middle } **深入源码**

  ______________________________________________________________________

  理解 SAGE 的内部实现

  [:octicons-arrow-right-24: 架构设计](../../concepts/architecture/overview.md)

- :material-account-group:{ .lg .middle } **参与贡献**

  ______________________________________________________________________

  为 SAGE 项目做出贡献

  [:octicons-arrow-right-24: 贡献指南](../../developers/commands.md)

- :material-forum:{ .lg .middle } **加入社区**

  ______________________________________________________________________

  与其他开发者交流经验

  [:octicons-arrow-right-24: 社区](../../community/community.md)

</div>

______________________________________________________________________

**注意**：本章内容持续更新中，部分教程页面正在完善。如有问题或建议，欢迎通过
[GitHub Issues](https://github.com/intellistream/SAGE/issues) 反馈。

## Distributed Pipeline

Build scalable distributed pipelines.

### Setup Distributed Environment

```python
from sage.kernel.api.local_environment import LocalStreamEnvironment

# Create distributed environment
env = LocalStreamEnvironment(
    "distributed_app",
    config={
        "execution_mode": "distributed",
        "ray": {"address": "ray://cluster-head:10001", "num_cpus": 16, "num_gpus": 2},
    },
)
```

### Distributed RAG Pipeline

```python
from sage.libs.io.sources import ChunkedFileSource
from sage.middleware.rag.operators import VLLMEmbeddingOperator, ChromaUpsertOperator

# Distributed embedding and indexing
stream = (
    env.from_source(ChunkedFileSource("large_docs/"))
    .map(
        VLLMEmbeddingOperator(model="sentence-transformers/all-MiniLM-L6-v2"),
        parallelism=8,
    )  # Parallel embedding
    .to_sink(ChromaUpsertOperator(collection="distributed_docs"))
)

env.execute()
```

### Multi-Node Processing

```python
# Process data across multiple nodes
from sage.kernel.api.datastream import DataStream


def create_distributed_pipeline(env):
    # Node 1: Data loading
    loaded = env.from_source(large_source).map(LoadOperator(), parallelism=4)

    # Node 2: Heavy computation
    processed = loaded.map(
        HeavyComputeOperator(),
        parallelism=8,
        resources={"num_cpus": 4, "memory": "8GB"},
    )

    # Node 3: GPU inference
    predicted = processed.map(
        GPUInferenceOperator(), parallelism=2, resources={"num_gpus": 1}
    )

    # Node 4: Aggregation
    aggregated = predicted.reduce(AggregateOperator())

    return aggregated
```

## Custom Operators

Create reusable custom operators.

### Base Custom Operator

```python
from sage.common.core.functions import MapFunction
from sage.kernel.runtime.context import RuntimeContext


class CustomOperator(MapFunction):
    """
    Template for custom operators.
    """

    def __init__(self, config: dict):
        """Initialize with configuration."""
        self.config = config
        self.state = None

    def open(self, context: RuntimeContext):
        """
        Initialize resources.
        Called once per parallel instance.
        """
        self.context = context
        self.state = self._initialize_state()

    def map(self, record):
        """
        Process a single record.
        Called for each record.
        """
        return self._process(record)

    def close(self):
        """
        Clean up resources.
        Called once when operator terminates.
        """
        if self.state:
            self.state.cleanup()

    def _initialize_state(self):
        """Override to initialize custom state."""
        return {}

    def _process(self, record):
        """Override to implement custom logic."""
        return record
```

### LLM Operator Example

```python
from openai import OpenAI


class CustomLLMOperator(MapFunction):
    """
    Custom LLM operator with retry logic and caching.
    """

    def __init__(self, model="gpt-4", max_retries=3):
        self.model = model
        self.max_retries = max_retries
        self.cache = {}

    def open(self, context):
        self.client = OpenAI()
        self.logger = context.get_logger()

    def map(self, record):
        prompt = record.get("prompt")

        # Check cache
        if prompt in self.cache:
            self.logger.info("Cache hit")
            return self.cache[prompt]

        # Generate with retries
        for attempt in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                )
                result = response.choices[0].message.content

                # Cache result
                self.cache[prompt] = result
                return result

            except Exception as e:
                self.logger.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt == self.max_retries - 1:
                    raise
                time.sleep(2**attempt)  # Exponential backoff
```

### Filter Operator Example

```python
from sage.common.core.functions import FilterFunction


class CustomFilterOperator(FilterFunction):
    """
    Custom filter with complex conditions.
    """

    def __init__(self, min_score=0.5, required_fields=None):
        self.min_score = min_score
        self.required_fields = required_fields or []

    def filter(self, record) -> bool:
        # Check required fields
        for field in self.required_fields:
            if field not in record:
                return False

        # Check score threshold
        if record.get("score", 0) < self.min_score:
            return False

        # Custom validation logic
        return self._validate(record)

    def _validate(self, record):
        """Override for custom validation."""
        return True
```

### Stateful Operator Example

```python
class WindowAggregateOperator(MapFunction):
    """
    Aggregate records over a time window.
    """

    def __init__(self, window_size=10, aggregate_fn=None):
        self.window_size = window_size
        self.aggregate_fn = aggregate_fn or (lambda x: sum(x) / len(x))
        self.window = []

    def map(self, record):
        self.window.append(record)

        if len(self.window) >= self.window_size:
            result = self.aggregate_fn(self.window)
            self.window = []
            return result

        return None  # No output until window is full
```

## Complex Workflows

Build sophisticated multi-stage workflows.

### Multi-Branch Pipeline

```python
def create_branching_pipeline(env):
    # Main stream
    main_stream = env.from_source(source)

    # Branch 1: NLP processing
    nlp_stream = (
        main_stream.filter(lambda r: r.type == "text")
        .map(TokenizeOperator())
        .map(NEROperator())
        .to_sink(nlp_sink)
    )

    # Branch 2: Vision processing
    vision_stream = (
        main_stream.filter(lambda r: r.type == "image")
        .map(ResizeOperator())
        .map(ObjectDetectionOperator())
        .to_sink(vision_sink)
    )

    # Branch 3: Audio processing
    audio_stream = (
        main_stream.filter(lambda r: r.type == "audio")
        .map(TranscribeOperator())
        .map(SentimentOperator())
        .to_sink(audio_sink)
    )

    return env
```

### Join Multiple Streams

```python
from sage.kernel.api.datastream import DataStream


def create_join_pipeline(env):
    # Stream 1: User data
    users = env.from_source(user_source).key_by(lambda r: r.user_id)

    # Stream 2: Event data
    events = env.from_source(event_source).key_by(lambda r: r.user_id)

    # Join streams
    joined = users.join(events).map(
        lambda pair: {
            "user": pair[0],
            "event": pair[1],
            "enriched": enrich(pair[0], pair[1]),
        }
    )

    joined.to_sink(output_sink)
    return env
```

### Iterative Refinement

```python
class IterativeRefinementOperator(MapFunction):
    """
    Iteratively refine results until quality threshold.
    """

    def __init__(self, max_iterations=5, quality_threshold=0.9):
        self.max_iterations = max_iterations
        self.quality_threshold = quality_threshold

    def map(self, record):
        result = record

        for iteration in range(self.max_iterations):
            # Process/refine result
            result = self.process(result)

            # Check quality
            quality = self.evaluate_quality(result)

            if quality >= self.quality_threshold:
                result["iterations"] = iteration + 1
                return result

        # Return best effort
        result["iterations"] = self.max_iterations
        result["warning"] = "Max iterations reached"
        return result

    def process(self, record):
        # Implement refinement logic
        return record

    def evaluate_quality(self, record):
        # Implement quality metric
        return 0.0
```

## Advanced RAG

Build sophisticated RAG systems.

### Multi-Source RAG

```python
from sage.middleware.rag.operators import (
    ChromaRetrieverOperator,
    OpenAIGeneratorOperator,
    ContextFusionOperator,
)


def create_multi_source_rag(env):
    # Query stream
    queries = env.from_source(query_source)

    # Retrieve from multiple sources
    docs_retriever = ChromaRetrieverOperator(collection="documents")
    code_retriever = ChromaRetrieverOperator(collection="code")
    web_retriever = ChromaRetrieverOperator(collection="web")

    # Parallel retrieval
    doc_results = queries.map(docs_retriever, parallelism=2)
    code_results = queries.map(code_retriever, parallelism=2)
    web_results = queries.map(web_retriever, parallelism=2)

    # Fuse contexts
    fused = (
        doc_results.union(code_results).union(web_results).map(ContextFusionOperator())
    )

    # Generate response
    responses = fused.map(OpenAIGeneratorOperator(model="gpt-4", temperature=0.7))

    responses.to_sink(output_sink)
    return env
```

### Hierarchical RAG

```python
class HierarchicalRAGOperator(MapFunction):
    """
    Two-stage retrieval: coarse then fine.
    """

    def __init__(self):
        self.coarse_retriever = ChromaRetrieverOperator(
            collection="summaries", top_k=20
        )
        self.fine_retriever = ChromaRetrieverOperator(collection="chunks", top_k=5)

    def open(self, context):
        self.coarse_retriever.open(context)
        self.fine_retriever.open(context)

    def map(self, query):
        # Stage 1: Coarse retrieval
        coarse_results = self.coarse_retriever.map(query)

        # Extract document IDs
        doc_ids = [r["doc_id"] for r in coarse_results]

        # Stage 2: Fine retrieval within selected docs
        query_with_filter = {**query, "filter": {"doc_id": {"$in": doc_ids}}}
        fine_results = self.fine_retriever.map(query_with_filter)

        return {
            "query": query,
            "coarse_results": coarse_results,
            "fine_results": fine_results,
        }
```

### RAG with Re-ranking

```python
from sage.middleware.rag.operators import RerankOperator


def create_reranking_rag(env):
    stream = (
        env.from_source(query_source)
        # Initial retrieval (high recall)
        .map(ChromaRetrieverOperator(collection="docs", top_k=50))
        # Re-rank (high precision)
        .map(RerankOperator(model="cross-encoder/ms-marco-MiniLM-L-12-v2", top_k=5))
        # Generate with best contexts
        .map(OpenAIGeneratorOperator(model="gpt-4")).to_sink(output_sink)
    )

    return env
```

## Performance Tuning

Optimize SAGE applications for production.

### Profiling

```python
import cProfile
import pstats
from sage.kernel.api.local_environment import LocalStreamEnvironment


def profile_pipeline():
    profiler = cProfile.Profile()
    profiler.enable()

    # Run pipeline
    env = LocalStreamEnvironment("profiling_app")
    create_pipeline(env)
    env.execute()

    profiler.disable()

    # Analyze results
    stats = pstats.Stats(profiler)
    stats.sort_stats("cumulative")

    print("\n=== Top 20 Functions by Cumulative Time ===")
    stats.print_stats(20)

    print("\n=== Top 20 Functions by Total Time ===")
    stats.sort_stats("tottime")
    stats.print_stats(20)
```

### Memory Optimization

```python
import gc
from memory_profiler import profile


class MemoryEfficientOperator(MapFunction):
    """
    Process large data with controlled memory usage.
    """

    @profile
    def map(self, record):
        # Process in chunks
        results = []
        for chunk in self.chunk_data(record):
            result = self.process_chunk(chunk)
            results.append(result)

            # Explicit cleanup
            del chunk
            gc.collect()

        return self.merge_results(results)

    def chunk_data(self, record, chunk_size=1000):
        data = record.get("data", [])
        for i in range(0, len(data), chunk_size):
            yield data[i : i + chunk_size]

    def process_chunk(self, chunk):
        return [self.process_item(item) for item in chunk]

    def merge_results(self, results):
        return [item for chunk in results for item in chunk]
```

### Batch Optimization

```python
class BatchedLLMOperator(MapFunction):
    """
    Batch LLM requests for efficiency.
    """

    def __init__(self, batch_size=10, batch_timeout=1.0):
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.buffer = []
        self.last_batch_time = time.time()

    def map(self, record):
        self.buffer.append(record)

        # Check if batch is ready
        batch_ready = (
            len(self.buffer) >= self.batch_size
            or time.time() - self.last_batch_time > self.batch_timeout
        )

        if batch_ready:
            results = self.process_batch(self.buffer)
            self.buffer = []
            self.last_batch_time = time.time()
            return results

        return None

    def process_batch(self, batch):
        # Batch API call
        prompts = [r["prompt"] for r in batch]
        responses = self.llm.batch_generate(prompts)
        return [{"prompt": p, "response": r} for p, r in zip(prompts, responses)]
```

## Fault Tolerance

Build resilient pipelines.

### Checkpointing

```python
env = LocalStreamEnvironment(
    "fault_tolerant_app",
    config={
        "fault_tolerance": {
            "strategy": "checkpoint",
            "checkpoint_interval": 60.0,
            "checkpoint_dir": "/data/checkpoints",
            "checkpoint_mode": "exactly_once",
        }
    },
)

# Pipeline will automatically checkpoint
stream = env.from_source(source).map(operator1).map(operator2).to_sink(sink)

env.execute()
```

### Retry Logic

```python
class RetryOperator(MapFunction):
    """
    Retry failed operations with exponential backoff.
    """

    def __init__(self, max_retries=3, base_delay=1.0):
        self.max_retries = max_retries
        self.base_delay = base_delay

    def map(self, record):
        last_error = None

        for attempt in range(self.max_retries + 1):
            try:
                return self.process(record)
            except Exception as e:
                last_error = e

                if attempt < self.max_retries:
                    delay = self.base_delay * (2**attempt)
                    self.logger.warning(
                        f"Attempt {attempt + 1} failed, " f"retrying in {delay}s: {e}"
                    )
                    time.sleep(delay)
                else:
                    self.logger.error(f"All retries failed: {e}")

        # All retries failed
        raise last_error

    def process(self, record):
        # Implement processing logic
        return record
```

## See Also

- [Best Practices](../../guides/best-practices/index.md)
- [API Reference](../../api-reference/index.md)
- [Architecture](../../concepts/architecture/overview.md)
