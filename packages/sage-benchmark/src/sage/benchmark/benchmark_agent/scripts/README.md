# SAGE Agent Bench 实验脚本# sage-benchmark 实验脚本# SAGE-Bench 评测框架# SAGE-Bench 评测框架

本目录包含 Paper 1 (Agent 能力评测框架) 的完整实验脚本，按论文章节组织。

## 目录结构本目录包含 Paper 1 (Agent 能力评测框架) 的完整实验脚本，按论文章节组织。> 支持 **15+ 种方法** 和 **8+ 数据集** 的 Agent 能力评测框架> 支持 **15+ 种方法** 和 **6+ 外部数据集** 的 Agent 能力评测框架

````

scripts/

├── sage-agent-bench              # CLI 入口脚本 (可执行)## 目录结构本框架服务于两篇论文：本框架服务于两篇论文：

├── README.md                     # 本文件

└── experiments/                  # 实验模块包

    ├── __init__.py

    │```1. **Paper 1 (Benchmark)**: SAGE-Bench - 统一评测框架，对比现有 SOTA 方法1. **Paper 1 (Benchmark)**: SAGE-Bench -

    │  === 核心工具 ===

    ├── exp_utils.py              # 共享工具 (环境、数据、保存、LLM客户端)scripts/   统一评测框架，对比现有 SOTA 方法

    ├── figure_generator.py       # 学术图表生成器 (PDF/PNG)

    ├── table_generator.py        # LaTeX 表格生成器├── sage_bench                    # CLI 入口脚本 (可执行)

    ├── llm_service.py            # LLM 服务管理 (vLLM)

    ├── sage_bench_cli.py         # CLI 实现├── README.md                     # 本文件1. **Paper 2 (Method)**: SAGE-Agent - Streaming Adaptive Learning 框架1. **Paper 2 (Method)**:

    │

    │  === Section 5.2: 主要评测 ===└── experiments/                  # 实验模块包   SAGE-Agent - Streaming Adaptive Learning 框架

    ├── exp_main_timing.py        # 工具调用时机评测

    ├── exp_main_planning.py      # 任务规划能力评测    ├── __init__.py

    ├── exp_main_selection.py     # 工具选择准确率评测

    │    │---\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_

    │  === Section 5.3: 深度分析 ===

    ├── exp_analysis_error.py     # 错误类型分布分析    │  === 核心工具 ===

    ├── exp_analysis_scaling.py   # 工具数量扩展性分析

    ├── exp_analysis_robustness.py # 鲁棒性分析    ├── exp_utils.py              # 共享工具 (环境、数据、保存、LLM客户端)## 🚀 快速开始## 📁 脚本架构

    ├── exp_analysis_ablation.py  # 消融实验

    │    ├── figure_generator.py       # 学术图表生成器 (PDF/PNG)

    │  === Section 5.4: 跨数据集 ===

    ├── exp_cross_dataset.py      # 跨数据集泛化评测    ├── table_generator.py        # LaTeX 表格生成器### 统一 CLI 入口 (推荐)### 统一入口 (推荐)

    │

    │  === Section 5.5: 训练方法对比 ===    ├── llm_service.py            # LLM 服务管理 (vLLM)

    ├── exp_training_comparison.py # 训练方法对比 (A-D)

    │    ├── sage_bench_cli.py         # CLI 实现所有功能通过 `sage-bench` CLI 访问：\`\`\`bash

    │  === 主运行器 ===

    └── run_paper1_experiments.py  # Paper 1 全流程运行器    │

````

```
│  === Section 5.2: 主要评测 ===# 交互式运行
```

## 快速开始

```
├── exp_main_timing.py        # 工具调用时机评测
```

### 1. 环境准备

`````
├── exp_main_planning.py      # 任务规划能力评测````bashpython sage_benchmark_cli.py
`````

````bash

# 安装 sage-benchmark    ├── exp_main_selection.py     # 工具选择准确率评测

cd /path/to/SAGE

./quickstart.sh --dev --yes    │# 列出可用数据集



# 设置环境变量    │  === Section 5.3: 深度分析 ===

export SAGE_TEST_MODE=true  # 可选：启用测试模式

```    ├── exp_analysis_error.py     # 错误类型分布分析sage-bench list datasets# 或直接指定实验



### 2. 使用 CLI    ├── exp_analysis_scaling.py   # 工具数量扩展性分析



