# Agent Runtime & Middleware Integration

Runtime infrastructure and middleware operators for agent execution, providing unified interfaces
for tool selection, planning, and timing decisions with performance monitoring.

## Architecture

```
sage-libs/src/sage/libs/agentic/agents/runtime/
├── __init__.py           # Module exports
├── config.py             # Configuration models (RuntimeConfig, SelectorConfig, etc.)
├── orchestrator.py       # Unified scheduler for agent operations
├── adapters.py           # BenchmarkAdapter for evaluation integration
├── telemetry.py          # Performance metrics collection
└── configs/              # YAML configuration examples

sage-middleware/src/sage/middleware/operators/agentic/
├── __init__.py                     # Operator exports
├── tool_selection_operator.py     # Tool selection operator
├── planning_operator.py            # Planning operator
├── timing_operator.py              # Timing decision operator
└── configs/                        # Operator configuration examples
```

## Features

### Runtime Components

- **RuntimeConfig**: Pydantic-based configuration for all runtime components
- **Orchestrator**: Unified scheduler coordinating tool selection, planning, and timing
- **BenchmarkAdapter**: Interface for connecting runtime to benchmark evaluation
- **Telemetry**: Performance metrics collection and aggregation

### Middleware Operators

- **ToolSelectionOperator**: Wraps selector in middleware operator interface
- **PlanningOperator**: Wraps planner in middleware operator interface
- **TimingOperator**: Wraps timing decider in middleware operator interface

## Quick Start

### Using Runtime Components

```python
from sage.libs.agentic.agents.runtime import (
    RuntimeConfig,
    Orchestrator,
    BenchmarkAdapter
)

# Create configuration
config = RuntimeConfig(
    selector={"name": "keyword", "top_k": 5},
    planner={"name": "llm", "max_steps": 10},
    timing={"name": "rule_based", "threshold": 0.5}
)

# Create orchestrator with components
from your_selector import MySelector
from your_planner import MyPlanner

orchestrator = Orchestrator(
    config=config,
    selector=MySelector(),
    planner=MyPlanner()
)

# Use through adapter
adapter = BenchmarkAdapter(orchestrator)

# Execute operations
predictions = adapter.run_tool_selection(query, top_k=5)
plan = adapter.run_planning(request)
decision = adapter.run_timing(message)

# Get performance metrics
metrics = adapter.get_metrics()
print(f"Avg latency: {metrics['avg_latency']:.3f}s")
print(f"Success rate: {metrics['success_rate']:.2%}")
```

### Using Middleware Operators

```python
from sage.middleware.operators.agentic import ToolSelectionOperator
from your_selector import MySelector

# Create operator
operator = ToolSelectionOperator(
    selector=MySelector(),
    config={
        "selector": {"top_k": 5, "name": "embedding"},
        "telemetry": {"enabled": True}
    }
)

# Use in pipeline
predictions = operator(query)

# Access metrics
metrics = operator.get_metrics()
```

### Loading from YAML Configuration

```python
import yaml
from sage.libs.agentic.agents.runtime import RuntimeConfig

# Load config
with open("configs/tool_selection.yaml") as f:
    config_dict = yaml.safe_load(f)

config = RuntimeConfig(**config_dict)
```

## Configuration Examples

### Tool Selection Runtime

```yaml
# runtime/configs/tool_selection.yaml
selector:
  name: "keyword"
  top_k: 5
  cache_enabled: true
  params:
    min_score: 0.1

telemetry:
  enabled: true
  collect_latency: true
  output_path: "./outputs/telemetry.json"

max_turns: 8
timeout: 30.0
```

### Planning Runtime

```yaml
# runtime/configs/planning.yaml
planner:
  name: "llm"
  min_steps: 1
  max_steps: 10
  enable_repair: true
  params:
    allow_tool_reuse: true

telemetry:
  enabled: true
  collect_latency: true

max_turns: 8
```

### Timing Detection Runtime

```yaml
# runtime/configs/timing_detection.yaml
timing:
  name: "rule_based"
  threshold: 0.5
  use_context: true
  params:
    confidence_threshold: 0.7

telemetry:
  enabled: true

max_turns: 8
```

## Integration with Benchmark

The BenchmarkAdapter provides a standardized interface for benchmark evaluation:

```python
from sage.libs.agentic.agents.runtime import BenchmarkAdapter, Orchestrator
from sage.benchmark.benchmark_agent.experiments import ToolSelectionExperiment

# Create runtime
orchestrator = Orchestrator(config, selector=my_selector)
adapter = BenchmarkAdapter(orchestrator)

# Use in benchmark
exp = ToolSelectionExperiment(config)
exp.prepare()

# Replace strategy with runtime adapter
for sample in exp.benchmark_loader.iter_split("tool_selection", "dev"):
    query = exp._create_query(sample)
    predictions = adapter.run_tool_selection(query, top_k=5)
    # ... evaluate predictions
```

## Telemetry and Metrics

The runtime automatically collects performance metrics:

