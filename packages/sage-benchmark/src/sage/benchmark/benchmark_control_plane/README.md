# sageLLM Control Plane Benchmark

This module provides comprehensive benchmarking tools for evaluating different scheduling policies
in sageLLM's Control Plane. It supports both **LLM-only** and **Hybrid (LLM + Embedding)**
workloads.

## Overview

The benchmark measures key performance metrics across various scheduling strategies:

- **Throughput**: Requests per second and tokens per second
- **Latency**: End-to-end latency, Time to First Token (TTFT), Time Between Tokens (TBT)
- **SLO Compliance**: Percentage of requests meeting their SLO deadlines
- **Error Rates**: Failed requests and timeout rates
- **Resource Utilization**: GPU memory and compute utilization (optional)

## Architecture

```
                                 ┌─────────────────────────────────────────────┐
                                 │           Control Plane                     │
┌─────────────┐      HTTP        │  ┌─────────────────────────────────────┐   │
│  Benchmark  │ ───────────────► │  │     Scheduler (Policy: X)           │   │
│   Client    │                  │  │  ┌───────────┬───────────────────┐  │   │
│             │                  │  │  │ LLM Queue │ Embedding Queue   │  │   │
└─────────────┘                  │  │  └───────────┴───────────────────┘  │   │
     │                           │  └─────────────────────────────────────┘   │
     │                           └──────────────────┬──────────────────────────┘
     │                                              │
     │                           ┌──────────────────┴──────────────────────┐
     │                           │                                         │
     ▼                           ▼                                         ▼
┌─────────────┐           ┌──────────────┐                         ┌──────────────┐
│   Metrics   │           │ vLLM Inst 1  │                         │  Embedding   │
│  Collector  │           │ (Qwen-7B)    │                         │   Server     │
└─────────────┘           ├──────────────┤                         │  (BGE-M3)    │
                          │ vLLM Inst 2  │                         └──────────────┘
                          │ (Llama-13B)  │
                          └──────────────┘
```

## Quick Start

### Installation

```bash
# Install sage-benchmark package
pip install isage-benchmark

# Or for development:
pip install -e "packages/sage-benchmark[dev]"

# CLI dependencies
pip install typer aiohttp pyyaml

# Visualization dependencies (optional)
pip install matplotlib jinja2
```

### Running Your First Benchmark

```bash
# 1. Run a simple LLM benchmark
sage-cp-bench run --mode llm --policy fifo --requests 100 --rate 10

# 2. Run a hybrid (LLM + Embedding) benchmark
sage-cp-bench run --mode hybrid --policy hybrid_slo --llm-ratio 0.7 --requests 100

# 3. Compare multiple policies
sage-cp-bench compare --mode llm --policies fifo,priority,slo_aware --requests 500

# 4. Run a predefined experiment
sage-cp-bench experiment --name throughput --policies fifo,priority
```

## CLI Reference

### Commands Overview

| Command      | Description                                  |
| ------------ | -------------------------------------------- |
| `run`        | Run benchmark for a single scheduling policy |
| `compare`    | Compare multiple scheduling policies         |
| `sweep`      | Sweep across multiple request rates          |
| `experiment` | Run predefined experiments                   |
| `visualize`  | Generate charts from existing results        |
| `config`     | Show/save example configuration              |
| `validate`   | Validate a configuration file                |

### `run` Command

```bash
sage-cp-bench run [OPTIONS]

Options:
  --mode            -m   [llm|hybrid]  Benchmark mode (default: llm)
  --control-plane   -c   TEXT          Control Plane URL (default: http://localhost:8080)
  --policy          -p   TEXT          Scheduling policy (default: fifo)
  --requests        -n   INTEGER       Number of requests (default: 100)
  --rate            -r   FLOAT         Request rate req/s (default: 10.0)
  --llm-ratio            FLOAT         LLM ratio for hybrid mode (default: 0.7)
  --output          -o   TEXT          Output directory (default: ./benchmark_results)
  --warmup          -w   INTEGER       Warmup requests (default: 10)
  --timeout         -t   FLOAT         Request timeout seconds (default: 60.0)
  --no-visualize                       Disable auto visualization
  --config               TEXT          Load config from YAML/JSON file
  --quiet           -q                 Suppress progress output
```

