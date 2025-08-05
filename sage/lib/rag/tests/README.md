# SAGE RAG测试

RAG（检索增强生成）模块的测试套件。

## 测试概述

本目录包含对SAGE RAG模块各个组件的测试，确保检索增强生成系统的正确性和性能。

## 测试范围

### 检索测试
- 向量检索准确性
- 搜索性能基准
- 多模态检索能力
- 检索结果相关性

### 生成测试
- 文本生成质量
- 上下文一致性
- 多语言生成能力
- 生成速度测试

### 评估测试
- 答案质量评估
- 检索质量评估
- 端到端系统评估
- 对比基准测试

### 组件集成测试
- RAG管道完整性
- 组件协作测试
- 错误处理测试
- 性能集成测试

## 运行测试

```bash
# 运行所有RAG测试
python -m pytest sage/lib/rag/tests/

# 运行特定组件测试
python -m pytest sage/lib/rag/tests/ -k "retriever"
python -m pytest sage/lib/rag/tests/ -k "generator"
```

## 测试数据

- 标准评估数据集
- 多领域测试语料
- 多语言测试数据
- 性能基准数据集

## 评估指标

- **检索指标**: Precision@K, Recall@K, MRR
- **生成指标**: BLEU, ROUGE, BERTScore
- **质量指标**: 事实准确性, 相关性, 流畅性
- **性能指标**: 延迟, 吞吐量, 资源使用
