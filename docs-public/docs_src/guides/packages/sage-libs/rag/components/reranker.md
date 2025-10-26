# 重排序组件 (Reranking Components)

本文档详细介绍SAGE框架中重排序组件的使用方法。重排序组件是RAG系统的检索优化层，负责对初步检索结果进行精确重新排序，显著提升检索质量和最终答案准确性。

## 组件概述

### 核心功能

重排序组件在RAG系统中承担以下关键职责：

- **精确排序**：对粗排检索结果进行精细化重新排序
- **语义理解**：深度理解查询与文档间的语义关联性
- **质量提升**：显著改善检索精度，减少噪声文档影响
- **性能平衡**：在准确性和计算效率间找到最优平衡点

### 技术架构

重排序采用两阶段检索架构：

```
用户查询 → 粗排检索(Retrieval) → 精排重排序(Reranking) → 高质量结果
   ↓           ↓                    ↓                    ↓
 向量化    →  向量相似度          →  语义相关性         →  最终排序
```

### 支持的重排序器

| 组件名              | 模型基础              | 适用场景       | 特点                 |
| ------------------- | --------------------- | -------------- | -------------------- |
| `BGEReranker`       | BGE-reranker-v2-m3    | 通用文本重排序 | 轻量级，速度快       |
| `LLMbased_Reranker` | BGE-reranker-v2-gemma | 复杂语义理解   | 精度高，支持复杂推理 |

## BGEReranker

### 组件描述

`BGEReranker`基于BAAI/bge-reranker-v2-m3模型的传统重排序器，专门优化中英文跨语言检索场景，在保持较高精度的同时提供良好的推理速度。

### 技术规格

**模型特性**：

- 模型基础：BAAI/bge-reranker-v2-m3
- 支持语言：中文、英文、多语言混合
- 输入长度：最大8192 tokens
- 推理速度：中等（适合实时应用）

**配置参数**：

| 参数名           | 类型 | 默认值                    | 说明                      |
| ---------------- | ---- | ------------------------- | ------------------------- |
| `model_name`     | str  | "BAAI/bge-reranker-v2-m3" | 重排序模型名称            |
| `topk` / `top_k` | int  | 3                         | 返回的顶部文档数量        |
| `device`         | str  | "auto"                    | 运行设备（cuda/cpu/auto） |
| `batch_size`     | int  | 32                        | 批处理大小                |
| `max_length`     | int  | 512                       | 最大输入长度              |

### 实现示例

#### 基础重排序操作

```python
from sage.libs.rag.reranker import BGEReranker

# 配置重排序器
config = {
    "model_name": "BAAI/bge-reranker-v2-m3",
    "topk": 5,
    "device": "cuda",  # 如果有GPU可用
}

# 初始化重排序器
reranker = BGEReranker(config)

# 准备测试数据
query = "向量数据库的主要优势是什么？"
candidate_documents = [
    "向量数据库支持高维向量的高效存储和检索，特别适合AI应用。",
    "传统关系数据库主要处理结构化数据，使用SQL查询语言。",
    "向量数据库在相似度检索方面具有显著优势，支持语义搜索。",
    "NoSQL数据库提供了灵活的数据模型，支持分布式存储。",
    "向量数据库通过向量相似度计算实现快速的语义匹配。",
    "云计算平台提供了弹性的计算和存储资源。",
]

# 执行重排序
query_result, reranked_docs = reranker.execute((query, candidate_documents))

print(f"原始查询: {query_result}")
print(f"重排序结果 (Top-{config['topk']}):")
for i, doc in enumerate(reranked_docs, 1):
    print(f"{i}. {doc}")
```

#### 批量重排序处理

