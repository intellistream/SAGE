# Agent Capability Benchmark - Evaluation Module

## Overview

The evaluation module provides comprehensive metrics, analysis, and reporting capabilities for the
Agent Capability Benchmark. It evaluates agent performance across three core capabilities:

1. **Tool Selection** - Selecting appropriate tools from a catalog
1. **Task Planning** - Planning multi-step task execution sequences
1. **Timing Judgment** - Deciding when to invoke tools

## Architecture

```
evaluation/
├── __init__.py                  # Core interfaces and data models
├── metrics.py                   # Metric implementations
├── evaluator.py                 # Evaluation pipeline orchestrator
├── report_builder.py            # JSON and Markdown report generators
└── analyzers/
    ├── tool_selection_analyzer.py
    ├── planning_analyzer.py
    └── timing_analyzer.py
```

## Core Components

### 1. Metrics (`metrics.py`)

Implements quantitative performance metrics:

- **TopKAccuracyMetric**: Measures if correct tool appears in top-K predictions
- **RecallAtKMetric**: Fraction of relevant tools retrieved in top-K
- **PlanSuccessRateMetric**: Exact or partial plan matching rate
- **TimingF1Metric**: F1 score for tool invocation timing decisions
- **TimingPrecisionMetric** / **TimingRecallMetric**: Component metrics for timing

All metrics follow a common interface:

```python
class Metric(Protocol):
    name: str
    def compute(predictions, references) -> MetricOutput
```

### 2. Analyzers (`analyzers/`)

Provide detailed breakdowns and error analysis:

- **ToolSelectionAnalyzer**: Error patterns, category coverage, tool frequency
- **PlanningAnalyzer**: Step-level correctness, length analysis, failure modes
- **TimingAnalyzer**: Confusion matrix, confidence distribution, threshold sensitivity

### 3. Report Builders (`report_builder.py`)

Generate formatted reports:

- **JsonReportBuilder**: Structured JSON output
- **MarkdownReportBuilder**: Human-readable Markdown reports with tables

### 4. Evaluation Pipeline (`evaluator.py`)

Orchestrates the evaluation workflow:

```python
# Create from config
pipeline = EvaluationPipeline.from_config(config)

# Evaluate experiment result
report = pipeline.evaluate(experiment_result, config)

# Report contains:
# - metrics: Dict[str, float]
# - breakdowns: Dict[str, Any]
# - artifacts: Dict[str, Path] (saved files)
```

## Usage Examples

### Basic Usage

```python
from sage.benchmark.benchmark_agent.evaluation import EvaluationPipeline
from sage.benchmark.benchmark_agent.experiments import ExperimentResult

# Create experiment result
result = ExperimentResult(
    task="tool_selection",
    experiment_id="exp_001",
    predictions=[...],
    references=[...]
)

# Create pipeline from config
pipeline = EvaluationPipeline.from_config(config)

# Run evaluation
report = pipeline.evaluate(result, config)

# Access results
print(f"Top-K Accuracy: {report.metrics['top_k_accuracy']:.4f}")
print(f"Report saved to: {report.artifacts['report_json']}")
```

### Custom Metrics

```python
from sage.benchmark.benchmark_agent.evaluation.metrics import MetricRegistry, load_metrics

# Load specific metrics
metrics = load_metrics(["top_k_accuracy@10", "recall_at_k@5"])

# Or use registry directly
metric = MetricRegistry.get("top_k_accuracy", k=10)
result = metric.compute(predictions, references)
```

### Standalone Report Generation

```python
from sage.benchmark.benchmark_agent.evaluation import save_report, EvaluationReport

report = EvaluationReport(
    task="planning",
    experiment_id="exp_002",
    metrics={"plan_success": 0.85},
    breakdowns={...}
)

save_report(report, output_dir, formats=["json", "markdown"])
```

## Configuration

Evaluation is configured through the `ReportConfig` section of experiment configs:

```yaml
report:
  format: ["json", "markdown"]
  include_breakdowns: true
  path: ${PROJECT_ROOT}/outputs/agent_benchmark/tool_selection
```

## Metrics Reference

### Tool Selection

- `top_k_accuracy@k`: Hit rate if any correct tool in top-K (default k=5)
- `recall_at_k@k`: Average fraction of relevant tools retrieved (default k=5)

### Task Planning

- `plan_success_rate`: Exact sequence match rate
  - Set `allow_partial=true` for partial credit

### Timing Judgment

- `timing_f1`: F1 score for binary classification
- `timing_precision`: Precision (positive predictive value)
- `timing_recall`: Recall (sensitivity)

## Report Format

### JSON Report

```json
{
  "task": "tool_selection",
  "experiment_id": "exp_20250125_143022",
  "metrics": {
    "top_k_accuracy": 0.8450,
    "recall_at_k": 0.7123
  },
  "breakdowns": {
    "tool_selection": {
      "error_patterns": {...},
      "tool_coverage": {...}
    }
  },
  "artifacts": {...},
  "timestamp": "2025-01-25T14:30:45.123456"
}
```

### Markdown Report

Includes:

- Metrics table with formatted values
- Detailed analysis sections with breakdowns
- Links to artifact files

## Testing

Run tests with:

```bash
pytest packages/sage-benchmark/tests/benchmark_agent/test_evaluation.py -v
```

Test coverage includes:

- Individual metric computations
- Analyzer outputs
- Report builder formatting
- End-to-end pipeline execution

## Performance

- **Vectorized computation**: Uses NumPy for efficient metric calculation
- **Target**: \<1 minute for 10k samples (typical benchmark size)
- **Logging**: Each metric logs computation time in `details`

## Extensibility

### Adding Custom Metrics

```python
from sage.benchmark.benchmark_agent.evaluation.metrics import MetricRegistry

@MetricRegistry.register("my_custom_metric")
class MyCustomMetric:
    name = "my_custom_metric"

    def compute(self, predictions, references):
        # Your logic here
        return MetricOutput(value=score, details={...})
```

### Adding Custom Analyzers

```python
class MyCustomAnalyzer:
    name = "my_analyzer"

    def analyze(self, predictions, references, metadata):
        # Your analysis logic
        return {"breakdown_key": value}
```

## Integration with Experiment Pipeline

The evaluation module is called automatically by experiment runners:

```python
from sage.benchmark.benchmark_agent.experiments import ToolSelectionExperiment

experiment = ToolSelectionExperiment(config, data_manager, adapter_registry)
result = experiment.run()

# Evaluation happens automatically if metrics configured
# Or manually:
from sage.benchmark.benchmark_agent.evaluation import EvaluationPipeline
pipeline = EvaluationPipeline.from_config(config)
report = pipeline.evaluate(result, config)
```

## Troubleshooting

### Import Errors

Ensure the module is properly installed:

```bash
cd /path/to/SAGE
./quickstart.sh --dev --yes
```

### Missing Artifacts

Check that `config.report.path` is writable and exists.

### Performance Issues

For large datasets:

- Use `max_samples` in config to limit test set
- Disable `include_breakdowns` if not needed
- Select only necessary metrics

## References

- Experiment Config: `../experiments/base_experiment.py`
- Data Sources: `../../data/sources/agent_benchmark/`
- Usage Profiles: DataManager `agent_eval` usage
