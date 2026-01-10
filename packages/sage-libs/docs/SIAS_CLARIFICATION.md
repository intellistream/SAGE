# SIAS 定位澄清

**日期**: 2026-01-10\
**状态**: ✅ 已澄清

## 🎯 SIAS 真实定位

**SIAS (Sample-Importance-Aware Selection)** 是一个**工具选择算法**，但当前实现不完整。

### 完整架构（设计目标）

SIAS 应该实现 `BaseToolSelector` 接口，用于运行时的工具选择：

```python
# 正确位置
agentic/agents/action/tool_selection/sias_selector.py

class SiasToolSelector(BaseToolSelector):
    """SIAS-based tool selector using importance sampling."""

    def select_tools(self, query: str, candidates: list[Tool]) -> list[Tool]:
        """Select most important tools based on query."""
        # 使用 CoresetSelector 算法选择最重要的工具子集
        pass
```

### 当前实现状态

**已实现组件**（用于训练阶段）：

- ✅ `CoresetSelector` - 从训练样本中选择重要子集（coreset selection）
- ✅ `OnlineContinualLearner` - 增量学习/持续学习

**位置**：

- 当前在 `sage-tools/agent_training/sft_trainer.py` 中使用
- 用途：**训练数据选择**，不是运行时工具选择

**未实现组件**（运行时工具选择）：

- ❌ `SiasToolSelector(BaseToolSelector)` - 运行时工具选择器
- ❌ 与其他 selectors (keyword, embedding, gorilla, dfsdt) 的集成
- ❌ 注册到 tool selector registry

## 📋 完整实现计划

### 阶段 1: 保持训练组件在 sage-tools ✅ 当前状态

**CoresetSelector** 和 **OnlineContinualLearner** 应该留在哪里？

**选项 A**（推荐）：整合到 isage-agentic

- 位置：`isage-agentic/src/sage/libs/agentic/training/`
- 结构：
  ```
  agentic/
  ├── agents/          # 运行时组件
  │   └── action/
  │       └── tool_selection/
  │           ├── keyword_selector.py
  │           ├── embedding_selector.py
  │           ├── gorilla_selector.py
  │           ├── dfsdt_selector.py
  │           └── sias_selector.py    # ← 运行时工具选择（待实现）
  └── training/        # 训练组件
      ├── coreset_selector.py         # ← 当前已有
      └── continual_learner.py        # ← 当前已有
  ```

**选项 B**：保持在 sage-tools

- 位置：`sage-tools/agent_training/`
- 理由：只是训练辅助工具，不是核心 agent 功能

### 阶段 2: 实现运行时 SiasToolSelector ⏳ 待开发

```python
# isage-agentic/src/sage/libs/agentic/agents/action/tool_selection/sias_selector.py

from sage.libs.agentic.interface import BaseToolSelector
from sage.libs.agentic.training import CoresetSelector  # 复用训练组件

class SiasToolSelector(BaseToolSelector):
    """SIAS-based tool selector using importance sampling.

    Uses CoresetSelector algorithm to select the most important tools
    from candidates based on query embeddings and tool descriptions.
    """

    def __init__(self, strategy: str = "hybrid", top_k: int = 5):
        self.coreset_selector = CoresetSelector(strategy=strategy)
        self.top_k = top_k

    def select_tools(self, query: str, candidates: list[Tool]) -> list[Tool]:
        """Select top-k most important tools."""
        # 1. 计算 query embedding
        # 2. 计算 tool embeddings
        # 3. 使用 CoresetSelector 选择最重要的 k 个工具
        # 4. 返回选中的工具列表
        pass
```

### 阶段 3: 注册到 registry

```python
# isage-agentic/src/sage/libs/agentic/agents/action/tool_selection/__init__.py

from .sias_selector import SiasToolSelector

# 自动注册
register_selector("sias", SiasToolSelector)
```

## 🎯 外迁策略更新（选项 A）

基于澄清后的 SIAS 定位，更新外迁计划：

### 1. isage-agentic 包含内容

**核心组件**：

- ✅ `interface/` - 接口层（已有）
- ✅ `agents/` - Agent 实现
  - `runtime/`
  - `planning/`
  - `action/tool_selection/` - 包含所有 tool selectors
    - `keyword_selector.py`
    - `embedding_selector.py`
    - `gorilla_selector.py`
    - `dfsdt_selector.py`
    - `sias_selector.py` ← **待实现**
  - `bots/`
- ✅ `workflow/` - 工作流引擎
- ✅ `eval/` - Agent 评估
- ✅ `training/` - **新增**训练组件模块
  - `coreset_selector.py` ← 从 sage-tools 迁移或重构
  - `continual_learner.py` ← 从 sage-tools 迁移或重构

### 2. sage-libs/sias/ 处理

**删除**：

- ❌ 删除 `packages/sage-libs/src/sage/libs/sias/`
- 理由：架构定位错误，SIAS 不是独立的顶层模块

**迁移路径**：

- 训练组件 → `isage-agentic/training/`
- 运行时选择器 → `isage-agentic/agents/action/tool_selection/sias_selector.py`（待实现）

### 3. sage-tools 更新

更新导入语句：

```python
# 旧导入（当前）
from sage.libs.sias import CoresetSelector, OnlineContinualLearner

# 新导入（外迁后）
from sage.libs.agentic.training import CoresetSelector, OnlineContinualLearner
```

## 📝 总结

1. **SIAS 是工具选择算法**（你说的对）
1. **当前只实现了训练部分**（CoresetSelector 用于数据选择）
1. **运行时工具选择器还未实现**（SiasToolSelector 待开发）
1. **正确位置**：
   - 训练组件：`agentic/training/`
   - 运行时选择器：`agentic/agents/action/tool_selection/sias_selector.py`
1. **外迁策略**：整合到 isage-agentic，作为完整的 agent 工具选择解决方案

## 🚀 下一步

继续执行选项 A 的外迁计划：

1. ✅ 迁移 agentic 接口层到 isage-agentic
1. ⏳ 决定是否迁移 SIAS 训练组件（CoresetSelector/OnlineContinualLearner）
1. ⏳ 在 isage-agentic 中实现完整的 SiasToolSelector
1. ✅ 删除 sage-libs/sias 目录
1. ✅ 继续 rag 外迁
