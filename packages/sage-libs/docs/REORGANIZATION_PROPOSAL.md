# sage-libs 重组（建议方案）

**最后更新**: 2026-01-10 20:05\
**状态**: ✅ **选项 A 已执行** - agentic 和 rag 已提取为独立仓库

______________________________________________________________________

## 📋 执行总结 (2026-01-10)

**✅ 已完成的外迁**:

- `agentic/` → **sage-agentic** (PyPI: `isage-agentic`) - 仓库已创建 `~/sage-agentic`
- `rag/` → **sage-rag** (PyPI: `isage-rag`) - 仓库已创建 `~/sage-rag`
- `sias/` → 已合并到 sage-agentic (需要重构为 ToolSelector)

**📦 新仓库状态**:

- **sage-agentic**: 3 commits, 4 Python files (596 lines), 完整文档
- **sage-rag**: 3 commits, 7 Python files (1498 lines), 完整文档
- 两个仓库均包含: pyproject.toml, README.md, MIGRATION_GUIDE.md, LICENSE, .gitignore

**⏭️ 下一步**:

1. 在 GitHub 创建仓库 `intellistream/sage-agentic` 和 `intellistream/sage-rag`
1. 推送代码到 GitHub
1. 更新 sage-libs 的 `pyproject.toml` 添加可选依赖
1. 实现缺失的组件（Agent, Planner, ToolSelector, DocumentLoader, etc.）

______________________________________________________________________

## 零、本文档目的

本文档描述 `packages/sage-libs` 的模块重组方案，确定哪些子模块保留在 `sage-libs` 中、哪些外迁为独立 PyPI 包，以及如何通过可选依赖实现按需安装。

**🎯 核心原则：sage-libs 不会被清空！它将保留与 SAGE 框架紧密耦合的核心工具模块。**

**⚠️ 最新变更 (2026-01-10)**:

- ✅ 删除了重复的 `ann/` 目录（只保留 `anns/` 作为接口层）
- 📝 `anns/` 接口层保留在 sage-libs，算法实现已外迁至 `isage-anns`

______________________________________________________________________

## 一、快速总览（TL;DR）

### ✅ 已外迁为独立仓库 (2026-01-10)

| 模块             | 新仓库                | PyPI 包名                 | 状态                     |
| ---------------- | --------------------- | ------------------------- | ------------------------ |
| `agentic/`       | `sage-agentic`        | `isage-agentic`           | ✅ 已创建，待推送 GitHub |
| `rag/`           | `sage-rag`            | `isage-rag`               | ✅ 已创建，待推送 GitHub |
| `sias/`          | (合并到 sage-agentic) | (作为 SIAS tool selector) | ✅ 已迁移                |
| `anns/` 算法实现 | `sage-anns`           | `isage-anns`              | ✅ 已发布 PyPI           |
| `amms/`          | `sage-amms`           | `isage-amms`              | ✅ 已发布 PyPI           |
| `finetune/`      | `sage-finetune`       | `isage-finetune`          | ✅ 已发布 PyPI           |

### ✅ 保留在 sage-libs (核心工具，紧密耦合)

- `dataops/` - 数据操作工具
- `safety/` - 安全检查
- `privacy/` - 隐私保护
- `integrations/` - 第三方集成
- `foundation/` - 基础工具
- `anns/` - **接口层保留**（算法实现在 isage-anns）
- `intent/` - 意图识别

### 📦 未来可选外迁 (按需)

- `intent/` → `isage-intent` (意图识别可作为独立 NLU 组件)

### ❌ 已清理

- `ann/` - 已删除（重复目录，改用 `anns/`）

______________________________________________________________________

## 一、总体原则

- 优先保持语义上紧密耦合的模块在同一个包内。可选功能通过 `extras`（pyproject `[project.optional-dependencies]`）暴露。
- 对于可以独立复用的算法/实现，优先外部化为单独包（有助于独立发布和更快迭代）。
- 保持 SAGE 中的接口/协议稳定（如果需要可使用轻量兼容层或接口包）。
- 外迁前准备：完整 README、pyproject、LICENSE、基础 CI、导出公共 API 列表。

______________________________________________________________________

## 二、当前主要子模块（来自 `packages/sage-libs/src/sage/libs/`）

**当前实际存在的目录** (2026-01-10):

