# Agent Benchmark Module

Configuration-driven experiment framework for evaluating agent capabilities through three core
experiments:

1. **Tool Selection** - Tool retrieval and ranking evaluation
1. **Planning** - Multi-step planning with tool composition
1. **Timing Detection** - Timing judgment for tool invocation decisions

## Architecture

```
benchmark_agent/
├── config/                    # Configuration system
│   ├── config_loader.py      # YAML loader with env var support
│   ├── default_config.yaml   # Default settings
│   ├── tool_selection_exp.yaml
│   ├── planning_exp.yaml
│   └── timing_detection_exp.yaml
├── experiments/               # Experiment implementations
│   ├── base_experiment.py    # Abstract base class & config models
│   ├── tool_selection_exp.py # Tool selection experiment
│   ├── planning_exp.py       # Planning experiment
│   └── timing_detection_exp.py # Timing detection experiment
├── __init__.py               # Module exports
├── __main__.py               # CLI entry point
└── README.md                 # This file
```

## Quick Start

### CLI Usage

```bash
# Tool selection experiment
python -m sage.benchmark.benchmark_agent \
    --config config/tool_selection_exp.yaml

# Planning experiment with custom output
python -m sage.benchmark.benchmark_agent \
    --config config/planning_exp.yaml \
    --output results/my_planning_results.json \
    --verbose

# Timing detection experiment
python -m sage.benchmark.benchmark_agent \
    --config config/timing_detection_exp.yaml

# Dry-run to validate config
python -m sage.benchmark.benchmark_agent \
    --config config/tool_selection_exp.yaml \
    --dry-run
```

### Programmatic Usage

```python
from sage.benchmark.benchmark_agent import ToolSelectionExperiment
from sage.benchmark.benchmark_agent.config import ConfigLoader

# Load configuration
loader = ConfigLoader()
config = loader.load_config("config/tool_selection_exp.yaml")

# Create and run experiment
exp = ToolSelectionExperiment(config)
exp.prepare()
result = exp.run()
exp.finalize()

# Access results
print(f"Total samples: {result.metadata['total_samples']}")
print(f"Predictions: {len(result.predictions)}")
print(f"Output saved to: {result.output_path}")
```

## Experiment Types

### 1. Tool Selection

Evaluates tool retrieval and ranking capabilities.

**Config Example** (`tool_selection_exp.yaml`):

```yaml
experiment_type: tool_selection
profile: quick_eval          # Data profile to use
split: dev                   # Dataset split (train/dev/test)
top_k: 5                     # Number of tools to retrieve
retriever: bm25              # Retrieval strategy name
max_samples: 100             # Limit samples (optional)
output_path: ${PROJECT_ROOT}/results/tool_selection_results.json
verbose: true
```

**Metrics**: Recall@k, Precision@k, NDCG@k

### 2. Planning

Evaluates multi-step planning and tool composition.

**Config Example** (`planning_exp.yaml`):

```yaml
experiment_type: planning
profile: quick_eval
split: dev
max_steps: 5                 # Maximum planning steps
planner: cot                 # Planning strategy name
output_path: ${PROJECT_ROOT}/results/planning_results.json
verbose: false
```

**Metrics**: Plan accuracy, Tool sequence match, Step coherence

### 3. Timing Detection

Evaluates timing judgment for when to invoke tools vs. answer directly.

**Config Example** (`timing_detection_exp.yaml`):

```yaml
experiment_type: timing_detection
profile: quick_eval
split: dev
threshold: 0.7               # Confidence threshold
detector: llm_based          # Detection strategy name
output_path: ${PROJECT_ROOT}/results/timing_results.json
```

**Metrics**: Accuracy, Precision, Recall, F1-score

## Configuration System

### Environment Variables

Configs support environment variable substitution:

```yaml
output_path: ${PROJECT_ROOT}/results/output.json
api_key: ${OPENAI_API_KEY}
```

Supported variables:

- `${PROJECT_ROOT}` - Auto-detected project root
- `${HOME}` - User home directory
- Any environment variable via `${VAR_NAME}`

### Config Merging

Load base config and override specific fields:

```python
from sage.benchmark.benchmark_agent.config import ConfigLoader

loader = ConfigLoader()
config = loader.load_config("config/tool_selection_exp.yaml")

# Override programmatically
config.top_k = 10
config.verbose = True
config.max_samples = 50
```

## Experiment Lifecycle

All experiments follow a three-phase lifecycle:

### 1. Prepare Phase

```python
exp.prepare()
```

- Generates unique experiment ID
- Loads data via DataManager
- Initializes strategy from adapter registry
- Validates configuration

### 2. Run Phase

```python
result = exp.run()
```

- Iterates over benchmark samples
- Calls strategy for predictions
- Collects ground truth references
- Tracks metadata (success/failure counts)
- Returns `ExperimentResult` object

### 3. Finalize Phase

```python
exp.finalize()
```

- Saves results to JSON file
- Logs completion summary
- Cleans up resources

## Integration with DataManager

Experiments use DataManager for unified data access:

```python
# Automatic in experiments
agent_eval = self.dm.get_by_usage("agent_eval")
profile_data = agent_eval.load_profile(self.config.profile)

tools_loader = profile_data["tools"]
benchmark_loader = profile_data["benchmark"]

# Iterate samples
for sample in benchmark_loader.iter_split(
    task_type="tool_selection",
    split="dev"
):
    # Process sample
    ...
```

