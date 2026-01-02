# Scheduling Strategies

This directory contains scheduling strategy implementations for the sageLLM Control Plane.

## Directory Structure

```
strategies/
├── __init__.py          # Module exports
├── base.py              # SchedulingPolicy abstract base class
├── fifo.py              # First-In-First-Out strategy
├── priority.py          # Priority-based strategy
├── slo_aware.py         # SLO deadline-aware strategy
├── cost_optimized.py    # Cost-optimized strategy
├── adaptive.py          # Adaptive strategy selection
└── README.md            # This file
```

## Available Strategies

### 1. FIFOPolicy (`fifo.py`)

**Description**: Simple First-In-First-Out scheduling

**Use Case**: Fair scheduling without special requirements

**Behavior**:

- Schedules requests in arrival order
- Selects least loaded instance for each request

**Example**:

```python
from control_plane.strategies import FIFOPolicy
manager = ControlPlaneManager(scheduling_policy=FIFOPolicy())
```

### 2. PriorityPolicy (`priority.py`)

**Description**: Priority-based scheduling with performance optimization

**Use Case**: Systems with clear priority levels

**Behavior**:

- Schedules high-priority requests first
- Uses fastest instances for CRITICAL/HIGH priority
- Uses least loaded instances for NORMAL/LOW priority

**Example**:

```python
from control_plane.strategies import PriorityPolicy
manager = ControlPlaneManager(scheduling_policy=PriorityPolicy())
```

### 3. SLOAwarePolicy (`slo_aware.py`)

**Description**: SLO deadline-aware scheduling with urgency calculation

**Use Case**: Production systems with strict latency requirements

**Behavior**:

- Calculates urgency score based on remaining time
- Prioritizes requests approaching their SLO deadline
- Uses fastest instances for urgent requests

**Example**:

```python
from control_plane.strategies import SLOAwarePolicy
manager = ControlPlaneManager(scheduling_policy=SLOAwarePolicy())
```

### 4. CostOptimizedPolicy (`cost_optimized.py`)

**Description**: Cost-aware scheduling to minimize operational costs

**Use Case**: Budget-constrained environments with variable instance types

**Behavior**:

- Estimates cost per request based on GPU usage
- Selects cheapest instance that can meet requirements
- Considers token count and instance GPU count

**Example**:

```python
from control_plane.strategies import CostOptimizedPolicy
policy = CostOptimizedPolicy(price_per_gpu_hour=2.5)
manager = ControlPlaneManager(scheduling_policy=policy)
```

### 5. AdaptivePolicy (`adaptive.py`)

**Description**: Dynamically switches between strategies based on system state

**Use Case**: Dynamic workloads with changing characteristics

**Behavior**:

- Monitors system metrics (load, SLO requests, priorities)
- Switches to PriorityPolicy when high-priority requests present
- Switches to SLOAwarePolicy under high load with SLO requests
- Switches to CostOptimizedPolicy under low load
- Defaults to SLOAwarePolicy

**Example**:

```python
from control_plane.strategies import AdaptivePolicy
manager = ControlPlaneManager(scheduling_policy=AdaptivePolicy())
```

## Creating Custom Strategies

### Step 1: Create a new file

Create `control_plane/strategies/my_strategy.py`:

```python
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""My custom scheduling strategy."""

from .base import SchedulingPolicy
from control_plane.types import (
    ExecutionInstance,
    ParallelismType,
    RequestMetadata,
    SchedulingDecision,
)


class MyCustomPolicy(SchedulingPolicy):
    """My custom scheduling policy."""

    def __init__(self):
        super().__init__("MyCustom")

    def schedule(
        self,
        requests: list[RequestMetadata],
        instances: list[ExecutionInstance],
    ) -> list[SchedulingDecision]:
        """Schedule requests with custom logic."""
        decisions = []

        # Your scheduling logic here
        sorted_requests = self.prioritize(requests)

        for request in sorted_requests:
            available = [i for i in instances if i.can_accept_request]
            if not available:
                continue

            # Select instance based on your criteria
            target = min(available, key=lambda i: i.current_load)

            decision = SchedulingDecision(
                request_id=request.request_id,
                target_instance_id=target.instance_id,
                parallelism_strategy=ParallelismType.TENSOR_PARALLEL,
                tensor_parallel_size=target.tensor_parallel_size,
                pipeline_parallel_size=target.pipeline_parallel_size,
                estimated_latency_ms=target.avg_latency_ms,
                estimated_cost=0.0,
                reason="My custom scheduling logic",
            )
            decisions.append(decision)

        return decisions

    def prioritize(self, requests: list[RequestMetadata]) -> list[RequestMetadata]:
        """Prioritize requests for scheduling."""
        # Your prioritization logic
        return sorted(requests, key=lambda r: r.arrival_time)
```

