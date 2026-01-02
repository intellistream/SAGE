# L5 Benchmark Notes

`sage-benchmark` 属于 L5（应用 & 评测层），目前已经包含**六类**基准套件。该目录用于追踪这些套件的设计、迁移、以及与 `examples/` 的对齐情况。

## Benchmark 套件概览

| Suite                            | 位置                           | 作用                                                          | 入口 / 快速命令                                                              | 依赖 / 数据                                          |
| -------------------------------- | ------------------------------ | ------------------------------------------------------------- | ---------------------------------------------------------------------------- | ---------------------------------------------------- |
| **benchmark_agent** ⭐新         | `.../benchmark_agent/`         | Agent 能力评测（工具选择、任务规划、时机判断）                | `python -m sage.benchmark.benchmark_agent --config <yaml>`                   | 依赖 `sage.libs.agentic`、`agent_benchmark/` 数据    |
| **benchmark_control_plane** ⭐新 | `.../benchmark_control_plane/` | sageLLM Control Plane 调度策略评测                            | `sage-cp-bench run --mode llm --policy fifo`                                 | 依赖 Control Plane 服务、vLLM                        |
| `benchmark_rag`                  | `.../benchmark_rag/`           | RAG 管道基准，含 `implementations/`, `evaluation/`, `config/` | `python -m sage.benchmark.benchmark_rag.evaluation.pipeline_experiment`      | 需要 `sage/data/qa/` 数据子模块、Milvus/Chroma/FAISS |
| `benchmark_memory`               | `.../benchmark_memory/`        | 内存系统（SAGE Memory Service）吞吐/延迟评测                  | `python -m sage.benchmark.benchmark_memory.experiment.run_memory_experiment` | 依赖 `sage.middleware.components.sage_mem`           |
| `benchmark_libamm`               | `.../benchmark_libamm/`        | LibAMM 矩阵乘性能基准 & C++ 评测                              | `cmake .. && cmake --build .`、`python pythonTest.py`                        | 数据存放于 `sage/data/libamm-benchmark/`             |
| `benchmark_scheduler`            | `.../benchmark_scheduler/`     | 调度策略比较（Ray vs Local 等）                               | `python -m sage.benchmark.benchmark_scheduler.scheduler_comparison`          | 依赖 `sage.kernel` 调度接口                          |
| `benchmark_refiner`              | `.../benchmark_refiner/`       | Refiner 上下文压缩算法评测                                    | `sage-refiner-bench compare --algorithms baseline,longrefiner`               | 依赖 `sageRefiner` 子模块、FlashRAG 数据             |

## 新增套件详情

### benchmark_refiner (Refiner 压缩算法评测)

评估 RAG 上下文压缩算法的性能（ICML 2025 投稿）：

| 算法              | 类型             | 描述                    |
| ----------------- | ---------------- | ----------------------- |
| **Baseline**      | 截断             | 无压缩基线              |
| **LongRefiner**   | LLM-based        | 三阶段压缩              |
| **REFORM**        | Attention-based  | 注意力头驱动 token 选择 |
| **Provence**      | Provenance-aware | 句子级上下文剪枝        |
| **LongLLMLingua** | LLM-PPL          | 问题感知长文档压缩      |
| **LLMLingua-2**   | BERT-based       | 快速 token 分类压缩     |

**CLI**：

```bash
# 多算法对比
sage-refiner-bench compare \
    --algorithms baseline,longrefiner,reform,longllmlingua,llmlingua2 \
    --samples 100
```

**文档**：

- [benchmark_refiner/README.md](../../../../packages/sage-benchmark/src/sage/benchmark/benchmark_refiner/README.md)
- [ICML_REFINER_TASKS.md](./ICML_REFINER_TASKS.md) - ICML 投稿任务分解

### benchmark_agent (Agent 能力评测)

评估 Agent 的三个核心能力（对应论文难题4）：

| 挑战       | 描述 | 目标 | 策略 |
| ---------- | ---- | ---- | ---- |
| **文档**： |      |      |      |

- [benchmark_agent/README.md](../../../../packages/sage-benchmark/src/sage/benchmark/benchmark_agent/README.md)
  详细的实验脚本与配置请参考 `archive/ICML_REFINER_TASKS.md` 与 `archive/PAPER1_EXPERIMENTS_DESIGN.md`，其中包含：
- [agent-benchmark-tasks.md](../agent-benchmark-tasks.md)

### benchmark_control_plane (Control Plane 调度评测)

评估 sageLLM Control Plane 的调度策略性能：

| 模式                         | 策略                                        | 指标                     |
| ---------------------------- | ------------------------------------------- | ------------------------ |
| **LLM-only**                 | `fifo`, `priority`, `slo_aware`, `adaptive` | 吞吐量、延迟、SLO 合规率 |
| **Hybrid** (LLM + Embedding) | `hybrid`, `hybrid_slo`                      | 混合负载下的资源调度效率 |

**CLI**：

```bash
# LLM 调度评测
sage-cp-bench run --mode llm --policy fifo --requests 100

# Hybrid 调度评测
sage-cp-bench run --mode hybrid --policy hybrid_slo --llm-ratio 0.7

# 策略对比
sage-cp-bench compare --mode llm --policies fifo,priority,slo_aware
```

**文档**：

- [benchmark_control_plane/README.md](../../../../packages/sage-benchmark/src/sage/benchmark/benchmark_control_plane/README.md)

## 当前状态（2025-11）

1. **RAG 示例彻底迁出 `examples/`**：所有 RAG/向量数据库示例均集中在
   `benchmark_rag/implementations/`；`examples/tutorials/` 仅保留入门级示例。