```bash    ├── exp_analysis_robustness.py # 鲁棒性分析python sage_benchmark_cli.py --paper 1 --experiment tool_selection

# 查看帮助

./sage-agent-bench --help    ├── exp_analysis_ablation.py  # 消融实验



# === LLM 服务管理 ===    │# 列出可用方法python sage_benchmark_cli.py --paper 2 --experiment sage_agent_full

./sage-agent-bench llm start                    # 启动 vLLM 服务

./sage-agent-bench llm status                   # 检查服务状态    │  === Section 5.4: 跨数据集 ===

./sage-agent-bench llm stop                     # 停止服务

    ├── exp_cross_dataset.py      # 跨数据集泛化评测sage-bench list methods```

# === 运行实验 ===

# 运行单个章节    │

./sage-agent-bench run --section 5.2            # 主要评测

./sage-agent-bench run --section 5.3            # 深度分析    │  === Section 5.5: 训练方法对比 ===

./sage-agent-bench run --section 5.4            # 跨数据集

./sage-agent-bench run --section 5.5            # 训练方法对比    ├── exp_training_comparison.py # 训练方法对比 (A-D)



# 运行全部实验    │# 工具选择评测### 脚本对照表

./sage-agent-bench run --all

    │  === 主运行器 ===

# 快速测试

./sage-agent-bench run --quick    └── run_paper1_experiments.py  # Paper 1 全流程运行器sage-bench eval --dataset sage --samples 100



# === 列出资源 ===```

./sage-agent-bench list datasets                # 列出数据集

./sage-agent-bench list methods                 # 列出方法sage-bench eval --dataset acebench --methods keyword,embedding,gorilla| 脚本                              | Paper | 用途                                    |

./sage-agent-bench list experiments             # 列出实验

```## 快速开始



### 3. 使用 Python APIsage-bench eval --dataset all        # 跨数据集对比| --------------------------------- | ----- | --------------------------------------- |



```python### 1. 环境准备

# 运行单个实验

from sage.benchmark.benchmark_agent.scripts.experiments import exp_main_timing| `sage_benchmark_cli.py`           | 1 & 2 | **统一交互式入口**                      |

exp_main_timing.main()

```bash

# 运行全部实验

from sage.benchmark.benchmark_agent.scripts.experiments import run_paper1_experiments# 安装 sage-benchmark# 运行完整 Benchmark (三个 Challenge)| `run_all_experiments.py`          | 1     | Benchmark: 三个 Challenge 全量评测      |

run_paper1_experiments.main(sections=["5.2", "5.3", "5.4", "5.5"])

cd /path/to/SAGE

# 生成表格

from sage.benchmark.benchmark_agent.scripts.experiments.table_generator import (./quickstart.sh --dev --yessage-bench run --quick               # 快速模式| `run_unified_eval.py`             | 1     | Benchmark: 跨数据集 Tool Selection 对比 |

    generate_main_results_table,

    generate_training_comparison_table,

)

latex = generate_main_results_table(results_data)# 设置环境变量sage-bench run --challenge timing    # 单个 Challenge| `run_full_training_comparison.py` | 2     | Method: SAGE-Agent 方法对比             |



# 管理 LLM 服务export SAGE_TEST_MODE=true  # 可选：启用测试模式

from sage.benchmark.benchmark_agent.scripts.experiments.llm_service import (

    start_llm_service, stop_llm_service, check_llm_status```| `run_acebench_comparison.py`      | 1     | Benchmark: 外部数据集验证               |

)

start_llm_service(model="Qwen/Qwen2.5-7B-Instruct")

````

### 2. 使用 CLI# 训练方法对比 (Paper 2)

## 控制常量

所有实验使用统一的控制常量，定义在 `exp_utils.py`：

````bashsage-bench train --quick______________________________________________________________________

```python

RANDOM_SEED = 42                                    # 随机种子# 查看帮助

BENCHMARK_EMBEDDING_MODEL = "BAAI/bge-small-zh-v1.5"  # Embedding 模型

BENCHMARK_LLM_TEMPERATURE = 0.1                     # LLM 温度./sage_bench --helpsage-bench train --methods A_baseline,D_combined

````

## 输出目录

# === LLM 服务管理 ===## 🎯 方法分类

所有输出保存在 `.sage/benchmark/paper1/`：

./sage_bench llm start # 启动 vLLM 服务

`````

