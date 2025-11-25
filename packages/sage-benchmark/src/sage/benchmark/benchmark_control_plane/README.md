# sageLLM Control Plane Benchmark

This module provides benchmarking tools for evaluating different scheduling policies in sageLLM's Control Plane.

## Overview

The benchmark measures key performance metrics across various scheduling strategies:

- **Throughput**: Requests per second and tokens per second
- **Latency**: End-to-end latency, Time to First Token (TTFT), Time Between Tokens (TBT)
- **SLO Compliance**: Percentage of requests meeting their SLO deadlines
- **Error Rates**: Failed requests and timeout rates

## Architecture

```
┌─────────────┐      HTTP       ┌─────────────────┐      HTTP      ┌──────────────┐
│  Benchmark  │ ──────────────► │  Control Plane  │ ─────────────► │ vLLM Inst 1  │
│   Client    │                 │   (Scheduler)   │                │ (llama-7b)   │
└─────────────┘                 │                 │ ─────────────► ├──────────────┤
                                │  Policy: X      │                │ vLLM Inst 2  │
                                └─────────────────┘                │ (llama-13b)  │
                                                                   ├──────────────┤
                                                                   │ vLLM Inst N  │
                                                                   │ (mistral-7b) │
                                                                   └──────────────┘
```

## Installation

The benchmark module is part of the `sage-benchmark` package. Install with:

```bash
pip install isage-benchmark
# Or for development:
pip install -e "packages/sage-benchmark[dev]"
```

Additional dependencies for HTTP client:
```bash
pip install aiohttp
```

For CLI:
```bash
pip install typer
```

## Usage

### Command Line Interface

```bash
# Run single policy benchmark
sage-bench run \
  --control-plane http://10.0.0.1:8080 \
  --policy aegaeon \
  --requests 1000 \
  --rate 100 \
  --output results/aegaeon_100rps.json

# Compare multiple policies
sage-bench compare \
  --control-plane http://10.0.0.1:8080 \
  --policies fifo,priority,slo_aware,aegaeon \
  --requests 1000 \
  --rate 100 \
  --output results/comparison/

# Request rate sweep
sage-bench sweep \
  --control-plane http://10.0.0.1:8080 \
  --policy aegaeon \
  --requests 500 \
  --rates 50,100,200,500 \
  --output results/rate_sweep/

# Show example configuration
sage-bench config

# Validate configuration file
sage-bench validate config.json
```

### Python API

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
    policies=["fifo", "priority", "slo_aware", "aegaeon"],
    num_requests=1000,
    request_rate=100.0,
    model_distribution={
        "llama-7b": 0.5,
        "llama-13b": 0.3,
        "mistral-7b": 0.2,
    },
    priority_distribution={
        "HIGH": 0.2,
        "NORMAL": 0.6,
        "LOW": 0.2,
    },
)

# Run benchmark
runner = BenchmarkRunner(config)
result = asyncio.run(runner.run())

# Generate report
reporter = BenchmarkReporter(result)
reporter.print_summary()
reporter.save_all("./benchmark_results")
```

## Supported Scheduling Policies

| Policy | Description |
|--------|-------------|
| `fifo` | First-In-First-Out scheduling |
| `priority` | Priority-based scheduling |
| `slo_aware` | SLO-deadline aware scheduling |
| `cost_optimized` | Cost-optimized scheduling |
| `adaptive` | Adaptive scheduling based on system state |
| `aegaeon` | Advanced scheduling with multiple optimizations |

## Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| `control_plane_url` | Control Plane HTTP address | `http://localhost:8080` |
| `policies` | List of policies to benchmark | `["fifo", "priority", "slo_aware"]` |
| `num_requests` | Total requests per policy | `100` |
| `request_rate` | Target request rate (req/s) | `10.0` |
| `arrival_pattern` | Request arrival pattern | `poisson` |
| `model_distribution` | Request distribution across models | `{"llama-7b": 1.0}` |
| `priority_distribution` | Request priority distribution | `{"NORMAL": 1.0}` |
| `prompt_len_range` | Prompt length range (min, max) | `(50, 500)` |
| `output_len_range` | Output length range (min, max) | `(50, 200)` |
| `timeout_seconds` | Request timeout | `60.0` |
| `warmup_requests` | Warmup requests before measurement | `10` |

## Output Formats

### Terminal Output

```
============================================================
          sageLLM Scheduling Policy Benchmark Report
============================================================
Config: 1000 requests @ 100 req/s | Models: llama-7b, llama-13b, mistral-7b
------------------------------------------------------------

| Policy     | Throughput | Avg E2E | P99 E2E | Avg TTFT | SLO Rate | Errors |
|------------|------------|---------|---------|----------|----------|--------|
| fifo       | 95.2 req/s | 156 ms  | 423 ms  | 45 ms    | 71.2%    | 0.3%   |
| priority   | 94.1 req/s | 162 ms  | 445 ms  | 48 ms    | 76.8%    | 0.2%   |
| slo_aware  | 91.3 req/s | 148 ms  | 389 ms  | 42 ms    | 88.5%    | 0.4%   |
| aegaeon    | 98.5 req/s | 132 ms  | 312 ms  | 38 ms    | 93.7%    | 0.1%   |

Best Throughput: aegaeon (98.5 req/s)
Best SLO Compliance: aegaeon (93.7%)
Best P99 Latency: aegaeon (312 ms)
```

### JSON Report

Full results including raw request data saved to `report_<timestamp>.json`.

### CSV Summary

Summary metrics saved to `summary_<timestamp>.csv` for spreadsheet analysis.

## Metrics Collected

### Latency Metrics
- End-to-end latency (avg, p50, p95, p99, min, max)
- Time to First Token (TTFT)
- Time Between Tokens (TBT)

### Throughput Metrics
- Requests per second
- Tokens per second

### SLO Metrics
- Overall SLO compliance rate
- SLO compliance by priority level

### Error Metrics
- Error rate
- Timeout rate

## Control Plane Integration

### Required API Endpoints

The benchmark expects the following Control Plane endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/v1/chat/completions` | POST | OpenAI-compatible completion endpoint |
| `/admin/set_policy` | POST | Switch scheduling policy |
| `/admin/metrics` | GET | Get Control Plane metrics |

### Request Headers

Custom headers for request metadata:
- `X-Request-ID`: Unique request identifier
- `X-Request-Priority`: Request priority (HIGH, NORMAL, LOW)
- `X-SLO-Deadline-Ms`: SLO deadline in milliseconds

## Module Structure

```
benchmark_control_plane/
├── __init__.py          # Module exports
├── config.py            # Configuration classes
├── workload.py          # Workload generation
├── client.py            # HTTP client
├── metrics.py           # Metrics collection
├── runner.py            # Benchmark orchestration
├── reporter.py          # Result reporting
├── cli.py               # CLI interface
├── datasets/            # Dataset directory
│   └── README.md        # Dataset documentation
└── README.md            # This file
```

## Future Enhancements

- [ ] ShareGPT dataset integration for realistic prompts
- [ ] Matplotlib/Plotly charts for visualization
- [ ] Distributed benchmark client for higher load generation
- [ ] Real-time metrics dashboard