```python
# 配置批量处理
batch_config = {
    "model_name": "BAAI/bge-reranker-v2-m3",
    "topk": 3,
    "batch_size": 16,  # 提高批处理效率
    "device": "cuda",
}

batch_reranker = BGEReranker(batch_config)

# 多查询批量处理
queries = ["什么是机器学习？", "深度学习的应用领域", "自然语言处理技术"]

# 对应的候选文档集合
doc_sets = [
    ["机器学习是AI的子领域...", "深度学习使用神经网络...", ...],
    ["深度学习在图像识别...", "NLP是AI的重要分支...", ...],
    ["NLP处理人类语言...", "语言模型的发展历程...", ...],
]

# 批量执行重排序
for query, docs in zip(queries, doc_sets):
    _, reranked = batch_reranker.execute((query, docs))
    print(f"查询: {query}")
    print(f"最佳匹配: {reranked[0][:100]}...")
    print()
```

## LLMbased_Reranker

### 组件描述

`LLMbased_Reranker`基于BAAI/bge-reranker-v2-gemma模型，采用大语言模型架构，在复杂语义理解和推理任务中表现卓越。

### 技术规格

**模型特性**：

- 模型基础：BAAI/bge-reranker-v2-gemma
- 架构类型：基于Gemma的生成式重排序器
- 推理能力：支持复杂语义推理和多文档关联
- 精度表现：在复杂场景下精度更高

**配置参数**：

| 参数名           | 类型  | 默认值                       | 说明                       |
| ---------------- | ----- | ---------------------------- | -------------------------- |
| `model_name`     | str   | "BAAI/bge-reranker-v2-gemma" | LLM重排序模型              |
| `topk`           | int   | 3                            | 输出文档数量               |
| `device`         | str   | "auto"                       | 运行设备                   |
| `temperature`    | float | 0.1                          | 生成温度（用于排序置信度） |
| `max_new_tokens` | int   | 64                           | 最大生成token数            |

### 实现示例

#### 复杂查询重排序

```python
from sage.libs.rag.reranker import LLMbased_Reranker

# 配置LLM重排序器
llm_config = {
    "model_name": "BAAI/bge-reranker-v2-gemma",
    "topk": 4,
    "temperature": 0.1,
    "device": "cuda",
}

# 初始化LLM重排序器
llm_reranker = LLMbased_Reranker(llm_config)

# 复杂推理查询
complex_query = "比较分析向量数据库和传统数据库在AI应用中的性能差异"
complex_documents = [
    "向量数据库专为高维向量检索优化，在AI相似度搜索中性能卓越。",
    "传统关系数据库擅长结构化数据管理，支持复杂的事务处理。",
    "在机器学习特征存储方面，向量数据库提供更高的查询效率。",
    "传统数据库的ACID特性保证了数据一致性，但在向量检索上性能有限。",
    "向量数据库支持近似最近邻搜索，大幅提升大规模数据检索速度。",
    "混合数据库架构结合了两者优势，在不同场景下灵活切换。",
]

# 执行复杂查询重排序
query_result, llm_reranked = llm_reranker.execute((complex_query, complex_documents))

print(f"复杂查询: {query_result}")
print("LLM重排序结果:")
for i, doc in enumerate(llm_reranked, 1):
    print(f"{i}. {doc}")
```

## 性能对比与选择指南

### 模型对比分析

| 对比维度       | BGEReranker | LLMbased_Reranker |
| -------------- | ----------- | ----------------- |
| **推理速度**   | 快速        | 中等              |
| **内存消耗**   | 较低        | 较高              |
| **准确性**     | 高          | 更高              |
| **复杂推理**   | 基础        | 强                |
| **多语言支持** | 优秀        | 优秀              |
| **部署复杂度** | 简单        | 中等              |

### 应用场景选择

#### 推荐使用BGEReranker的场景：

1. **实时应用**：对响应时间要求严格的在线服务
1. **资源受限**：计算资源或内存有限的环境
1. **简单查询**：主要处理事实性查询和直接匹配
1. **高并发**：需要处理大量并发请求的系统

#### 推荐使用LLMbased_Reranker的场景：

1. **复杂推理**：需要多文档综合分析的查询
1. **高精度要求**：对检索质量要求极高的应用
1. **离线处理**：批处理或对实时性要求不严格的场景
1. **研究分析**：学术研究或深度内容分析任务

