# Agentic Registry Usage Guide

## Overview

The agentic registry system provides a unified interface for creating and managing planners, tool
selectors, and workflow optimizers. This enables loose coupling between interface and
implementation, making it easy to swap implementations or add new ones.

## Quick Start

### 1. Basic Registry Usage

```python
from sage.libs.agentic.registry import planner_registry, tool_selector_registry

# List available implementations
print("Available planners:", planner_registry.registered())
print("Available selectors:", tool_selector_registry.registered())

# Create instances via registry
planner = planner_registry.create("react", llm=llm_client)
selector = tool_selector_registry.create("hybrid", embedder=embedder)
```

### 2. Using Interfaces

```python
from sage.libs.agentic.interfaces.planner import Planner, PlanningContext, Plan
from sage.libs.agentic.interfaces.tool_selector import ToolSelector, Tool

def my_agent(planner: Planner, selector: ToolSelector):
    """Agent that works with any planner/selector implementation."""

    # Create planning context
    context = PlanningContext(
        task="Analyze this document",
        available_tools=[...],
        constraints={"max_cost": 100}
    )

    # Generate plan
    plan: Plan = planner.plan(context)

    # Select tools
    tools: list[Tool] = selector.select(
        query="search for information",
        available_tools=[...],
        k=5
    )

    return plan, tools
```

## Built-in Implementations

### Planners

| Name           | Aliases            | Description                            |
| -------------- | ------------------ | -------------------------------------- |
| `react`        | -                  | ReAct: Reasoning + Acting interleaved  |
| `tot`          | `tree_of_thoughts` | Tree of Thoughts: Multi-path reasoning |
| `hierarchical` | -                  | Hierarchical task decomposition        |
| `simple`       | `simple_llm`       | Simple LLM-based planning              |

**Usage**:

```python
from sage.libs.agentic.registry import planner_registry

# ReAct planner
react = planner_registry.create("react", llm=llm_client, max_iterations=10)

# Tree of Thoughts
tot = planner_registry.create("tot", llm=llm_client, beam_width=5)

# Hierarchical
hierarchical = planner_registry.create("hierarchical", llm=llm_client)
```

### Tool Selectors

| Name        | Aliases  | Description                   |
| ----------- | -------- | ----------------------------- |
| `keyword`   | -        | Keyword-based matching        |
| `embedding` | -        | Semantic embedding similarity |
| `hybrid`    | -        | Combined keyword + embedding  |
| `dfsdt`     | `dfs_dt` | DFS-DT decision tree selector |
| `gorilla`   | -        | Gorilla-style tool retrieval  |

**Usage**:

```python
from sage.libs.agentic.registry import tool_selector_registry

# Keyword selector
keyword = tool_selector_registry.create("keyword", config=config, resources=resources)

# Embedding selector
embedding = tool_selector_registry.create("embedding", embedder=embedder)

# Hybrid selector
hybrid = tool_selector_registry.create("hybrid", embedder=embedder, keyword_weight=0.4)
```

### Workflow Optimizers

| Name       | Aliases           | Description                                 |
| ---------- | ----------------- | ------------------------------------------- |
| `noop`     | `baseline`        | No-op optimizer (returns original workflow) |
| `greedy`   | -                 | Greedy node removal based on cost           |
| `parallel` | `parallelization` | Identifies parallelization opportunities    |

**Usage**:

```python
from sage.libs.agentic.registry import workflow_registry
from sage.libs.agentic.interfaces.workflow import WorkflowGraph

# Create workflow
workflow = WorkflowGraph()
# ... add nodes and edges ...

# No-op optimizer (baseline)
noop = workflow_registry.create("noop")
result = noop.optimize(workflow)

# Greedy optimizer
greedy = workflow_registry.create("greedy", max_removals=5)
result = greedy.optimize(workflow, constraints={"max_cost": 100})

# Parallelization optimizer
parallel = workflow_registry.create("parallel")
result = parallel.optimize(workflow)
```

