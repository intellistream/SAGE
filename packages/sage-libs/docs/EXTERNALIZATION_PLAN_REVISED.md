# sage-libs 外迁执行计划（修订版 - 选项 A）

**日期**: 2026-01-10\
**状态**: 🚧 执行中\
**策略**: 完整外迁（先处理明确的模块）

## 🎯 核心发现

### SIAS 现状调查结果

经过代码检查发现：

1. **sage-libs/sias/** 只有一个空的 `__init__.py`
1. **接口定义缺失** - `sias/interface/` 目录不存在
1. **实现已外迁** - CoresetSelector, OnlineContinualLearner 在外部包（但未安装）
1. **实际用途** - 用于 **Agent 训练/微调**，不是运行时工具选择
   - 使用位置：`sage-tools/agent_training/sft_trainer.py`
   - 功能：样本重要性选择（CoresetSelector）+ 增量学习（OnlineContinualLearner）

**决策**：**暂时保留 SIAS 讨论**，先完成明确的 agentic 和 rag 外迁。

## 📋 修订后的执行清单

### 阶段 1: 外迁 agentic → isage-agentic ⚡ **优先**

- [ ] **1.1** 检查 sage-libs/agentic 当前状态

  ```bash
  tree packages/sage-libs/src/sage/libs/agentic -L 2
  ```

- [ ] **1.2** 检查 sage-agentic 仓库状态

  - 仓库：`/home/shuhao/sage-agentic`
  - 确认 git 状态、pyproject.toml

- [ ] **1.3** 迁移接口层到 sage-agentic

  - 源：`packages/sage-libs/src/sage/libs/agentic/interface/`
  - 目标：`sage-agentic/src/sage/libs/agentic/interface/`

- [ ] **1.4** 检查是否有其他实现代码

  - 如果 sage-libs/agentic 有除 interface/ 外的内容，一并迁移

- [ ] **1.5** 更新 sage-agentic/pyproject.toml

  - 包名：`isage-agentic`
  - 版本：`0.1.0`
  - 依赖：根据实际需要添加

- [ ] **1.6** 在 sage-libs 添加 extras 依赖

  ```toml
  [project.optional-dependencies]
  agentic = ["isage-agentic>=0.1.0"]
  ```

- [ ] **1.7** 删除 sage-libs/agentic（或保留空的重导出层）

### 阶段 2: 外迁 rag → isage-rag

- [ ] **2.1** 检查 sage-libs/rag 当前状态

  ```bash
  ls -la packages/sage-libs/src/sage/libs/rag/
  ```

  - 已知文件：`chunk.py`, `document_loaders.py`, `types.py`, `interface/`

- [ ] **2.2** 迁移代码到 sage-rag

  - 源：`packages/sage-libs/src/sage/libs/rag/`
  - 目标：`sage-rag/src/sage/libs/rag/`

- [ ] **2.3** 更新 sage-rag/pyproject.toml

  - 包名：`isage-rag`
  - 版本：`0.1.0`
  - Extras：`[retrieval]`, `[generation]`, `[evaluation]`

- [ ] **2.4** 在 sage-libs 添加 extras 依赖

  ```toml
  [project.optional-dependencies]
  rag = ["isage-rag>=0.1.0"]
  ```

- [ ] **2.5** 删除 sage-libs/rag（或保留重导出层）

### 阶段 3: 清理 sage-libs

- [ ] **3.1** 更新 sage-libs/pyproject.toml

  - 添加完整的 extras 列表
  - 添加 `all` extras

- [ ] **3.2** 更新 sage-libs/README.md

  - 列出外迁包
  - 说明安装方式

- [ ] **3.3** 更新文档

  - 标记 REORGANIZATION_PROPOSAL.md 为已完成
  - 删除过时文档

- [ ] **3.4** 运行测试

  ```bash
  sage-dev project test --coverage
  ```

### 阶段 4: 发布与验证

- [ ] **4.1** 发布到 TestPyPI

  ```bash
  cd ~/sage-pypi-publisher
  ./publish.sh isage-agentic --test-pypi --version 0.1.0
  ./publish.sh isage-rag --test-pypi --version 0.1.0
  ```

- [ ] **4.2** 安装测试

  ```bash
  pip install -i https://test.pypi.org/simple/ isage-agentic
  pip install -i https://test.pypi.org/simple/ isage-rag
  ```

- [ ] **4.3** 正式发布

  ```bash
  ./publish.sh isage-agentic --version 0.1.0
  ./publish.sh isage-rag --version 0.1.0
  ```

## 🚧 SIAS 处理方案（待定）

### 选项 A: 保持现状

- SIAS 已经外迁（接口 + 实现都在外部包）
- sage-libs/sias 只是个空壳
- 暂时保留，等待 isage-sias 包开发完成

### 选项 B: 完全删除

- 删除 sage-libs/sias 目录
- 在 sage-tools 中直接依赖 isage-sias
- 更新所有导入语句

### 选项 C: 整合到 agentic

- 如果 SIAS 确实属于 agent 训练组件
- 应该整合到 isage-agentic（作为可选依赖）
- `from sage.libs.agentic.training import CoresetSelector`

**推荐**：选项 A（保持现状），等明确了 SIAS 的完整架构再处理

## 📊 最终架构（不含 SIAS）

### sage-libs（核心工具包）

**保留模块**：

- `dataops/` - 数据操作
- `safety/` - 安全检查
- `privacy/` - 隐私保护
- `integrations/` - 第三方集成
- `foundation/` - 基础工具
- `anns/` - ANN 接口层（实现在 isage-anns）
- `intent/` - 意图识别
- `sias/` - SIAS 接口层（暂时保留，实现在 isage-sias）

**已外迁**：

- ~~`agentic/`~~ → `isage-agentic`
- ~~`rag/`~~ → `isage-rag`
- `anns/` 实现 → `isage-anns`
- `amms/` → `isage-amms`
- `finetune/` → `isage-finetune`

## 🎯 立即开始

让我们从最简单明确的开始：

1. **先做 agentic 外迁**（只有 interface/，最简单）
1. **再做 rag 外迁**（有完整实现，清晰明确）
1. **最后处理 SIAS**（需要更多信息和讨论）

准备好了吗？我们开始执行！