**Examples:**

```bash
# LLM-only benchmark
sage-cp-bench run --mode llm --policy fifo --requests 100 --rate 10

# Hybrid benchmark with 70% LLM, 30% Embedding
sage-cp-bench run --mode hybrid --policy hybrid_slo --llm-ratio 0.7 --requests 100

# Load configuration from file
sage-cp-bench run --config benchmark_config.yaml
```

### `compare` Command

```bash
sage-cp-bench compare [OPTIONS]

Options:
  --mode            -m   [llm|hybrid]  Benchmark mode (default: llm)
  --policies        -p   TEXT          Comma-separated policy list (default: fifo,priority,slo_aware)
  --requests        -n   INTEGER       Requests per policy (default: 100)
  --rate            -r   FLOAT         Request rate (default: 10.0)
  --llm-ratio            FLOAT         LLM ratio for hybrid mode (default: 0.7)
  --output          -o   TEXT          Output directory
  --no-visualize                       Disable comparison charts
```

**Examples:**

```bash
# Compare LLM scheduling policies
sage-cp-bench compare --mode llm --policies fifo,priority,slo_aware

# Compare hybrid scheduling policies
sage-cp-bench compare --mode hybrid --policies fifo,hybrid_slo --llm-ratio 0.7
```

### `sweep` Command

```bash
sage-cp-bench sweep [OPTIONS]

Options:
  --mode            -m   [llm|hybrid]  Benchmark mode (default: llm)
  --policy          -p   TEXT          Policy to test (default: fifo)
  --rates                TEXT          Comma-separated rates (default: 10,50,100,200)
  --requests        -n   INTEGER       Requests per rate (default: 100)
  --output          -o   TEXT          Output directory
```

**Examples:**

```bash
# Sweep request rates for LLM benchmark
sage-cp-bench sweep --mode llm --policy fifo --rates 10,50,100,200

# Sweep rates for hybrid benchmark
sage-cp-bench sweep --mode hybrid --policy hybrid_slo --rates 10,50,100
```

### `experiment` Command

```bash
sage-cp-bench experiment [OPTIONS]

Options:
  --name            -e   TEXT          Experiment: throughput|latency|slo|mixed_ratio [required]
  --control-plane   -c   TEXT          Control Plane URL
  --requests        -n   INTEGER       Requests per test (default: 500)
  --rate            -r   INTEGER       Request rate (default: 100)
  --llm-ratio            FLOAT         LLM ratio (default: 0.5)
  --policies        -p   TEXT          Policies to test (default: fifo,priority,slo_aware)
  --output          -o   TEXT          Output directory
  --no-visualize                       Skip visualization
```

**Available Experiments:**

| Experiment    | Description                                   |
| ------------- | --------------------------------------------- |
| `throughput`  | Sweep request rates to find max throughput    |
| `latency`     | Analyze latency distribution under fixed load |
| `slo`         | Compare SLO compliance across policies        |
| `mixed_ratio` | Test different LLM/Embedding ratios           |

**Examples:**

```bash
# Run throughput experiment
sage-cp-bench experiment --name throughput --policies fifo,priority

# Run latency analysis
sage-cp-bench experiment --name latency --rate 100 --requests 1000

# Run SLO compliance comparison
sage-cp-bench experiment --name slo --policies fifo,slo_aware

# Run mixed ratio sweep (hybrid only)
sage-cp-bench experiment --name mixed_ratio --rate 100
```

### `visualize` Command

```bash
sage-cp-bench visualize [OPTIONS]

Options:
  --input           -i   TEXT          Results JSON file [required]
  --output          -o   TEXT          Output directory (default: ./visualizations)
  --format          -f   TEXT          Output format: charts|html|markdown|all (default: all)
```

