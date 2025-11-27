# SAGE-Bench 评测框架

> 支持 **15+ 种方法** 和 **6+ 外部数据集** 的 Agent 能力评测框架

本框架服务于两篇论文：

1. **Paper 1 (Benchmark)**: SAGE-Bench - 统一评测框架，对比现有 SOTA 方法
1. **Paper 2 (Method)**: SAGE-Agent - Streaming Adaptive Learning 框架

______________________________________________________________________

## 📁 脚本架构

### 统一入口 (推荐)

```bash
# 交互式运行
python sage_benchmark_cli.py

# 或直接指定实验
python sage_benchmark_cli.py --paper 1 --experiment tool_selection
python sage_benchmark_cli.py --paper 2 --experiment sage_agent_full
```

### 脚本对照表

| 脚本                              | Paper | 用途                                    |
| --------------------------------- | ----- | --------------------------------------- |
| `sage_benchmark_cli.py`           | 1 & 2 | **统一交互式入口**                      |
| `run_all_experiments.py`          | 1     | Benchmark: 三个 Challenge 全量评测      |
| `run_unified_eval.py`             | 1     | Benchmark: 跨数据集 Tool Selection 对比 |
| `run_full_training_comparison.py` | 2     | Method: SAGE-Agent 方法对比             |
| `run_acebench_comparison.py`      | 1     | Benchmark: 外部数据集验证               |

______________________________________________________________________

## 🎯 方法分类

### 📘 Paper 1: Benchmark (现有 SOTA 方法对比)

这些是 **文献中已有的方法**，用于建立 baseline 对比。 **Benchmark 论文不提出新方法，只做系统性评测。**

#### Challenge 1: Timing Judgment

| 方法 ID             | 名称       | 来源   | 描述                  |
| ------------------- | ---------- | ------ | --------------------- |
| `timing.rule_based` | Rule-based | Common | 关键词匹配 + 正则模式 |
| `timing.llm_based`  | LLM-based  | Common | 直接用 LLM 判断       |
| `timing.hybrid`     | Hybrid     | Common | Rule 初筛 + LLM 精判  |
| `timing.embedding`  | Embedding  | Common | 语义相似度判断        |

#### Challenge 2: Task Planning

| 方法 ID                | 名称             | 来源   | 参考文献         |
| ---------------------- | ---------------- | ------ | ---------------- |
| `planner.simple`       | Simple (Greedy)  | Common | -                |
| `planner.hierarchical` | Hierarchical     | Common | -                |
| `planner.llm_based`    | LLM-based        | Common | -                |
| `planner.react`        | ReAct            | SOTA   | Yao et al., 2023 |
| `planner.tot`          | Tree-of-Thoughts | SOTA   | Yao et al., 2023 |

#### Challenge 3: Tool Selection

| 方法 ID              | 名称            | 来源    | 参考文献           |
| -------------------- | --------------- | ------- | ------------------ |
| `selector.keyword`   | Keyword (BM25)  | Classic | Robertson et al.   |
| `selector.embedding` | Embedding       | Common  | BGE-M3 (BAAI)      |
| `selector.hybrid`    | Hybrid (RRF)    | Common  | -                  |
| `selector.gorilla`   | Gorilla         | SOTA    | Patil et al., 2023 |
| `selector.dfsdt`     | DFSDT (ToolLLM) | SOTA    | Qin et al., 2023   |
| `llm_direct`         | LLM Direct      | Common  | -                  |

______________________________________________________________________

### 📙 Paper 2: SAGE-Agent (原创方法)

**核心创新**: 将 Agent 学习重新定义为 **在线流学习问题**，提出 Streaming Adaptive Learning 框架。