## Registering Custom Implementations

### Option 1: Direct Registration

```python
from sage.libs.agentic.registry import planner_registry
from sage.libs.agentic.interfaces.planner import Planner

class MyCustomPlanner(Planner):
    def plan(self, context):
        # Custom implementation
        pass

    def replan(self, context, failed_step):
        # Custom replan logic
        pass

# Register
planner_registry.register("my_planner", lambda **kwargs: MyCustomPlanner(**kwargs))

# Use
planner = planner_registry.create("my_planner", custom_param=123)
```

### Option 2: External Package (Recommended for isage-agentic)

```python
# In isage-agentic package
from sage.libs.agentic.registry import planner_registry
from sage.libs.agentic.interfaces.planner import Planner

class AdvancedPlanner(Planner):
    # Implementation
    pass

def register_advanced_planners():
    planner_registry.register("advanced", lambda **kwargs: AdvancedPlanner(**kwargs))

# Auto-register on import
register_advanced_planners()
```

```python
# User code
from sage.libs.agentic.registry import planner_registry
import isage_agentic  # Triggers registration

planner = planner_registry.create("advanced")  # Uses external implementation
```

## Error Handling

```python
from sage.libs.agentic.registry import planner_registry

try:
    planner = planner_registry.create("nonexistent")
except KeyError as e:
    print(f"Error: {e}")
    # Suggests available planners and mentions isage-agentic package
```

## Migration Path

### Current (Transitional)

```python
# Direct import (still works, but will require isage-agentic in future)
from sage.libs.agentic.agents.planning import ReActPlanner

planner = ReActPlanner(llm=llm_client)
```

### Recommended (Forward-compatible)

```python
# Via registry (works now, will work with external package)
from sage.libs.agentic.registry import planner_registry

planner = planner_registry.create("react", llm=llm_client)
```

### Future (After externalization)

```python
# Interface stays in sage-libs, implementation in isage-agentic
from sage.libs.agentic.interfaces.planner import Planner
from sage.libs.agentic.registry import planner_registry
import isage_agentic  # Optional: for additional implementations

# Works with built-in or external implementations
planner: Planner = planner_registry.create("react", llm=llm_client)
```

## Best Practices

1. **Type hints**: Use interface types (`Planner`, `ToolSelector`) not concrete classes
1. **Dependency injection**: Pass registry-created instances to functions
1. **Fail fast**: Registry raises `KeyError` if implementation not found (no silent fallbacks)
1. **Discover implementations**: Use `registered()` to list available implementations
1. **Test with mocks**: Implement interface protocols for testing

## Example: Complete Agent Pipeline

```python
from sage.libs.agentic.registry import planner_registry, tool_selector_registry
from sage.libs.agentic.interfaces.planner import PlanningContext
from sage.libs.agentic.interfaces.tool_selector import Tool

# Setup
llm = get_llm_client()
embedder = get_embedder()

# Create components via registry
planner = planner_registry.create("react", llm=llm, max_iterations=10)
selector = tool_selector_registry.create("hybrid", embedder=embedder)

# Define tools
tools = [
    Tool(name="search", description="Search the web", parameters={}),
    Tool(name="calculator", description="Perform calculations", parameters={}),
    Tool(name="python", description="Execute Python code", parameters={}),
]

# Plan
context = PlanningContext(
    task="What is the population of France divided by 2?",
    available_tools=tools,
    constraints={"max_cost": 10},
)
plan = planner.plan(context)

# Select relevant tools
selected_tools = selector.select(
    query=context.task,
    available_tools=tools,
    k=3
)

print(f"Plan: {plan.steps}")
print(f"Selected tools: {[t.name for t in selected_tools]}")
```

## See Also

- `packages/sage-libs/docs/agentic/EXTERNALIZATION_PLAN.md` - Migration strategy
- `packages/sage-libs/src/sage/libs/agentic/interfaces/` - Interface definitions
- `packages/sage-libs/src/sage/libs/agentic/README.md` - Module overview
