# sage-libs 重组（建议方案）

目的：在保证可维护性和用户体验的前提下，整理 `sage-libs` 的模块边界，确定哪些子模块保留在 `sage-libs` 中、哪些外迁为独立 PyPI 仓库，以及如何通过可选依赖实现按需安装。

本文为建议草案，包含模块映射、可选依赖配置、迁移顺序与时间表、兼容策略（可选）。

______________________________________________________________________

## 一、总体原则

- 优先保持语义上紧密耦合的模块在同一个包内。可选功能通过 `extras`（pyproject `[project.optional-dependencies]`）暴露。
- 对于可以独立复用的算法/实现，优先外部化为单独包（有助于独立发布和更快迭代）。
- 保持 SAGE 中的接口/协议稳定（如果需要可使用轻量兼容层或接口包）。
- 外迁前准备：完整 README、pyproject、LICENSE、基础 CI、导出公共 API 列表。

______________________________________________________________________

## 二、当前主要子模块（来自 `packages/sage-libs/src/sage/libs/`）

- `agentic/` (agent 框架、规划、工具选择、runtime、bots)
- `anns/` (已外迁为 isage-anns)
- `amms/` (已外迁为 isage-amms)
- `finetune/` (已外迁为 isage-finetune)
- `sias/` (Sample-Importance-Aware Selection)
- `workflow/` (工作流生成和优化)
- `intent/` (意图识别)
- `dataops/` (数据操作工具)
- `rag/`, `integrations/`, `safety/`, `privacy/`, `eval/`, `reasoning/` 等

______________________________________________________________________

## 三、建议的包划分（最终目标）

说明：优先保守拆分，推荐按“核心 + 可选子包”策略（混合方案）。

1. isage-agentic (已创建: `sage-agentic`)

   - 包含：`agentic/` 中的核心模块
     - `interface/`, `interfaces/`, `registry/`（协议与注册）
     - `agents/`（runtime, planning, action/tool-selection, bots）
     - `workflow/`（工作流 orchestrator + generators + optimizers）
     - `eval/`（agent evaluation & telemetry）
     - `reasoning/`（用于 planning 的推理工具）
   - extras:
     - `[planning]` (如果需要可拆为 extras，包含 heavier dependencies)
     - `[tool-selection]` (embedding/ann clients)
     - `[llm]` (openai/anthropic client helpers)

1. isage-sias (可选独立包)

   - 包含：`sias/`（continual learner, coreset selection, types）
   - 理由：通用采样/重要性选择算法，可被非 agentic 场景复用

1. isage-intent (可选独立包)

   - 包含：`intent/`（keyword recognizer, llm recognizer, classifier）
   - 理由：对话系统与检索系统也会使用意图识别，独立包提高可复用性

1. isage-workflow (可选)

   - 包含：`workflow/`、`workflows/`（如果需要独立部署工作流引擎）
   - 理由：工作流引擎可作为独立编排层被其他项目使用

1. sage-libs 保留

   - 作为 meta/算法集合包（轻量），保留不易独立或强耦合的工具
   - `dataops/`, `safety/`, `privacy/`, `rag/` 等可按需决定是否独立

______________________________________________________________________

## 四、推荐 `pyproject.toml` extras（示例）

在 `packages/sage-libs/pyproject.toml` 或 `packages/<package>/pyproject.toml` 中添加：

```toml
[project.optional-dependencies]
agentic = ["isage-agentic>=0.1.0"]
sias = ["isage-sias>=0.1.0"]
intent = ["isage-intent>=0.1.0"]n
workflow = ["isage-workflow>=0.1.0"]
all = [
    "isage-agentic>=0.1.0",
    "isage-sias>=0.1.0",
    "isage-intent>=0.1.0",
    "isage-workflow>=0.1.0",
]
```

说明：`all` 用于开发与 CI 跑全套测试；用户安装时可按需选择。

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

阶段 3: SAGE 仓库调整

- 删除原目录（或保留空的兼容层，视是否需要后向兼容）
- 在 `sage-libs` 中添加 `pyproject.toml` extras（指向新包名）
- 更新 `packages/sage-libs/README.md` 文档和 `docs-public/` 的引用

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

## 八、下一步建议（请选一项）

- A. 按照本草案，把 `isage-agentic` 保持为完整包，另外将 `sias` 和 `intent` 作为可选独立仓库（推荐）
- B. 全部保留在 `isage-agentic`（简单），以后再拆分
- C. 按模块细分（复杂，需更多维护）

请回复你选择 A/B/C，或对上面的包边界和 extras 进行具体调整。我收到确认后会执行对应的迁移步骤（创建仓库、复制代码、更新 SAGE）。