#### 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                    SAGE-Agent Framework                      │
│                                                             │
│  Query Stream ──→ [SSIS] ──→ [Priority Buffer] ──→ [Train]  │
│       │              │              │                │      │
│       │     Importance Score   Experience      Online Update │
│       │     (U + D + F)        Replay               │      │
│       │                                              │      │
│       └──────────────────────────────────────────────┘      │
│                                                             │
│  [Unified Multi-Task Network]                               │
│  ├── Timing Head    ←──┐                                    │
│  ├── Selection Head ←──┼── Cross-Task Attention             │
│  └── Planning Head  ←──┘                                    │
└─────────────────────────────────────────────────────────────┘
```

#### 三大核心组件

| 组件                     | 全称                               | 功能                 | 创新点                                            |
| ------------------------ | ---------------------------------- | -------------------- | ------------------------------------------------- |
| **SSIS**                 | Streaming Sample Importance Scorer | 实时评估样本训练价值 | 三维度评分 (Uncertainty + Diversity + Forgetting) |
| **Priority Replay**      | Importance-Weighted Replay Buffer  | 优先级经验回放       | Sum-tree O(log n) 采样 + IS 权重校正              |
| **Cross-Task Attention** | Unified Multi-Task Network         | 跨任务信息共享       | Timing ↔ Selection ↔ Planning 协同                |

#### 消融实验配置

| 方法 ID             | 名称                | SSIS | Replay | CrossTask | 说明               |
| ------------------- | ------------------- | :--: | :----: | :-------: | ------------------ |
| `SAGE_sft_baseline` | Baseline SFT        |  ❌  |   ❌   |    ❌     | 消融基准           |
| `SAGE_ssis_only`    | +SSIS               |  ✅  |   ❌   |    ❌     | 加入样本重要性评估 |
| `SAGE_ssis_replay`  | +SSIS +Replay       |  ✅  |   ✅   |    ❌     | 加入优先级回放     |
| `SAGE_full`         | **Full SAGE-Agent** |  ✅  |   ✅   |    ✅     | 完整方法           |

#### 预期性能提升

| Challenge               | Baseline Best | SAGE-Agent | 提升 |
| ----------------------- | ------------- | ---------- | ---- |
| Tool Selection (Top-5)  | 82%           | **94%**    | +12% |
| Task Planning (Success) | 27%           | **85%**    | +58% |
| Timing Judgment (Acc)   | 76%           | **95%**    | +19% |

#### 效率提升

| 指标                   | 传统 SFT | SAGE-Agent | 提升       |
| ---------------------- | -------- | ---------- | ---------- |
| 训练时间               | 1.0x     | **0.4x**   | 2.5x 更快  |
| 数据利用               | 100%     | **~35%**   | 更高效     |
| 在线适应 (性能下降/轮) | -8%      | **-0.5%**  | 16x 更稳定 |

______________________________________________________________________

## 📚 数据集

### SAGE-Bench 原生数据

| 任务            | 样本数    | Train | Dev | Test |
| --------------- | --------- | ----- | --- | ---- |
| Tool Selection  | 600       | 420   | 90  | 90   |
| Task Planning   | 300       | 210   | 45  | 45   |
| Timing Judgment | 300       | 210   | 45  | 45   |
| **Total**       | **1,200** | 840   | 180 | 180  |

### 外部数据集集成

| 数据集     | 来源                   | 样本数  | 用途           |
| ---------- | ---------------------- | ------- | -------------- |
| ACEBench   | Team-ACE (HuggingFace) | 10,000+ | 跨数据集验证   |
| API-Bank   | Microsoft/Alibaba      | 2,138   | 多轮 API 对话  |
| ToolAlpaca | Microsoft              | 3,928   | 工具学习对话   |
| ToolBench  | Tsinghua/OpenBMB       | 16,000+ | 大规模工具检索 |

______________________________________________________________________

## 🚀 快速开始

### Paper 1: Benchmark 实验

```bash
# 1. 运行完整 Benchmark (三个 Challenge)
python run_all_experiments.py --quick  # 快速测试
python run_all_experiments.py          # 完整评测

# 2. 跨数据集验证
python run_unified_eval.py --datasets sage acebench --samples 100

# 3. 单独评测 Tool Selection
python sage_benchmark_cli.py --paper 1 --experiment tool_selection
```

### Paper 2: SAGE-Agent 实验

```bash
# 1. 完整消融实验
python run_full_training_comparison.py --quick  # 快速测试
python run_full_training_comparison.py          # A100 完整训练

# 2. 单独测试 SAGE-Agent Full
python sage_benchmark_cli.py --paper 2 --experiment sage_agent_full

# 3. 在线适应实验 (动态工具库)
python sage_benchmark_cli.py --paper 2 --experiment online_adaptation
```

______________________________________________________________________

## 📊 结果输出

所有实验结果保存在 `outputs/` 目录：

```
outputs/
├── paper1_benchmark/
│   ├── timing_results.json
│   ├── planning_results.json
│   ├── tool_selection_results.json
│   └── cross_dataset_validation.json
│
└── paper2_method/
    ├── ablation_study/
    │   ├── SAGE_sft_baseline.json
    │   ├── SAGE_ssis_only.json
    │   ├── SAGE_ssis_replay.json
    │   └── SAGE_full.json
    ├── efficiency_analysis.json
    └── online_adaptation.json
```

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