**Examples:**

```bash
# Generate all visualizations
sage-cp-bench visualize --input results.json --output ./charts

# Generate only HTML report
sage-cp-bench visualize --input results.json --format html
```

### `config` and `validate` Commands

```bash
# Show example LLM configuration
sage-cp-bench config --mode llm

# Show and save hybrid configuration
sage-cp-bench config --mode hybrid --output config.yaml

# Validate configuration file
sage-cp-bench validate config.json --mode llm
sage-cp-bench validate config.yaml --mode hybrid
```

## Python API

### LLM-only Benchmark

```python
import asyncio
from sage.benchmark.benchmark_control_plane import (
    BenchmarkConfig,
    BenchmarkRunner,
    BenchmarkReporter,
)

# Configure benchmark
config = BenchmarkConfig(
    control_plane_url="http://localhost:8080",
    policies=["fifo", "priority", "slo_aware"],
    num_requests=1000,
    request_rate=100.0,
)

# Run benchmark
runner = BenchmarkRunner(config)
result = asyncio.run(runner.run())

# Generate report
reporter = BenchmarkReporter(result)
reporter.print_summary()
reporter.save_all("./benchmark_results")
```

### Hybrid Benchmark (LLM + Embedding)

```python
import asyncio
from sage.benchmark.benchmark_control_plane.hybrid_scheduler import (
    HybridBenchmarkConfig,
    HybridBenchmarkRunner,
    HybridBenchmarkReporter,
)

# Configure hybrid benchmark
config = HybridBenchmarkConfig(
    control_plane_url="http://localhost:8080",
    num_requests=1000,
    request_rate=100.0,
    llm_ratio=0.7,              # 70% LLM, 30% Embedding
    embedding_ratio=0.3,
    policies=["fifo", "hybrid_slo"],
)

# Run benchmark
runner = HybridBenchmarkRunner(config)
result = asyncio.run(runner.run())

# Generate report
reporter = HybridBenchmarkReporter(result)
reporter.print_summary()
reporter.save_json("./results/hybrid_benchmark.json")
```

### Running Predefined Experiments

```python
import asyncio
from sage.benchmark.benchmark_control_plane.experiments import (
    ThroughputExperiment,
    LatencyExperiment,
    SLOComplianceExperiment,
    MixedRatioExperiment,
)
from sage.benchmark.benchmark_control_plane.common.base_config import SchedulingPolicy

# Throughput experiment
exp = ThroughputExperiment(
    name="throughput_sweep",
    control_plane_url="http://localhost:8080",
    policies=[SchedulingPolicy.FIFO, SchedulingPolicy.PRIORITY],
    request_rates=[50, 100, 200, 500],
)
result = asyncio.run(exp.run_full())  # Includes visualization
print(f"Best policy: {result.summary['best_policy']}")

# Latency experiment
exp = LatencyExperiment(
    name="latency_analysis",
    control_plane_url="http://localhost:8080",
    request_rate=100,
    num_requests=1000,
)
result = asyncio.run(exp.run_full())

# Mixed ratio experiment (hybrid)
exp = MixedRatioExperiment(
    name="ratio_sweep",
    control_plane_url="http://localhost:8080",
    llm_ratios=[0.0, 0.25, 0.5, 0.75, 1.0],
)
result = asyncio.run(exp.run_full())
```

### Generating Visualizations

```python
from pathlib import Path
from sage.benchmark.benchmark_control_plane.visualization import (
    BenchmarkCharts,
    ReportGenerator,
)

# Generate charts
charts = BenchmarkCharts(output_dir=Path("./charts"))
charts.plot_throughput_comparison(policy_metrics)
charts.plot_latency_distribution(latency_data)
charts.plot_slo_compliance(slo_data)

# Generate reports
report_gen = ReportGenerator(result=benchmark_result, charts_dir=Path("./charts"))
report_gen.generate_html_report(Path("./report.html"))
report_gen.generate_markdown_report(Path("./report.md"))
```