- `agentic/` - Agent 框架（待确认：可能为兼容层或待迁移）
- `amms/` - 近似矩阵乘（已外迁为 isage-amms）
- `anns/` - ANN 接口层（算法实现在 isage-anns）
- `dataops/` - 数据操作工具
- `finetune/` - 模型微调（已外迁为 isage-finetune）
- `foundation/` - 基础工具
- `integrations/` - 第三方集成
- `intent/` - 意图识别
- `privacy/` - 隐私保护
- `rag/` - RAG 相关工具
- `safety/` - 安全检查
- `sias/` - **代码结构错误** - 应该在 `agentic/agents/action/tool_selection/` 作为 tool selector 实现

**已删除**:

- ~~`ann/`~~ - 已于 2026-01-10 删除（重复目录，使用 `anns/` 代替）

______________________________________________________________________

## 三、建议的包划分（最终目标）

说明：优先保守拆分，推荐按“核心 + 可选子包”策略（混合方案）。

1. **isage-agentic** (建议外迁，已创建仓库: `sage-agentic`)

   - **包含**：`agentic/` 中的核心模块（不包含 SIAS，SIAS 应留在原处重构）
     - `interface/`, `interfaces/`, `registry/`（协议与注册）
     - `agents/`（runtime, planning, action/tool-selection, bots）
     - `workflow/`（工作流 orchestrator + generators + optimizers）
     - `eval/`（agent evaluation & telemetry）
     - `reasoning/`（用于 planning 的推理工具）
   - **extras**:
     - `[planning]` (heavier planning dependencies)
     - `[tool-selection]` (embedding/ann clients)
     - `[llm]` (openai/anthropic client helpers)

1. **isage-rag** (新建议，与 agentic 对称)

   - 包含：`rag/` 中的核心模块
     - `document_loaders/`（文档加载：TextLoader, PDFLoader, DocxLoader, MarkdownLoader）
     - `chunk/`（文本分块：CharacterSplitter, SentenceTransformersTokenTextSplitter）
     - `types/`（类型定义：RAGDocument, RAGQuery, RAGResponse）
     - `pipeline/`（RAG 管道编排）
   - 理由：
     - 与 agentic 同等级别的应用层工具
     - 可被非 SAGE 项目使用（任何需要 RAG 的项目）
     - 不强依赖 SAGE kernel/platform 层
     - 当前在 `sage-middleware/operators/rag/` 中只是重导出
   - extras:
     - `[retrieval]` (vector database clients: Chroma, Milvus)
     - `[generation]` (LLM clients: OpenAI, HuggingFace)
     - `[evaluation]` (RAG metrics: F1, RougeL, BRS)

### 3. ~~isage-sias~~ (已取消 - 代码结构错误)

- **状态**: ❌ 不作为独立包，也不是独立框架
- **真实定位**: SIAS (Sample-Importance-Aware Selection) 实际上是 **tool selection 的一个具体算法实现**
- **核心组件**: `CoresetSelector` - 用于从候选中选择最重要的样本/工具（基于 loss, diversity, hybrid 策略）
- **当前问题**:
  - ❌ 错误地放在顶层目录 `sias/` 作为独立模块
  - ❌ 与其他 tool selectors (keyword, embedding, gorilla, dfsdt) 分离
  - ❌ 没有实现 `BaseToolSelector` 接口
- **正确位置**: 应该在 `agentic/agents/action/tool_selection/sias_selector.py`
- **重构方案**:
  1. 创建 `agentic/agents/action/tool_selection/sias_selector.py`
  1. 实现 `SiasToolSelector(BaseToolSelector)` 使用 `CoresetSelector` 算法
  1. 删除顶层 `sias/` 目录（或保留为兼容层指向 agentic）
  1. 在 registry 中注册：`register_selector("sias", SiasToolSelector)`
- **架构对齐**:
  ```
  agentic/agents/action/tool_selection/
  ├── keyword_selector.py   # 关键词匹配算法
  ├── embedding_selector.py # 向量相似度算法
  ├── gorilla_selector.py   # Gorilla 检索增强算法
  ├── dfsdt_selector.py     # DFSDT 搜索树算法
  └── sias_selector.py      # SIAS 重要性采样算法 ← 应该在这里
  ```

### 4. isage-intent (可选独立包)

- 包含：`intent/`（keyword recognizer, llm recognizer, classifier）
- 理由：对话系统与检索系统也会使用意图识别，独立包提高可复用性

### 5. ~~isage-workflow~~ (已取消)

- **状态**: ❌ 已取消，workflow 实际不存在独立目录
- ~~包含：`workflow/`、`workflows/`（如果需要独立部署工作流引擎）~~
- ~~理由：工作流引擎可作为独立编排层被其他项目使用~~

