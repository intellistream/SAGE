# SAGE 示例集合 (sage-examples)

<<<<<<< HEAD
本目录包含了SAGE框架的各种示例，采用**简单明了**的功能分类，方便用户快速找到需要的示例。

## 📚 目录结构

```
sage-examples/
├── src/                # 示例代码
│   ├── tutorials/      # 基础教程和入门示例
│   ├── rag/            # RAG (检索增强生成) 相关示例
│   ├── agents/         # 多智能体系统示例
│   ├── streaming/      # 流处理和实时数据示例  
│   ├── memory/         # 内存管理和持久化示例
│   └── evaluation/     # 评估和基准测试工具
├── resources/          # 资源文件
│   ├── config/         # 配置文件
│   └── data/           # 示例数据
└── README.md
```

### 🎓 src/tutorials/ - 框架学习教程
**适合对象**: 初学者和想深入理解框架的开发者
- `hello_world.py` - 框架入门第一步
- `core-api/` - 核心API使用教程
  - 批处理、流处理、协同处理等核心概念教程

### 🧠 src/rag/ - 检索增强生成示例
**完整的RAG系统实现和优化**
- **基础RAG**: `rag_simple.py`, `rag.py`
- **检索策略**: `qa_dense_retrieval*.py`, `qa_bm25_retrieval*.py`
- **生成优化**: `qa_openai*.py`, `qa_hf.py`, `qa_refiner.py`
- **高级功能**: `qa_rerank.py`, `qa_multiplex.py`, `qa_batch.py`

### 🤖 src/agents/ - 智能体系统
**多智能体协作和决策系统**
- `multiagent_app.py` - 完整的多智能体协作示例

### 🌊 src/streaming/ - 流处理示例
**实时数据流和事件驱动处理**
- `kafka_query.py` - Kafka实时流处理
- `multiple_pipeline.py` - 多管道并行处理

### 💾 src/memory/ - 内存和数据管理
**知识库构建、内存管理和数据摄取**
- `biology_rag_knowledge.py` - 专业知识库示例
- `memqa.py` - 内存问答系统
- `external_memory_ingestion_pipeline.py` - 大规模数据摄取
- `experiment/` - 实验性功能

### 📊 src/evaluation/ - 系统评估
**模型和系统效果评估**
- `qa_evaluate.py` - 问答系统综合评估

## 🚀 快速开始

### 🔰 初学者 - 从教程开始
```bash
# 1. 框架基础
cd src/tutorials && python hello_world.py

# 2. 核心API学习
cd src/tutorials/core-api && python batch_operator_examples.py
```

### 🧠 RAG开发者
```bash
# 1. 简单RAG入门
cd src/rag && python rag_simple.py

# 2. 探索不同检索策略
python qa_dense_retrieval.py      # 稠密检索
python qa_bm25_retrieval.py       # 稀疏检索
```

### 🤖 智能体开发者
```bash
cd src/agents && python multiagent_app.py
```

### 🌊 流处理开发者
```bash
cd src/streaming && python kafka_query.py
```

## 💡 为什么这样分类？

### ✅ 简单明了的原则
- **按功能分类**: 直接按应用领域分类，一目了然
- **避免概念混淆**: 不区分"应用"和"管道"，因为它们本质上都是应用
- **便于查找**: 用户知道要做RAG就去rag目录，要做智能体就去agents目录