1. **数据子模块统一管理**：`packages/sage-benchmark/src/sage/data` 作为 git submodule，包含 `qa_knowledge_base.*`,
   `queries.jsonl`, `libamm-benchmark` 数据。任何新的基准数据应放入该子模块或 `.sage/` 缓存（避免重新引入 `examples/data/`).
1. **CI 策略**：
   - `benchmark_rag` 和 `benchmark_memory` 默认标记为 `slow`，由 `sage-dev project test --coverage` 的扩展阶段触发。
   - `benchmark_libamm` 采用独立 CMake 构建，不在常规 CI 中运行；本地需要 `cmake`, `openblas` 等依赖。
1. **待补文档**：`benchmark_memory/README.md` 为空，需要在未来 PR 中补充实验说明；若新增 suite，请在此 dev-note 追加行并在
   `docs-public` 对应章节更新。

## 论文与 Refiner 专题实验概览

### ICML Refiner 投稿实验（benchmark_refiner）

`benchmark_refiner`
目前已经支持多种上下文压缩算法（Baseline、LongRefiner、REFORM、Provence、LongLLMLingua、LLMLingua‑2），并围绕 ICML
投稿完成了两轮主要工程与实验工作：

- **Round 1：基础模块落地**
  - 结果收集器 `ResultsCollector` 实现并接入 F1/Latency/Compression 等评测。
  - LongLLMLingua / LLMLingua‑2 Pipeline 集成，包含对应 `config_*.yaml` 与 `*_rag.py` 管道脚本。
  - 统计检验模块（配对 t 检验、Bootstrap 置信区间、Cohen's d、Wilcoxon、Bonferroni/ Holm‑Bonferroni 校正等）。
- **Round 2：集成与多数据集支持**
  - `ComparisonExperiment` 重构，统一通过真实 Pipeline 运行并从 `ResultsCollector` 收集结果，而非再使用占位模拟数据。
  - 支持多数据集批量运行、结果聚合和统一结果容器（`DatasetResult`、`MultiDatasetExperimentResult`）。

> 更细粒度的任务拆解、文件列表与 Prompt 记录见 `ICML_REFINER_TASKS.md`；日常开发只需关注 `benchmark_refiner` 目录下的 README 与 CLI
> 即可。

### SAGE-Bench Paper 1（benchmark_agent）实验设计

围绕 `benchmark_agent`，已经根据 Paper 1（Agent Benchmark）规划出一套完整的实验章节与脚本结构，对应论文中的 `5. Experiments`：

- **Section 5.2: Main Results（RQ1–RQ3）**
  - RQ1 Timing Detection：`exp_main_timing.py`，比较 `timing.rule_based` / `timing.embedding` /
    `timing.llm_based` / `timing.hybrid`，主指标为 Accuracy（目标 ≥95%），辅以 Precision/Recall/F1 与延迟。
  - RQ2 Task Planning：`exp_main_planning.py`，比较 `planner.simple` / `planner.hierarchical` /
    `planner.llm_based` / `planner.react`，主指标为 Plan Success Rate（目标 ≥90%），并观测步骤质量与覆盖率。
  - RQ3 Tool Selection：`exp_main_selection.py`，比较 `selector.keyword` / `selector.embedding` /
    `selector.hybrid` / `selector.gorilla` / `selector.dfsdt`，主指标为 Top‑K Accuracy（K=5），辅以
    MRR/Recall@K/Latency。
- **Section 5.3: Analysis & Discussion**
  - Error Analysis、Scaling Analysis、Robustness Analysis、Ablation Studies 分别由 `exp_analysis_*.py`
    系列脚本实现，输出统一放在 `figures/`、`tables/`、`results/` 目录，方便直接引用到论文中。
- **Section 5.4: Cross-Dataset Generalization**
  - 通过 `exp_cross_dataset.py` 评估跨数据集泛化能力。

在 CLI 层面，预期通过 `sage-bench paper1 ...` 提供一套统一入口：

- `sage-bench paper1 run [--quick] [--section 5.2|5.3]` 复现整套或部分实验。
- `sage-bench paper1 timing|planning|selection` 运行单个主实验。
- `sage-bench paper1 analysis error|scaling|robustness|ablation` 运行各类分析实验。

> 详细 CLI 设计与脚本布局目前记录在 `PAPER1_EXPERIMENTS_DESIGN.md`，实现时请优先对齐该文档，并在落地后同步更新本 README 与
> `benchmark_agent` 目录下的 README。

## 建议工作流

1. **提交新的 benchmark**：
   - 在 `packages/sage-benchmark/src/sage/benchmark/<suite>/` 内新增目录与 README。
   - 如果需要示例/入口脚本，可在 `examples/tutorials/L5-apps/` 或 `examples/apps/` 中添加轻量包装。
   - 将运行命令、依赖、数据路径同步到本 README 与 docs-public（参考
     `docs-public/docs_src/guides/packages/sage-benchmark/`).
1. **数据管理**：大体量数据放入 `packages/sage-benchmark/src/sage/data/` 子模块；运行期产物写入 `.sage/benchmark_results/`。
1. **测试标签**：在任何 CLI/脚本文件头部添加
   `@test_category: benchmark`、`@test_speed: slow`、`@test_skip_ci: true/false` 等元数据，以便
   `sage-dev project test` 分类执行。

## 参考

- `packages/sage-benchmark/README.md`
- `packages/sage-benchmark/src/sage/benchmark/benchmark_rag/README.md`
- `packages/sage-benchmark/src/sage/benchmark/benchmark_libamm/README.md`
- `packages/sage-benchmark/src/sage/data/README.md` (数据目录)
- `docs-public/docs_src/guides/packages/sage-benchmark/`（公共文档，若不存在需创建）
