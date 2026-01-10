# sage-libs 当前状态分析

## 🔍 模块实际状态检查

### 已外迁模块（只保留接口/兼容层）

| 模块        | 当前状态        | 实际代码位置        | 本地保留内容                           |
| ----------- | --------------- | ------------------- | -------------------------------------- |
| `agentic/`  | ✅ 已删除目录   | `isage-agentic` 包  | `agentic.py` 兼容层                    |
| `finetune/` | ✅ 已删除目录   | `isage-finetune` 包 | `finetune.py` 兼容层                   |
| `anns/`     | ⚠️ 保留接口目录 | `isage-anns` 包     | `anns/interface/` + `anns/__init__.py` |
| `amms/`     | ⚠️ 保留接口目录 | `isage-amms` 包     | `amms/interface/` + `amms/__init__.py` |

### 实际内容模块（完整实现在本地）

| 模块            | 文件数量 | 主要内容                                                        | 是否可外迁          |
| --------------- | -------- | --------------------------------------------------------------- | ------------------- |
| `rag/`          | 4 个文件 | `document_loaders.py`, `chunk.py`, `types.py`                   | ✅ **应该外迁**     |
| `dataops/`      | 5 个文件 | `json_ops.py`, `sampling.py`, `table.py`, `text.py`             | 🤔 可能保留         |
| `safety/`       | 4 个文件 | `content_filter.py`, `pii_scrubber.py`, `policy_check.py`       | 🤔 可能保留         |
| `privacy/`      | 2 个目录 | `unlearning/`                                                   | 🤔 可能保留         |
| `integrations/` | 5 个文件 | `chroma.py`, `milvus.py`, `huggingface.py`, `chroma_adapter.py` | 🤔 可能保留         |
| `foundation/`   | 4 个目录 | `context/`, `io/`, `tools/`                                     | ✅ 保留（基础工具） |

## 🚨 关键发现

### 1. 模块外迁方式不一致

**方式 A：完全删除 + 单文件兼容层**（推荐）

- ✅ `agentic/` → 删除目录，保留 `agentic.py`
- ✅ `finetune/` → 删除目录，保留 `finetune.py`

**方式 B：保留接口目录**（不推荐）

- ⚠️ `anns/` → 保留 `anns/interface/` 目录
- ⚠️ `amms/` → 保留 `amms/interface/` 目录

**问题**：

- 方式 B 增加维护复杂度（需要同步接口定义）
- 方式 B 不清晰（用户不知道实现在哪里）
- 应该统一使用方式 A

### 2. RAG 模块状态矛盾

**当前状态**：

```
packages/sage-libs/src/sage/libs/rag/
├── __init__.py
├── chunk.py              # 完整实现（120 行）
├── document_loaders.py   # 完整实现（200+ 行）
└── types.py              # 完整实现（150+ 行）
```

**矛盾点**：

- ❌ RAG 有完整实现（与 agentic/finetune 不同）
- ❌ 计划保留在 sage-libs（与外迁策略矛盾）
- ❌ 功能上与 agentic 同级（应用层工具）
- ❌ 在 middleware 中只是重导出（不是核心依赖）

### 3. ANNS/AMMS 需要清理

**问题**：

- `anns/interface/` 和 `amms/interface/` 目录应该删除
- 应该改为单文件兼容层（如 `anns.py`）
- 接口定义应该在 `isage-anns` 包中维护

## 📋 推荐的清理方案

### 阶段 1：统一外迁模块的兼容层（立即执行）

#### 1.1 清理 ANNS 目录

```bash
# 删除接口目录
rm -rf packages/sage-libs/src/sage/libs/anns/

# 创建单文件兼容层
cat > packages/sage-libs/src/sage/libs/anns.py << 'EOF'
"""ANNS compatibility layer - use isage-anns package.

⚠️ DEPRECATION NOTICE:
ANNS implementations have been externalized to isage-anns.

Installation:
    pip install isage-anns

Migration:
    # Old (deprecated)
    from sage.libs.anns import create, AnnIndex

    # New (recommended)
    from isage_anns import create, AnnIndex
"""

import warnings

warnings.warn(
    "sage.libs.anns is deprecated. Install 'isage-anns' instead: "
    "pip install isage-anns. Then import from isage_anns.",
    DeprecationWarning,
    stacklevel=2,
)

try:
    from isage_anns import *  # noqa: F401, F403
except ImportError as e:
    raise ImportError(
        "ANNS implementations require 'isage-anns' package. Install with:\n"
        "  pip install isage-anns\n"
        "or: pip install isage-libs[anns]"
    ) from e
EOF
```

#### 1.2 清理 AMMS 目录

