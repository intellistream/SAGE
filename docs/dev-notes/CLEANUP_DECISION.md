# dev-notes 文档清理决策

## 保留的文档（有持续价值）

### 架构设计文档（保留）
- `DATA_TYPES_ARCHITECTURE.md` - 数据类型架构，核心设计
- `NEUROMEM_ARCHITECTURE_ANALYSIS.md` - NeuroMem 架构分析
- `VLLM_SERVICE_INTEGRATION_DESIGN.md` - vLLM 集成设计
- `SAGE_CHAT_ARCHITECTURE.md` - Chat 命令架构

### 系统文档（保留）
- `APPLICATION_ORGANIZATION_STRATEGY.md` - 代码组织策略
- `EMBEDDING_README.md` - Embedding 系统总览
- `EMBEDDING_QUICK_REFERENCE.md` - API 快速参考
- `EMBEDDING_SYSTEM_COMPLETE_SUMMARY.md` - 完整总结

### 运维文档（保留）
- `CODECOV_SETUP_GUIDE.md` - CI/CD 配置
- `KNOWN_ISSUES.md` - 已知问题
- `DEV_INFRASTRUCTURE_SETUP.md` - 基础设施配置

### 模板（保留）
- `TEMPLATE.md` - 文档模板
- `README.md` - 目录索引

## 归档的文档（历史参考）

### 使用指南（归档到 guides/）
- `PIPELINE_BUILDER_ENHANCEMENT_PHASE5.md` - Phase 5 已完成
- `PIPELINE_EMBEDDING_GUIDE.md` - 功能指南
- `RAG_DATA_TYPES_GUIDE.md` - 使用指南
- `PYLANCE_TYPE_ERRORS_GUIDE.md` - 问题排查指南

理由：这些是具体功能的使用说明，应该整合到 docs-public 或 package 文档中

## 总结

- **保留**: 12 个核心设计和运维文档
- **归档**: 4 个使用指南
- **已删除**: 6 个已迁移文档
- **已归档**: 5 个临时报告和迁移指南
