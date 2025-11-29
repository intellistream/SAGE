# L3 Kernel 开发文档

`sage-kernel` 属于 L3（核心 & 算法层），提供 SAGE 框架的核心执行引擎、调度器和数据流处理。本目录记录 sage-kernel 的开发文档和历史。

## 📦 主要模块

### 🔧 API 模块 (`api/`)

数据流编程接口：

| 模块 | 描述 |
|------|------|
| `datastream.py` | `DataStream` - 数据流抽象 |
| `environment.py` | 执行环境配置 |
| `function/` | 算子函数接口（已迁移到 L1 common） |

### ⚙️ 核心模块 (`core/`)

执行引擎核心：

| 模块 | 描述 |
|------|------|
| `graph.py` | 执行图构建 |
| `operator.py` | 算子实现 |
| `partition.py` | 数据分区 |

### 📋 调度器 (`scheduler/`)

任务调度系统：

| 模块 | 描述 |
|------|------|
| `simple_scheduler.py` | 简单调度器 |
| `resource_aware_scheduler.py` | 资源感知调度器 |

### 🛡️ 容错模块 (`fault_tolerance/`)

故障恢复机制：

| 模块 | 描述 |
|------|------|
| `checkpoint.py` | 检查点机制 |
| `recovery.py` | 故障恢复 |

### 🏃 运行时 (`runtime/`)

执行运行时：

| 模块 | 描述 |
|------|------|
| `ray_runtime.py` | Ray 分布式运行时 |
| `local_runtime.py` | 本地运行时 |

## 📁 文档结构

### 架构文档

- **[KERNEL_REFACTORING_COMPLETED.md](./KERNEL_REFACTORING_COMPLETED.md)** - Kernel 层重构完成报告（函数接口迁移到 L1）
- **[KEYED_STATE_GUIDE.md](./KEYED_STATE_GUIDE.md)** - Keyed State 使用指南
- **[RESOURCE_CONFIG_SUPPORT_FEATURE.md](./RESOURCE_CONFIG_SUPPORT_FEATURE.md)** - 资源配置支持特性

> 📁 历史 Issue 文档已归档到 `archive/l3-kernel/`

## 🔄 重要架构变更

### 函数接口迁移 (Issue #1041)

原本位于 `sage.kernel.api.function` 的 13 个函数接口已迁移到 `sage.common.core.functions`：

| 函数 | 新位置 |
|------|--------|
| `BaseFunction` | `sage.common.core.functions` |
| `MapFunction` | `sage.common.core.functions` |
| `FilterFunction` | `sage.common.core.functions` |
| `SinkFunction` | `sage.common.core.functions` |
| `SourceFunction` | `sage.common.core.functions` |
| ... | ... |

**向后兼容**：`sage.kernel.api.function` 仍可使用（会显示 DeprecationWarning）

```python
# 新代码（推荐）
from sage.common.core.functions import MapFunction

# 旧代码（仍然有效，但已弃用）
from sage.kernel.api.function import MapFunction  # DeprecationWarning
```

## 🎯 快速导航

| 想要了解... | 查看 |
|-------------|------|
| DataStream 使用 | `packages/sage-kernel/src/sage/kernel/api/datastream.py` |
| 函数接口迁移 | [KERNEL_REFACTORING_COMPLETED.md](./KERNEL_REFACTORING_COMPLETED.md) |
| Keyed State | [KEYED_STATE_GUIDE.md](./KEYED_STATE_GUIDE.md) |
| 资源配置 | [RESOURCE_CONFIG_SUPPORT_FEATURE.md](./RESOURCE_CONFIG_SUPPORT_FEATURE.md) |

## 🔗 相关资源

- **代码位置**: `packages/sage-kernel/src/sage/kernel/`
- **测试**: `packages/sage-kernel/tests/`
- **函数接口（新位置）**: `packages/sage-common/src/sage/common/core/functions/`
- **归档文档**: `docs/dev-notes/archive/l3-kernel/`

---

**最后更新**: 2025-11-29