.sage/benchmark/paper1/./sage_bench llm status                   # 检查服务状态# LLM 服务管理

├── section_5_2_main/           # 主要评测结果

│   ├── timing_results.json./sage_bench llm stop                     # 停止服务

│   ├── planning_results.json

│   └── selection_results.jsonsage-bench llm status### 📘 Paper 1: Benchmark (现有 SOTA 方法对比)

├── section_5_3_analysis/       # 深度分析结果

│   ├── error_analysis.json# === 运行实验 ===

│   ├── scaling_analysis.json

│   ├── robustness_analysis.json# 运行单个章节sage-bench llm start --model Qwen/Qwen2.5-7B-Instruct

│   └── ablation_results.json

├── section_5_4_generalization/ # 跨数据集结果./sage_bench run --section 5.2            # 主要评测

│   └── cross_dataset_results.json

├── section_5_5_training/       # 训练对比结果./sage_bench run --section 5.3            # 深度分析sage-bench llm stop这些是 **文献中已有的方法**，用于建立 baseline 对比。 **Benchmark 论文不提出新方法，只做系统性评测。**

│   └── training_comparison.json

├── figures/                    # 生成的图表 (PDF/PNG)./sage_bench run --section 5.4            # 跨数据集

└── tables/                     # 生成的 LaTeX 表格

```./sage_bench run --section 5.5            # 训练方法对比



## 论文章节对应



| 章节 | 实验脚本 | 描述 |# 运行全部实验# 交互式模式#### Challenge 1: Timing Judgment

|------|----------|------|

| 5.2.1 | `exp_main_timing.py` | 工具调用时机评测 |./sage_bench run --all

| 5.2.2 | `exp_main_planning.py` | 任务规划能力评测 |

| 5.2.3 | `exp_main_selection.py` | 工具选择准确率评测 |sage-bench interactive

| 5.3.1 | `exp_analysis_error.py` | 错误类型分布分析 |

| 5.3.2 | `exp_analysis_scaling.py` | 工具数量扩展性分析 |# 快速测试

| 5.3.3 | `exp_analysis_robustness.py` | 鲁棒性分析 |

| 5.3.4 | `exp_analysis_ablation.py` | 消融实验 |./sage_bench run --quick```| 方法 ID             | 名称       | 来源   | 描述                  |

| 5.4 | `exp_cross_dataset.py` | 跨数据集泛化评测 |

| 5.5 | `exp_training_comparison.py` | 训练方法对比 |



## 训练方法说明 (Section 5.5)# === 生成输出 ===| ------------------- | ---------- | ------ | --------------------- |



| 方法 | 名称 | 描述 |./sage_bench tables                       # 生成 LaTeX 表格

|------|------|------|

| A | Baseline SFT | 基础监督微调 |./sage_bench figures                      # 生成图表---| `timing.rule_based` | Rule-based | Common | 关键词匹配 + 正则模式 |

| B1 | Random Coreset | 随机采样核心集 |

| B2 | Stratified Coreset | 分层采样核心集 |

| B3 | Embedding Coreset | 嵌入聚类核心集 |

| B4 | Difficulty Coreset | 难度平衡核心集 |# === 报告 ===| `timing.llm_based`  | LLM-based  | Common | 直接用 LLM 判断       |

| C | Continual Learning | 持续学习 |

| D | Combined | 组合方法 (B3 + C) |./sage_bench report                       # 查看实验状态



## LLM 服务配置```## 📁 脚本架构| `timing.hybrid`     | Hybrid     | Common | Rule 初筛 + LLM 精判  |



实验默认使用 vLLM 在端口 8901 (SagePorts.BENCHMARK_LLM)：



```bash### 3. 使用 Python API| `timing.embedding`  | Embedding  | Common | 语义相似度判断        |

# 默认配置

Model: Qwen/Qwen2.5-7B-Instruct

Port: 8901

GPU Memory: 90%```python````



# 自定义模型# 运行单个实验

./sage-agent-bench llm start --model "meta-llama/Llama-3.1-8B-Instruct"

```from sage.benchmark.benchmark_agent.scripts.experiments import exp_main_timingscripts/#### Challenge 2: Task Planning



## 依赖关系exp_main_timing.main()



```├── sage_bench # 🌟 统一 CLI 入口 (推荐使用)

