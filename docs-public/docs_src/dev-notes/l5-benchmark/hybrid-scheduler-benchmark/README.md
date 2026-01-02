# Control Plane Scheduler Benchmark Implementation

> **分支**: `feature/embedding_lmm_mixed_scheduler`\
> **完成时间**: 2025年11月28日\
> **状态**: ✅ 已完成

______________________________________________________________________

## 概述

本次任务为 sageLLM Control Plane 调度策略实现了完整的 Benchmark 评测框架，支持：

1. **LLM 调度 Benchmark** (`llm_scheduler/`): 评测 FIFO、Priority、SLO-Aware 等策略
1. **混合调度 Benchmark** (`hybrid_scheduler/`): 评测 LLM + Embedding 混合负载调度
1. **自动可视化** (`visualization/`): Benchmark 运行后自动生成图表和报告
1. **预定义实验** (`experiments/`): 标准化的 Throughput、Latency、SLO、混合比例实验
1. **CLI 工具** (`cli.py`): 统一的命令行接口 `sage-cp-bench`

______________________________________________________________________

## 实现清单

### 模块结构

```
packages/sage-benchmark/src/sage/benchmark/benchmark_control_plane/
├── __init__.py                    # 统一导出 (向后兼容)
├── README.md                      # 模块文档 (546 行)
├── DATA_PATHS.md                  # 数据路径文档
├── VISUALIZATION.md               # 可视化指南
├── cli.py                         # CLI 入口 (1278 行)
│
├── common/                        # 共享组件
│   ├── __init__.py
│   ├── base_config.py             # 基础配置类 (221 行)
│   ├── base_metrics.py            # 基础指标类 (368 行)
│   ├── gpu_monitor.py             # GPU 监控 (526 行)
│   └── strategy_adapter.py        # 策略适配器 (370 行)
│
├── llm_scheduler/                 # LLM 调度 Benchmark
│   ├── __init__.py
│   ├── config.py                  # LLM 配置
│   ├── workload.py                # LLM 负载生成
│   ├── client.py                  # HTTP 客户端
│   ├── metrics.py                 # 指标收集
│   ├── runner.py                  # 执行器
│   └── reporter.py                # 报告输出
│
├── hybrid_scheduler/              # 混合调度 Benchmark
│   ├── __init__.py
│   ├── config.py                  # Hybrid 配置
│   ├── workload.py                # 混合负载生成
│   ├── client.py                  # 支持 chat/embed 的客户端
│   ├── metrics.py                 # 混合指标收集
│   ├── runner.py                  # 混合执行器
│   └── reporter.py                # 混合报告
│
├── visualization/                 # 可视化模块
│   ├── __init__.py
│   ├── charts.py                  # 图表生成 (1113 行)
│   ├── report_generator.py        # 报告生成器
│   └── templates/                 # HTML 模板
│       ├── benchmark_report.html
│       └── comparison_report.html
│
└── experiments/                   # 预定义实验
    ├── __init__.py
    ├── base_experiment.py         # 实验基类 (333 行)
    ├── throughput_exp.py          # 吞吐量实验
    ├── latency_exp.py             # 延迟分布实验
    ├── slo_compliance_exp.py      # SLO 达成率实验 (392 行)
    └── mixed_ratio_exp.py         # 混合比例实验
```

### 数据目录

```
packages/sage-benchmark/src/sage/data/sources/control_plane_benchmark/
├── __init__.py
├── README.md
├── dataloader.py                  # 数据加载器
├── dataset.yaml                   # 数据集配置
├── metadata/                      # 元数据
└── data/
    ├── llm_workloads/
    │   ├── light.jsonl            # 轻量负载 (100 req, 10 req/s)
    │   ├── medium.jsonl           # 中等负载 (1000 req, 100 req/s)
    │   └── heavy.jsonl            # 重负载 (5000 req, 500 req/s)
    ├── hybrid_workloads/
    │   ├── balanced.jsonl         # 50% LLM, 50% Embedding
    │   ├── llm_heavy.jsonl        # 80% LLM, 20% Embedding
    │   ├── embed_heavy.jsonl      # 20% LLM, 80% Embedding
    │   └── burst.jsonl            # 突发负载模式
    └── prompts/
        ├── llm_prompts.jsonl      # LLM 测试 prompts
        └── embed_texts.jsonl      # Embedding 测试文本
```

### 测试覆盖

```
packages/sage-benchmark/tests/benchmark_control_plane/
├── __init__.py
├── test_benchmark_control_plane.py  # 原有测试 (480 行)
├── test_cli.py                      # CLI 测试
├── test_common.py                   # 共享组件测试 (392 行)
├── test_experiments.py              # 实验测试
├── test_hybrid_scheduler.py         # 混合调度测试
├── test_llm_scheduler.py            # LLM 调度测试
└── test_visualization.py            # 可视化测试 (595 行)

总测试代码: ~3438 行
```

______________________________________________________________________

## 核心功能

### 1. CLI 命令 (`sage-cp-bench`)

```bash
# LLM Benchmark
sage-cp-bench run --mode llm --policy fifo --requests 100 --rate 10

# Hybrid Benchmark
sage-cp-bench run --mode hybrid --policy hybrid_slo --llm-ratio 0.7 --requests 100

# 策略对比
sage-cp-bench compare --mode hybrid --policies fifo,priority,hybrid_slo

# 运行预定义实验
sage-cp-bench experiment --name throughput --policies fifo,priority

# 从结果生成可视化
sage-cp-bench visualize --input results.json --output ./charts
```

