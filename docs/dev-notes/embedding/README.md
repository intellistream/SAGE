# SAGE Embedding 系统 - 详细文档

本目录包含 SAGE embedding 系统的完整开发文档。

---

## 📋 文档列表

### 规划与设计

- **[EMBEDDING_OPTIMIZATION_PLAN.md](EMBEDDING_OPTIMIZATION_PLAN.md)** - 完整规划和架构设计
  - 系统架构
  - 技术路线
  - 实施计划

### 实施报告

- **[EMBEDDING_OPTIMIZATION_PHASE1_COMPLETE.md](EMBEDDING_OPTIMIZATION_PHASE1_COMPLETE.md)** - Phase 1: 核心架构
  - BaseEmbedding 抽象基类
  - EmbeddingFactory 工厂模式
  - EmbeddingRegistry 注册系统
  - 3 个基础 wrapper

- **[EMBEDDING_OPTIMIZATION_PHASE2_COMPLETE.md](EMBEDDING_OPTIMIZATION_PHASE2_COMPLETE.md)** - Phase 2: 全面支持
  - 8 个新 wrapper
  - 总计 11 种方法
  - 完整测试覆盖

- **[EMBEDDING_OPTIMIZATION_PHASE3_COMPLETE.md](EMBEDDING_OPTIMIZATION_PHASE3_COMPLETE.md)** - Phase 3: CLI 工具
  - 4 个 CLI 命令
  - 批量 API 优化
  - 性能对比工具

### 集成与应用

- **[PIPELINE_BUILDER_EMBEDDING_INTEGRATION.md](PIPELINE_BUILDER_EMBEDDING_INTEGRATION.md)** - Pipeline Builder 集成
  - 知识库增强
  - CLI 参数支持
  - 分析工具
  - 使用指南

### 版本历史

- **[EMBEDDING_CHANGELOG.md](EMBEDDING_CHANGELOG.md)** - 完整更新日志
  - 版本历史
  - 功能变更
  - 性能改进

---

## 🎯 快速导航

**我想...**

- 了解整体架构 → `EMBEDDING_OPTIMIZATION_PLAN.md`
- 查看开发历程 → `EMBEDDING_OPTIMIZATION_PHASE*.md`
- 学习如何使用 → 回到 `../EMBEDDING_README.md`
- 快速参考命令 → `../EMBEDDING_QUICK_REFERENCE.md`
- 了解版本变更 → `EMBEDDING_CHANGELOG.md`

---

**目录结构**: `docs/dev-notes/embedding/`  
**更新时间**: 2024-10-06
