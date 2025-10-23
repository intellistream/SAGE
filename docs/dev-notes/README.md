# SAGE 开发者笔记 (Dev Notes)

> **注意**: 本目录主要供核心开发团队内部使用。
> 
> **用户文档**: 请访问 [docs-public](../../docs-public/) 获取完整的用户和开发者文档。

## 📂 当前文档

### 🏗️ 架构设计

| 文档 | 描述 | 状态 |
|------|------|------|
| [DATA_TYPES_ARCHITECTURE.md](DATA_TYPES_ARCHITECTURE.md) | 数据类型架构设计 | ✅ 活跃 |
| [NEUROMEM_ARCHITECTURE_ANALYSIS.md](NEUROMEM_ARCHITECTURE_ANALYSIS.md) | NeuroMem 架构分析 | ✅ 活跃 |
| [VLLM_SERVICE_INTEGRATION_DESIGN.md](VLLM_SERVICE_INTEGRATION_DESIGN.md) | vLLM 服务集成设计 | ✅ 活跃 |
| [SAGE_CHAT_ARCHITECTURE.md](SAGE_CHAT_ARCHITECTURE.md) | Chat 命令架构 | ✅ 活跃 |

### 📋 系统文档

| 文档 | 描述 | 状态 |
|------|------|------|
| [APPLICATION_ORGANIZATION_STRATEGY.md](APPLICATION_ORGANIZATION_STRATEGY.md) | 应用代码组织策略 | ✅ 活跃 |
| [EMBEDDING_README.md](EMBEDDING_README.md) | Embedding 系统总览 | ✅ 活跃 |
| [EMBEDDING_QUICK_REFERENCE.md](EMBEDDING_QUICK_REFERENCE.md) | Embedding API 快速参考 | ✅ 活跃 |
| [EMBEDDING_SYSTEM_COMPLETE_SUMMARY.md](EMBEDDING_SYSTEM_COMPLETE_SUMMARY.md) | Embedding 系统完整总结 | ✅ 活跃 |

### ⚙️ 运维配置

| 文档 | 描述 | 状态 |
|------|------|------|
| [CODECOV_SETUP_GUIDE.md](CODECOV_SETUP_GUIDE.md) | CodeCov CI/CD 配置 | ✅ 活跃 |
| [KNOWN_ISSUES.md](KNOWN_ISSUES.md) | 已知问题跟踪 | ✅ 活跃 |
| [DEV_INFRASTRUCTURE_SETUP.md](DEV_INFRASTRUCTURE_SETUP.md) | 开发基础设施配置 | ✅ 活跃 |

### 📄 模板

| 文档 | 描述 |
|------|------|
| [TEMPLATE.md](TEMPLATE.md) | 新文档模板 |

## 📦 归档文档

所有历史文档已整理到 `archive/` 目录：

```
archive/
├── 2025-restructuring/     # 2025年重构相关文档
│   ├── PACKAGE_RESTRUCTURING_*.md
│   ├── RESTRUCTURING_SUMMARY.md
│   ├── TOP_LAYER_REVIEW*.md
│   ├── TEST_*.md
│   └── ...
├── guides/                 # 功能使用指南
│   ├── PIPELINE_*.md
│   ├── RAG_DATA_TYPES_GUIDE.md
│   └── PYLANCE_TYPE_ERRORS_GUIDE.md
└── migration-guides/       # 已完成的迁移指南
    ├── EMBEDDING_PATH_MIGRATION.md
    ├── ENV_VARIABLES_MIGRATION.md
    └── NAMESPACE_PACKAGE_FIX.md
```

## 🔍 查找文档

| 需要了解 | 查看 |
|---------|------|
| 系统架构 | [docs-public/architecture/](../../docs-public/docs_src/architecture/) |
| 快速开始 | [docs-public/getting-started/](../../docs-public/docs_src/getting-started/) |
| 开发指南 | [docs-public/developers/](../../docs-public/docs_src/developers/) |
| 数据类型设计 | [DATA_TYPES_ARCHITECTURE.md](DATA_TYPES_ARCHITECTURE.md) |
| Embedding 系统 | [EMBEDDING_README.md](EMBEDDING_README.md) |
| 已知问题 | [KNOWN_ISSUES.md](KNOWN_ISSUES.md) |

## 📝 文档原则

1. **公开优先**: 用户文档放在 `docs-public/`
2. **架构设计**: 系统设计文档保留在 `dev-notes/`
3. **及时归档**: 完成的工作及时归档到 `archive/`
4. **保持精简**: 只保留活跃的核心文档

## 📊 统计

- **活跃文档**: 13 个
- **归档文档**: 15+ 个
- **文档分类**: 架构设计 (4) + 系统文档 (4) + 运维配置 (3) + 模板 (2)

## 🆘 需要帮助？

- 查看 [清理决策](CLEANUP_DECISION.md) 了解文档整理原则
- 阅读 [docs-public 重组计划](../../docs-public/DOCS_RESTRUCTURE_PLAN.md)
- 提交 [GitHub Issue](https://github.com/intellistream/SAGE/issues)

---

**最后更新**: 2025-10-23  
**维护者**: SAGE Core Team
