# SAGE Data 快速使用指南

## 🚀 30 秒上手

```python
from sage.data import DataManager

# 初始化
manager = DataManager.get_instance()

# 查看架构
manager.print_structure()

# 使用方式 1：按用途访问（推荐）
rag_data = manager.get_by_usage("rag")
qa_loader = rag_data.load("qa_base")
queries = qa_loader.load_queries()

# 使用方式 2：直接访问数据源
qa_loader = manager.get_by_source("qa_base")
queries = qa_loader.load_queries()
```

## 📊 可用的数据源

| 数据源    | 描述                    | 类型               |
| --------- | ----------------------- | ------------------ |
| `qa_base` | QA 知识库               | text               |
| `bbh`     | BIG-Bench Hard 推理任务 | text               |
| `mmlu`    | MMLU 多任务评估         | text (HuggingFace) |
| `gpqa`    | 研究生级别专家问题      | text (HuggingFace) |
| `locomo`  | 长上下文记忆数据        | text               |

## 🎯 可用的用途

| 用途       | 包含数据集                       | 适用场景             |
| ---------- | -------------------------------- | -------------------- |
| `rag`      | qa_base, mmlu, locomo, bbh, gpqa | RAG 实验             |
| `libamm`   | libamm_data                      | 矩阵近似乘法基准测试 |
| `neuromem` | conversation_data (=locomo)      | 记忆系统实验         |

## 💡 实用示例

### 示例 1: RAG 实验

```python
from sage.data import DataManager

manager = DataManager.get_instance()

# 获取 RAG 相关数据
rag = manager.get_by_usage("rag")

# 加载知识库
kb_loader = rag.load("qa_base")
knowledge_base = kb_loader.load_knowledge_base()

# 加载查询
queries = kb_loader.load_queries()

# 加载 MMLU 用于评估
mmlu_loader = rag.load("mmlu")
subjects = mmlu_loader.get_all_subjects()
```

### 示例 2: 直接访问特定数据集

```python
from sage.data import DataManager

manager = DataManager.get_instance()

# 直接加载 BBH 数据集
bbh_loader = manager.get_by_source("bbh")
tasks = bbh_loader.get_task_names()
examples = bbh_loader.load_task("boolean_expressions")
```

### 示例 3: 使用便捷函数

```python
from sage.data import load_dataset, get_usage_view

# 方式 1: 直接加载
qa_loader = load_dataset("qa_base")

# 方式 2: 通过用途
rag = get_usage_view("rag")
qa_loader = rag.load("qa_base")
```

### 示例 4: 探索数据集

```python
from sage.data import DataManager

manager = DataManager.get_instance()

# 列出所有数据源
print("Available sources:", manager.list_sources())

# 列出所有用途
print("Available usages:", manager.list_usages())

# 查看元数据
metadata = manager.get_source_metadata("qa_base")
print(f"Dataset: {metadata.name}")
print(f"Type: {metadata.type}")
print(f"Size: {metadata.size}")
```

## 🔧 添加自己的数据

### 添加数据源

1. 在 `sources/` 下创建目录
1. 添加 `dataset.yaml`
1. 添加包装器 `__init__.py`

### 添加用途

1. 在 `usages/` 下创建目录
1. 添加 `config.yaml` 指定需要的数据集

详见：[Extension Guide](./data_extension_guide.md)

## ⚡ 直接访问数据源

```python
from sage.data.sources.qa_base import QADataLoader

qa_loader = QADataLoader()
queries = qa_loader.load_queries()
```

## 📚 更多文档

- [架构设计](./data_architecture_redesign.md)
- [完整文档](../../../packages/sage-benchmark/src/sage/data/ARCHITECTURE.md)
- [扩展指南](./data_extension_guide.md)
- [迁移指南](./data_migration_guide.md)
