# Pull Request: Control Plane Scheduler Benchmark Framework

## 📋 概述

本 PR 为 sageLLM Control Plane 的调度策略实现完整的 Benchmark 评测框架，支持 LLM 调度和混合调度（LLM +
Embedding）两种模式，并提供自动可视化和预定义实验功能。

## 🔗 关联

- **分支**: `feature/embedding_lmm_mixed_scheduler`
- **实现说明**: [README.md](./README.md)

______________________________________________________________________

## ✨ 新增功能

### 1. Benchmark 框架重构

- 将原有 `benchmark_control_plane/` 代码重构为 `llm_scheduler/` 子模块
- 抽取共享组件到 `common/` 目录（base_config, base_metrics, gpu_monitor, strategy_adapter）
- 保持 API 向后兼容（`BenchmarkConfig` 等别名）

### 2. 混合调度 Benchmark (`hybrid_scheduler/`)

新增支持 LLM + Embedding 混合负载的 Benchmark：

- `HybridBenchmarkConfig`: 支持 `llm_ratio`, `embedding_model`, `embedding_slo_deadline_ms` 等配置
- `HybridWorkloadGenerator`: 生成混合请求序列（LLM_CHAT / LLM_GENERATE / EMBEDDING）
- `HybridBenchmarkClient`: 同时支持 `/v1/chat/completions` 和 `/v1/embeddings`
- `HybridMetricsCollector`: 分别收集 LLM 和 Embedding 指标
- `HybridBenchmarkRunner`: 执行混合 Benchmark 并集成 GPU 监控

### 3. 可视化模块 (`visualization/`)

Benchmark 运行完成后自动生成图表和报告：

- **图表类型**:
  - 吞吐量: comparison, vs_rate
  - 延迟: distribution, percentiles, CDF
  - SLO: compliance, by_priority
  - GPU: utilization, memory
  - 混合: ratio_impact, type_breakdown, batch_efficiency
- **报告格式**: HTML（Jinja2 模板）、Markdown
- **Runner 集成**: `auto_visualize=True` 参数

### 4. 预定义实验 (`experiments/`)

| 实验                    | 描述                                     |
| ----------------------- | ---------------------------------------- |
| `throughput_exp.py`     | 扫描请求速率，找到最大吞吐量             |
| `latency_exp.py`        | 固定负载下分析延迟分布                   |
| `slo_compliance_exp.py` | 对比各策略的 SLO 达成率                  |
| `mixed_ratio_exp.py`    | 测试不同 LLM/Embedding 比例（仅 hybrid） |

### 5. CLI 工具 (`sage-cp-bench`)

```bash
# LLM Benchmark
sage-cp-bench run --mode llm --policy fifo --requests 100 --rate 10

# Hybrid Benchmark
sage-cp-bench run --mode hybrid --policy hybrid_slo --llm-ratio 0.7 --requests 100

# 策略对比
sage-cp-bench compare --mode hybrid --policies fifo,priority,hybrid_slo

# 运行实验
sage-cp-bench experiment --name throughput --policies fifo,priority

# 从结果生成可视化
sage-cp-bench visualize --input results.json --output ./charts
```

### 6. 测试数据目录

```
sage/data/sources/control_plane_benchmark/
├── data/
│   ├── llm_workloads/     # light, medium, heavy
│   ├── hybrid_workloads/  # balanced, llm_heavy, embed_heavy, burst
│   └── prompts/           # llm_prompts.jsonl, embed_texts.jsonl
├── dataloader.py          # 数据加载器
└── dataset.yaml           # 数据集配置
```

______________________________________________________________________

## 📁 文件变更

### 新增文件 (~36 个源文件)

```
packages/sage-benchmark/src/sage/benchmark/benchmark_control_plane/
├── common/
│   ├── __init__.py
│   ├── base_config.py          # 基础配置类
│   ├── base_metrics.py         # 基础指标类
│   ├── gpu_monitor.py          # GPU 监控（pynvml/nvidia-smi/mock）
│   └── strategy_adapter.py     # 策略适配器
├── llm_scheduler/              # 重构后的 LLM Benchmark
│   ├── __init__.py
│   ├── config.py
│   ├── workload.py
│   ├── client.py
│   ├── metrics.py
│   ├── runner.py
│   └── reporter.py
├── hybrid_scheduler/           # 新增混合 Benchmark
│   ├── __init__.py
│   ├── config.py
│   ├── workload.py
│   ├── client.py
│   ├── metrics.py
│   ├── runner.py
│   └── reporter.py
├── visualization/              # 新增可视化
│   ├── __init__.py
│   ├── charts.py
│   ├── report_generator.py
│   └── templates/
│       ├── benchmark_report.html
│       └── comparison_report.html
├── experiments/                # 新增预定义实验
│   ├── __init__.py
│   ├── base_experiment.py
│   ├── throughput_exp.py
│   ├── latency_exp.py
│   ├── slo_compliance_exp.py
│   └── mixed_ratio_exp.py
├── __init__.py                 # 更新：统一导出
├── cli.py                      # 更新：支持 hybrid 模式
├── README.md
├── DATA_PATHS.md
└── VISUALIZATION.md

packages/sage-benchmark/src/sage/data/sources/control_plane_benchmark/
├── __init__.py
├── dataloader.py
├── dataset.yaml
├── README.md
├── data/
│   ├── llm_workloads/*.jsonl
│   ├── hybrid_workloads/*.jsonl
│   └── prompts/*.jsonl
└── metadata/
```

