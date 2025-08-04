# SAGE 应用示例 - 模块化组织

本目录包含了SAGE框架的各种应用示例，按功能类别进行了重新组织和分类。

## 📁 目录结构

### 🔰 basic/ - 基础示例
包含最简单的入门示例，帮助新用户快速了解SAGE框架的基本概念。
- `hello_world.py` - 最基础的Hello World示例
- `simple_pipeline.py` - 简单的数据处理管道

### 🧠 rag/ - 检索增强生成示例  
展示各种RAG（Retrieval-Augmented Generation）应用场景。
- **检索器类型**:
  - `dense_retrieval.py` - 稠密向量检索
  - `bm25_retrieval.py` - BM25稀疏检索
  - `mixed_retrieval.py` - 混合检索策略
- **生成器示例**:
  - `openai_generator.py` - OpenAI生成器
  - `hf_generator.py` - HuggingFace生成器
- **完整RAG流水线**:
  - `simple_rag.py` - 简化RAG流程
  - `advanced_rag.py` - 高级RAG配置

### 🤖 agent/ - 智能体示例
多智能体系统和复杂决策流程的示例。
- `multiagent_system.py` - 多智能体协作系统
- `question_answering_bot.py` - 问答机器人
- `search_agent.py` - 搜索智能体

### 🌊 streaming/ - 流处理示例
实时数据流处理和事件驱动的应用。
- `kafka_streaming.py` - Kafka流处理
- `real_time_qa.py` - 实时问答系统
- `pipeline_monitoring.py` - 管道监控

### 💾 memory/ - 内存管理示例
展示SAGE框架的内存和存储功能。
- `memory_ingestion.py` - 数据摄取到内存系统
- `knowledge_base.py` - 知识库构建
- `context_management.py` - 上下文管理

### 📦 batch/ - 批处理示例
大规模批量数据处理的示例。
- `batch_operations.py` - 批处理操作示例
- `file_processing.py` - 文件批量处理
- `dataset_analysis.py` - 数据集分析

### 📊 evaluation/ - 评估示例
模型和系统性能评估的各种方法。
- `qa_evaluation.py` - 问答系统评估
- `retrieval_metrics.py` - 检索效果评估
- `performance_analysis.py` - 性能分析

## 🚀 使用指南

### 1. 从基础示例开始
```bash
cd basic/
python hello_world.py
```

### 2. 探索RAG应用
```bash
cd rag/
python simple_rag.py
```

### 3. 体验智能体系统
```bash
cd agent/
python multiagent_system.py
```

## 📋 配置文件

每个示例都有对应的配置文件在 `config/` 目录中：
- `config_basic.yaml` - 基础示例配置
- `config_rag.yaml` - RAG示例配置  
- `config_agent.yaml` - 智能体配置
- 等等...

## 🔧 依赖要求

确保已安装SAGE框架的所有依赖：
```bash
pip install -e .
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
