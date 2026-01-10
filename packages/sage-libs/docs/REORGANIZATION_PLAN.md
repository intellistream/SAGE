# sage-libs 模块重组方案

## 当前问题

1. `sias/` 在顶层和 `agentic/` 下都有（已移动但顶层残留）
1. `ann/` 和 `anns/` 并存（需要合并或明确关系）
1. 多个小模块散落顶层：`dataops/`, `eval/`, `reasoning/`, `safety/`

## 重组方案

### A. 合并到 agentic（agent 相关）

- ✅ `sias/` → `agentic/sias/` (已移动，需删除顶层残留)
- 🔄 `reasoning/` → `agentic/reasoning/` (搜索、评分算法)
- 🔄 `eval/` → `agentic/eval/` (评估、遥测)

### B. 保留独立（通用算法/工具）

- ✅ `foundation/` - 低级工具
- ✅ `dataops/` - 数据变换（JSON/表/文本/采样）
- ✅ `safety/` - 内容过滤/PII/策略检查
- ✅ `rag/` - RAG 组件
- ✅ `privacy/` - 隐私算法
- ✅ `finetune/` - 训练工具
- ✅ `integrations/` - 第三方适配器

### C. ANN 接口整理

- `ann/` - 旧接口（保留向后兼容）
- `anns/` - 新统一接口（主要接口）
- **建议**: 让 `ann/` 成为 `anns/` 的别名（兼容层）

### D. 外迁的接口层

- ✅ `amms/` - AMM 接口
- ✅ `anns/` - ANNS 接口（主）
- ✅ `ann/` - ANNS 接口（兼容）

## 目标结构

```
sage-libs/src/sage/libs/
├── agentic/              # Agent 框架
│   ├── agents/
│   ├── intent/
│   ├── workflow/
│   ├── workflows/
│   ├── sias/            # 🆕 tool selection reasoning
│   ├── reasoning/       # 🆕 搜索/评分算法
│   └── eval/            # 🆕 评估/遥测
│
├── foundation/          # 低级工具
├── dataops/             # 数据变换
├── safety/              # 安全/过滤
├── rag/                 # RAG 组件
├── privacy/             # 隐私算法
├── finetune/            # 训练工具
├── integrations/        # 第三方适配器
│
├── anns/                # ANNS 接口（主）
├── ann/                 # ANNS 兼容别名
└── amms/                # AMM 接口
```

## 执行步骤

### 1. 移动模块到 agentic

```bash
# reasoning 和 eval 移到 agentic 下
mv reasoning/ agentic/
mv eval/ agentic/
```

### 2. 删除顶层 sias 残留

```bash
rm -rf sias/
```

### 3. 让 ann 成为 anns 的别名

```python
# ann/__init__.py
from sage.libs.anns import *  # noqa
```

### 4. 更新 __init__.py 导入

移除：sias, reasoning, eval, ann 保留独立：foundation, dataops, safety, rag, privacy, finetune, integrations
保留接口：anns, amms