## Supported Scheduling Policies

| Policy           | Mode   | Description                                     |
| ---------------- | ------ | ----------------------------------------------- |
| `fifo`           | Both   | First-In-First-Out scheduling                   |
| `priority`       | Both   | Priority-based scheduling                       |
| `slo_aware`      | Both   | SLO-deadline aware scheduling                   |
| `cost_optimized` | LLM    | Cost-optimized scheduling                       |
| `adaptive`       | LLM    | Adaptive scheduling based on system state       |
| `aegaeon`        | LLM    | Advanced scheduling with multiple optimizations |
| `hybrid`         | Hybrid | Hybrid LLM/Embedding scheduling                 |
| `hybrid_slo`     | Hybrid | Hybrid with SLO awareness                       |

## Configuration Options

### LLM Benchmark Configuration

| Option                  | Description                        | Default                             |
| ----------------------- | ---------------------------------- | ----------------------------------- |
| `control_plane_url`     | Control Plane HTTP address         | `http://localhost:8080`             |
| `policies`              | List of policies to benchmark      | `["fifo", "priority", "slo_aware"]` |
| `num_requests`          | Total requests per policy          | `100`                               |
| `request_rate`          | Target request rate (req/s)        | `10.0`                              |
| `arrival_pattern`       | Request arrival pattern            | `poisson`                           |
| `model_distribution`    | Request distribution across models | `{"default": 1.0}`                  |
| `priority_distribution` | Request priority distribution      | `{"NORMAL": 1.0}`                   |
| `timeout_seconds`       | Request timeout                    | `60.0`                              |
| `warmup_requests`       | Warmup requests before measurement | `10`                                |

### Hybrid Benchmark Configuration

| Option                      | Description                       | Default       |
| --------------------------- | --------------------------------- | ------------- |
| `llm_ratio`                 | Ratio of LLM requests (0.0-1.0)   | `0.5`         |
| `embedding_ratio`           | Ratio of Embedding requests       | `0.5`         |
| `embedding_model`           | Embedding model name              | `BAAI/bge-m3` |
| `embedding_batch_size`      | Batch size for embedding requests | `32`          |
| `llm_slo_deadline_ms`       | SLO deadline for LLM requests     | `5000`        |
| `embedding_slo_deadline_ms` | SLO deadline for embedding        | `500`         |

## Output Formats

### Terminal Output

```
============================================================
       sageLLM Hybrid Scheduling Benchmark Report
============================================================
Config: 1000 requests @ 100 req/s | LLM: 70% | Embedding: 30%
------------------------------------------------------------

| Policy     | Throughput | LLM Avg | Emb Avg | LLM SLO | Emb SLO | Errors |
|------------|------------|---------|---------|---------|---------|--------|
| fifo       | 95.2 req/s | 156 ms  | 23 ms   | 71.2%   | 92.1%   | 0.3%   |
| hybrid_slo | 98.5 req/s | 132 ms  | 18 ms   | 93.7%   | 98.2%   | 0.1%   |

Best Throughput: hybrid_slo (98.5 req/s)
Best LLM SLO: hybrid_slo (93.7%)
Best Embedding SLO: hybrid_slo (98.2%)
```

### JSON Report

Full results saved to `report_<timestamp>.json` including:

- Configuration summary
- Per-policy metrics
- Raw request results
- Summary statistics

### HTML Report

Interactive HTML report with embedded charts and tables.

### Markdown Report

Markdown format suitable for documentation and GitHub.

## Module Structure

