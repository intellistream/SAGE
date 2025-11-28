# SAGE-Bench 评测框架# SAGE-Bench 评测框架

> 支持 **15+ 种方法** 和 **8+ 数据集** 的 Agent 能力评测框架> 支持 **15+ 种方法** 和 **6+ 外部数据集** 的 Agent 能力评测框架

本框架服务于两篇论文：本框架服务于两篇论文：

1. **Paper 1 (Benchmark)**: SAGE-Bench - 统一评测框架，对比现有 SOTA 方法1. **Paper 1 (Benchmark)**: SAGE-Bench -
   统一评测框架，对比现有 SOTA 方法

1. **Paper 2 (Method)**: SAGE-Agent - Streaming Adaptive Learning 框架1. **Paper 2 (Method)**:
   SAGE-Agent - Streaming Adaptive Learning 框架

---\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_

## 🚀 快速开始## 📁 脚本架构

### 统一 CLI 入口 (推荐)### 统一入口 (推荐)

所有功能通过 `sage-bench` CLI 访问：\`\`\`bash

# 交互式运行

````bashpython sage_benchmark_cli.py

# 列出可用数据集

sage-bench list datasets# 或直接指定实验

python sage_benchmark_cli.py --paper 1 --experiment tool_selection

# 列出可用方法python sage_benchmark_cli.py --paper 2 --experiment sage_agent_full

sage-bench list methods```



# 工具选择评测### 脚本对照表

sage-bench eval --dataset sage --samples 100

sage-bench eval --dataset acebench --methods keyword,embedding,gorilla| 脚本                              | Paper | 用途                                    |

sage-bench eval --dataset all        # 跨数据集对比| --------------------------------- | ----- | --------------------------------------- |

| `sage_benchmark_cli.py`           | 1 & 2 | **统一交互式入口**                      |

# 运行完整 Benchmark (三个 Challenge)| `run_all_experiments.py`          | 1     | Benchmark: 三个 Challenge 全量评测      |

sage-bench run --quick               # 快速模式| `run_unified_eval.py`             | 1     | Benchmark: 跨数据集 Tool Selection 对比 |

sage-bench run --challenge timing    # 单个 Challenge| `run_full_training_comparison.py` | 2     | Method: SAGE-Agent 方法对比             |

| `run_acebench_comparison.py`      | 1     | Benchmark: 外部数据集验证               |

# 训练方法对比 (Paper 2)

sage-bench train --quick______________________________________________________________________

sage-bench train --methods A_baseline,D_combined

## 🎯 方法分类

# LLM 服务管理

sage-bench llm status### 📘 Paper 1: Benchmark (现有 SOTA 方法对比)

sage-bench llm start --model Qwen/Qwen2.5-7B-Instruct

sage-bench llm stop这些是 **文献中已有的方法**，用于建立 baseline 对比。 **Benchmark 论文不提出新方法，只做系统性评测。**



# 交互式模式#### Challenge 1: Timing Judgment

sage-bench interactive

