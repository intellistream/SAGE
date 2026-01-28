# Reranker 服务使用指南

## 服务信息

- **服务地址**: `http://11.11.11.31:8907/v1`
- **模型**: `BAAI/bge-reranker-v2-m3`
- **用途**: 专门训练的文档重排序模型，比 embedding 相似度更准确

## 使用方式

### 1. SimpleReranker（推荐用于标准RAG）

**使用真实 reranker 服务**（默认，最准确）：
```python
.map(
    SimpleReranker,
    parallelism=self.config.parallelism,
    use_reranker_service=True,  # ✅ 默认，使用真实reranker
    reranker_base_url="http://11.11.11.31:8907/v1",
    reranker_model="BAAI/bge-reranker-v2-m3",
    top_k=5,
    stage=3,
)
```

**Fallback 到 embedding 相似度**：
```python
.map(
    SimpleReranker,
    parallelism=self.config.parallelism,
    use_reranker_service=False,  # 使用embedding相似度
    embedding_base_url=self.config.embedding_base_url,
    embedding_model=self.config.embedding_model,
    top_k=5,
    stage=3,
)
```

### 2. CPUIntensiveReranker（用于性能测试）

**三种重排序方式**（按准确性排序）：

#### 方式1: 真实 Reranker 服务（最准确）
```python
CPUIntensiveReranker(
    num_candidates=500,
    top_k=10,
    use_reranker_service=True,  # ✅ 优先级最高，最准确
    reranker_base_url="http://11.11.11.31:8907/v1",
    reranker_model="BAAI/bge-reranker-v2-m3",
)
```
- ✅ 专门训练的排序模型，最准确
- ✅ 适合准确性测试和真实RAG场景
- ⚠️  包含网络I/O + 模型推理

#### 方式2: 真实 Embedding + CPU计算（准确 + CPU密集）
```python
CPUIntensiveReranker(
    num_candidates=500,
    vector_dim=1024,
    top_k=10,
    use_reranker_service=False,
    use_real_embedding=True,
    embedding_base_url=self.config.embedding_base_url,
    embedding_model=self.config.embedding_model,
)
```
- ✅ 真实语义向量
- ✅ CPU密集的余弦相似度计算
- ⚠️  包含网络I/O + CPU计算

#### 方式3: 确定性伪随机向量（纯CPU测试）
```python
CPUIntensiveReranker(
    num_candidates=500,
    vector_dim=1024,
    top_k=10,
    use_reranker_service=False,
    use_real_embedding=False,  # ✅ 默认
)
```
- ✅ 纯CPU计算，无网络依赖
- ✅ 确定性（同一文档总是生成相同向量）
- ✅ 适合纯CPU性能测试
- ⚠️  不是真实语义向量

### 3. 直接调用 Reranker 服务

```python
from operators import rerank_with_service

# 调用 reranker 服务
results = rerank_with_service(
    query="What is machine learning?",
    documents=[
        "Machine learning is a subset of AI...",
        "Python is a programming language...",
        "Deep learning uses neural networks...",
    ],
    base_url="http://11.11.11.31:8907/v1",
    model="BAAI/bge-reranker-v2-m3",
    top_k=2,
)

# 返回格式: [{"index": 0, "relevance_score": 0.95}, {"index": 2, "relevance_score": 0.87}]
for result in results:
    print(f"Doc {result['index']}: score={result['relevance_score']:.3f}")
```

## 完整 RAG Pipeline 示例

### 标准 RAG（使用真实 reranker）
```python
env.from_source(FiQATaskSource, num_tasks=100)
    .map(
        FiQAFAISSRetriever,
        parallelism=1,
        top_k=20,  # 检索20个候选
        stage=1,
    )
    .map(
        SimpleReranker,
        parallelism=self.config.parallelism,
        use_reranker_service=True,  # ✅ 真实reranker
        top_k=5,  # 重排序后保留5个
        stage=2,
    )
    .map(SimplePromptor, parallelism=self.config.parallelism, stage=3)
    .map(SimpleGenerator, parallelism=self.config.parallelism, stage=4)
    .sink(MetricsSink, metrics_collector=self.metrics)
```