```
benchmark_control_plane/
├── __init__.py              # Module exports (backward compatible)
├── cli.py                   # CLI interface (sage-cp-bench)
├── config.py                # Legacy config (→ llm_scheduler)
├── workload.py              # Legacy workload (→ llm_scheduler)
├── client.py                # Legacy client (→ llm_scheduler)
├── metrics.py               # Legacy metrics (→ llm_scheduler)
├── runner.py                # Legacy runner (→ llm_scheduler)
├── reporter.py              # Legacy reporter (→ llm_scheduler)
├── README.md                # This file
│
├── common/                  # Shared components
│   ├── __init__.py
│   ├── base_config.py       # Base configuration classes
│   ├── base_metrics.py      # Base metrics classes
│   ├── gpu_monitor.py       # GPU resource monitoring
│   └── strategy_adapter.py  # Scheduling strategy adapter
│
├── llm_scheduler/           # LLM-only benchmark
│   ├── __init__.py
│   ├── config.py            # LLM benchmark config
│   ├── workload.py          # LLM workload generation
│   ├── client.py            # LLM HTTP client
│   ├── metrics.py           # LLM metrics collection
│   ├── runner.py            # LLM benchmark runner
│   └── reporter.py          # LLM result reporting
│
├── hybrid_scheduler/        # Hybrid LLM+Embedding benchmark
│   ├── __init__.py
│   ├── config.py            # Hybrid benchmark config
│   ├── workload.py          # Hybrid workload generation
│   ├── client.py            # Hybrid HTTP client
│   ├── metrics.py           # Hybrid metrics collection
│   ├── runner.py            # Hybrid benchmark runner
│   └── reporter.py          # Hybrid result reporting
│
├── visualization/           # Charts and reports
│   ├── __init__.py
│   ├── charts.py            # Matplotlib chart generation
│   ├── report_generator.py  # HTML/Markdown reports
│   └── templates/           # Report templates
│       ├── benchmark_report.html
│       └── comparison_report.html
│
└── experiments/             # Predefined experiments
    ├── __init__.py
    ├── base_experiment.py   # Experiment base class
    ├── throughput_exp.py    # Throughput sweep
    ├── latency_exp.py       # Latency analysis
    ├── slo_compliance_exp.py # SLO compliance
    └── mixed_ratio_exp.py   # LLM/Embedding ratio sweep
```

## Related Documentation

- [DATA_PATHS.md](./DATA_PATHS.md) - Data directory structure and formats
- [VISUALIZATION.md](./VISUALIZATION.md) - Chart types and report formats
- [examples/run_llm_benchmark.py](../../../../examples/benchmark/run_llm_benchmark.py) - LLM
  benchmark example
- [examples/run_hybrid_benchmark.py](../../../../examples/benchmark/run_hybrid_benchmark.py) -
  Hybrid benchmark example

## Control Plane Integration

### Required API Endpoints

| Endpoint               | Method | Description                          |
| ---------------------- | ------ | ------------------------------------ |
| `/health`              | GET    | Health check                         |
| `/v1/chat/completions` | POST   | OpenAI-compatible LLM endpoint       |
| `/v1/embeddings`       | POST   | OpenAI-compatible embedding endpoint |
| `/admin/set_policy`    | POST   | Switch scheduling policy             |
| `/admin/metrics`       | GET    | Get Control Plane metrics            |

### Request Headers

- `X-Request-ID`: Unique request identifier
- `X-Request-Priority`: Request priority (HIGH, NORMAL, LOW)
- `X-SLO-Deadline-Ms`: SLO deadline in milliseconds
- `X-Request-Type`: Request type (llm_chat, llm_generate, embedding)

## Troubleshooting

### Common Issues

1. **Connection refused**: Ensure Control Plane is running at the specified URL
1. **Timeout errors**: Increase `--timeout` or reduce `--rate`
1. **No visualization**: Install matplotlib: `pip install matplotlib`
1. **YAML config error**: Install pyyaml: `pip install pyyaml`

### Debug Mode

```bash
# Enable verbose logging
export SAGE_LOG_LEVEL=DEBUG
sage-cp-bench run --mode llm --policy fifo --requests 10
```

______________________________________________________________________

*Updated: 2025-11-28*