exp_utils.py ← 所有实验脚本依赖

    ↑# 运行全部实验

figure_generator.py, table_generator.py ← 可视化工具

    ↑from sage.benchmark.benchmark_agent.scripts.experiments import run_paper1_experiments├── \_internal/ # 内部模块 (不要直接调用)| 方法 ID | 名称 | 来源 | 参考文献 |

llm_service.py ← LLM 管理

    ↑run_paper1_experiments.main(sections=["5.2", "5.3", "5.4", "5.5"])

run_paper1_experiments.py ← 主运行器

    ↑│ ├── unified_eval.py # 工具选择评测| ---------------------- | ---------------- | ------ |

sage_bench_cli.py ← CLI 实现

```# 生成表格\---------------- |



## 故障排除from sage.benchmark.benchmark_agent.scripts.experiments.table_generator import (



### LLM 服务无法启动    generate_main_results_table,│ ├── all_experiments.py # 完整 Benchmark| `planner.simple` | Simple (Greedy) | Common | - |



```bash    generate_training_comparison_table,

# 检查端口占用

lsof -i :8901)│ ├── training_comparison.py # 训练对比| `planner.hierarchical` | Hierarchical | Common | - |



# 检查 GPU 状态latex = generate_main_results_table(results_data)

nvidia-smi

│ └── interactive.py # 交互模式| `planner.llm_based` | LLM-based | Common | - |

# 手动启动 vLLM

vllm serve Qwen/Qwen2.5-7B-Instruct --port 8901 --gpu-memory-utilization 0.9# 管理 LLM 服务

`````

from sage.benchmark.benchmark_agent.scripts.experiments.llm_service import (├── run_unified_eval.py
\# 功能模块 (支持直接调用，建议用 CLI)| `planner.react` | ReAct | SOTA | Yao et al., 2023 |

### 实验结果不一致

```
start_llm_service, stop_llm_service, check_llm_status
```

确保使用相同的随机种子和控制常量：

)├── run_all_experiments.py # 功能模块 (支持直接调用，建议用 CLI)| `planner.tot` | Tree-of-Thoughts | SOTA | Yao
et

````python

from sage.benchmark.benchmark_agent.scripts.experiments.exp_utils import RANDOM_SEEDstart_llm_service(model="Qwen/Qwen2.5-7B-Instruct")al., 2023 |

import random

random.seed(RANDOM_SEED)```

````

└── ...

### 内存不足

## 控制常量

`````bash

# 使用更小的模型````#### Challenge 3: Tool Selection

./sage-agent-bench llm start --model "Qwen/Qwen2.5-1.5B-Instruct"

所有实验使用统一的控制常量，定义在 `exp_utils.py`：

# 或降低 GPU 内存使用率

# 编辑 llm_service.py 中的 gpu_memory_utilization 参数

`````

```python

## 相关文档

RANDOM_SEED = 42                                    # 随机种子### CLI 子命令| 方法 ID              | 名称            | 来源    | 参考文献           |

- [SAGE 开发指南](../../../../../../DEVELOPER.md)

- [Benchmark 架构](../../../../docs/benchmark_architecture.md)BENCHMARK_EMBEDDING_MODEL = "BAAI/bge-small-zh-v1.5"  # Embedding 模型

- [评测指标定义](../evaluation/metrics.py)

BENCHMARK_LLM_TEMPERATURE = 0.1                     # LLM 温度| -------------------- | --------------- | ------- | ------------------ |

```

| 命令 | 功能 | 示例 || `selector.keyword` | Keyword (BM25) | Classic | Robertson et al. |

## 输出目录

|------|------|------|| `selector.embedding` | Embedding | Common | BGE-M3 (BAAI) |

所有输出保存在 `.sage/benchmark/paper1/`：

| `eval` | 工具选择评测 | `sage-bench eval --dataset all` || `selector.hybrid` | Hybrid (RRF) | Common | -
|

````

.sage/benchmark/paper1/| `run` | 完整 Benchmark | `sage-bench run --quick` || `selector.gorilla`   | Gorilla         | SOTA    | Patil et al., 2023 |

├── section_5_2_main/           # 主要评测结果

│   ├── timing_results.json| `train` | 训练方法对比 | `sage-bench train --dry-run` || `selector.dfsdt`     | DFSDT (ToolLLM) | SOTA    | Qin et al., 2023   |

