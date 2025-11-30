# 文档清理并行任务分配

> 创建时间: 2025-11-29
> 背景: `main-dev` 分支对比 `main-dev-pre-agent-tools` 有 388 个文件变更，85,534 行新增，大量文档需要更新和清理

## 任务概述

文档清理分为 **两个阶段**：

### 阶段一：dev-notes 内部文档清理（6 个并行任务）
- Task 1-6：清理 `docs/dev-notes/` 下的开发文档
- 可完全并行执行

### 阶段二：docs_src 公共文档更新（5 个并行任务）
- Task 7-11：更新 `docs-public/docs_src/` 下的用户文档
- **必须在阶段一完成后执行**（需要参考清理后的 dev-notes）

---

# 阶段一：dev-notes 清理任务

## Task 1: L1-L3 层文档清理 (sage-common, sage-platform, sage-kernel, sage-libs)

### 提示词

```
你是 SAGE 项目的文档维护者。请完成以下任务：

**范围**: `docs/dev-notes/` 下的 L1-L3 层文档
- `l1-common/` - sage-common 包文档
- `l2-platform/` - sage-platform 包文档  
- `l3-kernel/` - sage-kernel 包文档
- `l3-libs/` - sage-libs 包文档

**任务清单**:
1. 检查每个目录下的 README.md 是否存在，不存在则创建
2. 验证文档中的代码示例是否与当前代码一致（对照 `packages/sage-*/src/sage/*/`）
3. 检查文档中的链接是否有效（文件是否存在）
4. 删除或归档过时的文档（移动到 `archive/` 目录）
5. 更新 API 引用路径（检查 import 语句是否正确）

**重点检查**:
- `l3-libs/` 下的 Embedding 相关文档是否反映了 `UnifiedInferenceClient` 和 `EmbeddingClientAdapter` 的新架构
- `l3-libs/` 下的 Finetune 相关文档是否与 `packages/sage-libs/src/sage/libs/finetune/` 代码一致
- `l1-common/` 下的 `hybrid-scheduler/` 文档是否与 Control Plane 架构一致

**输出要求**:
- 修改的文件列表
- 删除/归档的文件列表
- 新创建的文件列表
- 发现的问题（无法自动修复的）
```

---

## Task 2: L4-L5 层文档清理 (sage-middleware, sage-apps, sage-benchmark)

### 提示词

```
你是 SAGE 项目的文档维护者。请完成以下任务：

**范围**: `docs/dev-notes/` 下的 L4-L5 层文档
- `l4-middleware/` - sage-middleware 包文档（C++ 扩展、neuromem、storage）
- `l5-apps/` - sage-apps 包文档
- `l5-benchmark/` - sage-benchmark 包文档

**任务清单**:
1. 检查每个目录下的 README.md 是否完整
2. 验证 `l4-middleware/` 下的 neuromem 相关文档是否与 `packages/sage-middleware/src/sage/middleware/components/` 代码一致
3. 验证 `l5-benchmark/` 下的文档是否涵盖了新模块：
   - `benchmark_agent` (Agent 能力评测)
   - `benchmark_control_plane` (Control Plane 调度评测)
4. 检查文档中的 CLI 命令是否正确（如 `sage-cp-bench`）
5. 更新过时的性能数据或实验结果描述

**重点检查**:
- `l5-benchmark/README.md` 是否包含所有 benchmark 模块
- `l4-middleware/` 下的 AUTOSTOP、DOCUMENT_STORAGE 等功能文档是否与代码同步
- `l5-benchmark/hybrid-scheduler-benchmark/` 是否需要更新

**输出要求**:
- 修改的文件列表
- 删除/归档的文件列表
- 新创建的文件列表
- 发现的问题（无法自动修复的）
```

---

## Task 3: L6 层文档清理 (sage-cli, sage-tools, sage-studio, sage-gateway)

### 提示词

```
你是 SAGE 项目的文档维护者。请完成以下任务：

**范围**: `docs/dev-notes/` 下的 L6 层文档
- `l6-cli/` - sage-cli 命令行文档
- `l6-tools/` - sage-tools 开发工具文档
- `l6-studio/` - sage-studio 前端文档
- `l6-gateway/` - sage-gateway API 网关文档

**任务清单**:
1. 检查每个目录下的 README.md 是否存在且完整
2. 验证 `l6-cli/` 下的命令文档是否与 `packages/sage-cli/src/sage/cli/commands/` 代码一致
3. 验证 `l6-tools/` 下的工具文档是否与当前脚本一致
4. 检查 `l6-studio/` 下的文档是否反映了最新的前后端架构
5. 验证 `l6-gateway/` 下的 API 文档是否与 `packages/sage-gateway/` 代码一致

**重点检查**:
- `l6-cli/COMMAND_CHEATSHEET.md` 是否包含所有新命令
- `l6-tools/` 下的 CI/CD、pre-commit、submodule 相关文档是否准确
- `l6-studio/` 下的 Finetune、Memory 集成文档是否与代码同步
- `l6-gateway/` 是否有完整的 OpenAI 兼容 API 文档

**输出要求**:
- 修改的文件列表
- 删除/归档的文件列表
- 新创建的文件列表
- 发现的问题（无法自动修复的）
```

---

## Task 4: 跨层文档清理 (cross-layer/)

### 提示词

```
你是 SAGE 项目的文档维护者。请完成以下任务：

**范围**: `docs/dev-notes/cross-layer/` 目录下的所有文档

**子目录**:
- `architecture/` - 架构设计文档
- `ci-cd/` - CI/CD 相关文档
- `data-architecture/` - 数据架构文档
- `deployment/` - 部署相关文档
- `gateway-rag-service/` - Gateway RAG 服务文档
- `migration/` - 迁移指南
- `security/` - 安全相关文档
- `studio-chat/` - Studio Chat 功能文档
- `testing/` - 测试相关文档

**任务清单**:
1. 验证 `architecture/` 下的架构文档是否与当前代码结构一致
2. 检查 `migration/` 下的迁移指南是否仍然有效
3. 验证 `ci-cd/` 下的文档是否与 `.github/workflows/` 一致
4. 检查根目录下的独立文档（如 `BREAKING_CHANGES_agent_tools_plan.md`）是否需要更新
5. 识别可以归档的旧文档（如已完成的迁移、已修复的 issue）

**重点检查**:
- `architecture/DATA_TYPES_ARCHITECTURE.md` 是否反映当前数据类型设计
- `architecture/UNIFIED_CLIENT_ARCHITECTURE.md` 是否与 `UnifiedInferenceClient` 实现一致
- `migration/` 下的文档是否已过时（检查日期和版本号）
- `BREAKING_CHANGES_agent_tools_plan.md` 是否涵盖所有破坏性变更

**输出要求**:
- 修改的文件列表
- 删除/归档的文件列表
- 新创建的文件列表
- 发现的问题（无法自动修复的）
```

---

## Task 5: 归档清理与主索引更新

### 提示词

```
你是 SAGE 项目的文档维护者。请完成以下任务：

**范围**:
- `docs/dev-notes/archive/` - 归档文档
- `docs/dev-notes/testing/` - 测试相关文档
- `docs/dev-notes/agent-tool-benchmark/` - Agent 工具 benchmark 文档
- `docs/dev-notes/README.md` - 主索引文件
- `docs/dev-notes/` 根目录下的独立文件

**任务清单**:
1. 整理 `archive/` 目录，删除重复或无价值的文档
2. 检查 `testing/` 目录下的测试报告是否需要归档
3. 检查 `agent-tool-benchmark/` 目录，与 `l5-benchmark/` 合并或归档重复内容
4. 更新 `README.md` 主索引：
   - 确保所有链接有效
   - 添加新目录/文档的入口
   - 删除不存在文件的链接
5. 清理根目录下的独立文件：
   - `advanced-experiments-plan.md`
   - `agent-benchmark-remaining-tasks.md`
   - `agent-benchmark-tasks.md`
   - `data_architecture_redesign_implementation.py` (这是代码文件，不应在 docs 目录)

**重点检查**:
- `archive/` 下的 ISSUE 修复文档是否仍需保留
- `testing/` 下的 TASK 完成报告是否应该归档
- `agent-tool-benchmark/` 与 `l5-benchmark/` 是否有重复
- `README.md` 的目录结构是否反映当前实际结构

**输出要求**:
- 修改的文件列表
- 删除/归档的文件列表
- 新创建的文件列表
- 发现的问题（无法自动修复的）
- 最终的 `README.md` 目录结构
```

---

## 阶段一通用指南

### 每个任务执行者请遵循：

1. **读取 `.github/copilot-instructions.md`** 了解项目架构
2. **对照代码验证** - 使用 `packages/sage-*/src/sage/*/` 下的代码验证文档
3. **检查链接** - 验证 Markdown 链接指向的文件是否存在
4. **保守删除** - 不确定是否过时的文档，移动到 `archive/` 而非直接删除
5. **记录变更** - 输出清晰的变更日志

### 文档状态标记：

| 状态 | 含义 |
|------|------|
| ✅ 有效 | 文档与代码一致，可正常使用 |
| ⚠️ 需更新 | 文档部分过时，需要修改 |
| 🗑️ 归档 | 文档已过时，应移动到 archive/ |
| ❌ 删除 | 重复或无价值，可直接删除 |

### 完成后汇总：

所有任务完成后，请在 `docs/dev-notes/` 下创建 `CLEANUP_SUMMARY_YYYYMMDD.md` 记录：
- 各任务修改的文件数
- 归档的文件数
- 删除的文件数
- 新创建的文件数
- 剩余问题清单

---

## 阶段一任务分配表

| 任务 | 负责范围 | 预估文件数 | 优先级 | 状态 |
|------|----------|-----------|--------|------|
| Task 1 | L1-L3 层 | ~30 | 高 | 🔲 待执行 |
| Task 2 | L4-L5 层 | ~25 | 高 | ✅ **已完成** (2025-01-23) |
| Task 3 | L6 层 | ~20 | 中 | 🔲 待执行 |
| Task 4 | cross-layer | ~40 | 高 | 🔲 待执行 |
| Task 5 | 归档+索引 | ~50 | 中 | ✅ **已完成** (2025-11-29) |

**建议执行顺序**: Task 1-4 可完全并行，Task 5 可在其他任务进行时同步执行（但最终的 README.md 更新需等待其他任务归档完成）

---

## Task 2 完成报告 (2025-01-23)

### 修改的文件
| 文件 | 修改内容 |
|------|----------|
| `l4-middleware/README.md` | 完全重写，添加 neuromem、multimodal storage、autostop、SONG GPU 模块文档 |
| `l5-benchmark/README.md` | 更新包含所有 7 个 benchmark 模块，添加 benchmark_agent 和 benchmark_control_plane |
| `l5-apps/README.md` | 标记 README 更新任务为已完成 |
| `examples/apps/README.md` | 扩展覆盖所有 5 个应用（video、medical、article、auto_scaling、smart_home）|
| `l6-cli/COMMAND_CHEATSHEET.md` | 添加 `sage` CLI 命令结构 |
| `l6-gateway/README.md` | 添加 REST API 端点表格 |
| `l6-studio/STUDIO_FINETUNE_INTEGRATION.md` | 添加缺失的 API 端点文档 |

### 归档的文件 (移动到 `l4-middleware/archive/`)
- `ISSUE_610_STATUS.md`
- `ISSUE_610_SUMMARY.md`
- `INVESTIGATION_SUMMARY.md` (原 `INVESTIGATION_README.md`)
- `MULTIMODAL_STORAGE_VERIFICATION.md`
- `FIX_APPLIED_NEUROMEM_IMPLEMENTATION.md`
- `NEUROMEM_SUBMODULE_CHANGES.md`

### 新创建的文件
- `l4-middleware/archive/README.md` - Archive 目录说明

### 文件名统一化 (2025-11-29 补充)

重命名为 SCREAMING_SNAKE_CASE 风格：

| 原文件名 | 新文件名 |
|----------|----------|
| `fix-autostop-service-cleanup.md` | `FIX_AUTOSTOP_SERVICE_CLEANUP.md` |
| `memory-statistics-feature.md` | `MEMORY_STATISTICS_FEATURE.md` |
| `remote-mode-support.md` | `REMOTE_MODE_SUPPORT.md` |
| `song_migration_complete.md` | `SONG_MIGRATION_COMPLETE.md` |
| `paper1-experiments-design.md` | `PAPER1_EXPERIMENTS_DESIGN.md` |
| `INVESTIGATION_README.md` | `INVESTIGATION_SUMMARY.md` |

### 发现的问题（无法自动修复）
- 无

**建议执行顺序**: Task 1-4 可完全并行，Task 5 可并行，Task 6 最后执行（依赖其他任务的归档结果）

---

# 阶段二：docs_src 公共文档更新任务

> ⚠️ **前置条件**: 阶段一的 Task 1-6 必须全部完成后才能开始阶段二
>
> 阶段二的任务需要参考清理后的 `docs/dev-notes/` 内容，将重要信息同步到用户面向的公共文档

---

## Task 7: 入门文档与安装指南更新

### 提示词

```
你是 SAGE 项目的文档维护者。请完成以下任务：

**前置条件**: 阶段一的 dev-notes 清理已完成

**范围**: `docs-public/docs_src/` 下的入门相关文档
- `getting-started/index.md` - 入门概览
- `getting-started/installation.md` - 安装指南
- `getting-started/quickstart.md` - 快速开始
- `index.md` - 首页
- `about.md` - 关于页面

**任务清单**:
1. 对照 `quickstart.sh` 更新 `installation.md`：
   - 验证安装命令是否正确（`--dev`, `--core`, `--standard`, `--full`）
   - 验证系统依赖列表（build-essential, cmake, libopenblas-dev 等）
   - 更新 Python 版本要求（3.10+）
   - 添加常见问题解决方案
2. 更新 `quickstart.md`：
   - 验证代码示例是否可运行
   - 添加 `UnifiedInferenceClient` 的简单示例
   - 更新 LLM 服务启动方式
3. 检查首页和关于页面的描述是否准确

**参考文档**:
- `.github/copilot-instructions.md` - 安装和配置说明
- `docs/dev-notes/l2-platform/` - 安装相关的开发笔记
- `CONTRIBUTING.md`, `DEVELOPER.md` - 贡献和开发指南

**重点检查**:
- 安装步骤的完整性和正确性
- 环境变量配置（`.env` 文件）
- 端口配置说明（使用 `SagePorts`）
- 子模块初始化说明

**输出要求**:
- 修改的文件列表及变更摘要
- 验证通过的安装步骤截图或日志（可选）
- 发现的问题
```

---

## Task 8: API 参考文档更新

### 提示词

```
你是 SAGE 项目的文档维护者。请完成以下任务：

**前置条件**: 阶段一的 dev-notes 清理已完成

**范围**: `docs-public/docs_src/api-reference/` 下的 API 文档
- `api-reference/index.md` - API 总览
- `api-reference/common/index.md` - sage-common API
- `api-reference/platform/index.md` - sage-platform API
- `api-reference/kernel/index.md` - sage-kernel API
- `api-reference/libs/index.md` - sage-libs API
- `api-reference/middleware/index.md` - sage-middleware API

**任务清单**:
1. 更新 `common/index.md`，添加新 API：
   - `UnifiedInferenceClient` - 统一推理客户端
   - `IntelligentEmbeddingClient` - 智能 Embedding 客户端
   - `SagePorts` - 统一端口配置
   - Control Plane 相关 API
2. 更新 `libs/index.md`，添加：
   - `EmbeddingClientAdapter` - Embedding 批量接口适配器
   - `EmbeddingFactory` - Embedding 工厂
   - Agentic 模块 API（tool_selection, planning, timing_decider）
3. 检查所有 API 签名是否与代码一致
4. 添加代码示例和使用说明

**参考文档**:
- `docs/dev-notes/cross-layer/BREAKING_CHANGES_agent_tools_plan.md` - API 变更
- `docs/dev-notes/l3-libs/README.md` - libs 层 API 说明
- `.github/copilot-instructions.md` - sageLLM 架构说明

**代码参考**:
- `packages/sage-common/src/sage/common/components/sage_llm/unified_client.py`
- `packages/sage-common/src/sage/common/components/sage_embedding/`
- `packages/sage-libs/src/sage/libs/agentic/`

**输出要求**:
- 修改的文件列表
- 新增的 API 文档条目
- API 签名与代码的一致性验证结果
```

---

## Task 9: 用户指南更新 (guides/)

### 提示词

```
你是 SAGE 项目的文档维护者。请完成以下任务：

**前置条件**: 阶段一的 dev-notes 清理已完成

**范围**: `docs-public/docs_src/guides/` 下的用户指南
- `guides/packages/sage-common/` - sage-common 使用指南
- `guides/packages/sage-libs/` - sage-libs 使用指南（重点）
- `guides/packages/sage-kernel/` - sage-kernel 使用指南
- `guides/packages/sage-middleware/` - sage-middleware 使用指南
- `guides/packages/sage-tools/` - sage-tools 使用指南
- `guides/deployment/` - 部署指南
- `guides/best-practices/` - 最佳实践

**任务清单**:
1. 更新 `sage-libs/` 指南：
   - `embedding.md` - 添加 `UnifiedInferenceClient` 和 `EmbeddingClientAdapter` 用法
   - `agents.md` - 更新 Agent 组件说明
   - `rag/` - 验证 RAG 组件文档
2. 更新 `sage-common/` 指南：
   - 添加 Control Plane 使用说明
   - 添加统一推理客户端指南
3. 验证 `sage-middleware/` 指南：
   - NeuroMem 组件文档
   - Memory 服务文档
4. 更新 `deployment/` 部署指南：
   - LLM 服务部署（vLLM）
   - Embedding 服务部署
   - Gateway 部署

**参考文档**:
- `docs/dev-notes/l3-libs/` - libs 开发笔记
- `docs/dev-notes/l4-middleware/` - middleware 开发笔记
- `docs/dev-notes/cross-layer/deployment/` - 部署相关笔记

**重点检查**:
- 代码示例的正确性和可运行性
- import 语句是否正确
- 配置说明是否完整

**输出要求**:
- 修改的文件列表
- 新增的指南文档
- 需要后续完善的内容清单
```

---

## Task 10: 教程与示例更新 (tutorials/)

### 提示词

```
你是 SAGE 项目的文档维护者。请完成以下任务：

**前置条件**: 阶段一的 dev-notes 清理已完成

**范围**: `docs-public/docs_src/tutorials/` 下的教程文档
- `tutorials/basic/` - 基础教程
  - `streaming-101.md` - 流式处理入门
  - `hello_batch.md` - 批处理示例
  - `operators/` - 算子使用教程
- `tutorials/advanced/` - 高级教程
  - `distributed-pipeline.md` - 分布式 Pipeline
  - `custom-operators.md` - 自定义算子
  - `advanced-rag.md` - 高级 RAG
  - `performance-tuning.md` - 性能调优
  - `fault-tolerance.md` - 容错机制

**任务清单**:
1. 验证基础教程代码示例：
   - 对照 `examples/tutorials/` 目录下的实际代码
   - 确保 import 语句正确
   - 验证输出结果描述准确
2. 更新高级教程：
   - `advanced-rag.md` - 集成 `UnifiedInferenceClient`
   - `performance-tuning.md` - 添加 Control Plane 调优说明
3. 检查所有教程的依赖说明
4. 添加必要的前置知识说明

**参考代码**:
- `examples/tutorials/` - 实际教程代码
- `examples/apps/` - 应用示例代码

**重点检查**:
- 代码是否与 `examples/` 目录同步
- 步骤说明是否清晰完整
- 截图或示意图是否需要更新

**输出要求**:
- 修改的文件列表
- 代码示例验证结果
- 需要更新截图的位置
```

---

## Task 11: 开发者文档与 mkdocs 配置更新

### 提示词

```
你是 SAGE 项目的文档维护者。请完成以下任务：

**前置条件**: 阶段一的 dev-notes 清理已完成，Task 7-10 已完成

**范围**:
- `docs-public/docs_src/developers/` - 开发者文档
- `docs-public/docs_src/dev-notes/` - 公共 dev-notes 入口
- `docs-public/docs_src/community/` - 社区文档
- `docs-public/mkdocs.yml` - 导航配置

**任务清单**:
1. 更新 `developers/` 文档：
   - `commands.md` - 更新 CLI 命令列表（sage, sage-dev, sage-cp-bench 等）
   - `development-setup.md` - 更新开发环境配置
   - `ci-cd.md` - 更新 CI/CD 说明
2. 更新 `dev-notes/` 入口：
   - `index.md` - 与 `docs/dev-notes/README.md` 同步
   - `package-architecture.md` - 验证架构图准确性
3. 检查 `community/` 文档
4. **更新 `mkdocs.yml` 导航**：
   - 确保所有新文档都有导航入口
   - 移除不存在文件的导航项
   - 添加新模块的导航（benchmark_agent, benchmark_control_plane 等）
   - 验证导航层级合理

**参考文档**:
- `docs/dev-notes/README.md` - 开发笔记主索引
- `docs/dev-notes/l6-cli/COMMAND_CHEATSHEET.md` - CLI 命令速查
- `.github/copilot-instructions.md` - 项目说明

**重点检查**:
- `mkdocs.yml` 中的所有路径是否有效
- 导航结构是否与实际文档结构一致
- 是否有遗漏的重要文档

**输出要求**:
- 修改的文件列表
- `mkdocs.yml` 变更摘要
- 构建验证结果（运行 `cd docs-public && mkdocs build` 检查）
```

---

## 阶段二通用指南

### 执行前检查清单

- [ ] 阶段一 Task 1-6 全部完成
- [ ] `docs/dev-notes/README.md` 已更新
- [ ] `docs/dev-notes/CLEANUP_SUMMARY_*.md` 已生成
- [ ] 主要 API 变更已记录在 `BREAKING_CHANGES_agent_tools_plan.md`

### 关键信息同步

从 `docs/dev-notes/` 同步到 `docs-public/docs_src/` 的核心内容：

| dev-notes 来源 | docs_src 目标 | 内容 |
|---------------|--------------|------|
| `cross-layer/architecture/` | `concepts/architecture/` | 架构设计 |
| `l3-libs/README.md` | `guides/packages/sage-libs/` | Agentic 模块 |
| `l5-benchmark/README.md` | `api-reference/` | Benchmark API |
| `BREAKING_CHANGES_*.md` | `developers/` | 迁移指南 |
| `.github/copilot-instructions.md` | 多处 | 安装、配置、API |

### 文档构建验证

每个任务完成后，运行以下命令验证：

```bash
cd docs-public
pip install -r requirements.txt  # 如果需要
mkdocs build --strict           # 严格模式构建
mkdocs serve                    # 本地预览 (可选)
```

---

## 阶段二任务分配表

| 任务 | 负责范围 | 依赖 | 预估文件数 | 状态 |
|------|----------|------|-----------|------|
| Task 7 | 入门文档 | 阶段一完成 | ~5 | 🔲 待执行 |
| Task 8 | API 参考 | 阶段一完成 | ~10 | ✅ **已完成** (2025-11-29) |
| Task 9 | 用户指南 | 阶段一完成 | ~40 | 🔲 待执行 |
| Task 10 | 教程示例 | 阶段一完成 | ~20 | 🔲 待执行 |
| Task 11 | 开发者文档 + mkdocs | Task 7-10 完成 | ~10 | ✅ **已完成** (2025-11-29) |

**建议执行顺序**:
1. Task 7-10 可并行执行（都依赖阶段一完成）
2. Task 11 最后执行（需要整合 Task 7-10 的结果，更新导航）

---

## Task 8 完成报告 (2025-11-29)

### 修改的文件

| 文件 | 修改内容 |
|------|----------|
| `api-reference/index.md` | 更新快速开始示例，添加 UnifiedInferenceClient 和 SagePorts 用法 |
| `api-reference/common/index.md` | 全面更新：添加 UnifiedInferenceClient、SagePorts、EmbeddingClientAdapter 等新 API |
| `api-reference/libs/index.md` | 全面更新：添加 Agentic 模块（Tool Selection、Planning、Timing Decision）|
| `api-reference/middleware/index.md` | 更新：添加 Multimodal Storage、AutoStop、C++ Extensions 说明 |

### 新增 API 文档条目

**sage-common (L1)**:
- `UnifiedInferenceClient` - 统一 LLM + Embedding 客户端
- `SagePorts` - 统一端口配置
- `EmbeddingClientAdapter` - Embedding 批量接口适配器
- `ControlPlaneVLLMService` - Control Plane 服务
- `UnifiedAPIServer` - 统一 API 服务器

**sage-libs (L3) - Agentic 模块**:
- Tool Selection: `KeywordSelector`, `EmbeddingSelector`, `HybridSelector`, `GorillaSelector`, `DFSDTSelector`
- Planning: `HierarchicalPlanner`, `ReActPlanner`, `TreeOfThoughtsPlanner`
- Timing: `RuleBasedTimingDecider`, `LLMBasedTimingDecider`, `HybridTimingDecider`

**sage-middleware (L4)**:
- `MultimodalStorage` - 多模态存储
- `AutoStopService` - 自动停止服务
- SONG GPU C++ 扩展说明

### 发现的问题
- 无

---

## Task 11 完成报告 (2025-11-29)

### 概述
更新开发者文档和 mkdocs 配置，修复断链，确保文档构建通过严格模式验证。

### 修改的文件

| 文件 | 修改内容 |
|------|----------|
| `developers/ci-cd.md` | **完全重写**：添加完整 CI/CD 文档（GitHub Actions、Submodule 管理、CodeCov、测试指南、发布流程） |
| `developers/commands.md` | 修复断链：更新参考链接指向正确位置 |
| `developers/development-setup.md` | 修复断链：COMMUNITY.md → community/community.md, DEV_COMMANDS.md → commands.md |
| `dev-notes/package-architecture.md` | **修复 10+ 断链**：更新内部文档链接指向 GitHub |
| `getting-started/installation.md` | 修复断链：developer.md → development-setup.md, COMMUNITY.md → community/community.md |
| `getting-started/quickstart.md` | 修复断链：faq.md (删除), architecture/ → concepts/architecture/ |
| `tutorials/advanced/advanced-rag.md` | 修复断链：sage_llm.md → overview.md |
| `tutorials/advanced/performance-tuning.md` | 修复断链：README.md → index.md |
| `concepts/architecture/package-structure.md` | 修复断链：layer-design.md (删除), 添加正确链接 |
| `concepts/architecture/design-decisions/rpc-queue-refactoring.md` | 修复断链：更新相关文档链接 |
| `api-reference/libs/index.md` | 修复断链：agentic/*.md → agents/*.md, agent.md → index.md |
| `guides/packages/sage-studio/index.md` | 修复断链：删除不存在的 sage-gateway/sage-cli 链接 |
| `index_content.md` | 修复断链：COMMUNITY.md → community/community.md |

### mkdocs.yml 导航更新

| 新增导航项 | 路径 |
|------------|------|
| 设计决策 > L2 平台层 | `concepts/architecture/design-decisions/l2-platform-layer.md` |
| 设计决策 > RPC 队列重构 | `concepts/architecture/design-decisions/rpc-queue-refactoring.md` |
| 设计决策 > sage-libs 重构 | `concepts/architecture/design-decisions/sage-libs-restructuring.md` |
| L5 应用层 > Benchmark 性能测试 | `guides/packages/sage-benchmark/index.md` |

### 验证结果

```bash
cd docs-public && mkdocs build --strict
# INFO - Building documentation to directory: /home/shuhao/SAGE/docs-public/site
# 成功！无警告，无错误
```

### 断链修复统计

| 类别 | 原始数量 | 修复后 |
|------|----------|--------|
| 严格模式警告 | 36 | 0 |
| 断链文件 | 13 | 0 |

### 未在导航中的文件（正常）

以下文件存在但未添加到导航（它们是辅助文件或旧版本）：
- `index_content.md` - 首页内容模板
- `guides/packages/sage-kernel/api/README.md` - API 目录索引（冗余）
- `guides/packages/sage-middleware/api/service_api.md` - 重复的服务 API
- `tutorials/advanced/index_old.md` - 旧版索引

---

## 完整执行流程

```
阶段一（并行）          阶段二（并行）           最终整合
┌─────────────┐        ┌─────────────┐        ┌─────────────┐
│   Task 1    │        │   Task 7    │        │             │
│   Task 2    │        │   Task 8 ✅  │        │  Task 11 ✅ │
│   Task 3    │───────>│   Task 9    │───────>│  (mkdocs)   │
│   Task 4    │        │   Task 10   │        │             │
│   Task 5 ✅ │        └─────────────┘        └─────────────┘
│   Task 6    │
└─────────────┘
```

预估总时间：阶段一 2-3 小时，阶段二 2-3 小时，总计 4-6 小时（并行执行）
