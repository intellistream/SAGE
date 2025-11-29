# Control Plane Benchmark Data Paths

This document describes the data directory structure and file formats for the Control Plane
Benchmark module.

## Overview

The benchmark uses data files for:
1. **Workload Configurations**: Define test scenarios (request rates, distributions, etc.)
2. **Test Prompts**: LLM prompts and embedding texts for realistic testing
3. **Results Output**: Benchmark results, metrics, and reports

## Directory Structure

```
sage/data/sources/control_plane_benchmark/
├── __init__.py
├── dataloader.py              # Data loading utilities
├── data/
│   ├── llm_workloads/         # LLM-only workload configurations
│   │   ├── light.jsonl        # Light load: 100 req, 10 req/s
│   │   ├── medium.jsonl       # Medium load: 1000 req, 100 req/s
│   │   └── heavy.jsonl        # Heavy load: 5000 req, 500 req/s
│   │
│   ├── hybrid_workloads/      # Hybrid LLM+Embedding configurations
│   │   ├── balanced.jsonl     # 50% LLM, 50% Embedding
│   │   ├── llm_heavy.jsonl    # 80% LLM, 20% Embedding
│   │   ├── embed_heavy.jsonl  # 20% LLM, 80% Embedding
│   │   └── burst.jsonl        # Burst load pattern
│   │
│   └── prompts/               # Test data
│       ├── llm_prompts.jsonl  # LLM test prompts
│       └── embed_texts.jsonl  # Embedding test texts
│
└── metadata/
    └── schema.json            # JSON schema definitions
```

## File Formats

### Workload Configuration (JSONL)

Each line in a workload file is a JSON object defining test parameters:

```jsonl
{"name": "light_load", "num_requests": 100, "request_rate": 10.0, "arrival_pattern": "poisson"}
{"name": "medium_load", "num_requests": 1000, "request_rate": 100.0, "arrival_pattern": "poisson"}
```

#### LLM Workload Fields

| Field                | Type   | Description                              | Default      |
| -------------------- | ------ | ---------------------------------------- | ------------ |
| `name`               | string | Workload identifier                      | required     |
| `num_requests`       | int    | Total number of requests                 | 100          |
| `request_rate`       | float  | Requests per second                      | 10.0         |
| `arrival_pattern`    | string | "uniform", "poisson", "burst"            | "poisson"    |
| `model_distribution` | object | Model name → ratio mapping               | {"default": 1.0} |
| `priority_distribution` | object | Priority → ratio mapping              | {"NORMAL": 1.0} |
| `prompt_len_range`   | array  | [min, max] prompt token length           | [50, 500]    |
| `output_len_range`   | array  | [min, max] output token length           | [50, 200]    |
| `timeout_seconds`    | float  | Request timeout                          | 60.0         |

**Example: `llm_workloads/medium.jsonl`**
```jsonl
{"name": "medium_uniform", "num_requests": 1000, "request_rate": 100.0, "arrival_pattern": "uniform", "model_distribution": {"Qwen/Qwen2.5-7B-Instruct": 0.6, "meta-llama/Llama-2-7b-chat-hf": 0.4}, "priority_distribution": {"HIGH": 0.2, "NORMAL": 0.6, "LOW": 0.2}}
{"name": "medium_poisson", "num_requests": 1000, "request_rate": 100.0, "arrival_pattern": "poisson", "model_distribution": {"Qwen/Qwen2.5-7B-Instruct": 1.0}}
{"name": "medium_burst", "num_requests": 1000, "request_rate": 100.0, "arrival_pattern": "burst", "burst_size": 50, "burst_interval": 1.0}
```

#### Hybrid Workload Fields

Additional fields for hybrid workloads:

| Field                      | Type   | Description                        | Default      |
| -------------------------- | ------ | ---------------------------------- | ------------ |
| `llm_ratio`                | float  | Ratio of LLM requests (0.0-1.0)    | 0.5          |
| `embedding_ratio`          | float  | Ratio of embedding requests        | 0.5          |
| `embedding_model`          | string | Embedding model name               | "BAAI/bge-m3"|
| `embedding_batch_size`     | int    | Embedding batch size               | 32           |
| `llm_slo_deadline_ms`      | int    | LLM SLO deadline (ms)              | 5000         |
| `embedding_slo_deadline_ms`| int    | Embedding SLO deadline (ms)        | 500          |

