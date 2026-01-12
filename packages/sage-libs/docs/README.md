# sage-libs 文档目录

**最后更新**: 2026-01-10\
**清理状态**: ✅ 已清理重复文档

## 📚 主文档（6个）

### 核心文档

1. **REORGANIZATION_PROPOSAL.md** ⭐ - sage-libs 重组方案（主文档）

   - 外迁策略、模块划分、实施步骤
   - 澄清"外迁"的含义（不是隔离，SAGE 仍使用）

1. **QUICK_REFERENCE.md** 📖 - 快速参考指南

   - 常用 API 快速查询
   - 导入路径速查

1. **EXTERNALIZATION_STATUS.md** 📊 - 外迁状态跟踪

   - 哪些包已外迁
   - 哪些包待外迁

### 技术文档

4. **INTERFACE_LAYER_USAGE_GUIDE.md** 🔧 - 接口层使用指南

   - 接口/实现分离模式
   - 如何使用外迁的包

1. **MIGRATION_EXTERNAL_LIBS.md** 📝 - 外部库迁移指南

   - 迁移流程和注意事项

1. **LIBAMM_DATA_QUICKSTART.md** 🚀 - AMMS 快速开始

   - 近似矩阵乘算法快速入门

## 📁 子目录文档（5个）

### agentic/ (1个)

- `REGISTRY_USAGE.md` - Agent 注册表使用方法

### amms/ (3个)

- `LIBAMM_README.md` - AMMS 库说明
- `PAPI_PRECOMPILED_SOLUTION.md` - PAPI 预编译解决方案
- `QUICKREF.md` - AMMS 快速参考

### anns/ (1个)

- `MIGRATION.md` - ANNS 迁移指南

## 🗑️ 已清理的文档

### 主目录删除（8个）

- ❌ `REORGANIZATION_PLAN.md` - 与 PROPOSAL 重复
- ❌ `REORGANIZATION_ANALYSIS.md` - 已整合
- ❌ `REORGANIZATION_SUMMARY.md` - 与 PROPOSAL 重复
- ❌ `REORGANIZATION_COMPLETED.md` - 状态过时
- ❌ `REORGANIZATION_COMPLETED_SUMMARY.md` - 与 PROPOSAL 重复
- ❌ `ARCHITECTURE_CORRECTION.md` - 历史误解记录
- ❌ `DECISION_SUMMARY.md` - 已整合到 PROPOSAL
- ❌ `INTERFACE_LAYER_REFACTOR_COMPLETED.md` - 重构完成记录
- ❌ `INTERFACE_LAYER_ARCHITECTURE.md` - 已整合到 USAGE_GUIDE

### agentic/ 删除（3个）

- ❌ `EXTERNALIZATION_PLAN.md` - 过时计划
- ❌ `PHASE1_INTERFACE_COMPLETE.md` - 完成记录
- ❌ `REGISTRY_MIGRATION_STRATEGY.md` - 迁移策略记录

### amms/ 删除（8个）

- ❌ `INSTALLATION.md` / `INSTALLATION_GUIDE.md` - 重复
- ❌ `PYPI_BUILD_STRATEGY.md` / `BUILD_PUBLISH.md` / `PYPI_PUBLISH_GUIDE.md` - 重复
- ❌ `MIGRATION.md` / `INDEPENDENT_MIGRATION.md` / `REFACTORING_SUMMARY.md` - 重复
- ❌ `CHECKLIST.md` / `implementations.md` - 不需要

## 📊 清理前后对比

| 统计项   | 清理前 | 清理后 | 减少      |
| -------- | ------ | ------ | --------- |
| 总文档数 | 30     | 11     | -19 (63%) |
| 主目录   | 19     | 6      | -13       |
| agentic/ | 4      | 1      | -3        |
| amms/    | 16     | 3      | -13       |
| anns/    | 1      | 1      | 0         |

## ✅ 清理原则

1. **删除重复** - 相同主题只保留一份最新最全的
1. **删除过时** - 已完成的计划、迁移记录等
1. **删除历史** - 误解纠正、决策记录等
1. **保留实用** - 使用指南、快速参考、状态跟踪

## 📌 文档维护建议

- **主文档**：只保留 `REORGANIZATION_PROPOSAL.md` 作为唯一的重组方案文档
- **状态跟踪**：`EXTERNALIZATION_STATUS.md` 记录实时状态
- **使用指南**：技术文档保持更新
- **避免重复**：新增文档前先检查是否已有类似内容
