# sage-libs 重组完成报告

**Date**: 2026-01-09\
**Status**: ✅ 完成

## 重组目标

将 sage-libs 打造为轻量接口层，重型实现外迁到独立 PyPI 包，并整理模块结构提升可维护性。

## 完成的工作

### 1. ✅ 外迁清理 (ANNS & AMMS)

#### ANNS

- **移除**: `anns/wrappers/` (376K) - 所有算法实现
- **保留**: `anns/interface/` - 基类、工厂、注册表
- **删除**: `ann/` 兼容目录（不保留别名）

#### AMMS

- **移除**: `amms/wrappers/` (8K) + 构建文件
- **保留**: `amms/interface/` - 基类、工厂、注册表
- **节省空间**: 248K (65%)

### 2. ✅ 模块重组 (Agentic 整合)

将分散的 agent 相关模块统一整合到 `agentic/` 下：

```
agentic/
├── agents/        # Agent 框架（原有）
├── intent/        # Intent 分类（原有）
├── workflow/      # Workflow 框架（原有）
├── sias/          # 🆕 Tool selection reasoning (从顶层移入)
├── reasoning/     # 🆕 搜索算法 (从顶层移入)
└── eval/          # 🆕 评估指标 (从顶层移入)
```

**清理内容**:

- 删除顶层 `sias/` 残留
- 移动 `reasoning/` → `agentic/reasoning/`
- 移动 `eval/` → `agentic/eval/`

### 3. ✅ 最终目录结构

```
sage-libs/src/sage/libs/
├── agentic/       # 🎯 Agent 完整生态（planning, tool selection, eval）
├── foundation/    # 低级工具
├── dataops/       # 数据变换
├── safety/        # 安全/过滤
├── rag/           # RAG 组件
├── privacy/       # 隐私算法
├── finetune/      # 训练工具
├── integrations/  # 第三方适配器
├── anns/          # ANNS 接口（外部实现: isage-anns）
└── amms/          # AMM 接口（外部实现: isage-amms）
```

**精简**: 从 13 个顶层模块 → 10 个顶层模块

### 4. ✅ 配置与文档更新

**代码**:

- `sage-libs/__init__.py` - 更新导入和 __all__
- `agentic/__init__.py` - 导出新整合的模块
- `anns/__init__.py` - 外迁警告
- `amms/__init__.py` - 外迁警告
- `tests/lib/test_libamm.py` - 指向外部包

**配置**:

- `pyproject.toml` - 添加 extras: [anns], [amms], [all]
- `dependencies-spec.yaml` - 添加外部包版本

**文档**:

- `EXTERNALIZATION_STATUS.md` - 外迁状态汇总
- `REORGANIZATION_PLAN.md` - 重组方案
- `docs/MIGRATION_EXTERNAL_LIBS.md` - 迁移指南
- `agentic/README.md` - 更新模块说明
- `anns/README.md` - 简化为接口文档
- `amms/README.md` - 简化为接口文档

## 模块职责清晰化

### Core Domains (纯 L3 算法)

- **agentic**: Agent 全栈 (planning + tool selection + eval)
- **rag**: RAG 组件
- **dataops**: 数据操作
- **safety**: 安全过滤
- **foundation**: 基础工具

### Interface Layers (外部实现)

- **anns**: ANNS 接口 → `isage-anns`
- **amms**: AMM 接口 → `isage-amms`

### Specialized (专业领域)

- **privacy**: 隐私算法
- **finetune**: 模型训练
- **integrations**: 第三方集成

## 安装方式

```bash
# 基础（仅接口）
pip install isage-libs

# 带外部实现
pip install isage-libs[anns,amms]

# 开发模式
pip install -e packages/sage-libs[all]
```

## 验证测试

```python
# ✅ 核心模块导入
from sage.libs import (
    anns, amms, agentic,
    dataops, safety, rag, foundation
)

# ✅ agentic 子模块
from sage.libs.agentic import (
    agents, intent, workflow,
    sias, reasoning, eval
)

# ✅ 接口功能
from sage.libs.anns import create, register, registered
from sage.libs.amms import create, register
```

## 原则与约束

1. **无回退逻辑**: 缺少外部包时快速失败
1. **层次纯净**: L3 不依赖 L4/L5/L6
1. **接口稳定**: 公共 API 保持向后兼容
1. **外部实现**: 重型算法独立版本控制

## 后续规划

### 待外迁模块

- [ ] `agentic/` → `isage-agentic` (保留接口)
- [ ] `rag/` → `isage-rag` (保留接口)
- [ ] `privacy/` → `isage-privacy` (保留接口)

### 保留模块

- ✅ `foundation/`, `dataops/`, `safety/` - 轻量工具
- ✅ `integrations/`, `finetune/` - 专业功能

______________________________________________________________________

**总结**: sage-libs 现在是清晰的接口/注册表层，模块职责明确，依赖关系清晰，为后续外迁做好准备。