```python
# Get aggregated metrics
metrics = adapter.get_metrics()

# Available metrics:
# - total_operations: Total number of operations
# - successful_operations: Number of successful operations
# - failed_operations: Number of failed operations
# - success_rate: Success rate (0.0 to 1.0)
# - avg_latency: Average operation latency in seconds
# - min_latency: Minimum latency
# - max_latency: Maximum latency
# - by_operation: Per-operation metrics breakdown

print(f"Total: {metrics['total_operations']}")
print(f"Success rate: {metrics['success_rate']:.2%}")
print(f"Avg latency: {metrics['avg_latency']:.3f}s")

# Per-operation breakdown
for op_name, op_metrics in metrics['by_operation'].items():
    print(f"{op_name}: {op_metrics['avg_latency']:.3f}s")
```

## Testing

### Runtime Tests

```bash
# Run runtime tests
pytest packages/sage-libs/tests/lib/agentic/runtime/ -v

# Run specific test class
pytest packages/sage-libs/tests/lib/agentic/runtime/test_runtime.py::TestOrchestrator -v
```

### Operator Tests

```bash
# Run operator tests
pytest packages/sage-middleware/tests/operators/agentic/ -v

# Run specific test
pytest packages/sage-middleware/tests/operators/agentic/test_operators.py::TestToolSelectionOperator -v
```

## API Reference

### RuntimeConfig

```python
class RuntimeConfig(BaseModel):
    selector: SelectorConfig          # Tool selector config
    planner: PlannerConfig            # Planner config
    timing: TimingConfig              # Timing decider config
    telemetry: TelemetryConfig        # Telemetry config
    max_turns: int = 8                # Max conversation turns
    timeout: float = 30.0             # Timeout in seconds
```

### Orchestrator

```python
class Orchestrator:
    def __init__(
        self,
        config: RuntimeConfig,
        selector: Optional[ToolSelector] = None,
        planner: Optional[Planner] = None,
        timing_decider: Optional[TimingDecider] = None,
        telemetry: Optional[TelemetryCollector] = None
    )

    def execute_tool_selection(self, query: Any, top_k: Optional[int] = None) -> List[Any]
    def execute_planning(self, request: Any) -> Any
    def execute_timing_decision(self, message: Any) -> Any
    def get_telemetry_metrics(self) -> Dict[str, Any]
    def reset_telemetry(self) -> None
```

### BenchmarkAdapter

```python
class BenchmarkAdapter:
    def __init__(self, orchestrator: Orchestrator)

    def run_tool_selection(self, query: Any, top_k: Optional[int] = None) -> List[Any]
    def run_planning(self, request: Any) -> Any
    def run_timing(self, message: Any) -> Any
    def get_metrics(self) -> dict
    def reset(self) -> None
```

### Middleware Operators

```python
class ToolSelectionOperator(MapFunction):
    def __init__(self, selector: Optional[Any] = None, config: Optional[Dict] = None)
    def __call__(self, query: Any) -> List[Any]
    def get_metrics(self) -> Dict[str, Any]

class PlanningOperator(MapFunction):
    def __init__(self, planner: Optional[Any] = None, config: Optional[Dict] = None)
    def __call__(self, request: Any) -> Any
    def get_metrics(self) -> Dict[str, Any]

class TimingOperator(MapFunction):
    def __init__(self, timing_decider: Optional[Any] = None, config: Optional[Dict] = None)
    def __call__(self, message: Any) -> Any
    def get_metrics(self) -> Dict[str, Any]
```

## Performance Targets

- Tool selection: < 50ms per query
- Planning: < 1.5s per request
- Timing decision: < 100ms per message
- Operator QPS: ≥ 5 per instance

## Development

### Adding Custom Strategies

1. Implement the Protocol interface (ToolSelector, Planner, or TimingDecider)
1. Inject into Orchestrator
1. Use through BenchmarkAdapter or Operators

```python
from sage.libs.agentic.agents.runtime.orchestrator import ToolSelector

class MyCustomSelector:
    """Custom tool selector implementing Protocol."""

    def select(self, query, top_k=5):
        # Your implementation
        return selected_tools

# Use in runtime
orchestrator = Orchestrator(config, selector=MyCustomSelector())
```

## Troubleshooting

### Import Errors

If you encounter import errors, ensure:

- `sage-libs` is installed with `--dev` flag
- Running from repository root
- All dependencies are installed

### Test Failures

- Check that mock components are properly configured
- Verify configuration models match expected schema
- Ensure telemetry is enabled if testing metrics

### Configuration Issues

- Validate YAML syntax
- Check that all required fields are provided
- Ensure environment variables are properly set (${PROJECT_ROOT})

## See Also

- [Task 3 Decomposition Plan](../../../../docs/dev-notes/research_work/agent-tool-benchmark/task3-decomposition-plan.md)
- [Agent Benchmark Module](../../../../packages/sage-benchmark/src/sage/benchmark/benchmark_agent/README.md)
- [SAGE Contributing Guide](../../../../CONTRIBUTING.md)