### 6. sage-libs 保留 (核心工具集合包)

- **保留在 sage-libs 中** (与 SAGE 框架紧密耦合，不易独立):

  - `dataops/` - 数据操作工具 (DataFrame/Dataset 处理)
  - `rag/` - RAG 相关工具 (文档加载、分块、索引)
  - `safety/` - 安全检查 (输入验证、内容过滤)
  - `privacy/` - 隐私保护 (数据脱敏、匿名化)
  - `integrations/` - 第三方集成 (LangChain, OpenAI, etc.)
  - `foundation/` - 基础工具 (配置、日志、工具类)
  - `anns/` - ANN 接口抽象层 (统一接口，算法实现在 isage-anns)

- **已外迁为独立包**:

  - ~~`agentic/`~~ → `isage-agentic` (待确认 - 目录仍存在)
  - `anns/` 算法实现 → `isage-anns` (接口层保留在 sage-libs)
  - `amms/` → `isage-amms` (目录仍存在，可能为兼容层)
  - `finetune/` → `isage-finetune` (目录仍存在，可能为兼容层)

- **未来可选外迁** (如有需求):

  - `intent/` → `isage-intent` (意图识别)

- **需要重构** (代码结构错误):

  - `sias/` - 应该是 tool selection 的一个算法实现，应该在 `agentic/agents/action/tool_selection/sias_selector.py`

- **已清理**:

  - ~~`ann/`~~ - 已删除 (2026-01-10，重复目录，统一使用 `anns/`)
  - ~~`workflow/`~~ - 不存在独立目录（功能可能在 agentic 中）

______________________________________________________________________

## 四、推荐 `pyproject.toml` extras（示例）

在 `packages/sage-libs/pyproject.toml` 或 `packages/<package>/pyproject.toml` 中添加：

```toml
[project.optional-dependencies]
# 已外迁的包（作为可选依赖）
agentic = ["isage-agentic>=0.1.0"]  # Agent 框架 (包含 SIAS tool selector)
anns = ["isage-anns>=0.1.0"]  # ANN 算法实现
amms = ["isage-amms>=0.1.0"]  # 近似矩阵乘
finetune = ["isage-finetune>=0.1.0"]  # 模型微调
rag = ["isage-rag>=0.1.0"]  # RAG 组件 (可选外迁)

# 未来可能外迁的包
intent = ["isage-intent>=0.1.0"]  # 意图识别

# 全量安装（开发/CI 用）
all = [
    "isage-agentic>=0.1.0",
    "isage-anns>=0.1.0",
    "isage-amms>=0.1.0",
    "isage-finetune>=0.1.0",
]
```

**说明**：

- **SAGE 完整安装**：`pip install sage-libs[all]` 会自动安装所有外迁的包
- **按需安装**：`pip install sage-libs[anns]` 只安装 ANN 算法实现
- **开发者安装**：`pip install -e packages/sage-libs[all]` 用于开发和 CI
- **接口层**：`anns/` 接口保留在 sage-libs，算法实现在 isage-anns
- **透明使用**：代码中 `from sage.libs.anns import create` 仍然有效

**用户体验不变**：无论包是内置还是外迁，用户的使用方式完全一致！

______________________________________________________________________

## 五、迁移步骤（建议顺序）

阶段 0: 讨论 & 确认（当前）

- 目标：确认分包边界、package 名称、extras 列表

阶段 1: 准备独立包模板（并行可做）

- 为每个要独立的模块创建仓库模板：`pyproject.toml`, `README.md`, `LICENSE`, `setup.py`,
  `.github/workflows/python.yml`
- 提取并整理公共 API（export list）、示例代码与 docs

阶段 2: 代码迁移（逐包）

- 复制模块代码到临时目录，整理 imports（相对改成包内导入）、更新包名/模块名
- 添加 CI (pytest matrix), ruff, mypy (可选)
- Commit + push -> GitHub repo creation (使用 `gh repo create ... --source`)

阶段 3: SAGE 仓库调整 **（关键：SAGE 仍使用外迁的包！）**

- 删除原目录（或保留空的兼容层，视是否需要后向兼容）
- **在 `sage-libs` 的 `pyproject.toml` 中添加 extras**（指向新包名）
  ```toml
  [project.optional-dependencies]
  anns = ["isage-anns>=0.1.0"]  # SAGE 通过这里依赖外迁的包
  ```
