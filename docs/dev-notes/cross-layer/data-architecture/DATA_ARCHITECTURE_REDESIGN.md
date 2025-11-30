# SAGE Data Architecture Redesign: Two-Layer Marketplace

## 1. 背景与目标 (Background & Goals)

当前 `sageData` (主要位于 `packages/sage-benchmark/src/sage/data`) 目录结构缺乏统一规范，文件夹组织混乱。为了支持 SAGE 作为一个通用 AI 数据处理框架的延展性，我们需要重构数据管理架构。

**核心目标：**
1.  **清理与规范化**：解决文件夹混乱问题。
2.  **数据共享**：最大化数据集的复用，避免重复存储。
3.  **用途隔离**：不同研究方向（如 LibAMM, NeuroMem, RAG）的用户只关注与自己相关的数据视图。
4.  **高延展性**：支持快速添加新数据集和定义新用途，适应不同实验需求。

## 2. 架构概览 (Architecture Overview)

采用 **两层结构 (Two-Layer Structure)**：

### Layer 1: 数据市场 (Data Marketplace / Sources)
*   **定位**：底层物理存储层。
*   **组织方式**：按**数据集本身特性**分类。
*   **原则**：一个数据集一个文件夹 (Single Source of Truth)。
*   **内容**：包含原始数据 (Raw Data)、数据加载器 (Loader)、辅助脚本 (Utils)、元数据 (Metadata) 和文档 (README)。

### Layer 2: 用途市场 (Usage Marketplace / Profiles)
*   **定位**：上层逻辑视图层。
*   **组织方式**：按**实际用途/实验场景**分类 (e.g., `libamm`, `rag`, `agents`, `neuromem`)。
*   **原则**：通过引用 (Reference) 指向底层数据，不复制数据。
*   **实现**：可以通过 软链接 (Symlinks)、配置文件 (Registry Config) 或 统一 API 路由实现。

---

## 3. 详细目录结构设计 (Directory Structure)

建议在 `packages/sage-benchmark/src/sage/data` (或独立的 `sage-data` 包) 下实施此结构：

```text
sage/data/
├── __init__.py          # 统一入口
├── core/                # 核心工具 (BaseLoader, Registry)
├── sources/             # [Layer 1] 数据市场
│   ├── bbh/             # BIG-Bench Hard
│   │   ├── raw/
│   │   ├── loader.py
│   │   └── README.md
│   ├── mmlu/            # MMLU
│   ├── locomo/          # LoCoMo
│   ├── sift/            # SIFT (Vector Data)
│   ├── mnist/           # MNIST
│   └── qa_base/         # QA Knowledge Base
│
└── usages/              # [Layer 2] 用途市场
    ├── __init__.py
    ├── libamm/          # LibAMM 实验用途
    │   ├── __init__.py  # 暴露 sift, mnist, etc.
    │   └── config.yaml  # 定义该用途包含哪些数据集
    ├── rag/             # RAG 实验用途
    │   ├── __init__.py  # 暴露 qa_base, mmlu, etc.
    │   └── config.yaml
    └── neuromem/        # NeuroMem 实验用途
```

## 4. 实现细节 (Implementation Details)

### 4.1 数据市场 (Sources) 规范
每个 Source 必须包含 `dataset.yaml` 描述元数据：

```yaml
# sources/sift/dataset.yaml
name: "sift"
description: "SIFT1M dataset for approximate nearest neighbor search"
type: "vector"
format: "fvecs"
maintainer: "libamm-team"
```

### 4.2 用途市场 (Usages) 映射
使用 Python 模块或配置来定义视图。

**方式 A: 动态注册 (推荐)**
用户导入用途模块时，自动注册相关数据集。

```python
# usages/libamm/__init__.py
from sage.data.core import register_usage_view

# 定义该用途可见的数据集
datasets = {
    "sift": "sources.sift",
    "mnist": "sources.mnist",
    "custom_matrix": "sources.matrix_v1"
}

# 用户使用方式:
# from sage.data.usages.libamm import load_dataset
# ds = load_dataset("sift")
```

### 4.3 统一访问 API

```python
from sage.data import DataManager

# 1. 直接访问底层数据 (高级用户)
ds = DataManager.get_source("sift")

# 2. 按用途访问 (推荐用户)
# 自动加载 libamm 用途下的配置
libamm_data = DataManager.get_usage("libamm")
ds = libamm_data.load("sift")
```

## 5. 扩展性 (Extensibility)

### 添加新数据集
1. 在 `sources/` 下新建文件夹。
2. 放入数据和加载脚本。
3. 添加 `dataset.yaml`。

### 添加新用途 (实验)
1. 在 `usages/` 下新建文件夹 (e.g., `usages/my_experiment/`)。
2. 创建配置文件，列出需要用到的 `sources`。
3. (可选) 添加该用途特有的预处理脚本。

## 6. 迁移计划 (Migration Plan)

1.  **Phase 1**: 建立 `sources` 和 `usages` 目录结构。
2.  **Phase 2**: 将现有 `sage/data/` 下的散乱文件夹 (e.g., `bbh`, `locomo`) 移动到 `sources/` 下。
3.  **Phase 3**: 为现有主要用途 (LibAMM, RAG) 创建 `usages` 映射。
4.  **Phase 4**: 更新 `__init__.py` 提供向后兼容的导入路径 (Deprecation Warning)。
