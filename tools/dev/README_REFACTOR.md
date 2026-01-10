# SAGE-Libs 重构方案总览

## 📋 文件清单

本目录包含 SAGE-Libs 重构的完整方案和执行指南。

### 核心文档

1. **sage_libs_refactor_meta_prompt.md** - Meta 提示词

   - 重构目标和原则
   - 目标架构（5 大领域 + 3 个保留模块）
   - 独立库清单
   - 工作流程概览

1. **agent_0_repo_orchestrator.md** - Agent-0: 仓库准备

   - 检查现有仓库
   - 创建 4 个新仓库（privacy, finetune, eval, safety）
   - 配置 CI/CD 模板

1. **agent_1_agentic.md** - Agent-1: Agentic 重构

   - 合并 Intent, Reasoning, SIAS
   - 创建统一接口层
   - 迁移到 isage-agentic

1. **agent_2_rag.md** - Agent-2: RAG 重构

   - Loader, Chunker, Retriever, Reranker, QueryRewriter 接口
   - 迁移到 isage-rag

1. **agents_3_8_summary.md** - Agent 3-8 汇总

   - Agent-3: Fine-tuning
   - Agent-4: Evaluation（新建）
   - Agent-5: Privacy
   - Agent-6: Safety（可选）
   - Agent-7: Documentation
   - Agent-8: Validation & Publishing

### 执行脚本

6. **run_refactor.sh** - 重构执行协调脚本

   - 4 个 Phase 的执行指南
   - 并行任务协调
   - 进度追踪

1. **create_sage_repos.sh** - 仓库创建脚本（由 Agent-0 生成）

   - 自动创建 4 个新仓库
   - 配置分支策略
   - 初始化基础文件

1. **generate_interface_layer.sh** - 接口层生成工具（已存在）

   - 快速生成标准接口模板

## 🎯 快速开始

### 1. 阅读 Meta 提示词

```bash
cat tools/dev/sage_libs_refactor_meta_prompt.md
```

了解：

- 为什么重构？
- 重构成什么样？
- 如何分工协作？

### 2. 执行 Agent-0（仓库准备）

```bash
# 阅读任务
cat tools/dev/agent_0_repo_orchestrator.md

# 创建仓库（会生成 create_sage_repos.sh 脚本）
# 手动或使用脚本创建 4 个新仓库
```

### 3. 并行执行 Agent 1-6（代码迁移）

打开多个终端窗口，每个窗口负责一个 Agent：

**终端 1 - Agent-1 (Agentic)** - 最复杂，优先级最高

```bash
cat tools/dev/agent_1_agentic.md
# 按步骤执行：创建接口 → 合并 Intent/Reasoning/SIAS → 迁移实现
```

**终端 2 - Agent-2 (RAG)**

```bash
cat tools/dev/agent_2_rag.md
# 按步骤执行：完善接口 → 迁移实现 → 注册
```

**终端 3 - Agent-3 (Fine-tuning)**

```bash
cat tools/dev/agents_3_8_summary.md  # 查看 Agent-3 部分
# 创建接口 → 实现基础训练器
```

**终端 4 - Agent-4 (Evaluation)**

```bash
cat tools/dev/agents_3_8_summary.md  # 查看 Agent-4 部分
# 新建接口 → 实现评估指标
```

**终端 5 - Agent-5 (Privacy)**

```bash
cat tools/dev/agents_3_8_summary.md  # 查看 Agent-5 部分
# 创建接口 → 迁移 unlearning 实现
```

**终端 6（可选）- Agent-6 (Safety)**

```bash
cat tools/dev/agents_3_8_summary.md  # 查看 Agent-6 部分
# 保留基础 + 可选高级接口
```

### 4. 执行 Agent-7（文档）

```bash
cat tools/dev/agents_3_8_summary.md  # 查看 Agent-7 部分
# 更新 README → 精简文档 → 生成架构图
```

### 5. 执行 Agent-8（验证发布）

```bash
cat tools/dev/agents_3_8_summary.md  # 查看 Agent-8 部分
# 集成测试 → 版本对齐 → PyPI 发布
```