```bash
# 删除接口目录
rm -rf packages/sage-libs/src/sage/libs/amms/

# 创建单文件兼容层（类似 anns.py）
cat > packages/sage-libs/src/sage/libs/amms.py << 'EOF'
"""AMMS compatibility layer - use isage-amms package."""
# ... 类似内容
EOF
```

### 阶段 2：外迁 RAG 模块（建议执行）

#### 2.1 创建 sage-rag 仓库

```bash
gh repo create intellistream/sage-rag --public
cd ../sage-rag
mkdir -p src/sagerag/{document_loaders,chunk,types} tests docs
```

#### 2.2 迁移代码

```bash
# 复制文件
cp ../SAGE/packages/sage-libs/src/sage/libs/rag/document_loaders.py src/sagerag/
cp ../SAGE/packages/sage-libs/src/sage/libs/rag/chunk.py src/sagerag/
cp ../SAGE/packages/sage-libs/src/sage/libs/rag/types.py src/sagerag/

# 更新 imports
find src/sagerag -name "*.py" -exec sed -i 's/sage\.libs\.rag/sagerag/g' {} \;
```

#### 2.3 清理 SAGE 仓库

```bash
cd ../SAGE

# 删除 rag 目录
rm -rf packages/sage-libs/src/sage/libs/rag/

# 创建兼容层
cat > packages/sage-libs/src/sage/libs/rag.py << 'EOF'
"""RAG compatibility layer - use isage-rag package."""
import warnings

warnings.warn(
    "sage.libs.rag is deprecated. Install 'isage-rag' instead: "
    "pip install isage-rag. Then import from sagerag.",
    DeprecationWarning,
    stacklevel=2,
)

try:
    from sagerag import *  # noqa: F401, F403
except ImportError as e:
    raise ImportError(
        "RAG tools require 'isage-rag' package. Install with:\n"
        "  pip install isage-rag\n"
        "or: pip install isage-libs[rag]"
    ) from e
EOF
```

## 📊 最终目标结构

### sage-libs 目录结构（清理后）

```
packages/sage-libs/src/sage/libs/
├── __init__.py
├── _version.py
├── py.typed
│
├── # 兼容层（单文件）
├── agentic.py          # → isage-agentic
├── anns.py             # → isage-anns （新建，删除 anns/ 目录）
├── amms.py             # → isage-amms （新建，删除 amms/ 目录）
├── finetune.py         # → isage-finetune
├── rag.py              # → isage-rag （新建，删除 rag/ 目录）
│
└── # 保留的核心模块（完整实现）
    ├── dataops/        # 数据操作工具（5 文件）
    ├── safety/         # 安全检查（4 文件）
    ├── privacy/        # 隐私保护（2 目录）
    ├── integrations/   # 第三方集成（5 文件）
    └── foundation/     # 基础工具（4 目录）
```

### 外部独立包

```
isage-agentic/      ✅ 已完成
isage-anns/         ✅ 已完成
isage-amms/         ✅ 已完成
isage-finetune/     ✅ 已完成
isage-rag/          📦 建议新建
```

## 🎯 立即行动项

### 优先级 1（立即执行，1-2 小时）

1. **清理 anns/ 目录** → 改为 `anns.py` 单文件兼容层
1. **清理 amms/ 目录** → 改为 `amms.py` 单文件兼容层
1. **更新测试** → 确保兼容层正常工作

### 优先级 2（建议执行，2 天）

4. **外迁 RAG 模块** → 创建 `isage-rag` 包
1. **删除 rag/ 目录** → 改为 `rag.py` 单文件兼容层
1. **更新 middleware** → 从 `sagerag` 导入

### 优先级 3（评估，待讨论）

7. **评估 dataops/** → 是否外迁为 `isage-dataops`？
1. **评估 safety/** → 是否外迁为 `isage-safety`？
1. **评估 integrations/** → 是否外迁为 `isage-integrations`？

## 💡 关键原则

1. **统一兼容层方式**：所有外迁模块使用单文件兼容层（`.py`），不保留目录
1. **清晰边界**：完整实现要么在本地，要么在外部包，不能分散
1. **接口维护**：接口定义在外部包中，不在 sage-libs 中维护
1. **渐进式迁移**：先清理已外迁的（优先级 1），再考虑新外迁（优先级 2-3）

## ❓ 待决策问题

1. **anns/amms 清理**：是否立即执行？（强烈建议 ✅）
1. **RAG 外迁**：是否外迁为 `isage-rag`？（强烈建议 ✅）
1. **dataops/safety 外迁**：是否需要？（待评估 🤔）

请回复你的决策，我可以立即开始执行清理工作。