## 集成最佳实践

### 与检索器集成

```python
from sage.libs.rag.retriever import ChromaRetriever
from sage.libs.rag.reranker import BGEReranker

# 配置检索-重排序流水线
retriever_config = {
    "top_k": 20,  # 粗排获取更多候选
    "embedding": {"model": "sentence-transformers/all-MiniLM-L6-v2"},
}

reranker_config = {
    "model_name": "BAAI/bge-reranker-v2-m3",
    "topk": 5,  # 精排获取最优结果
}


# 构建检索-重排序流水线
def retrieve_and_rerank(query):
    # 第一阶段：粗排检索
    retriever = ChromaRetriever(retriever_config)
    _, candidates = retriever.execute(query)

    # 第二阶段：精排重排序
    reranker = BGEReranker(reranker_config)
    _, final_results = reranker.execute((query, candidates))

    return final_results


# 使用流水线
query = "向量数据库的性能优化方法"
best_results = retrieve_and_rerank(query)
```

### 性能监控与优化

```python
import time
from typing import List, Tuple


class RerankerBenchmark:
    def __init__(self, reranker, test_queries: List[str], test_docs: List[List[str]]):
        self.reranker = reranker
        self.test_queries = test_queries
        self.test_docs = test_docs

    def benchmark(self) -> dict:
        total_time = 0
        total_queries = len(self.test_queries)

        for query, docs in zip(self.test_queries, self.test_docs):
            start_time = time.time()
            _ = self.reranker.execute((query, docs))
            end_time = time.time()

            total_time += end_time - start_time

        avg_latency = total_time / total_queries
        qps = 1.0 / avg_latency

        return {
            "average_latency": avg_latency,
            "queries_per_second": qps,
            "total_time": total_time,
            "total_queries": total_queries,
        }


# 性能测试
benchmark = RerankerBenchmark(reranker, test_queries, test_documents)
performance_metrics = benchmark.benchmark()
print(f"平均延迟: {performance_metrics['average_latency']:.3f}s")
print(f"QPS: {performance_metrics['queries_per_second']:.1f}")
```

### 输出示例

```
原始查询: 什么是人工智能？
重排序后的文档:
1. 人工智能是计算机科学的一个分支，致力于创建能够执行通常需要人类智能的任务的系统。
2. 机器学习是人工智能的一个子集，通过算法让计算机从数据中学习。
3. 自然语言处理是人工智能的一个领域，专注于计算机与人类语言的交互。
```

## LLMbased_Reranker 使用方法

### 基本配置

```python
config = {"topk": 3}
```

### 初始化和使用

```python
from sage.libs.rag.reranker import LLMbased_Reranker

# 初始化 LLM 重排序器
reranker = LLMbased_Reranker(config, model_name="BAAI/bge-reranker-v2-gemma")

# 使用方法与 BGEReranker 相同
query = "Python 中如何处理异常？"
documents = [
    "Python 使用 try-except 语句来处理异常。",
    "Java 中的异常处理使用 try-catch 块。",
    "在 Python 中，finally 块总是会执行。",
    "异常是程序运行时发生的错误。",
    "Python 提供了多种内置异常类型。",
]

input_data = (query, documents)
result_query, reranked_docs = reranker.execute(input_data)

print(f"查询: {result_query}")
print("LLM 重排序结果:")
for i, doc in enumerate(reranked_docs, 1):
    print(f"{i}. {doc}")
```

## 集成到 SAGE 管道中

```python
from sage.core.pipeline import Pipeline
from sage.libs.rag.reranker import BGEReranker

# 创建重排序组件
reranker_config = {"model_name": "BAAI/bge-reranker-v2-m3", "topk": 3}
reranker = BGEReranker(reranker_config)

# 集成到管道中
pipeline = Pipeline()
pipeline.add_component("reranker", reranker)

# 运行管道
result = pipeline.run({"query": query, "documents": documents})
```
