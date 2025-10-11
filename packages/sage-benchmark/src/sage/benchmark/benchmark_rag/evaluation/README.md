# Evaluation Framework

This directory contains the benchmark evaluation framework for RAG pipelines.

## Overview

The evaluation framework provides:
- **Generic Benchmark Runner**: Run any RAG pipeline on benchmark datasets
- **Result Collection**: Collect and save benchmark results with metadata
- **Metrics Evaluation**: Compute performance metrics (exact match, F1, etc.)
- **Legacy Experiments**: Original Self-RAG experiment (deprecated)

## Architecture

### New Architecture (Recommended)

```
evaluation/
├── benchmark_runner.py      # Generic benchmark runner
├── evaluate_results.py      # Metrics evaluation
├── config/
│   └── benchmark_config.yaml  # Benchmark configuration
└── legacy_selfrag_experiment.py  # Legacy implementation (deprecated)
```

**Key Components:**

1. **benchmark_runner.py**: Generic framework that can run ANY pipeline
   - `BatchDataLoader`: Load datasets in batches
   - `PipelineRunner`: Dynamically load and run pipelines
   - `ResultsCollector`: Collect and save results

2. **evaluate_results.py**: Compute metrics on results
   - Exact Match
   - F1 Score
   - Statistical analysis

3. **config/benchmark_config.yaml**: Universal configuration template

### Legacy Architecture (Deprecated)

The `legacy_selfrag_experiment.py` file contains the original implementation where
Self-RAG pipeline logic was embedded in the evaluation framework. This approach
mixed responsibilities and is no longer recommended.

## Usage

### Running a Benchmark

```bash
# Using config file
python -m sage.benchmark.benchmark_rag.evaluation.benchmark_runner \
    --config evaluation/config/benchmark_config.yaml

# Override specific options
python -m sage.benchmark.benchmark_rag.evaluation.benchmark_runner \
    --pipeline selfrag \
    --data data/selfrag/selfrag_dev_sample_100.jsonl \
    --output artifacts/benchmarks/selfrag_results.json
```

### Configuration File

```yaml
# benchmark_config.yaml
data:
  data_path: "data/selfrag/selfrag_dev_sample_100.jsonl"
  batch_size: 100
  max_samples: null  # null = process all

pipeline:
  pipeline_name: "selfrag"  # Name in implementations/pipelines/
  pipeline_config:  # Pipeline-specific config
    top_k: 5
    model_name: "mistralai/Mistral-7B-Instruct-v0.1"
    gpu_memory_utilization: 0.8
    temperature: 0.0
    max_tokens: 100

output:
  output_path: "artifacts/benchmarks/results.json"
  save_mode: "incremental"  # or "final"
```

### Evaluating Results

```bash
python -m sage.benchmark.benchmark_rag.evaluation.evaluate_results \
    --results artifacts/benchmarks/selfrag_results.json
```

## Pipeline Integration

To integrate a new pipeline with the benchmark runner:

1. **Create pipeline in `implementations/pipelines/`**:
   ```python
   # implementations/pipelines/my_pipeline.py
   
   def process_item(item: Dict, config: Dict) -> Dict:
       """
       Process a single data item.
       
       Args:
           item: Data item (question, answers, etc.)
           config: Pipeline configuration
       
       Returns:
           {
               "id": str,
               "question": str,
               "prediction": str,
               "ground_truth": List[str]
           }
       """
       # Your pipeline logic here
       ...
       return result
   ```

2. **Create config file**:
   ```yaml
   # evaluation/config/my_pipeline_config.yaml
   pipeline:
     pipeline_name: "my_pipeline"
     pipeline_config:
       # Your pipeline parameters
   ```

3. **Run benchmark**:
   ```bash
   python -m sage.benchmark.benchmark_rag.evaluation.benchmark_runner \
       --config evaluation/config/my_pipeline_config.yaml
   ```

## Result Format

Benchmark results are saved in JSON format:

```json
{
  "metadata": {
    "pipeline_name": "selfrag",
    "timestamp": "2024-01-01T12:00:00",
    "total_samples": 100,
    "completed_batches": "1/1",
    "elapsed_time_seconds": 45.2,
    "config": { ... }
  },
  "results": [
    {
      "id": "sample_1",
      "question": "What is ...?",
      "prediction": "The answer is ...",
      "ground_truth": ["Answer 1", "Answer 2"],
      "retrieved_docs": [ ... ]
    },
    ...
  ]
}
```

## Design Principles

1. **Separation of Concerns**:
   - Pipelines in `implementations/` (WHAT to test)
   - Evaluation in `evaluation/` (HOW to test)
   - Configurations in `config/` (PARAMETERS)

2. **Extensibility**:
   - Easy to add new pipelines without changing evaluation code
   - Generic interfaces (`process_item`)

3. **Reproducibility**:
   - All configurations saved in results
   - Timestamped results
   - Deterministic processing

## Migration from Legacy

If you're migrating from `legacy_selfrag_experiment.py`:

**Old way:**
```bash
python evaluation/pipeline_experiment.py --config config/config_selfrag.yaml
```

**New way:**
```bash
python -m sage.benchmark.benchmark_rag.evaluation.benchmark_runner \
    --config evaluation/config/benchmark_config.yaml
```

The new approach:
- ✅ Separates pipeline logic from evaluation framework
- ✅ Works with ANY pipeline, not just Self-RAG
- ✅ Cleaner, more maintainable code
- ✅ Follows SAGE architecture principles

## See Also

- [Implementations README](../implementations/README.md) - Available pipelines
- [Pipeline Development Guide](../implementations/pipelines/README.md) - How to create pipelines
- [Benchmark RAG README](../README.md) - Overall package documentation