## Adapter Registry Pattern

Experiments use pluggable strategies via adapter registry:

```python
# In experiment
self.strategy = self.adapter_registry.get(self.config.retriever)

# Call strategy
result = self.strategy.retrieve(query)  # Tool selection
plan = self.strategy.plan(task)         # Planning
decision = self.strategy.decide(msg)    # Timing detection
```

**Strategy Protocols**:

```python
# Tool Selection Strategy
class ToolSelectionStrategy(Protocol):
    def retrieve(self, query: ToolSelectionQuery) -> ToolSelectionResult:
        ...

# Planning Strategy
class PlanningStrategy(Protocol):
    def plan(self, task: PlanningTask) -> Plan:
        ...

# Timing Detection Strategy
class TimingDetectionStrategy(Protocol):
    def decide(self, message: TimingMessage) -> TimingDecision:
        ...
```

## Result Format

All experiments produce `ExperimentResult` with consistent structure:

```json
{
  "experiment_id": "tool_selection_20241125_143022_abc123",
  "experiment_type": "tool_selection",
  "config": {
    "profile": "quick_eval",
    "split": "dev",
    "top_k": 5,
    ...
  },
  "predictions": [
    {
      "sample_id": "sample_001",
      "tool_ids": ["tool_042", "tool_137", ...],
      "scores": [0.95, 0.87, ...]
    },
    ...
  ],
  "references": [
    {
      "sample_id": "sample_001",
      "tool_ids": ["tool_042", "tool_091"],
      "reasoning": "..."
    },
    ...
  ],
  "metadata": {
    "total_samples": 100,
    "failed_samples": 2,
    "timestamp": "2024-11-25T14:30:22"
  },
  "output_path": "/path/to/results.json"
}
```

## Testing

Run unit tests:

```bash
# All tests
pytest packages/sage-benchmark/tests/benchmark_agent/ -v

# Specific test file
pytest packages/sage-benchmark/tests/benchmark_agent/test_experiments.py -v

# With coverage
pytest packages/sage-benchmark/tests/benchmark_agent/ --cov=sage.benchmark.benchmark_agent
```

Test coverage includes:

- Config loading and validation
- Environment variable expansion
- Experiment lifecycle (prepare/run/finalize)
- Mock DataManager integration
- Mock adapter registry integration
- Result generation and saving

## Development

### Adding New Experiment Type

1. **Define config model** in `base_experiment.py`:

```python
class NewExperimentConfig(ExperimentConfig):
    experiment_type: Literal["new_experiment"] = "new_experiment"
    custom_param: int = 10
```

2. **Implement experiment** in `experiments/new_experiment.py`:

```python
class NewExperiment(BaseExperiment):
    def __init__(self, config: NewExperimentConfig, ...):
        super().__init__(config, ...)

    def prepare(self):
        super().prepare()
        # Custom preparation

    def run(self) -> ExperimentResult:
        # Custom logic
        return self._create_result(predictions, references, metadata)
```

3. **Create YAML config** in `config/new_experiment.yaml`

1. **Update exports** in `__init__.py`

1. **Add tests** in `tests/benchmark_agent/test_experiments.py`

### Custom Strategy Implementation

Implement strategy protocol and register:

```python
class MyCustomRetriever:
    def retrieve(self, query: ToolSelectionQuery) -> ToolSelectionResult:
        # Custom retrieval logic
        tool_ids = [...]
        scores = [...]
        return ToolSelectionResult(tool_ids=tool_ids, scores=scores)

# Register strategy
adapter_registry.register("my_retriever", MyCustomRetriever())

# Use in config
# retriever: my_retriever
```

## Integration with Subtask 2 & 3

This module (Subtask 1) provides the **experiment kernel**. Integration points:

- **Subtask 2 (Evaluation Metrics)**: Consumes `ExperimentResult.predictions` and
  `ExperimentResult.references`
- **Subtask 3 (Visualization)**: Reads saved JSON results for plotting and analysis

Expected workflow:

```python
# Subtask 1: Run experiment
result = experiment.run()
result.save()  # → results.json

# Subtask 2: Compute metrics
from sage.benchmark.benchmark_agent.metrics import compute_metrics
metrics = compute_metrics(result)  # → {recall@5: 0.85, ...}

# Subtask 3: Visualize
from sage.benchmark.benchmark_agent.visualization import plot_results
plot_results(result, metrics)  # → charts and tables
```

## Troubleshooting

### Config Loading Errors

```
ValueError: Unknown experiment type: xyz
```

→ Check `experiment_type` field in YAML matches: `tool_selection`, `planning`, or `timing_detection`

### DataManager Not Found

```
Error: Could not load data
```

→ Ensure DataManager is initialized and `agent_eval` usage profile exists

### Strategy Not Found

```
Warning: Could not load retriever: xyz
```

→ Verify strategy name in config matches registered adapter in registry

### Output Path Issues

```
Error: Permission denied: /path/to/results.json
```

→ Check output directory exists and is writable, or use `${PROJECT_ROOT}` variable

## References

- **Task Decomposition**: `task2-decomposition-plan.md` Section 2.1-2.3
- **Data Sources**: `agent_tools`, `agent_benchmark`, `agent_sft` in `sage.data.sources`
- **DataManager**: `sage.data.manager.DataManager`
- **Integration Report**: Cross-validation with other subtasks

## License

Part of the SAGE framework - See LICENSE file for details.