### 2. Python API

```python
# LLM Benchmark
from sage.benchmark.benchmark_control_plane import (
    LLMBenchmarkConfig,
    LLMBenchmarkRunner,
)

config = LLMBenchmarkConfig(
    control_plane_url="http://localhost:8080",
    num_requests=1000,
    request_rate=100.0,
    policies=["fifo", "priority", "slo_aware"],
)
runner = LLMBenchmarkRunner(config)
result = await runner.run()

# Hybrid Benchmark
from sage.benchmark.benchmark_control_plane.hybrid_scheduler import (
    HybridBenchmarkConfig,
    HybridBenchmarkRunner,
)

config = HybridBenchmarkConfig(
    control_plane_url="http://localhost:8080",
    num_requests=500,
    llm_ratio=0.7,
    policies=["hybrid_slo"],
)
runner = HybridBenchmarkRunner(config)
result = await runner.run()
```

### 3. 自动可视化

```python
from sage.benchmark.benchmark_control_plane.visualization import (
    BenchmarkCharts,
    ReportGenerator,
)

# 生成图表
charts = BenchmarkCharts(output_dir="./charts")
charts.generate_all_charts(policy_metrics=result.metrics)

# 生成报告
report = ReportGenerator(result=result, charts_dir="./charts")
report.generate_html_report("./benchmark_report.html")
report.generate_markdown_report("./benchmark_report.md")
```

### 4. 预定义实验

| 实验          | 说明                         |
| ------------- | ---------------------------- |
| `throughput`  | 扫描请求速率，找到最大吞吐量 |
| `latency`     | 固定负载下分析延迟分布       |
| `slo`         | 对比各策略的 SLO 达成率      |
| `mixed_ratio` | 测试不同 LLM/Embedding 比例  |

______________________________________________________________________

## 支持的调度策略

通过 `StrategyAdapter` 对接 `control_plane/strategies/`:

| 策略             | 类名                     | 支持 LLM | 支持 Embedding | 描述       |
| ---------------- | ------------------------ | :------: | :------------: | ---------- |
| `fifo`           | `FIFOPolicy`             |    ✅    |       ❌       | 先进先出   |
| `priority`       | `PriorityPolicy`         |    ✅    |       ❌       | 优先级调度 |
| `slo_aware`      | `SLOAwarePolicy`         |    ✅    |       ❌       | SLO 感知   |
| `adaptive`       | `AdaptivePolicy`         |    ✅    |       ❌       | 自适应调度 |
| `aegaeon`        | `AegaeonPolicy`          |    ✅    |       ❌       | 高级优化   |
| `cost_optimized` | `CostOptimizedPolicy`    |    ✅    |       ❌       | 成本优化   |
| `hybrid_slo`     | `HybridSchedulingPolicy` |    ✅    |       ✅       | 混合调度   |

______________________________________________________________________

## 图表类型

### 吞吐量图表

- `plot_throughput_comparison()` - 策略对比柱状图
- `plot_throughput_vs_rate()` - 吞吐量随请求速率变化曲线

### 延迟图表

- `plot_latency_distribution()` - 延迟分布直方图
- `plot_latency_percentiles()` - p50/p90/p95/p99 对比
- `plot_latency_cdf()` - 累积分布函数

### SLO 图表

- `plot_slo_compliance()` - SLO 达成率对比
- `plot_slo_by_priority()` - 按优先级分类的 SLO

### 资源图表

- `plot_gpu_utilization()` - GPU 利用率时序图
- `plot_gpu_memory()` - GPU 显存使用

### 混合调度图表

- `plot_mixed_ratio_impact()` - LLM/Embedding 比例影响
- `plot_type_breakdown()` - 请求类型分布
- `plot_embedding_batch_efficiency()` - Embedding 批处理效率

______________________________________________________________________

## 代码统计

| 类别     | 文件数 |  代码行数   |
| -------- | :----: | :---------: |
| 源代码   |   36   |   ~14,000   |
| 测试代码 |   7    |   ~3,400    |
| 文档     |   4    |   ~1,800    |
| **总计** | **47** | **~19,200** |

______________________________________________________________________

## 任务书对应

参考 [TASKS.md](./TASKS.md) 中的任务分解:

| Task                      | 状态 | 内容                                                |
| ------------------------- | :--: | --------------------------------------------------- |
| T1: 目录重构与共享组件    |  ✅  | `llm_scheduler/`, `common/`, 可视化骨架             |
| T2: 数据层实现            |  ✅  | `data/sources/control_plane_benchmark/`, dataloader |
| T3: hybrid_scheduler 核心 |  ✅  | config, workload, client, metrics, runner, reporter |
| T4: 可视化模块            |  ✅  | charts.py, report_generator.py, Runner 集成         |
| T5: 预定义实验与 CLI      |  ✅  | 5 个实验模块, CLI 实现                              |
| T6: 测试与文档            |  ✅  | 单元测试, README, 可视化文档                        |

______________________________________________________________________

## 参考文档

- [模块 README](../../../../../packages/sage-benchmark/src/sage/benchmark/benchmark_control_plane/README.md)
  \- CLI 参考和 API 文档
- [VISUALIZATION.md](../../../../../packages/sage-benchmark/src/sage/benchmark/benchmark_control_plane/VISUALIZATION.md)
  \- 图表和报告指南
- [DATA_PATHS.md](../../../../../packages/sage-benchmark/src/sage/benchmark/benchmark_control_plane/DATA_PATHS.md)
  \- 数据目录说明
