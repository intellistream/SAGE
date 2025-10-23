# sage-platform API

Platform services: queue descriptors, storage backends, and service base classes.

**Layer**: L2 (Platform Services)

## Overview

`sage-platform` provides distributed system infrastructure:

- Queue abstractions (Python, Ray, RPC)
- KV storage backends
- Service base classes
- Platform utilities

## Modules

### Queue Descriptors

::: sage.platform.queue
    options:
      show_root_heading: true
      members:
        - BaseQueueDescriptor
        - PythonQueueDescriptor
        - RayQueueDescriptor
        - RPCQueueDescriptor

### Storage Backends

::: sage.platform.storage.kv_backend
    options:
      show_root_heading: true
      members:
        - BaseKVBackend
        - DictKVBackend

### Service Base

::: sage.platform.service
    options:
      show_root_heading: true
      members:
        - BaseService

## Quick Examples

### Using Queue Descriptors

```python
from sage.platform.queue import RayQueueDescriptor

# Create a Ray queue descriptor
queue_desc = RayQueueDescriptor(maxsize=100)

# Use the queue
queue_desc.put("Hello")
data = queue_desc.get()
```

### Using KV Backend

```python
from sage.platform.storage.kv_backend import DictKVBackend

# Create in-memory KV store
store = DictKVBackend()

# Store and retrieve data
store.put("key1", {"value": 42})
data = store.get("key1")
```

## Design Decisions

- [L2 Platform Layer Design](../../concepts/architecture/design-decisions/l2-platform-layer.md)
- [RPC Queue Refactoring](../../concepts/architecture/design-decisions/rpc-queue-refactoring.md)

## See Also

- [Package Architecture](../../concepts/architecture/package-structure.md)
- [Platform Overview](../../guides/packages/sage-platform/overview.md)
