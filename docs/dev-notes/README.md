# SAGE 开发者笔记 (Dev Notes)

> **注意**: 本目录主要供核心开发团队内部使用。
>
> **用户文档**: 请访问 [docs-public](../../docs-public/) 获取完整的用户和开发者文档。

## 🧱 分层目录（与 `packages/sage/pyproject.toml` 对齐）

| 层级 | 关联包（pyproject） | 目录 | 角色 |
|------|--------------------|------|------|
| L1 | `isage-common` | `l1-common/` | 基础设施、共享组件、Hybrid Scheduler |
| L2 | `isage-platform` | `l2-platform/` | 平台服务、安装与部署能力 |
| L3 | `isage-kernel`, `isage-libs` | `l3-kernel/`, `l3-libs/` | 核心执行引擎、算法库、Agentic 模块 |
| L4 | `isage-middleware` | `l4-middleware/` | 运算符、C++ 组件、数据面能力 |
| L5 | `isage-apps`, `isage-benchmark` | `l5-apps/`, `l5-benchmark/` | 应用、Agent/Control Plane 评测 |
| L6 | `isage-cli`, `isage-studio`, `isage-tools`, `isage-gateway` | `l6-cli/`, `l6-studio/`, `l6-tools/`, `l6-gateway/` | 交互接口、可视化和开发者工具 |

交叉主题（`cross-layer/`, `testing/`, `archive/`）用于记录跨层设计、测试策略和历史材料。

## 📂 当前文档

### 🏗️ 架构设计

