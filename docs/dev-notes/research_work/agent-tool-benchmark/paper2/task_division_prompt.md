```markdown
# Paper 2 (SIAS) — 剩余工作分工提示词 / Task Division Prompt

目的：为 SIAS（Paper 2）剩余实现与实验工作生成清晰、可指派的任务说明（issues/PR 描述或团队 chat prompt）。文件同时给出“提示词模板”，便于快速分配任务给具体开发者或研究员。

使用方式（示例流程）：
- 维护者把某个任务复制到 GitHub issue，并把“提示词模板”粘贴到 issue description 中。
- 指派人（Assignee）按模板在 PR 中填写进度与测试证明。

注意：本文件为工作分工的“提示词”（prompt-for-assignment），并非实现文档。实现细节应在对应模块（`packages/sage-libs/src/sage/libs/sias/`）和实验目录中补充。

---

## 概览（High-level work areas）

将剩余工作划分为 9 个子域：

1. StreamingImportanceScorer (SSIS)
2. ReflectiveMemoryStore
3. AdaptiveExecutor (pre/post verification + localized replanning)
4. MultiAgentRouter / Specialist Agents
5. Streaming Trainer (streaming_trainer, batch/stream unified API)
6. Datasets & Benchmarks (Streaming Tool-Arena, Continual Tool Drop-In)
7. Experiments & Baselines (Paper 1 baselines + new ablations)
8. Tests & CI (unit/integration, quick GPU smoke tests)
9. Docs, LaTeX, Release & Submodule extraction

每一项下面给出：目标、可交付物、验收标准、估时（粗略）、提示词模板（用于指派）。

---

## 1) StreamingImportanceScorer (SSIS)

- 目标：实现 SSIS 得分函数 I(x) = α·L_grad + β·D_ctx + γ·T_exec（可配置权重），并提供在线增量计算接口。
- 可交付物：`packages/sage-libs/src/sage/libs/sias/ssjs.py`（或 `scorer.py`）、API 文档、单元测试、简单 benchmark（脚本测比较策略）。
- 验收标准：可在流式数据上每秒处理 N 个样本（N ≧ 200 的目标视硬件而定），在 benchmark 上优于随机/不确定性选择至少 1.5%（或按数据集设定）。
- 估时：2–4 周

任务指派提示词（中文示例）：

```
你负责实现 SIAS 的 StreamingImportanceScorer（SSIS）。目标：提供一个可插拔的打分器，实时给每个执行轨迹打分。请在 `packages/sage-libs/src/sage/libs/sias/scorer.py` 中实现类 `StreamingImportanceScorer`，包含：
- constructor(config: dict) 支持 alpha/beta/gamma 权重
- update(sample: Episode) -> score: float （增量更新统计）
- top_k(buffer, k) 返回当前 buffer 的 top-k important samples