```| 方法 ID             | 名称       | 来源   | 描述                  |

| ------------------- | ---------- | ------ | --------------------- |

---| `timing.rule_based` | Rule-based | Common | 关键词匹配 + 正则模式 |

| `timing.llm_based`  | LLM-based  | Common | 直接用 LLM 判断       |

## 📁 脚本架构| `timing.hybrid`     | Hybrid     | Common | Rule 初筛 + LLM 精判  |

| `timing.embedding`  | Embedding  | Common | 语义相似度判断        |

````

scripts/#### Challenge 2: Task Planning

├── sage_bench # 🌟 统一 CLI 入口 (推荐使用)

├── \_internal/ # 内部模块 (不要直接调用)| 方法 ID | 名称 | 来源 | 参考文献 |

│ ├── unified_eval.py # 工具选择评测| ---------------------- | ---------------- | ------ |
\---------------- |

│ ├── all_experiments.py # 完整 Benchmark| `planner.simple` | Simple (Greedy) | Common | - |

│ ├── training_comparison.py # 训练对比| `planner.hierarchical` | Hierarchical | Common | - |

│ └── interactive.py # 交互模式| `planner.llm_based` | LLM-based | Common | - |

├── run_unified_eval.py # 功能模块 (支持直接调用，建议用 CLI)| `planner.react` | ReAct | SOTA | Yao et al., 2023 |

├── run_all_experiments.py # 功能模块 (支持直接调用，建议用 CLI)| `planner.tot` | Tree-of-Thoughts | SOTA | Yao et
al., 2023 |

└── ...

````#### Challenge 3: Tool Selection



### CLI 子命令| 方法 ID              | 名称            | 来源    | 参考文献           |

| -------------------- | --------------- | ------- | ------------------ |

| 命令 | 功能 | 示例 || `selector.keyword`   | Keyword (BM25)  | Classic | Robertson et al.   |

|------|------|------|| `selector.embedding` | Embedding       | Common  | BGE-M3 (BAAI)      |

| `eval` | 工具选择评测 | `sage-bench eval --dataset all` || `selector.hybrid`    | Hybrid (RRF)    | Common  | -                  |

| `run` | 完整 Benchmark | `sage-bench run --quick` || `selector.gorilla`   | Gorilla         | SOTA    | Patil et al., 2023 |

| `train` | 训练方法对比 | `sage-bench train --dry-run` || `selector.dfsdt`     | DFSDT (ToolLLM) | SOTA    | Qin et al., 2023   |

| `llm` | LLM 服务管理 | `sage-bench llm status` || `llm_direct`         | LLM Direct      | Common  | -                  |

| `list` | 列出可用资源 | `sage-bench list datasets` |

| `interactive` | 交互式模式 | `sage-bench interactive` |______________________________________________________________________



---### 📙 Paper 2: SAGE-Agent (原创方法)



## 📊 支持的数据集**核心创新**: 将 Agent 学习重新定义为 **在线流学习问题**，提出 Streaming Adaptive Learning 框架。



| 数据集 | 来源 | 描述 |#### 架构概览

|--------|------|------|

| `sage` | Built-in | SAGE-Bench (1200 synthetic tools) |```

| `acebench` | HuggingFace | ToolACE from Team-ACE |┌─────────────────────────────────────────────────────────────┐

| `apibank` | External | API-Bank (Microsoft/Alibaba) |│                    SAGE-Agent Framework                      │

| `toolalpaca` | External | ToolAlpaca (Microsoft) |│                                                             │

| `bfcl` | External | Berkeley Function Calling Leaderboard |│  Query Stream ──→ [SSIS] ──→ [Priority Buffer] ──→ [Train]  │

| `toolbench` | External | ToolBench (Tsinghua/OpenBMB) |│       │              │              │                │      │

| `taskbench` | External | TaskBench (PKU) |│       │     Importance Score   Experience      Online Update │

| `metatool` | External | MetaTool (Tsinghua) |│       │     (U + D + F)        Replay               │      │

│       │                                              │      │

查看所有数据集：│       └──────────────────────────────────────────────┘      │

```bash│                                                             │

sage-bench list datasets│  [Unified Multi-Task Network]                               │

```│  ├── Timing Head    ←──┐                                    │

│  ├── Selection Head ←──┼── Cross-Task Attention             │

---│  └── Planning Head  ←──┘                                    │

└─────────────────────────────────────────────────────────────┘

## 🎯 支持的方法```



### Challenge 3: Tool Selection#### 三大核心组件



| 方法 | 来源 | 描述 || 组件                     | 全称                               | 功能                 | 创新点                                            |

|------|------|------|| ------------------------ | ---------------------------------- | -------------------- | ------------------------------------------------- |

| `keyword` | Classic | BM25 keyword matching || **SSIS**                 | Streaming Sample Importance Scorer | 实时评估样本训练价值 | 三维度评分 (Uncertainty + Diversity + Forgetting) |

| `embedding` | Common | Semantic embedding similarity || **Priority Replay**      | Importance-Weighted Replay Buffer  | 优先级经验回放       | Sum-tree O(log n) 采样 + IS 权重校正              |

