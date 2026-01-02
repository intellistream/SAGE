# RAG API 参考指南

RAG（Retrieval-Augmented Generation）模块提供完整的检索增强生成解决方案，结合知识检索和文本生成能力，为用户提供准确、丰富的智能问答和内容生成服务。

## 模块概述

RAG 模块实现了先进的检索增强生成系统，通过结合外部知识库的检索能力和大语言模型的生成能力，显著提升了AI系统的知识覆盖面和答案准确性。

## 核心组件 API

### Retriever（检索器）

智能检索器，实现高效的向量检索算法：

```python
from sage.libs.rag.retriever import Retriever

retriever = Retriever(
    index_path="knowledge_base.faiss",
    embedding_model="sentence-transformers/all-MiniLM-L6-v2",
)

# 执行检索
results = retriever.retrieve(query="什么是机器学习？", top_k=5)
```

**功能特性**：

- 支持多种检索策略（稠密检索、稀疏检索、混合检索）
- 提供语义相似度计算
- 支持多模态检索（文本、图像、音频）
- 包含检索结果排序和过滤

### Generator（生成器）

基于检索内容的智能文本生成：

```python
from sage.libs.rag.generator import Generator

generator = Generator(model_name="gpt-3.5-turbo", max_tokens=512)

# 基于检索结果生成回答
answer = generator.generate(query=question, contexts=retrieved_docs)
```

**功能特性**：

- 支持多种生成模式（摘要、问答、创作）
- 提供可控的生成参数配置
- 支持多轮对话和上下文保持
- 包含生成质量控制机制

### Reranker（重排序器）

对检索结果进行智能重排序：

```python
from sage.libs.rag.reranker import Reranker

reranker = Reranker(model="cross-encoder/ms-marco-MiniLM-L-12-v2")
reranked_results = reranker.rerank(query, retrieved_docs)
```

### 其他核心组件

- **`searcher.py`**: 统一搜索接口，集成多种搜索后端
- **`chunk.py`**: 智能文档分块算法
- **`promptor.py`**: 专业的提示词模板管理
- **`evaluate.py`**: 全面的RAG系统评估框架

## RAG 工作流程

```
Query → Retriever → Reranker → Generator → Answer
  ↓         ↓          ↓         ↓         ↓
Promptor  Searcher   Evaluate  Writer   Profiler
```

## 快速开始

### 基础用法

```python
from sage.libs.rag import Retriever, Generator, RAGPipeline

# 创建RAG组件
retriever = Retriever(
    index_path="knowledge_base.faiss",
    embedding_model="sentence-transformers/all-MiniLM-L6-v2",
)

generator = Generator(model_name="gpt-3.5-turbo", max_tokens=512)

# 创建RAG管道
rag = RAGPipeline(retriever=retriever, generator=generator)

# 执行问答
question = "什么是机器学习？"
answer = rag.generate(question, top_k=5)
print(answer)
```

### 高级配置

#### 检索配置

```python
retriever_config = {
    "top_k": 10,
    "similarity_threshold": 0.7,
    "retrieval_method": "hybrid",
    "rerank_enabled": True,
    "cache_enabled": True,
}
```

#### 生成配置

```python
generator_config = {
    "model": "gpt-4",
    "temperature": 0.7,
    "max_tokens": 1000,
    "top_p": 0.9,
    "presence_penalty": 0.1,
}
```

#### 评估配置

```python
evaluation_config = {
    "metrics": ["bleu", "rouge", "bertscore"],
    "reference_answers": True,
    "human_evaluation": False,
    "batch_size": 32,
}
```

## 知识库构建

### 文档预处理

```python
from sage.libs.rag.chunk import DocumentChunker

chunker = DocumentChunker(chunk_size=512, overlap=50, strategy="semantic")

chunks = chunker.chunk_documents(documents)
```

### 向量索引构建

```python
from sage.libs.rag.retriever import VectorIndexBuilder

builder = VectorIndexBuilder(embedding_model="text-embedding-ada-002", dimension=1536)

index = builder.build_index(chunks)
builder.save_index(index, "knowledge_base.faiss")
```

## 使用场景

- **智能问答**: 基于知识库的精准问答
- **内容创作**: 基于参考资料的内容生成
- **研究助手**: 学术研究和文献调研
- **教育辅导**: 个性化学习内容生成
- **客服系统**: 基于企业知识库的客服

## 性能优化

### 检索优化

- 向量索引优化（HNSW、IVF等）
- 缓存机制
- 批量检索
- 异步处理

### 生成优化

- 模型推理加速
- 批量生成
- 流式输出
- 缓存复用

### 系统优化

- 内存使用优化
- 并发处理
- 负载均衡
- 监控告警

## 评估体系

### 检索评估

- Precision@K, Recall@K
- Mean Reciprocal Rank (MRR)
- Normalized Discounted Cumulative Gain (NDCG)

### 生成评估

- BLEU Score
- ROUGE Score
- BERTScore
- 事实准确性评估

### 端到端评估

- 答案质量评估
- 用户满意度
- 响应时间
- 系统稳定性

## 最佳实践

1. **知识库质量**: 确保高质量的知识库内容
1. **分块策略**: 选择合适的文档分块方法
1. **检索调优**: 优化检索参数和策略
1. **提示词工程**: 设计有效的提示词模板
1. **持续评估**: 建立持续的评估和优化机制

## 相关文档

- RAG 组件详解 - 查看导航栏中的 RAG 组件各章节
- RAG 示例 - 查看导航栏中的 RAG 示例各章节
