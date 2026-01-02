# Cross-Layer Documentation

**Date**: 2025-11-29\
**Author**: SAGE Team\
**Summary**: 跨层级文档索引，包含架构设计、CI/CD、数据架构、迁移指南等跨多个包的文档

______________________________________________________________________

## 📁 目录结构

```
cross-layer/
├── README.md                              # 本索引文件
├── architecture/                          # 架构设计文档
├── ci-cd/                                 # CI/CD 相关文档
├── data-architecture/                     # 数据架构文档
├── deployment/                            # 部署相关文档
├── gateway-rag-service/                   # Gateway RAG 服务文档
├── migration/                             # 迁移指南
├── security/                              # 安全相关文档
├── studio-chat/                           # Studio Chat 功能文档
├── testing/                               # 测试相关文档
└── archive/                               # 归档的过时文档
```

______________________________________________________________________

## 📚 核心文档

### 架构设计 (architecture/)

| 文档                                                                                          | 描述                   | 状态    |
| --------------------------------------------------------------------------------------------- | ---------------------- | ------- |
| [DATA_TYPES_ARCHITECTURE.md](architecture/DATA_TYPES_ARCHITECTURE.md)                         | 数据类型分层架构设计   | ✅ 有效 |
| [SAGE_CHAT_ARCHITECTURE.md](architecture/SAGE_CHAT_ARCHITECTURE.md)                           | sage chat 功能架构     | ✅ 有效 |
| [VLLM_SERVICE_INTEGRATION_DESIGN.md](architecture/VLLM_SERVICE_INTEGRATION_DESIGN.md)         | vLLM 服务集成设计      | ✅ 有效 |
| [SAGE_VLLM_CONTROL_PLANE_INTEGRATION.md](architecture/SAGE_VLLM_CONTROL_PLANE_INTEGRATION.md) | Control Plane 集成方案 | ✅ 有效 |
| [NEUROMEM_ARCHITECTURE_ANALYSIS.md](architecture/NEUROMEM_ARCHITECTURE_ANALYSIS.md)           | NeuroMem 架构分析      | ✅ 有效 |

### CI/CD (ci-cd/)

| 文档                                                                 | 描述                       | 状态    |
| -------------------------------------------------------------------- | -------------------------- | ------- |
| [README.md](ci-cd/README.md)                                         | CI/CD 文档索引             | ✅ 有效 |
| [CICD_MIGRATION_TO_SAGE_DEV.md](ci-cd/CICD_MIGRATION_TO_SAGE_DEV.md) | CI/CD 迁移到 sage-dev 命令 | ✅ 有效 |
| [VERSION_MANAGEMENT.md](ci-cd/VERSION_MANAGEMENT.md)                 | 版本管理策略               | ✅ 有效 |
| [CODECOV_SETUP_GUIDE.md](ci-cd/CODECOV_SETUP_GUIDE.md)               | Codecov 设置指南           | ✅ 有效 |
| [CODE_QUALITY_GUIDE.md](ci-cd/CODE_QUALITY_GUIDE.md)                 | 代码质量指南               | ✅ 有效 |
| [PRE_COMMIT_TROUBLESHOOTING.md](ci-cd/PRE_COMMIT_TROUBLESHOOTING.md) | Pre-commit 故障排除        | ✅ 有效 |

### 数据架构 (data-architecture/)

| 文档                                                                             | 描述             | 状态    |
| -------------------------------------------------------------------------------- | ---------------- | ------- |
| [DATA_ARCHITECTURE_REDESIGN.md](data-architecture/DATA_ARCHITECTURE_REDESIGN.md) | 数据架构重设计   | ✅ 有效 |
| [DATA_QUICK_START.md](data-architecture/DATA_QUICK_START.md)                     | 数据架构快速入门 | ✅ 有效 |
| [DATA_EXTENSION_GUIDE.md](data-architecture/DATA_EXTENSION_GUIDE.md)             | 数据扩展指南     | ✅ 有效 |
| [DATA_MIGRATION_GUIDE.md](data-architecture/DATA_MIGRATION_GUIDE.md)             | 数据迁移指南     | ✅ 有效 |

### Control Plane (control-plane/)

| 文档                                                                       | 描述                                 | 状态    |
| -------------------------------------------------------------------------- | ------------------------------------ | ------- |
| [README.md](control-plane/README.md)                                       | Control Plane 任务规划与路由修复汇总 | ✅ 有效 |
| [LLM_CONTROL_PLANE_TASKS.md](control-plane/LLM_CONTROL_PLANE_TASKS.md)     | LLM 控制平面任务拆解                 | ✅ 有效 |
| [CONTROL_PLANE_ROUTING_FIX.md](control-plane/CONTROL_PLANE_ROUTING_FIX.md) | 控制平面路由修复记录                 | ✅ 有效 |

