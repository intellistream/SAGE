# sage-platform: Platform Services (L2)

## Overview

`sage-platform` provides cross-cutting platform services including RPC, distributed queuing, resource management, and observability.

## Key Components

### RPC System
- **RPC Framework**: Asynchronous RPC with multiple transports
- **Service Registry**: Service discovery and registration
- **Load Balancing**: Intelligent request routing

### Queue System
- **Distributed Queue**: High-performance distributed task queue
- **Priority Scheduling**: Priority-based task execution
- **Dead Letter Queue**: Failed task handling

### Resource Management
- **Allocator**: Resource allocation and tracking
- **Scheduler**: Task scheduling and orchestration
- **Monitor**: Resource usage monitoring

### Observability
- **Metrics**: Performance metrics collection
- **Tracing**: Distributed tracing
- **Logging**: Centralized logging infrastructure

## Architecture

```
sage-platform/
├── rpc/            # RPC framework
├── queue/          # Distributed queue
├── resources/      # Resource management
└── observability/  # Metrics, tracing, logging
```

## Usage

```python
from sage.platform.rpc import RPCClient, RPCServer
from sage.platform.queue import DistributedQueue

# Create RPC client
client = RPCClient("service_name")
response = await client.call("method", args)

# Use distributed queue
queue = DistributedQueue("task_queue")
await queue.push(task)
```

## Dependencies

- **External**: grpcio, aio-pika, prometheus-client
- **Internal**: sage-common (L1)

## Design Decisions

- [RPC Queue Refactoring](../../architecture/design-decisions/rpc-queue-refactoring.md)
- [L2 Platform Layer Analysis](../../architecture/design-decisions/l2-platform-layer.md)

## See Also

- [Architecture Overview](../../architecture/overview.md)
- [sage-kernel Documentation](../kernel/overview.md)
- [sage-libs Documentation](../libs/overview.md)
