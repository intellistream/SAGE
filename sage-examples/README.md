# SAGE 示例集合 (sage-examples)

本目录包含了SAGE框架的各种示例，采用**简单明了**的功能分类，方便用户快速找到需要的示例。

## 📚 目录结构

### 🎓 tutorials/ - 框架学习教程
**适合对象**: 初学者和想深入理解框架的开发者
- `hello_world.py` - 框架入门第一步
- `core-api/` - 核心API使用教程
  - 批处理、流处理、协同处理等核心概念教程

### 🧠 rag/ - 检索增强生成示例
**完整的RAG系统实现和优化**
- **基础RAG**: `rag_simple.py`, `rag.py`
- **检索策略**: `qa_dense_retrieval*.py`, `qa_bm25_retrieval*.py`
- **生成优化**: `qa_openai*.py`, `qa_hf.py`, `qa_refiner.py`
- **高级功能**: `qa_rerank.py`, `qa_multiplex.py`, `qa_batch.py`

### 🤖 agents/ - 智能体系统
**多智能体协作和决策系统**
- `multiagent_app.py` - 完整的多智能体协作示例

### 🌊 streaming/ - 流处理示例
**实时数据流和事件驱动处理**
- `kafka_query.py` - Kafka实时流处理
- `multiple_pipeline.py` - 多管道并行处理

### 💾 memory/ - 内存和数据管理
**知识库构建、内存管理和数据摄取**
- `biology_rag_knowledge.py` - 专业知识库示例
- `memqa.py` - 内存问答系统
- `external_memory_ingestion_pipeline.py` - 大规模数据摄取
- `experiment/` - 实验性功能

### 📊 evaluation/ - 系统评估
**模型和系统效果评估**
- `qa_evaluate.py` - 问答系统综合评估

## 🚀 快速开始

### 🔰 初学者 - 从教程开始
```bash
# 1. 框架基础
cd tutorials && python hello_world.py

# 2. 核心API学习
cd tutorials/core-api && python batch_operator_examples.py
```

### 🧠 RAG开发者
```bash
# 1. 简单RAG入门
cd rag && python rag_simple.py

# 2. 探索不同检索策略
python qa_dense_retrieval.py      # 稠密检索
python qa_bm25_retrieval.py       # 稀疏检索
```

### 🤖 智能体开发者
```bash
cd agents && python multiagent_app.py
```

### 🌊 流处理开发者
```bash
cd streaming && python kafka_query.py
```

## 💡 为什么这样分类？

### ✅ 简单明了的原则
- **按功能分类**: 直接按应用领域分类，一目了然
- **避免概念混淆**: 不区分"应用"和"管道"，因为它们本质上都是应用
- **便于查找**: 用户知道要做RAG就去rag目录，要做智能体就去agents目录

### 🎯 学习路径清晰
1. **tutorials/** - 学习框架基础概念
2. **功能目录** - 根据需求选择对应的功能示例
3. **evaluation/** - 评估和优化应用效果

## 📋 配置文件

相关配置文件位于 `../config/` 目录：
- `config.yaml` - 基础配置
- `config_*.yaml` - 特定功能配置

## 📖 详细文档

每个目录都包含README文件，说明具体的使用方法。

---

💡 **设计理念**: 简单、直观、易用 - 让用户能够快速找到并运行需要的示例！
