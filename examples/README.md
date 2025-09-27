# SAGE 示例集合 (sage-examples)

本目录包含了SAGE框架的各种示例，采用**简单明了**的功能分类，方便用户快速找到需要的示例。

## ⚠️ 重要说明：Examples vs Tests

**本目录仅包含示例和演示代码，不包含测试文件。**

- **Examples (示例)**: 位于 `examples/` 目录，用于演示如何使用SAGE框架的功能
- **Tests (测试)**: 位于 `packages/*/tests/` 目录，用于验证代码的正确性
- **Integration Tests (集成测试)**: 位于 `tools/tests/` 目录，用于测试整体功能

如果您要编写或运行测试，请使用相应的测试目录，而不是examples目录。

## 📚 目录结构

```
examples/
├── tutorials/          # 基础教程和入门示例
├── rag/               # RAG (检索增强生成) 相关示例
├── agents/            # 多智能体系统示例
├── memory/            # 内存管理和持久化示例
├── service/           # 服务相关示例
├── video/             # 视频处理相关示例
├── config/            # 配置文件示例
├── data/              # 示例数据
└── README.md
```

## 🚀 快速开始

### 🔰 初学者 - 从教程开始
```bash
# 1. 框架基础
cd tutorials && python hello_world.py

# 2. 核心API学习
cd tutorials/core-api && python batch_operator_examples.py
```

> **⚠️ 教程状态说明**: 当前 `core-api` 目录中的一些例子可能无法正常运行，这是正常现象，因为该部分尚未完成维护。其余的 `service-api` 等三个模块可以正常运行。

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
cd agents && python agent_workflow_demo.py
```

### 🌊 流处理开发者
```bash
# 流处理示例请查看 service/ 目录
cd service && python sage_flow_example.py
```

## 🔧 路径配置

### Python代码中的配置引用
```python
# 从 rag/ 目录运行时
config = load_config("../config/config.yaml")
```

### 配置文件中的数据引用
```yaml
# 在 config/*.yaml 中
source:
  data_path: "../data/sample/question.txt"
```

## 📚 详细文档

- [RAG示例说明](rag/README.md) - RAG相关示例详解
- [Memory服务演示](memory/README_memory_service_demo.md) - Memory服务使用指南
- [SageDB服务](service/sage_db/README.md) - 数据库服务示例
- [SageFlow服务](service/sage_flow/README.md) - 流处理服务示例
- [清理记录](CLEANUP_NOTES.md) - Examples vs Tests 清理记录

---

💡 **提示**: 每个子目录都有对应的README文件，包含更详细的使用说明和示例介绍。