**Example: `hybrid_workloads/balanced.jsonl`**
```jsonl
{"name": "balanced_50_50", "num_requests": 1000, "request_rate": 100.0, "llm_ratio": 0.5, "embedding_ratio": 0.5, "llm_slo_deadline_ms": 5000, "embedding_slo_deadline_ms": 500}
{"name": "balanced_slo_tight", "num_requests": 1000, "request_rate": 100.0, "llm_ratio": 0.5, "embedding_ratio": 0.5, "llm_slo_deadline_ms": 2000, "embedding_slo_deadline_ms": 200}
```

### Test Prompts (JSONL)

#### LLM Prompts: `prompts/llm_prompts.jsonl`

```jsonl
{"id": "prompt_001", "category": "qa", "prompt": "What is the capital of France?", "expected_tokens": 50}
{"id": "prompt_002", "category": "code", "prompt": "Write a Python function to calculate fibonacci numbers.", "expected_tokens": 200}
{"id": "prompt_003", "category": "creative", "prompt": "Write a short story about a robot learning to paint.", "expected_tokens": 500}
{"id": "prompt_004", "category": "analysis", "prompt": "Analyze the following text and summarize the key points: ...", "expected_tokens": 300}
```

| Field            | Type   | Description                     |
| ---------------- | ------ | ------------------------------- |
| `id`             | string | Unique prompt identifier        |
| `category`       | string | Category: qa, code, creative, analysis, etc. |
| `prompt`         | string | The actual prompt text          |
| `expected_tokens`| int    | Expected output length (tokens) |
| `system_prompt`  | string | (optional) System prompt        |
| `priority`       | string | (optional) HIGH, NORMAL, LOW    |

#### Embedding Texts: `prompts/embed_texts.jsonl`

```jsonl
{"id": "embed_001", "category": "document", "text": "Machine learning is a subset of artificial intelligence...", "expected_dim": 1024}
{"id": "embed_002", "category": "query", "text": "How does neural network training work?", "expected_dim": 1024}
{"id": "embed_003", "category": "code", "text": "def quicksort(arr): ...", "expected_dim": 1024}
```

| Field          | Type   | Description                       |
| -------------- | ------ | --------------------------------- |
| `id`           | string | Unique text identifier            |
| `category`     | string | Category: document, query, code   |
| `text`         | string | Text to embed                     |
| `expected_dim` | int    | Expected embedding dimension      |

## Using the Data Loader

```python
from sage.data.sources.control_plane_benchmark import ControlPlaneBenchmarkDataLoader

loader = ControlPlaneBenchmarkDataLoader()

# List available workloads
print(loader.list_workloads())
# Output: ['light', 'medium', 'heavy', 'balanced', 'llm_heavy', 'embed_heavy', 'burst']

# Load a specific workload
workload = loader.load_workload("medium")
print(workload)
# Output: {'name': 'medium_uniform', 'num_requests': 1000, ...}

# Load test prompts
prompts = loader.load_prompts("llm")
print(f"Loaded {len(prompts)} LLM prompts")

# Load embedding texts
texts = loader.load_prompts("embedding")
print(f"Loaded {len(texts)} embedding texts")
```

## Output Directory Structure

Benchmark results are saved to the output directory (default: `./benchmark_results/`):

```
benchmark_results/
├── llm_benchmark_20251128_143022/
│   ├── config.json              # Benchmark configuration
│   ├── results.json             # Full results with raw data
│   ├── summary.csv              # Summary metrics table
│   ├── charts/
│   │   ├── throughput_comparison.png
│   │   ├── latency_distribution.png
│   │   ├── latency_cdf.png
│   │   └── slo_compliance.png
│   └── reports/
│       ├── benchmark_report.html
│       └── benchmark_report.md
│
└── hybrid_benchmark_20251128_150045/
    ├── config.json
    ├── results.json
    ├── summary.csv
    ├── charts/
    │   ├── throughput_comparison.png
    │   ├── latency_by_type.png
    │   ├── slo_compliance_hybrid.png
    │   └── mixed_ratio_impact.png
    └── reports/
        ├── benchmark_report.html
        └── benchmark_report.md
```

### Results JSON Format

