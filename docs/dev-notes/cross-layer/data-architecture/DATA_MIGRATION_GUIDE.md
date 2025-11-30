# SAGE Data Migration Guide

## 从现有架构迁移到两层架构

### 第一步：理解当前结构

当前 `packages/sage-benchmark/src/sage/data/` 包含：
- `bbh/` - BIG-Bench Hard
- `locomo/` - Long Context
- `mmlu/` - MMLU
- `gpqa/` - GPQA  
- `qa/` - QA Knowledge Base
- `libamm-benchmark/` - LibAMM 数据集
- `memory_template/` - Memory 模板

### 第二步：迁移到 Sources 层

创建 `sources/` 目录并移动数据集：

```bash
cd packages/sage-benchmark/src/sage/data

# 创建新结构
mkdir -p sources usages/libamm usages/rag usages/neuromem

# 移动数据集到 sources
mv bbh sources/
mv locomo sources/
mv mmlu sources/
mv gpqa sources/
mv qa sources/qa_base
mv libamm-benchmark sources/libamm_data

# 为每个 source 添加 dataset.yaml
```

### 第三步：创建数据集元数据

为每个数据集创建 `dataset.yaml`，例如：

**sources/qa_base/dataset.yaml:**
```yaml
name: "qa_base"
description: "Question-Answering knowledge base for RAG systems"
type: "text"
format: "txt"
maintainer: "sage-team"
tags: ["qa", "rag", "knowledge-base"]
size: "~1MB"
license: "MIT"
```

**sources/sift/dataset.yaml:**
```yaml
name: "sift"
description: "SIFT1M dataset for ANN benchmarking"
type: "vector"
format: "fvecs"
maintainer: "libamm-team"
tags: ["ann", "vector-search", "benchmark"]
size: "~500MB"
license: "Research Use"
```

### 第四步：创建 Usage Profiles

**usages/rag/config.yaml:**
```yaml
description: "RAG (Retrieval-Augmented Generation) experiments"
datasets:
  qa_base: "qa_base"
  mmlu: "mmlu"
  locomo: "locomo"
  knowledge_corpus: "qa_base"  # 别名
```

**usages/libamm/config.yaml:**
```yaml
description: "LibAMM approximate matrix multiplication benchmarks"
datasets:
  sift: "sift"
  mnist: "mnist"
  ast: "libamm_data"
  bus: "libamm_data"
  qcd: "libamm_data"
```

**usages/neuromem/config.yaml:**
```yaml
description: "NeuroMem experiments and memory systems"
datasets:
  memory_templates: "memory_template"
  conversation_data: "locomo"  # 复用
```

### 第五步：更新代码导入

**旧代码：**
```python
from sage.data.qa import QADataLoader
from sage.data.locomo import LocomoDataLoader
```

**新代码（推荐）：**
```python
from sage.data import DataManager

# 按用途访问
rag_data = DataManager.get_usage("rag")
qa_loader = rag_data.load("qa_base")

# 或直接访问
qa_loader = DataManager.get_source("qa_base")
```

**兼容层（过渡期）：**

> **⚠️ 已移除：** `from sage.data.qa import ...` 之类的旧入口不再提供，请直接改用 `DataManager`。

### 第六步：更新文档和示例

1. 更新 README.md 说明新架构
2. 更新示例代码使用新 API
3. 添加迁移检查清单

---

## 迁移检查清单

- [ ] 创建 `sources/` 和 `usages/` 目录
- [ ] 为所有数据集添加 `dataset.yaml`
- [ ] 创建主要用途的 `config.yaml` (libamm, rag, neuromem)
- [ ] 实现 `DataManager` 类
- [ ] 在 `__init__.py` 中添加向后兼容层
- [ ] 更新所有 examples 和 tutorials
- [ ] 运行测试确保无破坏性变更
- [ ] 更新文档

---

## 常见问题

**Q: 迁移会破坏现有代码吗？**
A: 不会。通过兼容层，现有导入路径继续工作，只是会显示 deprecation warning。

**Q: 如何添加新数据集？**
A: 在 `sources/` 下创建新文件夹，添加数据和 `dataset.yaml`，然后在相关 usage 的 `config.yaml` 中注册。

**Q: 多个 usage 可以共享同一个 source 吗？**
A: 当然可以！这正是设计的核心目标。例如 `locomo` 可以同时被 `rag` 和 `neuromem` 使用。