### Step 2: Export from `__init__.py`

Add your strategy to `control_plane/strategies/__init__.py`:

```python
from .my_strategy import MyCustomPolicy

__all__ = [
    # ... existing exports
    "MyCustomPolicy",
]
```

### Step 3: Use your strategy

```python
from control_plane.strategies import MyCustomPolicy
manager = ControlPlaneManager(scheduling_policy=MyCustomPolicy())
```

## Strategy Interface

All strategies must implement the `SchedulingPolicy` interface defined in `base.py`:

### Required Methods

#### `schedule(requests, instances) -> list[SchedulingDecision]`

Main scheduling logic that assigns requests to instances.

**Parameters**:

- `requests`: List of pending requests to schedule
- `instances`: List of available execution instances

**Returns**: List of scheduling decisions

**Constraints**:

- Do NOT modify input lists
- Return empty list if no scheduling is possible
- Each decision must reference a valid request and instance

#### `prioritize(requests) -> list[RequestMetadata]`

Sorts requests by priority for scheduling order.

**Parameters**:

- `requests`: List of requests to prioritize

**Returns**: Sorted list of requests

### Request Information

Each `RequestMetadata` provides:

- `request_id`: Unique identifier
- `prompt`: Input text
- `max_tokens`: Maximum generation length
- `model_name`: Required model
- `priority`: RequestPriority enum (CRITICAL/HIGH/NORMAL/LOW/BACKGROUND)
- `slo_deadline_ms`: Optional SLO deadline in milliseconds
- `user_id`: Optional user identifier
- `arrival_time`: Submission timestamp
- `cost_budget`: Optional cost limit

### Instance Information

Each `ExecutionInstance` provides:

- `instance_id`: Unique identifier
- `host`, `port`: Network address
- `model_name`: Deployed model
- `tensor_parallel_size`: TP parallelism degree
- `pipeline_parallel_size`: PP parallelism degree
- `gpu_count`: Number of GPUs
- `can_accept_request`: Availability flag
- `current_load`: Running request count
- `max_concurrency`: Maximum concurrent requests
- `avg_latency_ms`: Average response latency
- `throughput_tokens_per_sec`: Throughput estimate

## Testing Your Strategy

Create `tests/control_plane/test_my_strategy.py`:

```python
import pytest
from control_plane.strategies import MyCustomPolicy
from control_plane.types import RequestMetadata, ExecutionInstance, RequestPriority

@pytest.fixture
def policy():
    return MyCustomPolicy()

@pytest.fixture
def sample_requests():
    return [
        RequestMetadata(
            request_id="req-1",
            prompt="Test",
            max_tokens=10,
            model_name="llama-2-7b",
            priority=RequestPriority.NORMAL,
        )
    ]

@pytest.fixture
def sample_instances():
    return [
        ExecutionInstance(
            instance_id="inst-1",
            host="localhost",
            port=8000,
            model_name="llama-2-7b",
            tensor_parallel_size=1,
            gpu_count=1,
        )
    ]

def test_schedule(policy, sample_requests, sample_instances):
    """Test scheduling behavior."""
    decisions = policy.schedule(sample_requests, sample_instances)
    assert len(decisions) == 1
    assert decisions[0].request_id == "req-1"
    assert decisions[0].target_instance_id == "inst-1"

def test_prioritize(policy, sample_requests):
    """Test prioritization logic."""
    prioritized = policy.prioritize(sample_requests)
    assert len(prioritized) == len(sample_requests)
```

Run tests:

```bash
pytest tests/control_plane/test_my_strategy.py -v
```

## Best Practices

1. **Performance**: Keep `schedule()` fast (< 1ms per decision)

   - Avoid O(n²) loops
   - Cache expensive calculations
   - Use list comprehensions

1. **Robustness**: Handle edge cases

   - Empty request/instance lists
   - No compatible instances
   - Already failed requests

1. **Observability**: Add logging

   - Log scheduling decisions
   - Track strategy metrics
   - Include reasoning in decisions

1. **Configurability**: Support parameters

   - Allow threshold tuning
   - Expose weight configurations
   - Document parameter effects

## Documentation

For detailed guidance on developing custom strategies, see:

- **[Custom Scheduling Guide](../../docs/CUSTOM_SCHEDULING.md)**: Comprehensive tutorial
- **[Metrics Documentation](../../docs/METRICS.md)**: Using metrics in strategies
- **[Topology Configuration](../../docs/TOPOLOGY.md)**: Leveraging topology information

## Related Files

- `control_plane/manager.py`: Strategy integration
- `control_plane/router.py`: Instance selection after scheduling
- `control_plane/monitoring.py`: Metrics collection for strategies
- `control_plane/topology.py`: Topology information for scheduling
- `tests/control_plane/test_scheduling.py`: Strategy integration tests
