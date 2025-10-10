# SAGE 示例集合

## 📦 依赖安装

部分示例需要额外的依赖包。推荐使用以下方式安装：

```bash
# 方法1：通过 sage-apps 安装应用相关依赖（推荐）
pip install -e packages/sage-apps[all]  # 所有应用
pip install -e packages/sage-apps[video]  # 仅视频应用
pip install -e packages/sage-apps[medical]  # 仅医疗应用

# 方法2：通过 sage-libs 安装库相关依赖
pip install -e packages/sage-libs[examples]

# 方法3：使用 requirements.txt（适用于 CI/CD 环境）
pip install -r examples/requirements.txt
```

**各类示例的依赖说明**：
- **应用示例** (`examples/apps/`): 使用 `sage-apps` 包，需要 `pip install -e packages/sage-apps[all]`
- **RAG 示例** (`examples/rag/`): 核心依赖已包含在 `sage-libs` 中
- **教程示例** (`examples/tutorials/`): 大部分无需额外依赖

**注意**: 如果您使用 `./quickstart.sh --dev --yes` 安装了完整的开发环境，大部分依赖已经安装。
本目录包含了SAGE框架的各种示例，采用**简单明了**的功能分类，方便用户快速找到需要的示例。

## ⚠️ 重要说明：Examples vs Tests

**本目录仅包含示例和演示代码，不包含测试文件。**

- **Examples (示例)**: 位于 `examples/` 目录，用于演示如何使用SAGE框架的功能
- **Tests (测试)**: 位于 `packages/*/tests/` 目录，用于验证代码的正确性
- **Integration Tests (集成测试)**: 位于 `tools/tests/` 目录，用于测试整体功能

如果您要编写或运行测试，请使用相应的测试目录，而不是examples目录。

## � 依赖安装

部分示例需要额外的依赖包。您可以选择性安装：

```bash
# 安装所有示例依赖（推荐）
pip install -r examples/requirements.txt

# 或者仅安装特定示例的依赖
# 视频处理示例需要：opencv-python, torch, torchvision, transformers
pip install opencv-python torch torchvision transformers
```

**注意**: 如果您使用 `./quickstart.sh --dev --yes` 安装了完整的开发环境，大部分依赖已经安装。

## �📚 目录结构

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

# 3. 🆕 多模态数据融合
python qa_multimodal_fusion.py    # 文本+图像联合检索
./run_multimodal_demo.sh          # 一键运行演示
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

### 🛡️ 容错机制开发者
```bash
# 容错策略演示（Checkpoint、重启策略等）
python fault_tolerance_demo.py
```

> **💡 说明**: 容错机制对应用用户是透明的，只需在配置文件中声明容错策略即可。开发者可以通过扩展 `BaseFaultHandler` 实现自定义容错策略。

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
- [Memory服务示例](memory/README_memory_service.md) - Memory特性与RAG集成指南
- [SageDB服务](service/sage_db/README.md) - 数据库服务示例
- [SageFlow服务](service/sage_flow/README.md) - 流处理服务示例
- [视频智能应用演示](video/README_intelligence_demo.md) - 多模型融合的视频分析Pipeline
- [清理记录](CLEANUP_NOTES.md) - Examples vs Tests 清理记录

---

💡 **提示**: 每个子目录都有对应的README文件，包含更详细的使用说明和示例介绍。