- **SAGE 的 CI/CD 也要安装 extras**：`pip install -e packages/sage-libs[all]`
- 更新 `packages/sage-libs/README.md` 文档和 `docs-public/` 的引用
- **验证 SAGE 功能完整**：确保所有测试通过，功能无损失

阶段 4: 发布与验证

- 在 testpypi 上发布 `isage-*` 包，运行集成测试
- 在 SAGE CI 中切换到安装 `isage-*` 包并运行完整测试矩阵
- 发布到 PyPI（可选）

阶段 5: 监控与清理

- 监控依赖问题、用户反馈
- 删除兼容代码或标注弃用

______________________________________________________________________

## 六、时间线（示例，按包估算）

- 准备模板 + docs: 1-2 天
- 迁移并创建仓库（单包）：0.5-1 天
- CI + 测试整合（单包）：0.5-1 天
- SAGE side updates + tests: 0.5-1 天

若并行处理多个包（2-3 人），整个外迁（agentic + sias + intent）可在 3-7 天内完成。

______________________________________________________________________

## 七、兼容性策略（可选）

- 如果不需要向后兼容：直接删除旧目录并将所有引用改为新的包名（推荐简单清晰）
- 如果需要逐步迁移：保留轻量的兼容层 `sage.libs.<mod>`，在导入时抛出 DeprecationWarning，指向 `isage-*` 包

______________________________________________________________________

## 八、当前状态与下一步建议

### 当前状态 (2026-01-10)

**✅ 已完成**:

- 删除了重复的 `ann/` 目录，统一使用 `anns/`
- `anns/` 接口层保留在 sage-libs，算法实现在 isage-anns
- 为 `agentic/`, `finetune/`, `rag/` 创建了接口层 (`interface/`)

**⚠️ 待确认**:

- `agentic/` 目录仍存在 - 需确认是兼容层还是待迁移代码
- `amms/` 目录仍存在 - 需确认与 isage-amms 的关系
- `finetune/` 目录仍存在 - 需确认与 isage-finetune 的关系

**🚧 需要迁移**:

- `sias/` - SIAS (Self-Improving Agentic Systems) 是完整的 Agent 自我改进框架，包含 4
  大组件。当前只实现了流式训练器（CoresetSelector/OnlineContinualLearner），应整体迁移至 `isage-agentic` 并补齐其他组件。

**📋 待决策**:

- RAG 工具（rag/）是否外迁为 isage-rag？（与 agentic 保持一致性）
- Intent（intent/）是否外迁为 isage-intent？

### 下一步建议（请选一项）

**选项 A: 完整外迁（保持一致性）** ⭐ 推荐

- 外迁 `agentic/` → `isage-agentic`
- 外迁 `rag/` → `isage-rag`（与 agentic 对称）
- 可选外迁 `intent/` → `isage-intent`
- 重构 `sias/` → `agentic/agents/action/tool_selection/sias_selector.py` (然后随 agentic 一起外迁)
- sage-libs 只保留核心工具：dataops, safety, privacy, integrations, foundation, anns 接口

**选项 B: 保守策略（渐进式）**

- 保留 `agentic/`, `rag/`, `intent/` 在 sage-libs
- 重构 `sias/` 为 `agentic/agents/action/tool_selection/sias_selector.py`
- 只外迁算法实现包（anns, amms, finetune）
- 以后根据需要再拆分

**选项 C: 混合策略**

- 外迁 `agentic/` → `isage-agentic`（重构 sias 为 tool selector 后一起迁移）
- 保留 `rag/`, `intent/` 在 sage-libs（与框架耦合度高）
- 通过 extras 提供可选依赖

**🚨 关键发现**：

- **SIAS 定位错误** - 它不是独立框架，而是 tool selection 的一个算法实现
- **CoresetSelector** 的作用是从候选中选择最重要的子集（与其他 tool selectors 完全对齐）
- **应该重构** - 实现 `SiasToolSelector(BaseToolSelector)` 并放在 `agentic/agents/action/tool_selection/`
- **重构后** - sias 就是 agentic 的一部分，外迁时自然一起迁移

请回复你选择 A/B/C，或对上面的包边界和 extras 进行具体调整。收到确认后可执行对应的迁移步骤。

### 相关文档

- `REORGANIZATION_ANALYSIS.md` - 详细分析（如存在）
- `ANN_CLEANUP_2026-01-10.md` - ann/anns 清理记录
- `QUICK_REFERENCE.md` - 快速参考指南