│   ├── planning_results.json

│   └── selection_results.json| `llm` | LLM 服务管理 | `sage-bench llm status` || `llm_direct`         | LLM Direct      | Common  | -                  |

├── section_5_3_analysis/       # 深度分析结果

│   ├── error_analysis.json| `list` | 列出可用资源 | `sage-bench list datasets` |

│   ├── scaling_analysis.json

│   ├── robustness_analysis.json| `interactive` | 交互式模式 | `sage-bench interactive` |______________________________________________________________________

│   └── ablation_results.json

├── section_5_4_generalization/ # 跨数据集结果

│   └── cross_dataset_results.json

├── section_5_5_training/       # 训练对比结果---### 📙 Paper 2: SAGE-Agent (原创方法)

│   └── training_comparison.json

├── figures/                    # 生成的图表 (PDF/PNG)

└── tables/                     # 生成的 LaTeX 表格

```## 📊 支持的数据集**核心创新**: 将 Agent 学习重新定义为 **在线流学习问题**，提出 Streaming Adaptive Learning 框架。



## 论文章节对应



| 章节 | 实验脚本 | 描述 || 数据集 | 来源 | 描述 |#### 架构概览

|------|----------|------|

| 5.2.1 | `exp_main_timing.py` | 工具调用时机评测 ||--------|------|------|

| 5.2.2 | `exp_main_planning.py` | 任务规划能力评测 |

| 5.2.3 | `exp_main_selection.py` | 工具选择准确率评测 || `sage` | Built-in | SAGE-Bench (1200 synthetic tools) |```

| 5.3.1 | `exp_analysis_error.py` | 错误类型分布分析 |

| 5.3.2 | `exp_analysis_scaling.py` | 工具数量扩展性分析 || `acebench` | HuggingFace | ToolACE from Team-ACE |┌─────────────────────────────────────────────────────────────┐

| 5.3.3 | `exp_analysis_robustness.py` | 鲁棒性分析 |

| 5.3.4 | `exp_analysis_ablation.py` | 消融实验 || `apibank` | External | API-Bank (Microsoft/Alibaba) |│                    SAGE-Agent Framework                      │

| 5.4 | `exp_cross_dataset.py` | 跨数据集泛化评测 |

| 5.5 | `exp_training_comparison.py` | 训练方法对比 || `toolalpaca` | External | ToolAlpaca (Microsoft) |│                                                             │



## 训练方法说明 (Section 5.5)| `bfcl` | External | Berkeley Function Calling Leaderboard |│  Query Stream ──→ [SSIS] ──→ [Priority Buffer] ──→ [Train]  │



| 方法 | 名称 | 描述 || `toolbench` | External | ToolBench (Tsinghua/OpenBMB) |│       │              │              │                │      │

|------|------|------|

| A | Baseline SFT | 基础监督微调 || `taskbench` | External | TaskBench (PKU) |│       │     Importance Score   Experience      Online Update │

| B1 | Random Coreset | 随机采样核心集 |

| B2 | Stratified Coreset | 分层采样核心集 || `metatool` | External | MetaTool (Tsinghua) |│       │     (U + D + F)        Replay               │      │

| B3 | Embedding Coreset | 嵌入聚类核心集 |

| B4 | Difficulty Coreset | 难度平衡核心集 |│       │                                              │      │

| C | Continual Learning | 持续学习 |

| D | Combined | 组合方法 (B3 + C) |查看所有数据集：│       └──────────────────────────────────────────────┘      │



## LLM 服务配置```bash│                                                             │



实验默认使用 vLLM 在端口 8901 (SagePorts.BENCHMARK_LLM)：sage-bench list datasets│  [Unified Multi-Task Network]                               │



```bash```│  ├── Timing Head    ←──┐                                    │

# 默认配置

Model: Qwen/Qwen2.5-7B-Instruct│  ├── Selection Head ←──┼── Cross-Task Attention             │

Port: 8901

GPU Memory: 90%---│  └── Planning Head  ←──┘                                    │



# 自定义模型└─────────────────────────────────────────────────────────────┘

./sage_bench llm start --model "meta-llama/Llama-3.1-8B-Instruct"

```## 🎯 支持的方法```



## 依赖关系



