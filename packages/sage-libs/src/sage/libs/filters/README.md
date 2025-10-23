# SAGE Filters

**Layer**: L3 (Core - Algorithm Library)  
**Purpose**: Data filtering and transformation utilities

## Overview

This module provides filters and transformers for agent workflows, including:
- Tool selection and filtering
- Output evaluation and scoring
- Context data routing (sources and sinks)

## Components

### Filters
- **tool_filter.py**: Filter and select appropriate tools for tasks
- **evaluate_filter.py**: Evaluate and score agent outputs

### Context Management
- **context_source.py**: Context data sources
- **context_sink.py**: Context data sinks

## Usage

```python
from sage.libs.filters import tool_filter, evaluate_filter

# Filter tools
selected_tools = tool_filter.filter_tools(available_tools, task)

# Evaluate outputs
score = evaluate_filter.evaluate(output, criteria)
```

## Design Principles

1. **Composability**: Filters can be chained together
2. **Configurability**: Filters accept configuration parameters
3. **Extensibility**: Easy to add new filter types
4. **Performance**: Efficient filtering for large datasets

## Common Patterns

### Tool Selection
Filter tools based on:
- Task requirements
- Capability matching
- Performance metrics
- Cost constraints

### Output Evaluation
Evaluate outputs based on:
- Quality metrics
- Relevance scores
- Consistency checks
- Custom criteria
