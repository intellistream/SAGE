# sage-kernel API

Execution engine, runtime, and streaming operators.

**Layer**: L3 (Core Engine)

## Overview

`sage-kernel` is the heart of SAGE's streaming execution engine:

- DataStream API for pipeline construction
- Execution environments (local, distributed)
- Core operators (map, filter, join, window, aggregate)
- Runtime system (scheduler, task manager, graph compiler)
- Job management and monitoring

## API Modules

### Environment API

::: sage.kernel.api.local_environment.LocalStreamEnvironment
    options:
      show_root_heading: true
      show_source: false
      members:
        - from_source
        - add_source
        - execute
        - submit

### DataStream API

::: sage.kernel.api.datastream.DataStream
    options:
      show_root_heading: true
      show_source: false
      members:
        - map
        - filter
        - flat_map
        - key_by
        - window
        - join
        - sink
        - print

### Function API

#### Map Function

::: sage.kernel.api.function.map_function.MapFunction
    options:
      show_root_heading: true
      members:
        - map
        - setup
        - teardown

#### Filter Function

::: sage.kernel.api.function.filter_function.FilterFunction
    options:
      show_root_heading: true
      members:
        - filter

### Operators

::: sage.kernel.operators
    options:
      show_root_heading: true
      members:
        - MapOperator
        - FilterOperator
        - FlatMapOperator
        - JoinOperator
        - WindowOperator

## Quick Examples

### Basic Pipeline

```python
from sage.kernel.api.local_environment import LocalStreamEnvironment
from sage.kernel.api.function.map_function import MapFunction

class UpperCaseMap(MapFunction):
    def map(self, value):
        return value.upper()

env = LocalStreamEnvironment("example")

# Build pipeline
stream = (env
    .from_source(data_source)
    .map(UpperCaseMap)
    .filter(lambda x: len(x) > 5)
    .sink(sink)
)

# Execute
env.execute()
```

### Service-Based Pipeline

```python
from sage.kernel.api.service import BaseService

class LLMService(BaseService):
    def process(self, request):
        # Your LLM processing logic
        return response

# Use in pipeline
env.add_service("llm", LLMService, config={...})
stream = env.from_source(...).map_service("llm").sink(...)
```

## Architecture

- [Kernel Architecture](../../guides/packages/sage-kernel/architecture.md)
- [Dataflow Model](../../guides/packages/sage-kernel/core/dataflow_model.md)
- [Execution Environments](../../guides/packages/sage-kernel/core/execution_environments.md)

## Advanced Topics

- [Runtime Communication](../../guides/packages/sage-kernel/runtime_communication.md)
- [Runtime Services](../../guides/packages/sage-kernel/runtime_services.md)
- [Runtime Tasks](../../guides/packages/sage-kernel/runtime_tasks.md)

## See Also

- [Getting Started](../../getting-started/quickstart.md)
- [Kernel Guide](../../guides/packages/sage-kernel/README.md)
- [Best Practices](../../guides/packages/sage-kernel/best-practices.md)