### 🎯 学习路径清晰
1. **src/tutorials/** - 学习框架基础概念
2. **src/功能目录** - 根据需求选择对应的功能示例
3. **evaluation/** - 评估和优化应用效果

## 📋 配置文件

相关配置文件位于 `../config/` 目录：
- `config.yaml` - 基础配置
- `config_*.yaml` - 特定功能配置

## 📖 详细文档

每个目录都包含README文件，说明具体的使用方法。

---

💡 **设计理念**: 简单、直观、易用 - 让用户能够快速找到并运行需要的示例！
=======
本目录包含了SAGE框架的各种应用示例，按功能类别进行了重新组织和分类。所有示例都展示了SAGE框架在不同场景下的实际应用。

## 📁 目录结构

### 🔰 basic/ - 基础示例
包含最简单的入门示例，帮助新用户快速了解SAGE框架的基本概念。
- `hello_world.py` - 最基础的Hello World示例

### 🧠 rag/ - 检索增强生成示例  
展示各种RAG（Retrieval-Augmented Generation）应用场景。
- **检索器类型**:
  - `qa_dense_retrieval.py` - 稠密向量检索
  - `qa_bm25_retrieval.py` - BM25稀疏检索
  - `qa_dense_retrieval_mixed.py` - 混合检索策略
- **生成器示例**:
  - `qa_openai.py` - OpenAI生成器
  - `qa_hf.py` - HuggingFace生成器
- **完整RAG流水线**:
  - `rag_simple.py` - 简化RAG流程
  - `rag.py` - 高级RAG配置
  - `qa_refiner.py` - 答案精炼器
  - `qa_rerank.py` - 检索结果重排

### 🤖 agent/ - 智能体示例
多智能体系统和复杂决策流程的示例。
- `multiagent_app.py` - 多智能体协作系统

### 🌊 streaming/ - 流处理示例
实时数据流处理和事件驱动的应用。
- `kafka_query.py` - Kafka流处理
- `multiple_pipeline.py` - 多管道处理

### 💾 memory_app/ - 内存管理示例
展示SAGE框架的内存和存储功能。
- `biology_rag_knowledge.py` - 生物学知识库
- `memqa.py` - 内存问答系统
- `mem_offline_write.py` - 离线写入示例

### 📦 batch/ - 批处理示例
大规模批量数据处理的示例。
- `qa_batch.py` - 批量问答处理
- `external_memory_ingestion_pipeline.py` - 外部内存摄取管道

### 🔧 api_examples/ - API使用示例
各种API操作和功能的具体使用方法。
- `batch_operator_examples.py` - 批处理操作示例
- `connected_stream_example.py` - 连接流示例
- `future_stream_example.py` - 异步流示例
- 更多API示例...

### 📊 evaluation/ - 评估示例
模型和系统性能评估的各种方法。
- `qa_evaluate.py` - 问答系统评估

## 🚀 使用指南

### 1. 从基础示例开始
```bash
cd basic/
python hello_world.py
```

### 2. 探索RAG应用
```bash
cd rag/
python rag_simple.py
```

### 3. 体验智能体系统
```bash
cd agent/
python multiagent_app.py
```

### 4. 查看API使用方法
```bash
cd api_examples/
python batch_operator_examples.py
```

## 📋 配置文件

每个示例都有对应的配置文件在 `../config/` 目录中：
- `config.yaml` - 基础配置
- `config_bm25s.yaml` - BM25检索配置  
- `config_ray.yaml` - Ray分布式配置
- `multiagent_config.yaml` - 多智能体配置
- 等等...

## 🔧 依赖要求

确保已安装SAGE框架的所有依赖：
```bash
cd .. && pip install -e .
```

## 📖 更多资源

- [SAGE框架文档](../docs/)
- [API参考](../packages/sage-userspace/docs/)
- [配置指南](../config/README.md)

## 🤝 贡献

欢迎提交新的示例或改进现有示例！请遵循以下规范：
1. 每个示例都要有清晰的文档说明
2. 包含适当的错误处理
3. 提供配置文件模板
4. 添加单元测试（如适用）

## 📝 文件分类说明

### 已分类的文件：
- **basic/**: hello_world.py
- **rag/**: qa_*.py, rag*.py 系列文件
- **agent/**: multiagent_app.py
- **streaming/**: kafka_query.py, multiple_pipeline.py
- **batch/**: qa_batch.py, external_memory_ingestion_pipeline.py
- **evaluation/**: qa_evaluate.py
- **保留原位置**: memory_app/, api_examples/ (作为子目录保持现有结构)
>>>>>>> 9065df8 (update)