### CPU密集型测试（三种模式对比）
```python
# 测试1: 真实reranker（最准确）
.map(CPUIntensiveReranker, use_reranker_service=True, top_k=10, stage=2)

# 测试2: 真实embedding（准确 + CPU密集）
.map(CPUIntensiveReranker, use_real_embedding=True, top_k=10, stage=2)

# 测试3: 伪随机向量（纯CPU）
.map(CPUIntensiveReranker, use_real_embedding=False, top_k=10, stage=2)
```

## 性能对比

| 重排序方法 | 准确性 | CPU使用率 | 网络I/O | 适用场景 |
|-----------|-------|----------|---------|----------|
| Reranker服务 | ⭐⭐⭐⭐⭐ | ~10% | ✅ 有 | 生产RAG、准确性测试 |
| Embedding + CPU | ⭐⭐⭐⭐ | 50-80% | ✅ 有 | CPU性能测试（真实语义） |
| 伪随机向量 | ⭐ | 70-100% | ❌ 无 | 纯CPU性能测试 |
| DelaySimulator | N/A | ~0% | ❌ 无 | ❌ 不推荐（无资源争用） |

## Reranker vs Embedding 相似度

### Reranker 的优势

1. **专门训练**: BGE-reranker 专门针对文档排序任务训练
2. **交互建模**: 考虑 query 和 document 之间的交互关系
3. **更高准确性**: 在排序任务上比简单的向量相似度更准确

### 使用建议

- **生产环境**: 使用 `SimpleReranker(use_reranker_service=True)`
- **准确性测试**: 使用 `CPUIntensiveReranker(use_reranker_service=True)`
- **CPU性能测试**: 使用 `CPUIntensiveReranker(use_real_embedding=True/False)`
- **快速原型**: 可以暂时使用 embedding 相似度作为 fallback

## Fallback 机制

所有 reranker 算子都实现了自动 fallback：

```
use_reranker_service=True
  ↓ (失败)
use_real_embedding=True
  ↓ (失败)
use_real_embedding=False (确定性伪随机)
  ↓ (失败)
保持原有排序
```

这确保了即使某个服务不可用，pipeline 仍能继续运行。

## 测试 Reranker 服务

```bash
# 测试 reranker 服务是否可用
curl -X POST http://11.11.11.31:8907/v1/rerank \
  -H "Content-Type: application/json" \
  -d '{
    "model": "BAAI/bge-reranker-v2-m3",
    "query": "What is machine learning?",
    "documents": [
      "Machine learning is a subset of artificial intelligence.",
      "Python is a programming language.",
      "Deep learning uses neural networks."
    ],
    "top_n": 2
  }'

# 预期返回:
# {
#   "results": [
#     {"index": 0, "relevance_score": 0.95},
#     {"index": 2, "relevance_score": 0.78}
#   ]
# }
```

## 配置优先级

当同时设置多个标志时，优先级为：

1. `use_reranker_service=True` → 使用真实 reranker 服务（最高优先级）
2. `use_real_embedding=True` → 使用真实 embedding + CPU计算
3. `use_real_embedding=False` → 使用确定性伪随机向量

## 总结

通过集成真实的 reranker 服务（BAAI/bge-reranker-v2-m3），SAGE benchmark 现在支持：

- ✅ **最准确的重排序**：专门训练的排序模型
- ✅ **灵活配置**：可选择 reranker/embedding/伪随机三种模式
- ✅ **自动 fallback**：服务不可用时自动降级
- ✅ **真实场景**：更接近生产环境的 RAG pipeline
- ✅ **性能测试**：仍支持纯 CPU 密集型测试

这使得 benchmark 既能测试真实的 RAG 准确性，又能测试调度器的性能！🎯
