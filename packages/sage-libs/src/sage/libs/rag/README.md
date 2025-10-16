# SAGE RAG (检索增强生成) 模块

RAG模块提供完整的检索增强生成解决方案，结合知识检索和文本生成能力。

## 快速开始

```python
from sage.libs.rag import Retriever, Generator, RAGPipeline

# 创建RAG管道
rag = RAGPipeline(
    retriever=Retriever("knowledge_base.faiss"),
    generator=Generator("gpt-3.5-turbo")
)

# 执行问答
answer = rag.generate("什么是机器学习？", top_k=5)
```

## 核心组件

- **`retriever.py`**: 智能检索器，支持多种检索策略
- **`generator.py`**: 内容生成器，基于检索内容的智能文本生成
- **`reranker.py`**: 结果重排序器，优化检索结果质量
- **`evaluate.py`**: 评估系统，全面的RAG系统评估框架
- **`searcher.py`**: 搜索引擎，统一的搜索接口
- **`chunk.py`**: 文档分块器，智能的文档分块算法
- **`promptor.py`**: 提示词管理器，专业的提示词模板管理
- **其他组件**: `writer.py`, `profiler.py`, `trigger.py`, `arxiv.py`

## 使用场景

- **智能问答**: 基于知识库的精准问答
- **内容创作**: 基于参考资料的内容生成  
- **研究助手**: 学术研究和文献调研
- **教育辅导**: 个性化学习内容生成
- **客服系统**: 基于企业知识库的客服

## 📖 详细文档

更多详细的API参考、配置选项和高级用法,请参阅：

**[📚 RAG API 完整参考文档](../../../docs-public/docs_src/librarys/rag/api_reference.md)**

**[📋 RAG 统一数据格式规范](./DATA_FORMAT.md)** ⭐ 重要

包含完整的：
- API 使用指南和示例
- 统一数据格式规范和字段说明
- 各阶段数据流详解
- 高级配置选项
- 性能优化建议
- 评估体系说明
- 最佳实践指南
