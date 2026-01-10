# sage-libs 重组决策摘要

## 📋 三个关键发现

### 发现 1：外迁方式不统一 ⚠️

| 模块        | 外迁状态 | 本地保留内容         | 是否需要清理    |
| ----------- | -------- | -------------------- | --------------- |
| `agentic/`  | ✅ 完成  | `agentic.py` 单文件  | ✅ 已统一       |
| `finetune/` | ✅ 完成  | `finetune.py` 单文件 | ✅ 已统一       |
| `anns/`     | ✅ 完成  | `anns/` 目录（接口） | ❌ **需要清理** |
| `amms/`     | ✅ 完成  | `amms/` 目录（接口） | ❌ **需要清理** |

**问题**：anns 和 amms 保留了接口目录，应该统一改为单文件兼容层。

### 发现 2：RAG 逻辑不一致 🚨

| 对比项   | Agent (agentic) | RAG (rag)     | 结论                |
| -------- | --------------- | ------------- | ------------------- |
| 层级     | L3/L4 应用层    | L3/L4 应用层  | ✅ 相同             |
| 依赖     | LLM/Embedding   | LLM/Embedding | ✅ 相同             |
| 耦合     | 松耦合          | 松耦合        | ✅ 相同             |
| 复用性   | 可独立使用      | 可独立使用    | ✅ 相同             |
| 当前状态 | **已外迁**      | **计划保留**  | ❌ **不一致！**     |
| 代码形式 | 完整实现        | **完整实现**  | ❌ **更应该外迁！** |

**问题**：RAG 与 agentic 完全同级，且有完整实现（不只是接口），更应该外迁。

### 发现 3：保留模块需要评估 🤔

| 模块            | 文件数 | 主要功能     | 建议            |
| --------------- | ------ | ------------ | --------------- |
| `dataops/`      | 5 文件 | 数据处理工具 | 🤔 评估是否外迁 |
| `safety/`       | 4 文件 | 安全检查     | 🤔 评估是否外迁 |
| `privacy/`      | 2 目录 | 隐私保护     | 🤔 评估是否外迁 |
| `integrations/` | 5 文件 | 第三方集成   | 🤔 评估是否外迁 |
| `foundation/`   | 4 目录 | 基础工具     | ✅ **应该保留** |

## 🎯 三个优先级

### 🔥 优先级 0：清理已外迁模块（立即执行）

**时间**：1-2 小时

**任务**：

1. 删除 `anns/` 目录 → 改为 `anns.py` 单文件兼容层
1. 删除 `amms/` 目录 → 改为 `amms.py` 单文件兼容层

**执行**：

```bash
./tools/cleanup/cleanup_externalized_modules.sh
```

**效果**：

- ✅ 统一外迁模块的兼容层方式
- ✅ 减少维护复杂度（不需要同步接口）
- ✅ 清晰的边界（实现在外部，兼容层在本地）

### 🚀 优先级 1：外迁 RAG 模块（强烈建议）

**时间**：2 天

**任务**：

1. 创建 `sage-rag` 仓库（`intellistream/sage-rag`）
1. 迁移 `rag/` 代码到新仓库
1. 发布 `isage-rag` 到 PyPI
1. 删除 `rag/` 目录 → 改为 `rag.py` 单文件兼容层
1. 更新 `sage-middleware` 从 `sagerag` 导入

**理由**：

- ✅ 与 agentic 保持一致性
- ✅ RAG 是应用层工具，可独立使用
- ✅ 其他项目可以单独使用 `isage-rag`
- ✅ 按需安装：`pip install isage-libs[rag]`

### 🤔 优先级 2：评估其他模块（待讨论）

**时间**：待定

**候选外迁模块**：

- `dataops/` → `isage-dataops`？
- `safety/` → `isage-safety`？
- `integrations/` → `isage-integrations`？

**保留模块**：

- `foundation/` → 基础工具，必须保留

## ❓ 需要你的决策

### 问题 1：是否立即清理 anns/amms？

- **A. 是（推荐）** → 立即执行 `cleanup_externalized_modules.sh`
- **B. 否** → 保持现状

**我的建议**：选择 A，理由：

- 统一外迁方式
- 减少维护成本
- 清晰的模块边界

### 问题 2：是否外迁 RAG？

- **A. 是（强烈推荐）** → 执行 RAG 外迁（2 天）
- **B. 否** → 需要把 agentic 移回 sage-libs（撤销外迁）

**我的建议**：选择 A，理由：

- 与 agentic 保持一致
- RAG 是应用层工具
- 更好的模块化和复用性

### 问题 3：是否评估其他模块？

- **A. 是** → 逐个评估 dataops/safety/integrations
- **B. 否** → 暂时保留，以后再说

**我的建议**：选择 B，理由：

- 先完成优先级 0 和 1
- 其他模块可以逐步评估
- 避免一次性改动过大

## 📝 最终目标结构

### 外部独立包（PyPI）

```
isage-agentic/      ✅ 已完成
isage-anns/         ✅ 已完成
isage-amms/         ✅ 已完成
isage-finetune/     ✅ 已完成
isage-rag/          📦 建议新建（优先级 1）
```

### sage-libs 保留内容

```
packages/sage-libs/src/sage/libs/
├── # 单文件兼容层
├── agentic.py          # → isage-agentic
├── anns.py             # → isage-anns （优先级 0 清理）
├── amms.py             # → isage-amms （优先级 0 清理）
├── finetune.py         # → isage-finetune
├── rag.py              # → isage-rag （优先级 1 外迁）
│
└── # 完整实现的核心模块
    ├── foundation/     # ✅ 保留（基础工具）
    ├── dataops/        # 🤔 待评估
    ├── safety/         # 🤔 待评估
    ├── privacy/        # 🤔 待评估
    └── integrations/   # 🤔 待评估
```

## 🚀 立即行动

如果你同意：

- **优先级 0：清理 anns/amms** → 我立即执行脚本
- **优先级 1：外迁 RAG** → 我开始创建 sage-rag 仓库

请回复你的决策：

1. 问题 1：A 还是 B？
1. 问题 2：A 还是 B？
1. 问题 3：A 还是 B？

或者直接说 "执行优先级 0" / "执行优先级 0 和 1" / "暂不执行"。