### 迁移指南 (migration/)

| 文档                                                                                   | 描述                   | 状态    |
| -------------------------------------------------------------------------------------- | ---------------------- | ------- |
| [EMBEDDING_README.md](migration/EMBEDDING_README.md)                                   | Embedding 系统说明     | ✅ 有效 |
| [EMBEDDING_SYSTEM_COMPLETE_SUMMARY.md](migration/EMBEDDING_SYSTEM_COMPLETE_SUMMARY.md) | Embedding 系统完整总结 | ✅ 有效 |
| [EMBEDDING_QUICK_REFERENCE.md](migration/EMBEDDING_QUICK_REFERENCE.md)                 | Embedding 快速参考     | ✅ 有效 |
| [PROJECT_STRUCTURE.md](migration/PROJECT_STRUCTURE.md)                                 | 项目结构规范           | ✅ 有效 |
| [TOOLS_INTEGRATION_TO_SAGE_TOOLS.md](migration/TOOLS_INTEGRATION_TO_SAGE_TOOLS.md)     | 工具集成到 sage-tools  | ✅ 有效 |
| [APPLICATION_ORGANIZATION_STRATEGY.md](migration/APPLICATION_ORGANIZATION_STRATEGY.md) | 应用组织策略           | ✅ 有效 |

### 安全 (security/)

| 文档                                                          | 描述             | 状态    |
| ------------------------------------------------------------- | ---------------- | ------- |
| [README.md](security/README.md)                               | 安全文档索引     | ✅ 有效 |
| [API_KEY_SECURITY.md](security/API_KEY_SECURITY.md)           | API Key 安全指南 | ✅ 有效 |
| [CONFIG_CLEANUP_REPORT.md](security/CONFIG_CLEANUP_REPORT.md) | 配置清理报告     | ✅ 有效 |

### 测试 (testing/)

| 文档                                                                             | 描述                     | 状态    |
| -------------------------------------------------------------------------------- | ------------------------ | ------- |
| [PYTEST_CONFIG_STRATEGY.md](testing/PYTEST_CONFIG_STRATEGY.md)                   | Pytest 配置策略          | ✅ 有效 |
| [SAGE_LIBS_TEST_COVERAGE_SUMMARY.md](testing/SAGE_LIBS_TEST_COVERAGE_SUMMARY.md) | sage-libs 测试覆盖率总结 | ✅ 有效 |

______________________________________________________________________

## 📝 根目录独立文档

### 重要参考文档

| 文档                                                                         | 描述                               | 状态    |
| ---------------------------------------------------------------------------- | ---------------------------------- | ------- |
| [BREAKING_CHANGES_agent_tools_plan.md](BREAKING_CHANGES_agent_tools_plan.md) | Agent Tools 功能分支破坏性变更说明 | ✅ 有效 |
| [MERGE_CONFLICT_RESOLUTION_GUIDE.md](MERGE_CONFLICT_RESOLUTION_GUIDE.md)     | 合并冲突解决指南                   | ✅ 有效 |
| [FINETUNE_ARCHITECTURE.md](FINETUNE_ARCHITECTURE.md)                         | Fine-tune 功能架构说明             | ✅ 有效 |
| [AGENT_TRAINING_PIPELINE.md](AGENT_TRAINING_PIPELINE.md)                     | Agent 训练流水线文档               | ✅ 有效 |

### 功能特定文档

| 文档                                                                       | 描述                      | 状态    |
| -------------------------------------------------------------------------- | ------------------------- | ------- |
| [FINETUNE_BACKEND_INTEGRATION.md](FINETUNE_BACKEND_INTEGRATION.md)         | Fine-tune 后端集成        | ✅ 有效 |
| [FINETUNE_GPU_RESOURCE_MANAGEMENT.md](FINETUNE_GPU_RESOURCE_MANAGEMENT.md) | Fine-tune GPU 资源管理    | ✅ 有效 |
| [FINETUNE_PROCESS_PERSISTENCE.md](FINETUNE_PROCESS_PERSISTENCE.md)         | Fine-tune 任务持久化      | ✅ 有效 |
| [CODE_SHARING_RAG_INDEXBUILDER.md](CODE_SHARING_RAG_INDEXBUILDER.md)       | RAG IndexBuilder 代码共享 | ✅ 有效 |