| 文档 | 描述 | 状态 |
|------|------|------|
| [cross-layer/architecture/DATA_TYPES_ARCHITECTURE.md](cross-layer/architecture/DATA_TYPES_ARCHITECTURE.md) | 数据类型架构设计 | ✅ 活跃 |
| [cross-layer/architecture/NEUROMEM_ARCHITECTURE_ANALYSIS.md](cross-layer/architecture/NEUROMEM_ARCHITECTURE_ANALYSIS.md) | NeuroMem 架构分析 | ✅ 活跃 |
| [cross-layer/architecture/VLLM_SERVICE_INTEGRATION_DESIGN.md](cross-layer/architecture/VLLM_SERVICE_INTEGRATION_DESIGN.md) | vLLM 服务集成设计 | ✅ 活跃 |
| [cross-layer/architecture/SAGE_CHAT_ARCHITECTURE.md](cross-layer/architecture/SAGE_CHAT_ARCHITECTURE.md) | Chat 命令架构 | ✅ 活跃 |
| [l3-kernel/KERNEL_REFACTORING_COMPLETED.md](l3-kernel/KERNEL_REFACTORING_COMPLETED.md) | Kernel 层重构完成报告 (Issue #1041) | ✅ 活跃 |
| [cross-layer/architecture/SAGE_VLLM_CONTROL_PLANE_INTEGRATION.md](cross-layer/architecture/SAGE_VLLM_CONTROL_PLANE_INTEGRATION.md) | sageLLM Control Plane 集成 | ✅ 活跃 |

### 📋 系统文档

| 文档 | 描述 | 状态 |
|------|------|------|
| [cross-layer/migration/APPLICATION_ORGANIZATION_STRATEGY.md](cross-layer/migration/APPLICATION_ORGANIZATION_STRATEGY.md) | 应用代码组织策略 | ✅ 活跃 |
| [cross-layer/migration/EMBEDDING_README.md](cross-layer/migration/EMBEDDING_README.md) | Embedding 系统总览 | ✅ 活跃 |
| [cross-layer/migration/EMBEDDING_QUICK_REFERENCE.md](cross-layer/migration/EMBEDDING_QUICK_REFERENCE.md) | Embedding API 快速参考 | ✅ 活跃 |
| [cross-layer/migration/EMBEDDING_SYSTEM_COMPLETE_SUMMARY.md](cross-layer/migration/EMBEDDING_SYSTEM_COMPLETE_SUMMARY.md) | Embedding 系统完整总结 | ✅ 活跃 |
| [cross-layer/BREAKING_CHANGES_agent_tools_plan.md](cross-layer/BREAKING_CHANGES_agent_tools_plan.md) | agent_tools_plan 分支重要改动 | ✅ 活跃 |

### 🤖 Agent & Benchmark

| 文档 | 描述 | 状态 |
|------|------|------|
| [l5-benchmark/README.md](l5-benchmark/README.md) | Benchmark 层概述（含 benchmark_agent, benchmark_control_plane） | ✅ 活跃 |
| [cross-layer/architecture/SAGE_VLLM_CONTROL_PLANE_INTEGRATION.md](cross-layer/architecture/SAGE_VLLM_CONTROL_PLANE_INTEGRATION.md) | sageLLM Control Plane 集成设计 | ✅ 活跃 |

### ⚙️ 运维配置

| 文档 | 描述 | 状态 |
|------|------|------|
| [cross-layer/ci-cd/CODECOV_SETUP_GUIDE.md](cross-layer/ci-cd/CODECOV_SETUP_GUIDE.md) | CodeCov CI/CD 配置 | ✅ 活跃 |
| [cross-layer/ci-cd/DEV_INFRASTRUCTURE_SETUP.md](cross-layer/ci-cd/DEV_INFRASTRUCTURE_SETUP.md) | 开发基础设施配置 | ✅ 活跃 |

### 🛠️ 开发工具

| 文档 | 描述 | 状态 |
|------|------|------|
| [l6-tools/PRE_COMMIT_AUTOFIX_GUIDE.md](l6-tools/PRE_COMMIT_AUTOFIX_GUIDE.md) | Pre-commit 自动修复详细指南 | ✅ 活跃 |

### 📄 模板

| 文档 | 描述 |
|------|------|
| [TEMPLATE.md](TEMPLATE.md) | 新文档模板 |

## 📦 归档文档

所有历史文档已整理到 `archive/` 目录：

```
archive/
├── 2025-restructuring/         # 2025年重构相关文档
├── agent-benchmark-2025/       # Agent Benchmark 任务文档
├── agent-tool-benchmark-2025/  # Agent 工具评测详细文档
├── data-architecture/          # 数据架构设计示例代码
├── guides/                     # 功能使用指南
├── l3-kernel/                  # Kernel 层历史文档
├── l3-libs/                    # Libs 层历史文档
├── migration-guides/           # 已完成的迁移指南
└── testing-2025/               # 2025年测试改进报告
```

## 🔍 查找文档

| 需要了解 | 查看 |
|---------|------|
| 系统架构 | [docs-public/architecture/](../../docs-public/docs_src/architecture/) |
| 快速开始 | [docs-public/getting-started/](../../docs-public/docs_src/getting-started/) |
| 开发指南 | [docs-public/developers/](../../docs-public/docs_src/developers/) |
| 数据类型设计 | [cross-layer/architecture/DATA_TYPES_ARCHITECTURE.md](cross-layer/architecture/DATA_TYPES_ARCHITECTURE.md) |
| Embedding 系统 | [cross-layer/migration/EMBEDDING_README.md](cross-layer/migration/EMBEDDING_README.md) |
| Agent Benchmark | [l5-benchmark/README.md](l5-benchmark/README.md) |
| Control Plane | [cross-layer/architecture/SAGE_VLLM_CONTROL_PLANE_INTEGRATION.md](cross-layer/architecture/SAGE_VLLM_CONTROL_PLANE_INTEGRATION.md) |
| Pre-commit 工具 | [l6-tools/PRE_COMMIT_AUTOFIX_GUIDE.md](l6-tools/PRE_COMMIT_AUTOFIX_GUIDE.md) |
| CLI 命令速查 | [l6-cli/COMMAND_CHEATSHEET.md](l6-cli/COMMAND_CHEATSHEET.md) |

## 📝 文档原则

1. **公开优先**: 用户文档放在 `docs-public/`
2. **架构设计**: 系统设计文档保留在 `dev-notes/`
3. **及时归档**: 完成的工作及时归档到 `archive/`
4. **保持精简**: 只保留活跃的核心文档

## 📊 统计

- **活跃文档**: 20+ 个
- **归档文档**: 15+ 个
- **文档分类**: 架构设计 (6) + 系统文档 (5) + Agent Benchmark (4) + 运维配置 (2) + 开发工具 (1) + 模板 (1)

## 🆘 需要帮助？

- 阅读 [docs-public 重组计划](../../docs-public/DOCS_RESTRUCTURE_PLAN.md)
- 提交 [GitHub Issue](https://github.com/intellistream/SAGE/issues)

---

**最后更新**: 2025-11-29
**维护者**: SAGE Core Team