```### Challenge 3: Tool Selection#### 三大核心组件

exp_utils.py ← 所有实验脚本依赖

    ↑

figure_generator.py, table_generator.py ← 可视化工具

    ↑| 方法 | 来源 | 描述 || 组件                     | 全称                               | 功能                 | 创新点                                            |

llm_service.py ← LLM 管理

    ↑|------|------|------|| ------------------------ | ---------------------------------- | -------------------- | ------------------------------------------------- |

run_paper1_experiments.py ← 主运行器

    ↑| `keyword` | Classic | BM25 keyword matching || **SSIS**                 | Streaming Sample Importance Scorer | 实时评估样本训练价值 | 三维度评分 (Uncertainty + Diversity + Forgetting) |

sage_bench_cli.py ← CLI 实现

```| `embedding` | Common | Semantic embedding similarity || **Priority Replay**      | Importance-Weighted Replay Buffer  | 优先级经验回放       | Sum-tree O(log n) 采样 + IS 权重校正              |



## 故障排除| `hybrid` | Common | Keyword + Embedding fusion (RRF) || **Cross-Task Attention** | Unified Multi-Task Network         | 跨任务信息共享       | Timing ↔ Selection ↔ Planning 协同                |



### LLM 服务无法启动| `gorilla` | Berkeley | Retrieval + LLM reranking |



```bash| `dfsdt` | Tsinghua | Tree search (ToolLLM) |#### 消融实验配置

# 检查端口占用

lsof -i :8901| `llm_direct` | Baseline | Direct LLM prompting |



# 检查 GPU 状态| 方法 ID             | 名称                | SSIS | Replay | CrossTask | 说明               |

nvidia-smi

查看所有方法：| ------------------- | ------------------- | :--: | :----: | :-------: | ------------------ |

# 手动启动 vLLM

vllm serve Qwen/Qwen2.5-7B-Instruct --port 8901 --gpu-memory-utilization 0.9```bash| `SAGE_sft_baseline` | Baseline SFT        |  ❌  |   ❌   |    ❌     | 消融基准           |

````

sage-bench list methods| `SAGE_ssis_only` | +SSIS | ✅ | ❌ | ❌ | 加入样本重要性评估 |

### 实验结果不一致

\`\`\`| `SAGE_ssis_replay` | +SSIS +Replay | ✅ | ✅ | ❌ | 加入优先级回放 |

确保使用相同的随机种子和控制常量：

| `SAGE_full` | **Full SAGE-Agent** | ✅ | ✅ | ✅ | 完整方法 |

```python

from sage.benchmark.benchmark_agent.scripts.experiments.exp_utils import RANDOM_SEED---

import random

random.seed(RANDOM_SEED)#### 预期性能提升

```

## 📋 使用示例

### 内存不足

| Challenge | Baseline Best | SAGE-Agent | 提升 |

````bash

# 使用更小的模型### Paper 1: Benchmark 实验| ----------------------- | ------------- | ---------- | ---- |

./sage_bench llm start --model "Qwen/Qwen2.5-1.5B-Instruct"

| Tool Selection (Top-5)  | 82%           | **94%**    | +12% |

# 或降低 GPU 内存使用率

# 编辑 llm_service.py 中的 gpu_memory_utilization 参数```bash| Task Planning (Success) | 27%           | **85%**    | +58% |

````

# 1. 快速评测 (跳过 LLM 方法)| Timing Judgment (Acc) | 76% | **95%** | +19% |

## 相关文档

sage-bench run --quick --skip-llm

- [SAGE 开发指南](../../../../../../DEVELOPER.md)

- [Benchmark 架构](../../../../docs/benchmark_architecture.md)#### 效率提升

- [评测指标定义](../evaluation/metrics.py)

# 2. 跨数据集工具选择对比

sage-bench eval --dataset all --methods keyword,embedding,hybrid,gorilla --samples 100| 指标 | 传统 SFT
| SAGE-Agent | 提升 |

| \---------------------- | -------- | ---------- | ---------- |

# 3. 单个 Challenge 评测| 训练时间 | 1.0x | **0.4x** | 2.5x 更快 |

sage-bench run --challenge tool_selection| 数据利用 | 100% | **~35%** | 更高效 |

sage-bench run --challenge timing| 在线适应 (性能下降/轮) | -8% | **-0.5%** | 16x 更稳定 |

sage-bench run --challenge planning

````______________________________________________________________________



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