### Fine-tune & Agent 训练（跨层）

Fine-tune 与 Agent 训练相关的文档分布在 cross-layer 与 L3 libs 两个层级，本小节对其进行集中说明：

- 架构与分层定位 (`FINETUNE_ARCHITECTURE.md`)
  - 解释为什么 Fine-tune 主要作为 L6 (sage-tools) 的开发工具存在，而不是下沉到 L1/L2。
  - 给出推荐方案：在 L1 定义 `IFineTuneService` 接口，具体实现保持在 L6，避免核心层依赖 heavy 训练库。
- Studio & Chat 后端集成
  - `FINETUNE_BACKEND_INTEGRATION.md`：描述微调模型如何被挂载为 Studio Chat 的后端（前端按钮 → FastAPI → vLLM Registry →
    Engine 切换）。
  - `FINETUNE_GPU_RESOURCE_MANAGEMENT.md`：说明 Studio 本地队列和 GPU 检测逻辑，强调「单 GPU 串行、任务排队、自动推荐模型」等策略。
  - `FINETUNE_PROCESS_PERSISTENCE.md`：记录从 daemon 线程到独立进程的重构，使 Studio 重启后微调任务能够继续运行。
- Agent 训练管线 (`AGENT_TRAINING_PIPELINE.md`)
  - 从业务挑战（工具选择、规划、时机决策、千级工具检索）出发设计 SFT + RL 训练流水线。
  - 提供阶段划分（Warmup / SFT / RL / Evaluation）与典型配置 `AgentSFTConfig` 的示例。
  - 与 L3-libs 中的 `AGENT_FINETUNE_API_REFERENCE.md` 呼应，前者侧重训练流程与数据组织，后者侧重具体 API 与实现。

在阅读顺序上，建议先看本 README 中的概览，再根据关注点分别跳转到上述 cross-layer 与 L3-libs 文档。

### 环境和部署

| 文档                                                   | 描述             | 状态    |
| ------------------------------------------------------ | ---------------- | ------- |
| [SELF_HOSTED_DEPLOYMENT.md](SELF_HOSTED_DEPLOYMENT.md) | 自托管部署指南   | ✅ 有效 |
| [CAMPUS_NETWORK_ACCESS.md](CAMPUS_NETWORK_ACCESS.md)   | 校园网络访问指南 | ✅ 有效 |
| [BUILD_CACHE_MANAGEMENT.md](BUILD_CACHE_MANAGEMENT.md) | 构建缓存管理     | ✅ 有效 |

______________________________________________________________________

## 🗄️ 归档文档 (archive/)

已过时或已完成的文档移至 `archive/` 目录：

| 文档                                 | 原因                     |
| ------------------------------------ | ------------------------ |
| `REBASE_FEAT_UNIFIED_CHAT_CANVAS.md` | 分支合并已完成           |
| `OPENAICLIENT_MIGRATION_SUMMARY.md`  | OpenAI Client 迁移已完成 |
| `STUDIO_ISSUES_FIX_SUMMARY.md`       | Studio 问题修复已完成    |
| `STUDIO_ISSUES_FIX.md`               | Studio 问题修复已完成    |
| `STUDIO_RESTART_AUTO_CLEAN.md`       | 功能已实现               |

______________________________________________________________________

## 🔗 关联文档

- **层级文档**: `docs/dev-notes/l1-common/` ~ `l6-*/`
- **公共文档**: `docs-public/docs_src/`
- **架构规范**: `docs-public/docs_src/dev-notes/package-architecture.md`
- **Copilot 指南**: `.github/copilot-instructions.md`

______________________________________________________________________

## 📋 维护指南

### 添加新文档

1. **确定分类**: 根据文档主题选择合适的子目录
1. **使用模板**: 参考 `docs/dev-notes/TEMPLATE.md`
1. **更新索引**: 在本 README 中添加链接

### 归档旧文档

当文档满足以下条件时应移至 `archive/`：

- ✅ 功能已完成且稳定
- ✅ 迁移/重构已完成
- ✅ 文档内容不再适用于当前代码
- ✅ 超过 6 个月未更新且内容过时

### 文档状态标记

| 状态      | 含义                          |
| --------- | ----------------------------- |
| ✅ 有效   | 文档与代码一致，可正常使用    |
| ⚠️ 需更新 | 文档部分过时，需要修改        |
| 🗑️ 归档   | 文档已过时，应移动到 archive/ |

______________________________________________________________________

*最后更新: 2025-11-29*