### 6. 或使用协调脚本

```bash
bash tools/dev/run_refactor.sh
# 交互式执行所有 Phase
```

## 🏗️ 架构设计亮点

### 1. **5 大核心接口领域**

- **Agentic**（智能体与编排）：Agent + Planner + ToolSelector + Intent + Reasoning + SIAS
- **RAG**（检索与知识）：Loader + Chunker + Retriever + Reranker + QueryRewriter
- **ANNS/AMMS**（向量与近似）：ANN 索引 + AMM 算法
- **Finetune/Eval**（模型优化）：Trainer + Strategy + Metrics + Profiler
- **Privacy/Safety**（安全与隐私）：Unlearning + DP + Guardrails + Jailbreak 检测

### 2. **3 个保留模块**

- **Foundation**: 纯 Python 工具（无重型依赖）
- **DataOps**: 轻量级数据操作
- **Integrations**: 瘦适配器层

### 3. **合并策略**

- ❌ 不创建 sage-intent（合并到 sage-agentic）
- ❌ 不创建 sage-reasoning（合并到 sage-agentic）
- ❌ 不创建 sage-sias（作为 isage-agentic[sias] 可选安装）

### 4. **依赖关系**

```
复合型 AI 应用
      ↓
isage-agentic, isage-rag, isage-finetune, ...
      ↓
sage-libs (接口层 + 轻量实现)
      ↓
sage-kernel, sage-common
```

## 📊 预期成果

### 代码结构

- sage-libs 代码量减少 **60%+**
- 接口层清晰（每个领域 < 500 行）
- 实现迁移到独立库（按需安装）

### 安装方式

```bash
# 最小安装（仅接口层）
pip install isage-libs

# 按需安装
pip install isage-libs[agentic]     # 智能体
pip install isage-libs[rag]         # RAG
pip install isage-libs[agentic,rag] # 组合

# 完整安装
pip install isage-libs[all]
```

### 独立库

- 可独立使用（不依赖 SAGE 主框架）
- 独立版本管理
- 独立 PyPI 发布

## 📝 注意事项

1. **SIAS 不独立成库**

   - SIAS 是 Agentic 的高级特性
   - 作为 `isage-agentic[sias]` 可选安装

1. **Intent/Reasoning 合并**

   - Intent 是 Agent 的输入理解
   - Reasoning 是 Agent 的规划核心
   - 统一到 isage-agentic

1. **Safety 基础功能保留**

   - 轻量级过滤保留在 sage-libs
   - 高级检测可选独立为 isage-safety

1. **并行执行优化**

   - Agent 1-6 可完全并行
   - 预计 3 小时并行完成（vs 15 小时串行）

## 🚀 执行时间表

| Phase   | 任务                | 预计时间 | 并行     |
| ------- | ------------------- | -------- | -------- |
| Phase 1 | Agent-0: 仓库准备   | 30min    | 串行     |
| Phase 2 | Agent 1-6: 代码迁移 | 3h       | 并行     |
| Phase 3 | Agent-7: 文档       | 2h       | 部分重叠 |
| Phase 4 | Agent-8: 验证发布   | 2h       | 串行     |

**总计**: 约 7-8 小时（并行优化）

## 🎯 成功标准

- [ ] 4 个新仓库已创建
- [ ] 5 大接口领域清晰定义
- [ ] sage-libs 代码量减少 60%+
- [ ] 所有独立库可独立安装
- [ ] 集成测试覆盖率 > 80%
- [ ] 文档完善（架构图 + API + 示例）
- [ ] 所有库发布到 PyPI

## 📚 参考资源

- SAGE 主仓库: `/home/shuhao/SAGE`
- 独立仓库目录: `/home/shuhao/sage-*`
- PyPI 发布工具: `/home/shuhao/sage-pypi-publisher`
- 文档: `docs-public/docs_src/dev-notes/l3-libs/`

______________________________________________________________________

**准备好开始了吗？运行：**

```bash
bash tools/dev/run_refactor.sh
```