```json
{
  "benchmark_type": "hybrid",
  "timestamp": "2025-11-28T15:00:45",
  "config": {
    "control_plane_url": "http://localhost:8080",
    "num_requests": 1000,
    "request_rate": 100.0,
    "llm_ratio": 0.7,
    "embedding_ratio": 0.3
  },
  "policy_results": {
    "fifo": {
      "metrics": {
        "throughput_rps": 95.2,
        "e2e_latency_avg_ms": 156.3,
        "e2e_latency_p99_ms": 423.1,
        "llm_slo_compliance_rate": 0.712,
        "embedding_slo_compliance_rate": 0.921,
        "error_rate": 0.003
      },
      "raw_results": [...]
    },
    "hybrid_slo": {
      "metrics": {...},
      "raw_results": [...]
    }
  },
  "summary": {
    "best_throughput": {"policy": "hybrid_slo", "value": 98.5},
    "best_llm_slo": {"policy": "hybrid_slo", "value": 0.937},
    "best_embedding_slo": {"policy": "hybrid_slo", "value": 0.982}
  }
}
```

### Summary CSV Format

```csv
policy,throughput_rps,e2e_avg_ms,e2e_p99_ms,llm_slo_rate,emb_slo_rate,error_rate
fifo,95.2,156.3,423.1,0.712,0.921,0.003
hybrid_slo,98.5,132.1,312.4,0.937,0.982,0.001
```

## Configuration File Formats

### YAML Configuration

```yaml
# benchmark_config.yaml
control_plane_url: http://localhost:8080
num_requests: 1000
request_rate: 100.0

# LLM-specific
arrival_pattern: poisson
model_distribution:
  Qwen/Qwen2.5-7B-Instruct: 0.7
  meta-llama/Llama-2-7b-chat-hf: 0.3

priority_distribution:
  HIGH: 0.2
  NORMAL: 0.6
  LOW: 0.2

# Hybrid-specific
llm_ratio: 0.7
embedding_ratio: 0.3
embedding_model: BAAI/bge-m3
embedding_batch_size: 32

# SLO settings
llm_slo_deadline_ms: 5000
embedding_slo_deadline_ms: 500

# Output
output_dir: ./benchmark_results
auto_visualize: true
```

### JSON Configuration

```json
{
  "control_plane_url": "http://localhost:8080",
  "num_requests": 1000,
  "request_rate": 100.0,
  "arrival_pattern": "poisson",
  "model_distribution": {
    "Qwen/Qwen2.5-7B-Instruct": 0.7,
    "meta-llama/Llama-2-7b-chat-hf": 0.3
  },
  "llm_ratio": 0.7,
  "embedding_ratio": 0.3,
  "output_dir": "./benchmark_results",
  "auto_visualize": true
}
```

## Creating Custom Workloads

### Step 1: Create Workload File

```bash
# Create custom workload
cat > my_workload.jsonl << 'EOF'
{"name": "custom_high_load", "num_requests": 2000, "request_rate": 200.0, "llm_ratio": 0.8}
{"name": "custom_burst", "num_requests": 1000, "request_rate": 50.0, "arrival_pattern": "burst"}
EOF
```

### Step 2: Use in Benchmark

```python
from sage.benchmark.benchmark_control_plane.hybrid_scheduler import (
    HybridBenchmarkConfig,
    HybridBenchmarkRunner,
)

# Load custom workload
import json
with open("my_workload.jsonl") as f:
    workload = json.loads(f.readline())

# Create config from workload
config = HybridBenchmarkConfig(
    control_plane_url="http://localhost:8080",
    num_requests=workload["num_requests"],
    request_rate=workload["request_rate"],
    llm_ratio=workload.get("llm_ratio", 0.5),
)

# Run benchmark
runner = HybridBenchmarkRunner(config)
result = asyncio.run(runner.run())
```

## Environment Variables

| Variable                 | Description                          | Default                    |
| ------------------------ | ------------------------------------ | -------------------------- |
| `SAGE_BENCHMARK_DATA`    | Custom data directory path           | (built-in)                 |
| `SAGE_BENCHMARK_OUTPUT`  | Default output directory             | `./benchmark_results`      |
| `SAGE_CONTROL_PLANE_URL` | Default Control Plane URL            | `http://localhost:8080`    |

---

*Updated: 2025-11-28*
