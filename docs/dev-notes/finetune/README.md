# Finetune 开发文档索引

本目录包含 SAGE 微调功能的开发文档和历史记录。

## 📁 文档结构

### 核心文档
- **[FINETUNE_REFACTOR_SUMMARY.md](./FINETUNE_REFACTOR_SUMMARY.md)** - 模块化重构总结
- **[CHAT_FINETUNE_INTEGRATION_SUMMARY.md](./CHAT_FINETUNE_INTEGRATION_SUMMARY.md)** - Chat 集成说明

### 历史记录
- **[FINETUNE_COMPATIBILITY_FIX.md](./FINETUNE_COMPATIBILITY_FIX.md)** - 兼容性修复
- **[FINETUNE_MODULE_TEST_REPORT.md](./FINETUNE_MODULE_TEST_REPORT.md)** - 模块测试报告
- **[CLEANUP_SUMMARY.md](./CLEANUP_SUMMARY.md)** - 清理工作总结
- **[DOCUMENTATION_STRUCTURE.md](./DOCUMENTATION_STRUCTURE.md)** - 文档结构说明
- **[DOCUMENTATION_REORGANIZATION_SUMMARY.md](./DOCUMENTATION_REORGANIZATION_SUMMARY.md)** - 文档重组总结

## 🎯 快速导航

### 想要了解...
- **如何使用微调功能？** → 查看主文档: `packages/sage-tools/src/sage/tools/finetune/README.md`
- **架构设计？** → 查看: `packages/sage-tools/src/sage/tools/finetune/ARCHITECTURE.md`
- **模块化重构？** → 查看: [FINETUNE_REFACTOR_SUMMARY.md](./FINETUNE_REFACTOR_SUMMARY.md)
- **Chat 集成？** → 查看: [CHAT_FINETUNE_INTEGRATION_SUMMARY.md](./CHAT_FINETUNE_INTEGRATION_SUMMARY.md)

## 📝 开发历史

### v2.0 - 模块化重构 (2025-10-07)
- 从 1270 行单文件拆分为 9 个模块
- 统一目录结构，删除重复
- 文档合并优化

### v1.5 - Chat 集成 (2025-10-07)
- 在 `sage chat` 中添加 finetune backend
- 自动服务检测和启动
- 代码简化（减少 85%）

### v1.0 - 初始实现
- SAGE 原生训练模块
- CLI 命令工具
- 支持多种微调场景

## 🔗 相关资源

- **用户文档**: `packages/sage-tools/src/sage/tools/finetune/README.md`
- **代码目录**: `packages/sage-tools/src/sage/tools/finetune/`
- **测试**: `tools/tests/test_finetune_*.py`

---

**注意**: 本目录下的文档主要面向开发者，记录了功能的演进历史和技术细节。
