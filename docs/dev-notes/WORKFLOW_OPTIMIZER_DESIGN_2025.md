# Issue #1037: Workflow Optimizer Module Design

## Overview

This issue tracks the design and implementation of a standardized **Workflow Optimizer Framework** that enables students and researchers to freely explore optimization strategies for agentic workflows.

## Objectives

✅ **Provide standard abstractions** for representing workflows as graphs  
✅ **Enable pluggable optimizers** through clean interface design  
✅ **Support constraint-based optimization** (budget, latency, quality)  
✅ **Facilitate research** with benchmarking and evaluation tools  
✅ **Include examples** so students can learn by doing

## Implementation

### Location

```
packages/sage-libs/src/sage/libs/workflow_optimizer/
```

**Layer**: L3 (Core - Research & Algorithm Library)  
**Dependencies**: sage-common, sage-kernel (optional for integration)

### Architecture

#### 1. Core Abstractions (`base.py`)

**WorkflowGraph**
- Represents workflows as directed acyclic graphs (DAGs)
- Nodes: agents, tools, operators, decisions, aggregators
- Edges: dependencies
- Metrics: cost, latency, quality per node
- Operations: add/remove nodes, topological sort, clone

**WorkflowNode**
- Individual workflow step with type, configuration, metrics
- Extensible metadata system

**BaseOptimizer**
- Abstract base class for optimization strategies
- `optimize(workflow, constraints) -> OptimizationResult`
- Automatic metrics calculation

**OptimizationResult**
- Contains original + optimized workflows
- Metrics (cost/latency/quality improvements)
- Optimization steps for debugging

#### 2. Constraint System (`constraints.py`)

**BaseConstraint** - Abstract interface for constraints

**Built-in Constraints**:
- `BudgetConstraint`: Maximum total cost
- `LatencyConstraint`: Maximum end-to-end latency  
- `QualityConstraint`: Minimum quality score

**ConstraintChecker**:
- Validates workflows against multiple constraints
- Returns violation details

#### 3. Evaluation (`evaluator.py`)

**WorkflowEvaluator**
- Benchmark multiple optimizers on multiple workflows
- Generate comparison tables
- Identify best optimizer per metric

**Utilities**:
- `create_synthetic_workflow()`: Generate test workflows
- Performance profiling helpers

#### 4. Example Optimizers (`optimizers/`)

**NoOpOptimizer**: Baseline (no changes)

**GreedyOptimizer**: Remove highest-cost nodes when safe
- Strategy: Sort by cost, remove if constraints still satisfied
- Simple but effective

**ParallelizationOptimizer**: Identify parallel execution opportunities
- Strategy: Find independent nodes at each level
- Conceptual (actual parallelization needs runtime support)

#### 5. Documentation

- `README.md`: Comprehensive guide with examples
- `examples.py`: Runnable code examples
- API docstrings for all classes

## Research Opportunities

Students can explore:

### Cost Optimization
- Node removal/merging
- Model substitution (GPT-4 → GPT-3.5)
- Caching and memoization
- Request batching

### Latency Optimization
- Parallelization detection
- Pipeline reordering
- Speculative execution
- Critical path analysis

### Quality Optimization
- Ensemble methods
- Verification layers
- Iterative refinement
- Confidence-based routing

### Multi-Objective
- Pareto optimization
- Constraint satisfaction
- Adaptive strategies

### Learning-Based
- Reinforcement learning policies
- Meta-learning for quick adaptation
- Transfer learning across domains

## Usage Examples

### Example 1: Basic Usage

```python
from sage.libs.workflow_optimizer import WorkflowGraph, NodeType
from sage.libs.workflow_optimizer.optimizers import GreedyOptimizer

# Create workflow
workflow = WorkflowGraph()
workflow.add_node("agent1", NodeType.AGENT, metrics={"cost": 10})
workflow.add_node("agent2", NodeType.AGENT, metrics={"cost": 20})
workflow.add_edge("agent1", "agent2")

# Optimize
optimizer = GreedyOptimizer()
result = optimizer.optimize(workflow, constraints={"max_cost": 25})

print(f"Cost reduction: {result.metrics.cost_reduction}%")
```