### 修改文件

- `packages/sage-benchmark/src/sage/benchmark/benchmark_control_plane/__init__.py`
  - 添加 common、llm_scheduler、hybrid_scheduler、visualization、experiments 导出
  - 保持向后兼容的别名
- `packages/sage-benchmark/src/sage/benchmark/benchmark_control_plane/cli.py`
  - 支持 `--mode llm|hybrid`
  - 新增 `experiment`、`visualize` 命令

### 新增测试 (~3400 行)

```
packages/sage-benchmark/tests/benchmark_control_plane/
├── test_benchmark_control_plane.py  # 原有测试
├── test_cli.py                      # CLI 测试
├── test_common.py                   # 共享组件测试
├── test_experiments.py              # 实验测试
├── test_hybrid_scheduler.py         # 混合调度测试
├── test_llm_scheduler.py            # LLM 调度测试
└── test_visualization.py            # 可视化测试
```

______________________________________________________________________

## 🧪 测试

### 运行测试

```bash
# 运行所有 benchmark_control_plane 测试
cd /home/yjy/SAGE/packages/sage-benchmark
pytest tests/benchmark_control_plane/ -v

# 快速测试
pytest tests/benchmark_control_plane/ -v --tb=short
```

### 测试覆盖

- ✅ 配置验证（LLM/Hybrid）
- ✅ 负载生成（均匀/泊松/突发）
- ✅ 指标收集与聚合
- ✅ GPU 监控（含 Mock 模式）
- ✅ 策略适配器
- ✅ 图表生成
- ✅ 报告生成（HTML/Markdown）
- ✅ CLI 命令
- ✅ 预定义实验

______________________________________________________________________

## 📊 代码统计

| 类别     | 文件数 |  代码行数   |
| -------- | :----: | :---------: |
| 源代码   |   36   |   ~14,000   |
| 测试代码 |   7    |   ~3,400    |
| 文档     |   4    |   ~1,800    |
| 数据文件 |   9    |    ~600     |
| **总计** | **56** | **~19,800** |

______________________________________________________________________

## 📝 使用示例

### Python API

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
    embedding_model="BAAI/bge-m3",
    policies=["hybrid_slo"],
)
runner = HybridBenchmarkRunner(config)
result = await runner.run()  # 自动生成图表
```

### CLI 快速开始

```bash
# 1. 运行简单 LLM Benchmark
sage-cp-bench run --mode llm --policy fifo --requests 100 --rate 10

# 2. 运行混合 Benchmark
sage-cp-bench run --mode hybrid --policy hybrid_slo --llm-ratio 0.7 --requests 100

# 3. 对比多个策略
sage-cp-bench compare --mode llm --policies fifo,priority,slo_aware --requests 500

# 4. 运行吞吐量实验
sage-cp-bench experiment --name throughput --policies fifo,priority

# 5. 从已有结果生成可视化
sage-cp-bench visualize --input ./results/benchmark_result.json --output ./charts
```

______________________________________________________________________

## ✅ 检查清单

- [x] 代码通过 Ruff 格式检查
- [x] 代码通过 Mypy 类型检查（warning 模式）
- [x] 单元测试全部通过
- [x] 向后兼容（原有 API 不变）
- [x] 文档完整（README, DATA_PATHS, VISUALIZATION）
- [x] CLI 帮助信息完整

______________________________________________________________________

## 📎 附件

- [ROADMAP.md](./ROADMAP.md) - 完整开发路线图
- [TASKS.md](./TASKS.md) - 团队任务分解（6 个 Task，18 个子任务）
- [README.md](./README.md) - 实现总结

______________________________________________________________________

## 🔜 后续计划

1. **性能优化**: 大规模负载下的内存优化
1. **更多图表**: 添加 Plotly 交互式图表支持
1. **CI 集成**: 添加 benchmark 回归测试到 CI
1. **实验扩展**: 添加更多预定义实验（fairness, cost, tail latency）
