# Agent Benchmark 数据路径说明

## 概述

Agent Benchmark 数据采用**两层架构**：

1. **源数据层 (Source Layer)**: 通过 `DataManager` 访问的原始数据
1. **运行数据层 (Runtime Layer)**: 脚本生成的实验特定数据

## 数据位置

### 1. 源数据 (通过 DataManager 访问)

位于 `packages/sage-benchmark/src/sage/data/sources/`:

```
sage/data/sources/
├── agent_benchmark/          # 评测数据 (1200+ 样本)
│   ├── splits/
│   │   ├── tool_selection.jsonl    # 工具选择 (600 样本)
│   │   ├── task_planning.jsonl     # 任务规划 (300 样本)
│   │   └── timing_judgment.jsonl   # 时机判断 (300 样本)
│   ├── metadata/
│   │   ├── schema.json
│   │   ├── rubric.json
│   │   └── difficulty_map.json
│   ├── dataloader.py                   # AgentBenchmarkDataLoader
│   ├── prepare_runtime_data.py         # 生成 tool_selection 运行时数据
│   ├── prepare_timing_data.py          # 生成 timing_judgment 运行时数据
│   └── prepare_planning_data.py        # 生成 task_planning 运行时数据
│
├── agent_tools/              # 工具目录 (1200+ 工具)
│   ├── data/
│   │   ├── tool_catalog.jsonl
│   │   ├── categories.json
│   │   └── stats.json
│   └── dataloader.py         # AgentToolsDataLoader
│
└── agent_sft/                # SFT 训练数据
    ├── data/
    │   └── sft_conversations.jsonl
    └── dataloader.py         # AgentSFTDataLoader
```

**访问方式**:

```python
from sage.data import DataManager

dm = DataManager.get_instance()
agent_eval = dm.get_by_usage("agent_eval")
profile = agent_eval.load_profile("quick_eval")

benchmark_loader = profile["benchmark"]
tools_loader = profile["tools"]

# 迭代样本
for sample in benchmark_loader.iter_split("tool_selection", "dev"):
    print(sample.instruction)
```

### 2. 运行数据 (脚本生成)

位于 `.sage/benchmark/data/`:

```
.sage/benchmark/data/
├── tool_selection/           # prepare_runtime_data.py 生成
│   ├── tool_selection.jsonl           # 基础数据
│   ├── tool_selection_100.jsonl       # 100 候选工具
│   ├── tool_selection_500.jsonl       # 500 候选工具
│   └── tool_selection_1000.jsonl      # 1000 候选工具
│
├── task_planning/            # prepare_planning_data.py 生成
│   └── task_planning.jsonl
│
└── timing_judgment/          # prepare_timing_data.py 生成
    ├── train.jsonl
    ├── dev.jsonl
    └── test.jsonl
```

**生成数据**:

```bash
# 方式 1: 直接运行 source 目录下的脚本
python sage/data/sources/agent_benchmark/prepare_runtime_data.py --create-splits
python sage/data/sources/agent_benchmark/prepare_timing_data.py
python sage/data/sources/agent_benchmark/prepare_planning_data.py

# 方式 2: 通过 scripts 目录的包装脚本
python scripts/evaluations/prepare_tool_selection_data.py --create-splits
```

### 3. 结果输出

```
.sage/benchmark/results/
├── tool_selection/
│   ├── metrics.json
│   └── comparison_chart.png
├── task_planning/
│   └── metrics.json
└── timing_judgment/
    └── metrics.json
```

## 数据流程图

```
┌─────────────────────────────────────────────────────────────────────┐
│                        数据准备流程                                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────────────┐                                            │
│  │ 源数据 (sage/data/)  │                                            │
│  │ - agent_benchmark    │                                            │
│  │ - agent_tools        │ ◄──── DataManager.get_by_usage("agent_eval")
│  │ - agent_sft          │                                            │
│  └──────────┬───────────┘                                            │
│             │                                                        │
│             │ prepare_xxx_data.py                                    │
│             ▼                                                        │
│  ┌──────────────────────┐                                            │
│  │ 运行数据 (.sage/)    │                                            │
│  │ - 不同候选池大小      │                                            │
│  │ - 扩展的测试用例      │ ◄──── run_xxx_benchmark.py --data-dir     │
│  └──────────┬───────────┘                                            │
│             │                                                        │
│             │ Experiments                                            │
│             ▼                                                        │
│  ┌──────────────────────┐                                            │
│  │ 结果 (.sage/results/)│                                            │
│  └──────────────────────┘                                            │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## 推荐工作流程

### 快速评测 (使用源数据)

```python
# 直接使用 DataManager，无需生成额外数据
from sage.benchmark.benchmark_agent import (
    ToolSelectionConfig,
    ToolSelectionExperiment,
    get_adapter_registry,
)
from sage.data import DataManager

dm = DataManager.get_instance()
registry = get_adapter_registry()

config = ToolSelectionConfig(
    profile="quick_eval",
    split="dev",
    selector="selector.keyword",
    max_samples=100,
)

exp = ToolSelectionExperiment(config, dm, registry)
exp.prepare()
result = exp.run()
```

### 完整评测 (使用生成数据)

```bash
# 1. 生成带有不同候选池大小的数据
python scripts/evaluations/prepare_tool_selection_data.py --create-splits

# 2. 运行完整评测
python scripts/evaluations/run_tool_selection_benchmark.py --max-samples 500

# 3. 或使用统一脚本
python scripts/run_all_experiments.py --eval-only --max-samples 500
```

## 数据格式对比

### 源数据格式 (agent_benchmark/splits/tool_selection.jsonl)

```json
{
  "sample_id": "ts_000001",
  "task_type": "tool_selection",
  "instruction": "Help plan a trip to Tokyo",
  "context": "User has budget 2k USD...",
  "candidate_tools": ["travel_search_012", "weather_query_001"],
  "ground_truth": {
    "top_k": ["weather_query_001"],
    "explanation": "Need weather info"
  },
  "metadata": {
    "difficulty": "medium",
    "tags": ["travel"],
    "created_by": "generator"
  },
  "split": "dev"
}
```

### 运行数据格式 (.sage/benchmark/data/tool_selection/\*.jsonl)

```json
{
  "sample_id": "ts_gen_000001",
  "instruction": "Query weather for a location",
  "candidate_tools": ["weather_001", "weather_002", ..., "tool_100"],
  "ground_truth": {
    "top_k": ["weather_001"],
    "explanation": "Best match"
  },
  "split": "test",
  "metadata": {
    "num_candidates": 100,
    "generated_by": "prepare_tool_selection_data.py"
  }
}
```

## 注意事项

1. **优先使用 DataManager**: 对于标准评测，应通过 DataManager 加载源数据
1. **运行数据用于扩展实验**: `.sage/` 下的数据用于特定实验（如不同候选池大小）
1. **保持格式一致**: 生成数据时应与源数据格式保持一致
1. **不要直接修改源数据**: 源数据应保持只读，修改请通过 PR
1. **Git 忽略运行数据**: `.sage/` 目录已在 `.gitignore` 中

## 相关文件

- 数据加载: `sage/data/sources/agent_benchmark/dataloader.py`
- 数据准备: `sage/benchmark/benchmark_agent/scripts/evaluations/prepare_*.py`
- 评测脚本: `sage/benchmark/benchmark_agent/scripts/evaluations/run_*.py`
- 统一入口: `sage/benchmark/benchmark_agent/scripts/run_all_experiments.py`
- Usage 配置: `sage/data/usages/agent_eval/`