### Example 2: Custom Optimizer

```python
from sage.libs.workflow_optimizer import BaseOptimizer, OptimizationResult

class MyOptimizer(BaseOptimizer):
    def optimize(self, workflow, constraints=None):
        optimized = workflow.clone()
        
        # Your optimization logic here
        
        return OptimizationResult(
            original_workflow=workflow,
            optimized_workflow=optimized,
            metrics=self.calculate_metrics(workflow, optimized)
        )
```

### Example 3: Benchmarking

```python
from sage.libs.workflow_optimizer import WorkflowEvaluator

evaluator = WorkflowEvaluator()
evaluator.add_benchmark("test1", workflow1)
evaluator.add_benchmark("test2", workflow2)

results = evaluator.evaluate_all([optimizer1, optimizer2])
evaluator.print_comparison(results)
```

## Integration with SAGE

The framework is designed to integrate with SAGE's execution engine:

1. **Workflow → Pipeline**: Convert optimized WorkflowGraph to SAGE Pipeline
2. **Node → Operator**: Map WorkflowNodes to SAGE operators
3. **Execution**: Run through SAGE's streaming engine
4. **Feedback**: Collect actual metrics for learning

## Testing Strategy

### Unit Tests
- WorkflowGraph operations (add/remove, cycles, topological sort)
- Constraint checking
- Optimizer interface compliance
- Metrics calculation

### Integration Tests
- End-to-end optimization workflows
- Constraint satisfaction
- Benchmarking framework

### Performance Tests
- Optimization speed on large workflows
- Memory usage with complex graphs

## Documentation

- ✅ README.md with comprehensive guide
- ✅ examples.py with runnable code
- ✅ API docstrings for all public classes
- ✅ This design document

## Timeline

**Phase 1: Core Framework** ✅ COMPLETED
- Base abstractions
- Constraint system
- Example optimizers

**Phase 2: Examples & Documentation** ✅ COMPLETED
- Usage examples
- README guide
- API documentation

**Phase 3: Testing** (Next)
- Unit tests
- Integration tests
- Validation

**Phase 4: SAGE Integration** (Future)
- Pipeline conversion
- Operator mapping
- Runtime integration

## Success Criteria

✅ Students can implement custom optimizers in <50 lines of code  
✅ Framework handles common constraints (budget, latency, quality)  
✅ Benchmarking compares multiple strategies automatically  
✅ Examples demonstrate key concepts clearly  
✅ Integration path with SAGE is clear

## Related Issues

- #XXX: SAGE Agent Framework
- #XXX: Pipeline Optimization
- #XXX: Execution Engine Performance

## Implementation Checklist

- [x] Design core abstractions
- [x] Implement WorkflowGraph
- [x] Implement BaseOptimizer
- [x] Implement constraint system
- [x] Implement evaluator
- [x] Create example optimizers (NoOp, Greedy, Parallelization)
- [x] Write comprehensive README
- [x] Create usage examples
- [ ] Add unit tests
- [ ] Add integration tests
- [ ] Validate with student feedback
- [ ] Document SAGE integration path

## Notes

This framework follows SAGE's layered architecture:
- **L1 (sage-common)**: Not used directly
- **L2 (sage-platform)**: Not used directly  
- **L3 (sage-libs)**: Framework lives here ✅
- **L3 (sage-kernel)**: Optional integration for execution
- **L4+**: Applications can use optimized workflows

The design prioritizes:
1. **Simplicity**: Easy for students to start
2. **Extensibility**: Custom optimizers, constraints, metrics
3. **Performance**: Efficient for large workflows
4. **Integration**: Clear path to SAGE runtime

## References

- AutoGen: https://github.com/microsoft/autogen
- LangGraph: https://github.com/langchain-ai/langgraph
- DSPy: https://github.com/stanfordnlp/dspy

---

**Status**: ✅ Implementation Complete  
**Next Steps**: Testing and validation with students