| `hybrid` | Common | Keyword + Embedding fusion (RRF) || **Cross-Task Attention** | Unified Multi-Task Network         | 跨任务信息共享       | Timing ↔ Selection ↔ Planning 协同                |

| `gorilla` | Berkeley | Retrieval + LLM reranking |

| `dfsdt` | Tsinghua | Tree search (ToolLLM) |#### 消融实验配置

| `llm_direct` | Baseline | Direct LLM prompting |

| 方法 ID             | 名称                | SSIS | Replay | CrossTask | 说明               |

查看所有方法：| ------------------- | ------------------- | :--: | :----: | :-------: | ------------------ |

```bash| `SAGE_sft_baseline` | Baseline SFT        |  ❌  |   ❌   |    ❌     | 消融基准           |

sage-bench list methods| `SAGE_ssis_only`    | +SSIS               |  ✅  |   ❌   |    ❌     | 加入样本重要性评估 |

```| `SAGE_ssis_replay`  | +SSIS +Replay       |  ✅  |   ✅   |    ❌     | 加入优先级回放     |

| `SAGE_full`         | **Full SAGE-Agent** |  ✅  |   ✅   |    ✅     | 完整方法           |

---

#### 预期性能提升

## 📋 使用示例

| Challenge               | Baseline Best | SAGE-Agent | 提升 |

### Paper 1: Benchmark 实验| ----------------------- | ------------- | ---------- | ---- |

| Tool Selection (Top-5)  | 82%           | **94%**    | +12% |

```bash| Task Planning (Success) | 27%           | **85%**    | +58% |

# 1. 快速评测 (跳过 LLM 方法)| Timing Judgment (Acc)   | 76%           | **95%**    | +19% |

sage-bench run --quick --skip-llm

#### 效率提升

# 2. 跨数据集工具选择对比

sage-bench eval --dataset all --methods keyword,embedding,hybrid,gorilla --samples 100| 指标                   | 传统 SFT | SAGE-Agent | 提升       |

| ---------------------- | -------- | ---------- | ---------- |

# 3. 单个 Challenge 评测| 训练时间               | 1.0x     | **0.4x**   | 2.5x 更快  |

sage-bench run --challenge tool_selection| 数据利用               | 100%     | **~35%**   | 更高效     |

sage-bench run --challenge timing| 在线适应 (性能下降/轮) | -8%      | **-0.5%**  | 16x 更稳定 |

sage-bench run --challenge planning

```______________________________________________________________________



### Paper 2: SAGE-Agent 实验## 📚 数据集



```bash### SAGE-Bench 原生数据

# 1. 快速训练对比

sage-bench train --quick| 任务            | 样本数    | Train | Dev | Test |

| --------------- | --------- | ----- | --- | ---- |

# 2. 完整消融实验| Tool Selection  | 600       | 420   | 90  | 90   |

sage-bench train --methods A_baseline,B_coreset,C_continual,D_combined| Task Planning   | 300       | 210   | 45  | 45   |

| Timing Judgment | 300       | 210   | 45  | 45   |

# 3. 模拟运行 (不实际训练)| **Total**       | **1,200** | 840   | 180 | 180  |

sage-bench train --dry-run

```### 外部数据集集成



### LLM 服务管理| 数据集     | 来源                   | 样本数  | 用途           |

| ---------- | ---------------------- | ------- | -------------- |

```bash| ACEBench   | Team-ACE (HuggingFace) | 10,000+ | 跨数据集验证   |

# 检查服务状态| API-Bank   | Microsoft/Alibaba      | 2,138   | 多轮 API 对话  |

sage-bench llm status| ToolAlpaca | Microsoft              | 3,928   | 工具学习对话   |

| ToolBench  | Tsinghua/OpenBMB       | 16,000+ | 大规模工具检索 |

# 启动 vLLM 服务

sage-bench llm start --model Qwen/Qwen2.5-0.5B-Instruct --port 8901______________________________________________________________________



# 停止服务## 🚀 快速开始

sage-bench llm stop

```### Paper 1: Benchmark 实验



