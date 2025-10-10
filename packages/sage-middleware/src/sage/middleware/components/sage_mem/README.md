# SAGE-Mem Component

SAGE-Mem is a memory management component for SAGE, providing flexible memory collection abstractions for RAG (Retrieval-Augmented Generation) applications.

## Architecture

```
sage-mem/
├── __init__.py              # Main export layer
├── examples/                # Usage examples for sage-mem
│   ├── basic_memory_manager.py
│   └── vdb_service_demo.py
├── services/                # Service layer (combines neuromem functionality)
│   ├── neuromem_vdb.py
│   └── neuromem_vdb_service.py
└── neuromem/                # Core sub-project (will be independent repo)
    ├── memory_manager.py
    ├── memory_collection/
    ├── search_engine/
    ├── storage_engine/
    ├── utils/
    ├── examples/            # neuromem-specific examples
    └── tests/               # neuromem-specific tests
```

## Components

### 1. neuromem (Core Sub-Project)

The core memory management engine that will eventually be separated into its own repository. It provides:

- **MemoryManager**: Central manager for memory collections
- **Memory Collections**: VDB, KV, and Graph collection types
- **Search Engine**: Multiple index implementations (FAISS, BM25s, etc.)
- **Storage Engine**: Pluggable storage backends

**Design Philosophy**: neuromem should be standalone and self-contained, usable independently from SAGE.

### 2. services (Service Layer)

Pre-defined services that combine neuromem functionality into higher-level APIs:

- **NeuroMemVDB**: Convenience class for VDB operations
- **NeuroMemVDBService**: BaseService implementation for SAGE integration

**Design Philosophy**: Services compose neuromem components into SAGE-compatible services.

### 3. examples

Demonstrates how to use sage-mem components:

- `basic_memory_manager.py`: Direct usage of MemoryManager
- `vdb_service_demo.py`: Using NeuroMemVDB service

## Usage

### Option 1: Simple Import (Recommended)

```python
from sage.middleware.components.sage_mem import MemoryManager, NeuroMemVDB

# Use MemoryManager
manager = MemoryManager()
collection = manager.create_collection({
    "name": "my_collection",
    "backend_type": "VDB"
})

# Or use the service
vdb = NeuroMemVDB()
vdb.register_collection("my_vdb")
```

### Option 2: Direct Import from Sub-Project

```python
from sage.middleware.components.sage_mem.neuromem import MemoryManager
from sage.middleware.components.sage_mem.neuromem.memory_collection import VDBMemoryCollection

# Work directly with core components
manager = MemoryManager()
```

### Option 3: Import from Service Layer

```python
from sage.middleware.components.sage_mem.services import NeuroMemVDB, NeuroMemVDBService

# Use pre-defined services
vdb = NeuroMemVDB()
```

## Migration from Old neuromem

The old `neuromem` module has been refactored into `sage-mem`. A backward compatibility layer is provided, but please update your code:

**Old way:**
```python
from sage.middleware.components.neuromem import MemoryManager
from sage.middleware.components.neuromem.micro_service.neuromem_vdb import NeuroMemVDB
```

**New way:**
```python
from sage.middleware.components.sage_mem import MemoryManager, NeuroMemVDB
```

## Future Plans

- The `neuromem` sub-project will be separated into its own repository
- Potential rewrite in C++/Rust for performance improvements
- Enhanced integration with SAGE's service framework

## Development

For neuromem-specific development, see `neuromem/README.md`.

For service-level examples, see `examples/` directory.

## License

See LICENSE file in the SAGE project root.
