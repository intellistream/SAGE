# Workflow Optimizer Framework

**Layer**: L3 (Core - Research & Algorithm Library)\
**Purpose**: Standardized framework for
researching agentic workflow optimization

## Overview

The Workflow Optimizer Framework provides a plug-and-play environment for students and researchers
to experiment with different optimization strategies for AI agent workflows. It handles all the
infrastructure (workflow representation, constraint checking, evaluation, benchmarking) so
researchers can focus purely on developing novel optimization algorithms.

## Key Features

✅ **Standardized Workflow Representation** - DAG-based workflow graphs with rich metadata\
✅
**Pluggable Optimizer Interface** - Easy to implement custom optimization strategies\
✅ **Constraint
System** - Budget, latency, and quality constraints with extensibility\
✅ **Automated Benchmarking**
\- Compare multiple optimizers on standard benchmarks\
✅ **Evaluation Metrics** - Comprehensive
metrics (cost, latency, quality, etc.)\
✅ **Example Implementations** - Reference optimizers to
learn from

## Quick Start

### 1. Create a Workflow

```python
from sage.libs.workflow import WorkflowGraph, NodeType

# Define workflow
workflow = WorkflowGraph(name="rag_pipeline")

# Add agent nodes
workflow.add_node(
    "retriever", NodeType.AGENT, metrics={"cost": 5.0, "latency": 0.5, "quality": 0.9}
)

workflow.add_node(
    "generator", NodeType.AGENT, metrics={"cost": 25.0, "latency": 2.0, "quality": 0.85}
)

# Define dependencies
workflow.add_edge("retriever", "generator")
```

### 2. Apply an Optimizer

```python
from sage.libs.workflow.optimizers import GreedyOptimizer

# Create optimizer
optimizer = GreedyOptimizer()

# Optimize with constraints
result = optimizer.optimize(
    workflow, constraints={"max_cost": 40.0, "min_quality": 0.85}
)

# View results
print(f"Cost reduction: {result.metrics.cost_reduction:.1f}%")
print(f"Quality change: {result.metrics.quality_change:+.2f}")
```

### 3. Implement Custom Optimizer

```python
from sage.libs.workflow import BaseOptimizer, OptimizationResult


class MyOptimizer(BaseOptimizer):
    """Your custom optimization strategy."""

    def __init__(self):
        super().__init__(name="MyOptimizer")

    def optimize(self, workflow, constraints=None):
        import time

        start = time.time()

        # Clone workflow for modification
        optimized = workflow.clone()

        # YOUR OPTIMIZATION LOGIC HERE
        # Examples:
        # - Remove redundant nodes
        # - Merge similar operations
        # - Reorder for better parallelization
        # - Cache intermediate results
        # - Replace expensive models with cheaper alternatives

        # Calculate metrics
        exec_time = time.time() - start
        metrics = self.calculate_metrics(workflow, optimized, exec_time)

        return OptimizationResult(
            original_workflow=workflow,
            optimized_workflow=optimized,
            metrics=metrics,
            steps=["Description of what you did"],
        )
```

### 4. Benchmark Multiple Optimizers

```python
from sage.libs.workflow import WorkflowEvaluator
from sage.libs.workflow.evaluator import create_synthetic_workflow

# Setup evaluator
evaluator = WorkflowEvaluator()

# Add benchmark workflows
evaluator.add_benchmark("small", create_synthetic_workflow(num_agents=5))
evaluator.add_benchmark("large", create_synthetic_workflow(num_agents=15))

# Compare optimizers
from sage.libs.workflow.optimizers import (
    NoOpOptimizer,
    GreedyOptimizer,
    ParallelizationOptimizer,
)

results = evaluator.evaluate_all(
    [
        NoOpOptimizer(),
        GreedyOptimizer(),
        ParallelizationOptimizer(),
        MyOptimizer(),  # Your custom optimizer
    ]
)

# Print comparison
evaluator.print_comparison(results)
```

## Architecture

```
workflow/
├── __init__.py           # Public API
├── base.py               # Core abstractions (WorkflowGraph, BaseOptimizer)
├── constraints.py        # Constraint system
├── evaluator.py          # Benchmarking and evaluation
├── examples.py           # Usage examples
├── optimizers/           # Example optimizer implementations
│   └── __init__.py       # NoOp, Greedy, Parallelization optimizers
└── README.md             # This file
```

## Core Concepts

### WorkflowGraph

Represents an agentic workflow as a directed acyclic graph (DAG):

- **Nodes**: Agents, tools, operators, decisions, aggregators
- **Edges**: Dependencies between nodes
- **Metrics**: Cost, latency, quality per node

### BaseOptimizer

Abstract base class for optimization strategies:

- `optimize()`: Transform workflow → optimized workflow
- `calculate_metrics()`: Compute optimization quality
- Automatically handles cloning, timing, and metrics

### Constraints

Define requirements for valid workflows:

- **BudgetConstraint**: Maximum total cost
- **LatencyConstraint**: Maximum end-to-end latency
- **QualityConstraint**: Minimum quality score
- Extensible: implement `BaseConstraint` for custom constraints

### WorkflowEvaluator

Benchmarking tool for comparing optimizers:

- Run multiple optimizers on multiple workflows
- Generate comparison tables and reports
- Identify best optimizer per metric

## Research Directions

Students can explore many optimization strategies:

### 1. Cost Optimization

- **Node removal**: Eliminate redundant or low-value nodes
- **Model substitution**: Replace expensive models with cheaper alternatives
- **Caching**: Reuse results from previous executions
- **Batching**: Combine multiple requests to reduce overhead

### 2. Latency Optimization

- **Parallelization**: Identify independent operations
- **Pipeline optimization**: Reorder operations for better flow
- **Speculative execution**: Start likely paths early
- **Lazy evaluation**: Defer unnecessary computations

### 3. Quality Optimization

- **Ensemble methods**: Combine multiple agents for better quality
- **Verification layers**: Add quality checking nodes
- **Iterative refinement**: Add feedback loops
- **Confidence-based routing**: Use expensive models only when needed

### 4. Multi-Objective Optimization

- **Pareto optimization**: Balance cost vs quality vs latency
- **Constraint satisfaction**: Meet all constraints optimally
- **Adaptive optimization**: Adjust based on runtime feedback

### 5. Learning-Based Optimization

- **Reinforcement learning**: Learn optimal policies from experience
- **Meta-learning**: Quickly adapt to new workflow types
- **Transfer learning**: Apply knowledge across domains

## Example Optimizers

### NoOpOptimizer

Baseline that makes no changes. Useful for comparison.

### GreedyOptimizer

Removes highest-cost nodes when safe to do so. Simple but effective.

### ParallelizationOptimizer

Identifies parallelization opportunities to reduce latency. Conceptual example.

## Running Examples

```bash
# Run all examples
python -m sage.libs.workflow.examples

# Or in Python
from sage.libs.workflow.examples import (
    example_basic_workflow,
    example_custom_optimizer,
    example_benchmarking
)

example_basic_workflow()
example_custom_optimizer()
example_benchmarking()
```

## Integration with SAGE

The workflow optimizer is designed to integrate with SAGE's execution engine:

```python
# Import SAGE operators
from sage.kernel.api.function.map_function import MapFunction

# Create workflow with actual SAGE operators
workflow = WorkflowGraph()
workflow.add_node(
    "my_agent",
    NodeType.AGENT,
    operator=my_sage_operator,  # Actual SAGE operator
    metrics={"cost": 10, "latency": 1},
)

# Optimize
result = optimizer.optimize(workflow)

# Deploy optimized workflow to SAGE runtime
# (Implementation depends on your SAGE setup)
```

## Best Practices

### For Students

1. **Start simple**: Implement a basic optimizer first (e.g., random node removal)
1. **Use baselines**: Always compare against NoOpOptimizer
1. **Test incrementally**: Validate on small workflows before scaling
1. **Document assumptions**: Explain your optimization strategy clearly
1. **Handle edge cases**: Empty workflows, disconnected graphs, etc.

### For Researchers

1. **Define clear metrics**: What does "better" mean for your use case?
1. **Create domain benchmarks**: Synthetic workflows may not reflect real patterns
1. **Consider constraints**: Real systems have budget/latency/quality limits
1. **Profile performance**: Optimization should be fast enough for production
1. **Validate empirically**: Test on real workflows, not just synthetic ones

## API Reference

See individual module docstrings for detailed API documentation:

- `base.py`: WorkflowGraph, WorkflowNode, BaseOptimizer
- `constraints.py`: Constraint system
- `evaluator.py`: Benchmarking tools
- `optimizers/`: Example implementations

## Testing

```bash
# Run tests (from package root)
pytest packages/sage-libs/tests/workflow/

# Run with coverage
pytest --cov=sage.libs.workflow packages/sage-libs/tests/workflow/
```

## Contributing

When implementing new optimizers or features:

1. Follow the `BaseOptimizer` interface
1. Add docstrings and type hints
1. Include usage examples
1. Add unit tests
1. Update this README

## Related Work

This framework is inspired by:

- **AutoGen**: Multi-agent workflow optimization
- **LangGraph**: Graph-based agent orchestration
- **DSPy**: Program optimization for LLM pipelines
- **Compiler optimization**: Classic code optimization techniques

## License

Part of the SAGE project. See main LICENSE file.

## Citation

If you use this framework in research, please cite:

```bibtex
@misc{sage_workflow_2025,
  title={SAGE Workflow Optimizer Framework},
  author={SAGE Team},
  year={2025},
  note={Research framework for agentic workflow optimization}
}
```

## Support

- **Issues**: File in main SAGE repository with \[workflow-optimizer\] tag
- **Discussions**: SAGE community forum
- **Examples**: See `examples.py` for comprehensive usage