---```bash

# 1. 运行完整 Benchmark (三个 Challenge)

## 📁 输出结构python run_all_experiments.py --quick  # 快速测试

python run_all_experiments.py          # 完整评测

所有结果保存在 `~/.sage/benchmark/results/`:

# 2. 跨数据集验证

```python run_unified_eval.py --datasets sage acebench --samples 100

~/.sage/benchmark/results/

├── unified_eval_results.json      # 工具选择评测结果# 3. 单独评测 Tool Selection

├── all_results.json               # 完整 Benchmark 结果python sage_benchmark_cli.py --paper 1 --experiment tool_selection

├── figures/                       # 生成的图表```

│   ├── fig4_overall_comparison.pdf

│   └── fig5_planning_by_complexity.pdf### Paper 2: SAGE-Agent 实验

└── tables/                        # LaTeX 表格

    ├── table1_projected_performance.tex```bash

    └── table2_observed_benchmark.tex# 1. 完整消融实验

```python run_full_training_comparison.py --quick  # 快速测试

python run_full_training_comparison.py          # A100 完整训练

---

# 2. 单独测试 SAGE-Agent Full

## 🔧 开发者指南python sage_benchmark_cli.py --paper 2 --experiment sage_agent_full



### 添加新数据集# 3. 在线适应实验 (动态工具库)

python sage_benchmark_cli.py --paper 2 --experiment online_adaptation

1. 在 `external_benchmarks/` 中添加下载脚本```

2. 在 `EXTERNAL_BENCHMARKS` 字典中注册

3. 更新 `sage-bench list datasets` 输出______________________________________________________________________



### 添加新方法## 📊 结果输出



1. 实现 `BaseSelectorAdapter` 接口所有实验结果保存在 `outputs/` 目录：

2. 在 `create_evaluator()` 中注册

3. 更新 `sage-bench list methods` 输出```

outputs/

---├── paper1_benchmark/

│   ├── timing_results.json

## 📝 引用│   ├── planning_results.json

│   ├── tool_selection_results.json

```bibtex│   └── cross_dataset_validation.json

@inproceedings{sage-bench-2026,│

  title={SAGE-Bench: A Unified Benchmark for Evaluating Agent Capabilities},└── paper2_method/

  author={...},    ├── ablation_study/

  booktitle={ICML},    │   ├── SAGE_sft_baseline.json

  year={2026}    │   ├── SAGE_ssis_only.json

}    │   ├── SAGE_ssis_replay.json

```    │   └── SAGE_full.json

    ├── efficiency_analysis.json
    └── online_adaptation.json
````

______________________________________________________________________

## 📖 相关论文

### Paper 1: SAGE-Bench (Benchmark)

- **定位**: Dataset & Benchmark Track
- **贡献**: 统一评测框架 + 数据集 + 现有方法系统对比
- **不包含**: 新方法提出

### Paper 2: SAGE-Agent (Method)

- **定位**: Method Paper
- **贡献**: Streaming Adaptive Learning 框架
- **核心组件**: SSIS + Priority Replay + Cross-Task Attention
- **背景**: 基于流计算和在线持续学习的研究经验

______________________________________________________________________

## 🔧 开发者指南

### 添加新方法

1. 在 `adapter_registry.py` 中注册工厂函数
1. 实现符合 `SelectorAdapter`/`PlannerAdapter`/`TimingAdapter` 接口
1. 在 README 中添加方法描述
1. 运行测试验证

### 添加新数据集

1. 实现 `DataLoader` 接口
1. 在 `DataManager` 中注册
1. 添加数据集描述到文档

______________________________________________________________________

## 📝 引用

```bibtex
@inproceedings{sage-bench-2026,
  title={SAGE-Bench: A Unified Benchmark for Evaluating Agent Capabilities in Tool-Augmented LLMs},
  author={...},
  booktitle={ICML},
  year={2026}
}

@inproceedings{sage-agent-2026,
  title={SAGE-Agent: Streaming Adaptive Learning for Tool-Augmented LLM Agents},
  author={...},
  booktitle={ICML},
  year={2026}
}
```
