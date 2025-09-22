# SAGE RAG (检索增强生成) 模块

RAG模块提供完整的检索增强生成解决方案，结合知识检索和文本生成能力，为用户提供准确、丰富的智能问答和内容生成服务。

## 模块概述

RAG（Retrieval-Augmented Generation）模块实现了先进的检索增强生成系统，通过结合外部知识库的检索能力和大语言模型的生成能力，显著提升了AI系统的知识覆盖面和答案准确性。

## 核心组件

### `retriever.py`
智能检索器：
- 实现高效的向量检索算法
- 支持多种检索策略（稠密检索、稀疏检索、混合检索）
- 提供语义相似度计算
- 支持多模态检索（文本、图像、音频）
- 包含检索结果排序和过滤

### `generator.py`
内容生成器：
- 基于检索内容的智能文本生成
- 支持多种生成模式（摘要、问答、创作）
- 提供可控的生成参数配置
- 支持多轮对话和上下文保持
- 包含生成质量控制机制

### `reranker.py`
结果重排序器：
- 对检索结果进行智能重排序
- 基于相关性和质量的多维评分
- 支持学习型排序算法
- 提供个性化排序策略
- 包含排序效果评估

### `evaluate.py`
评估系统：
- 全面的RAG系统评估框架
- 支持多种评估指标（BLEU、ROUGE、BERTScore等）
- 提供自动化评估流程
- 支持人工评估接口
- 包含评估报告生成

### `searcher.py`
搜索引擎：
- 统一的搜索接口
- 集成多种搜索后端（Elasticsearch、Faiss等）
- 支持混合搜索策略
- 提供搜索结果缓存
- 包含搜索性能优化

### `chunk.py`
文档分块器：
- 智能的文档分块算法
- 支持多种分块策略（固定长度、语义分块、滑动窗口）
- 保持语义完整性
- 提供重叠窗口处理
- 支持多种文档格式

### `promptor.py`
提示词管理器：
- 专业的提示词模板管理
- 支持动态提示词生成
- 提供提示词优化建议
- 支持多语言提示词
- 包含提示词效果评测

### `writer.py`
内容写作器：
- 专业的内容创作工具
- 支持多种写作风格和格式
- 提供写作质量检查
- 支持协同写作功能
- 包含写作过程记录

### `profiler.py`
性能分析器：
- RAG系统性能监控
- 详细的性能指标收集
- 瓶颈识别和优化建议
- 支持实时性能监控
- 提供性能报告生成

### `trigger.py`
触发器管理：
- 智能的检索触发机制
- 支持多种触发条件
- 提供触发策略配置
- 支持自适应触发调整
- 包含触发效果分析

### `arxiv.py`
学术资源集成：
- ArXiv论文数据集成
- 学术搜索和检索
- 论文内容解析和结构化
- 引用关系分析
- 学术知识图谱构建

### [测试模块](./tests/)
全面的RAG功能测试覆盖。

## 主要特性

- **高精度检索**: 先进的向量检索和语义匹配
- **高质量生成**: 基于检索内容的精准生成
- **模块化设计**: 各组件可独立使用和扩展
- **多模态支持**: 支持文本、图像等多种模态
- **性能优化**: 高效的检索和生成算法
- **可解释性**: 提供检索和生成过程的可解释性

## RAG工作流程

```
Query → Retriever → Reranker → Generator → Answer
  ↓         ↓          ↓         ↓         ↓
Promptor  Searcher   Evaluate  Writer   Profiler
```

## 使用场景

- **智能问答**: 基于知识库的精准问答
- **内容创作**: 基于参考资料的内容生成
- **研究助手**: 学术研究和文献调研
- **教育辅导**: 个性化学习内容生成
- **客服系统**: 基于企业知识库的客服

## 快速开始

```python
from sage.lib.rag import Retriever, Generator, RAGPipeline

# 创建RAG组件
retriever = Retriever(
    index_path="knowledge_base.faiss",
    embedding_model="sentence-transformers/all-MiniLM-L6-v2"
)

generator = Generator(
    model_name="gpt-3.5-turbo",
    max_tokens=512
)

# 创建RAG管道
rag = RAGPipeline(retriever=retriever, generator=generator)

# 执行问答
question = "什么是机器学习？"
answer = rag.generate(question, top_k=5)
print(answer)
```

## 高级配置

### 检索配置
```python
retriever_config = {
    "top_k": 10,
    "similarity_threshold": 0.7,
    "retrieval_method": "hybrid",
    "rerank_enabled": True,
    "cache_enabled": True
}
```

### 生成配置
```python
generator_config = {
    "model": "gpt-4",
    "temperature": 0.7,
    "max_tokens": 1000,
    "top_p": 0.9,
    "presence_penalty": 0.1
}
```

### 评估配置
```python
evaluation_config = {
    "metrics": ["bleu", "rouge", "bertscore"],
    "reference_answers": True,
    "human_evaluation": False,
    "batch_size": 32
}
```

## 知识库构建

### 文档预处理
```python
from sage.lib.rag.chunk import DocumentChunker

chunker = DocumentChunker(
    chunk_size=512,
    overlap=50,
    strategy="semantic"
)

chunks = chunker.chunk_documents(documents)
```

### 向量索引构建
```python
from sage.lib.rag.retriever import VectorIndexBuilder

builder = VectorIndexBuilder(
    embedding_model="text-embedding-ada-002",
    dimension=1536
)

index = builder.build_index(chunks)
builder.save_index(index, "knowledge_base.faiss")
```

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
2. **分块策略**: 选择合适的文档分块方法
3. **检索调优**: 优化检索参数和策略
4. **提示词工程**: 设计有效的提示词模板
5. **持续评估**: 建立持续的评估和优化机制
