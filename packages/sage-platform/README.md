# sage-platform

**Platform Services Layer (L2)** - Infrastructure abstractions for SAGE

## Overview

`sage-platform` provides core infrastructure abstractions that sit between the foundation layer (`sage-common`) and the execution engine (`sage-kernel`). It includes:

- **Queue Abstractions**: Unified interface for Python, Ray, and RPC queues
- **Storage Abstractions**: Key-Value backend interfaces
- **Service Base Classes**: Foundation for SAGE services

## Components

### 🔄 Queue (`sage.platform.queue`)

Polymorphic queue descriptors supporting multiple backends:

```python
from sage.platform.queue import (
    BaseQueueDescriptor,
    PythonQueueDescriptor,
    RayQueueDescriptor,
    RPCQueueDescriptor
)

# Create a Ray queue
queue_desc = RayQueueDescriptor(maxsize=1000, queue_id="my_queue")
queue = queue_desc.queue_instance

# Use queue operations
queue_desc.put(item)
item = queue_desc.get()
```

**Features**:
- Lazy initialization
- Serialization support
- Cross-process communication
- Backend-agnostic API

### 💾 Storage (`sage.platform.storage`)

Key-Value storage abstractions:

```python
from sage.platform.storage.kv_backend import BaseKVBackend, DictKVBackend

# Use in-memory backend
backend = DictKVBackend()
backend.set("key", "value")
value = backend.get("key")

# Extend with custom backends
class RedisKVBackend(BaseKVBackend):
    # Implement abstract methods
    ...
```

**Supported Operations**:
- `get(key)`, `set(key, value)`, `delete(key)`
- `has(key)`, `clear()`, `get_all_keys()`
- Disk persistence: `store_data_to_disk()`, `load_data_to_memory()`

### 🔌 Service (`sage.platform.service`)

Base class for SAGE services:

```python
from sage.platform.service import BaseService

class MyService(BaseService):
    def __init__(self, config):
        super().__init__(name="my_service")
        self.config = config

    def process(self, request):
        # Service logic
        return response
```

## Installation

```bash
# Basic installation
pip install isage-platform

# With Ray support
pip install isage-platform[ray]

# With Redis support
pip install isage-platform[redis]
```

## Architecture Position

```
L1: sage-common         ← Foundation
L2: sage-platform       ← YOU ARE HERE
L3: sage-kernel         ← Execution Engine
    sage-libs
L4: sage-middleware     ← Domain Components
L5: sage-apps           ← Applications
    sage-tools
    sage-benchmark
L6: sage-studio         ← User Interface
```

## Design Principles

1. **Generic Infrastructure**: Platform services are not SAGE-specific
2. **Backend Agnostic**: Support multiple implementations (Python, Ray, Redis, etc.)
3. **Minimal Dependencies**: Only depends on `sage-common`
4. **Extensible**: Easy to add new backends

## Why L2 Layer?

Originally, these abstractions were scattered:
- Queue Descriptor in `sage-kernel` (L3) ❌
- KV Backend in `sage-middleware` (L4) ❌
- BaseService in `sage-kernel` (L3) ❌

This caused:
- Architecture confusion (infrastructure mixed with business logic)
- Dependency violations (L1 → L3)
- Limited reusability

By creating L2:
- ✅ Clear separation of concerns
- ✅ Proper dependency direction
- ✅ Better reusability across components

## Contributing

See [CONTRIBUTING.md](../../CONTRIBUTING.md) for development guidelines.

## License

MIT License - see [LICENSE](../../LICENSE) for details.