交付物：实现文件 + pytest 单元测试（覆盖 80% 边界：空 buffer、高吞吐、权重变换）。在 `benchmarks/ss_is_compare.py` 提供一个小脚本比较 random/uncertainty/ssis 在示例数据上的选择效果。
验收：运行 `pytest` 全部通过；benchmark 比较脚本能运行并输出 CSV（含 selectivity/accuracy 列）。
```

---

## 2) ReflectiveMemoryStore

- 目标：实现持久化（可可选内存/磁盘）streaming memory，支持索引、摘要、pattern extraction 与查询接口。提供 snapshot/compact API。
- 可交付物：`memory/store.py`、summary extractor、向量索引 adapter（可选 FAISS/Annoy/flat）、一致性测试。
- 验收标准：能存储 N 条 episode（N≥100k 的目标可配置），支持按时间窗口/importance 检索 top-k，且检索延迟 < 100ms（内存模式）。
- 估时：3–5 周

任务指派提示词（英文模板）：

```
You are assigned to build the ReflectiveMemoryStore for SIAS. Deliver a Python class MemoryStore with APIs:
- append(episode)
- query(query_vector or text, top_k=10, filter=None)
- snapshot(path), load(path)
Provide an adapter interface for embeddings so the store can use either in-memory vector arrays or FAISS. Add unit tests and a small performance script that demonstrates insertion and retrieval latency on 10k episodes.
```

---

## 3) AdaptiveExecutor

- 目标：实现执行时的预检/后检（pre/post verification），以及局部 replanning 的策略接口（当工具返回不符合预期时）。
- 可交付物：`runtime/adaptive_executor.py`、integration tests with `orchestrator`、examples that show local replan flow.
- 验收标准：在故障注入场景（工具返回 error 或 hallucination）下，AdaptiveExecutor 能用 ≤3 次局部重试或变更 API 调用恢复成功（比直接重试/重启更高效）。
- 估时：2–3 周

提示词模板（中文）：

```
实现 AdaptiveExecutor：当工具输出与期待不符时，能触发 verifier → 如果 verifier 识别为“错误”，调用 replanner.generate_local_fix() 并仅重新执行受影响的子步骤。请补充集成测试，模拟工具返回错误的情况，验证成功率提升。
```

---

## 4) MultiAgentRouter / Specialist Agents

- 目标：实现 Router 用于任务分解和将子任务分配给专家 agent（Researcher/Coder/Analyst/Coordinator）。保持黑板式共享摘要，但只允许 Coordinator 提交最终结果。
- 可交付物：`agents/router.py`、示例 agents、end-to-end demo 和实验比较（单 agent vs multi-agent）。
- 验收标准：在 multi-hop task 上，multi-agent pipeline 的成功率要显著高于单 agent baseline（或在 case study 中展示定性提升）。
- 估时：3–6 周

---

## 5) Streaming Trainer

- 目标：实现统一 Trainer API 支持 streaming & batch；包括 replay + SSIS-based coreset sampling、EWC-style regularizer、可选 RL fine-tuning（PPO/DPO）hook。
- 可交付物：`training/streaming_trainer.py`、`training/batch_trainer.py`、training configs、sample scripts 来复现实验结果。
- 验收标准：能在本地小数据集上重现 Paper 2 的 sample-efficiency对比（流式 vs 批式）；训练脚本有可重复的随机种子配置。
- 估时：4–6 周

---

## 6) Datasets & Benchmarks

- 目标：设计并实现 Streaming Tool-Arena 数据生成脚本、Continual Tool Drop-In 分阶段任务集、以及 SAGE-Bench 接口扩展。
- 可交付物：`data/streaming_tool_arena/` 生成脚本、数据样例、benchmark runner。
- 验收标准：提供可复现数据集（或生成脚本），并在 benchmark runner 中成功运行 3 个 baseline。
- 估时：2–4 周

---

## 7) Experiments & Baselines

- 目标：搭建实验管线（自动跑多 seed、多方法），实现 baseline：ReAct、Reflexion、ToolLLM、Gorilla、AutoGPT、以及我们的 ablations。
- 可交付物：`experiments/paper2/*`、复现实验的 Slurm/CI 配置片段、结果分析脚本（生成图表/表格）。
- 验收标准：可在有限资源（2×A100）上跑出代表性曲线；结果可导出 CSV 并由 `paper2/main.tex` 脚注引用。
- 估时：3–8 周（受实验规模影响）

---

## 8) Tests & CI

- 目标：添加 unit/integration tests；在 repo CI 中加入轻量级 smoke tests，保证 core API 在变更后不回归。
- 可交付物：pytest cases、workflow snippet（`.github/workflows/paper2-experiments.yml` 的轻量 runner）。
- 验收标准：所有新增单元测试在 CI 中通过；核心的 smoke test（no-GPU）每提交触发。

---

## 9) Docs, LaTeX & Extraction

- 目标：补全 `docs/dev-notes/research_work/agent-tool-benchmark/paper2/icml_prompt.md` 的实现对齐文档，完善图表/数据引用，并准备 `SUBMODULE.md` 的 extraction 指引。
- 可交付物：`paper2/main.tex`（与 icml prompt 对齐）、README（编译/复现实验步骤）、submodule extraction checklist。

---

## Assignment / Issue Template（可直接贴到 GitHub Issue）

标题格式：[SIAS][Area] Short description — Assignee

Issue body 模板（中文）：

```
任务：<短标题>
领域：<SSIS | Memory | Runtime | Router | Trainer | Data | Experiments | Tests | Docs>
负责人：@<github-id>
目标：<一句话目标和验收标准>
实现文件（建议）：<相对路径>
测试：<需要添加的测试和验证脚本>
估时：<周数>
备注（可选）：<依赖/注意事项>

请在 PR 描述中引用本 issue 编写“完成证明”，并在 PR 中运行相关单元/集成测试。
```

Assignment prompt template (English, for copy/paste):

```
Task: <short title>
Area: <SSIS | Memory | Runtime | Router | Trainer | Data | Experiments | Tests | Docs>
Assignee: @<github-id>
Goal: <one-sentence goal and acceptance criteria>
Files (suggested): <relative paths>
Tests required: <unit/integration/benchmark scripts>
Estimate: <weeks>
Notes: <dependencies/risks>

When submitting the PR, include a short test run log and attach any benchmark CSVs/plots.
```

---

## 小结（Quick next steps）

1. 由项目负责人（或论文第一作者）按上面模板逐条创建 GitHub issues 并分配。  
2. 推荐先推进：1) SSIS、2) ReflectiveMemory、3) Streaming Trainer（这三项是核心互相依赖的）。  
3. 对于实验，先在本地做小规模 smoke-run（2 seeds，tiny dataset），确认 pipeline 后再扩规模。

---

如果想让我把这些任务直接转换为 GitHub issue 列表并创建草稿 PR（或把 `SUBMODULE.md` 指向此文件），告诉我：

- 是否要把文件引用写入 `packages/sage-libs/src/sage/libs/sias/SUBMODULE.md`（我可以自动添加一行链接）。
- 是否需要我为核心任务（SSIS/Memory/Trainer）创建初始 issue templates（包括 checklist）。

```
```
