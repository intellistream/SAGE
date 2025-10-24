# SAGE Platform

> Platform Services Layer (L2) - Infrastructure abstractions for SAGE

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](../../LICENSE)

## 📋 Overview

**SAGE Platform** provides core infrastructure abstractions that sit between the foundation layer (`sage-common`) and the execution engine (`sage-kernel`). This Layer-2 platform service offers:

- **Queue Abstractions**: Unified interface for Python, Ray, and RPC queues
- **Storage Abstractions**: Pluggable key-value storage backends
- **Service Base Classes**: Foundation for building SAGE services
- **Platform Interfaces**: Common patterns for distributed systems

This package enables seamless switching between local and distributed execution modes without changing application code.

## ✨ Key Features

- **Polymorphic Queues**: Single API for Python Queue, Ray Queue, and RPC Queue
- **Pluggable Storage**: In-memory, Redis, and custom storage backends
- **Service Framework**: Base classes for building platform services
- **Type-Safe**: Full type hints and runtime validation
- **Zero-Overhead**: Minimal abstraction cost for local execution

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

## 📦 Package Structure

```
sage-platform/
├── src/
│   └── sage/
│       └── platform/
│           ├── __init__.py
│           ├── queue/              # Queue abstractions
│           │   ├── base.py
│           │   ├── python_queue.py
│           │   ├── ray_queue.py
│           │   └── rpc_queue.py
│           ├── storage/            # Storage backends
│           │   └── kv_backend.py
│           └── service/            # Service base classes
│               └── base.py
├── tests/
├── pyproject.toml
└── README.md
```

## 🚀 Installation

### Basic Installation

```bash
pip install sage-platform
```

### Development Installation

```bash
cd packages/sage-platform
pip install -e .
```

### With Optional Dependencies

```bash
# With Ray support (distributed queues)
pip install sage-platform[ray]

# With Redis support (distributed storage)
pip install sage-platform[redis]

# Full installation
pip install sage-platform[all]
```

## 📖 Quick Start

### Using Queues

```python
from sage.platform.queue import RayQueueDescriptor

# Create a distributed queue
queue_desc = RayQueueDescriptor(
    maxsize=1000,
    queue_id="my_distributed_queue"
)

# Producer
queue_desc.put({"task": "process_data", "data": [1, 2, 3]})

# Consumer
task = queue_desc.get()
print(f"Processing: {task}")

# Check queue status
print(f"Queue size: {queue_desc.qsize()}")
print(f"Empty: {queue_desc.empty()}")
```

### Using Storage

```python
from sage.platform.storage.kv_backend import DictKVBackend

# Create storage backend
storage = DictKVBackend()

# Store data
storage.set("user:1", {"name": "Alice", "age": 30})
storage.set("user:2", {"name": "Bob", "age": 25})

# Retrieve data
user = storage.get("user:1")
print(f"User: {user}")

# List all keys
keys = storage.get_all_keys()
print(f"All keys: {keys}")

# Persist to disk
storage.store_data_to_disk("storage.pkl")
```

### Creating a Service

```python
from sage.platform.service import BaseService

class DataProcessingService(BaseService):
    def __init__(self, config):
        super().__init__(name="data_processing")
        self.config = config
        self.initialize()
    
    def initialize(self):
        """Initialize service resources"""
        self.logger.info(f"Initializing {self.name}")
    
    def process(self, request):
        """Process incoming requests"""
        self.logger.debug(f"Processing request: {request}")
        result = self._transform_data(request["data"])
        return {"status": "success", "result": result}
    
    def _transform_data(self, data):
        # Service logic
        return [x * 2 for x in data]

# Use service
service = DataProcessingService({"param": "value"})
result = service.process({"data": [1, 2, 3]})
print(result)  # {"status": "success", "result": [2, 4, 6]}
```

## 🔧 Configuration

Services can be configured through environment variables or configuration files:

```yaml
# platform_config.yaml
platform:
  queue:
    backend: ray  # or python, rpc
    maxsize: 1000
  
  storage:
    backend: dict  # or redis
    persist: true
    save_path: ./storage
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

## 🧪 Testing

```bash
# Run unit tests
pytest tests/unit

# Run integration tests
pytest tests/integration

# Run with coverage
pytest --cov=sage.platform --cov-report=html
```

## 📚 Documentation

- **User Guide**: See [docs-public](https://intellistream.github.io/SAGE-Pub/guides/packages/sage-platform/)
- **API Reference**: See package docstrings and type hints
- **Architecture**: See [Platform Layer Design](https://intellistream.github.io/SAGE-Pub/concepts/architecture/design-decisions/l2-platform-layer/)

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](../../CONTRIBUTING.md) for guidelines.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](../../LICENSE) file for details.

## 🔗 Related Packages

- **sage-common**: Foundation layer (L1) - provides basic utilities
- **sage-kernel**: Execution engine (L3) - uses platform abstractions
- **sage-middleware**: Service layer (L4) - uses storage and queues
- **sage-libs**: Library layer (L5) - uses all platform services

## 📮 Support

- **Documentation**: https://intellistream.github.io/SAGE-Pub/
- **Issues**: https://github.com/intellistream/SAGE/issues
- **Discussions**: https://github.com/intellistream/SAGE/discussions

---

**Part of the SAGE Framework** | [Main Repository](https://github.com/intellistream/SAGE)
