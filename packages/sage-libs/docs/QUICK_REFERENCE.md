# sage-libs 快速参考

**版本**: 0.1.4 (重组后)\
**日期**: 2026-01-09

## 📦 模块导入

### 核心域 (Core Domains)

```python
from sage.libs import foundation    # 基础工具
from sage.libs import agentic       # Agent 完整生态
from sage.libs import rag           # RAG 组件
from sage.libs import dataops       # 数据变换
from sage.libs import safety        # 安全过滤
```

### 接口层 (Interface Layers)

```python
from sage.libs import anns          # ANNS 接口 → isage-anns
from sage.libs import amms          # AMM 接口 → isage-amms
```

### 专业模块 (Specialized)

```python
from sage.libs import privacy       # 隐私算法
from sage.libs import finetune      # 模型训练
from sage.libs import integrations  # 第三方集成
```

## 🎯 Agentic 子模块

```python
from sage.libs.agentic import agents      # Agent 框架
from sage.libs.agentic import intent      # Intent 分类
from sage.libs.agentic import workflow    # Workflow 优化
from sage.libs.agentic import sias        # Tool selection reasoning
from sage.libs.agentic import reasoning   # 搜索算法
from sage.libs.agentic import eval        # 评估指标
```

### SIAS 常用组件

```python
from sage.libs.agentic.sias import (
    CoresetSelector,           # 重要性采样
    OnlineContinualLearner,    # 经验回放
)
```

## 🔧 ANNS/AMMS 接口

```python
# ANNS
from sage.libs.anns import create, register, registered
index = create("faiss_HNSW", dimension=128)  # 需要 isage-anns

# AMMS
from sage.libs.amms import create, register, registered
amm = create("countsketch", sketch_size=1000)  # 需要 isage-amms
```

## 📥 安装

```bash
# 基础 (仅接口)
pip install isage-libs

# 带实现
pip install isage-libs[anns,amms]

# 全部
pip install isage-libs[all]

# 开发
pip install -e packages/sage-libs[all]
```

## 🚨 迁移提示

### ❌ 旧路径 (已废弃)

```python
from sage.libs.sias import ...       # ❌
from sage.libs.reasoning import ...  # ❌
from sage.libs.eval import ...       # ❌
from sage.libs.ann import ...        # ❌ (目录已删除)
```

### ✅ 新路径

```python
from sage.libs.agentic.sias import ...      # ✅
from sage.libs.agentic.reasoning import ... # ✅
from sage.libs.agentic.eval import ...      # ✅
from sage.libs.anns import ...              # ✅ (统一为 anns)
```

## 📊 结构总览

```
sage-libs/
├── agentic/       🎯 Agent 生态 (6个子模块)
├── foundation/    🔧 基础工具
├── dataops/       📊 数据操作
├── safety/        🛡️ 安全过滤
├── rag/           🔍 RAG 组件
├── privacy/       🔐 隐私算法
├── finetune/      🎓 训练工具
├── integrations/  🔌 第三方集成
├── anns/          📐 ANNS 接口 (外部: isage-anns)
└── amms/          🧮 AMM 接口 (外部: isage-amms)
```

## 📚 文档

- 外迁状态: `EXTERNALIZATION_STATUS.md`
- 重组报告: `REORGANIZATION_COMPLETED.md`
- 迁移指南: `docs/MIGRATION_EXTERNAL_LIBS.md`
