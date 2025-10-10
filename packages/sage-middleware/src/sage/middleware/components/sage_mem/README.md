# SAGE-Mem Component

SAGE-Mem is a memory management component for SAGE, providing flexible memory collection abstractions for RAG (Retrieval-Augmented Generation) applications.

## 🏗️ Architecture

```
sage-mem/
├── __init__.py              # Main export layer
├── examples/                # Usage examples for sage-mem
│   ├── basic_memory_manager.py
│   └── vdb_service_demo.py
├── services/                # Service layer (combines neuromem functionality)
│   ├── neuromem_vdb.py
│   └── neuromem_vdb_service.py
└── neuromem/                # ⭐ Git Submodule -> intellistream/neuromem
    ├── memory_manager.py
    ├── memory_collection/
    ├── search_engine/
    ├── storage_engine/
    └── utils/
```

> **Note**: The `neuromem/` directory is now a **Git submodule** pointing to the independent [intellistream/neuromem](https://github.com/intellistream/neuromem) repository.

## Components

### 1. neuromem (Core Sub-Project - Git Submodule)

The core memory management engine, now maintained as an independent repository at [`intellistream/neuromem`](https://github.com/intellistream/neuromem).

**Features**:
- **MemoryManager**: Central manager for memory collections
- **Memory Collections**: VDB, KV, and Graph collection types
- **Search Engine**: Multiple index implementations (FAISS, BM25s, etc.)
- **Storage Engine**: Pluggable storage backends

**Design Philosophy**: neuromem is standalone and self-contained, usable independently from SAGE.

**Repository**: https://github.com/intellistream/neuromem

### 2. services (Service Layer)

Pre-defined services that combine neuromem functionality into higher-level APIs:

- **NeuroMemVDB**: Convenience class for VDB operations
- **NeuroMemVDBService**: BaseService implementation for SAGE integration

**Design Philosophy**: Services compose neuromem components into SAGE-compatible services.

### 3. examples

Demonstrates how to use sage-mem components:

- `basic_memory_manager.py`: Direct usage of MemoryManager
- `vdb_service_demo.py`: Using NeuroMemVDB service

## 🚀 Usage

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

## 🔧 Development

### Working with neuromem Submodule

The `neuromem/` directory is a Git submodule pointing to an independent repository. 

#### First-time Setup (New Team Members)

When cloning SAGE for the first time:

```bash
# Clone with all submodules
git clone --recurse-submodules https://github.com/intellistream/SAGE.git

# Or if already cloned, initialize submodules
cd SAGE
git submodule update --init --recursive
```

#### Updating neuromem to Latest Version

```bash
# Navigate to neuromem submodule
cd packages/sage-middleware/src/sage/middleware/components/sage_mem/neuromem

# Update to latest main-dev
git checkout main-dev
git pull origin main-dev

# Go back to SAGE root and commit the submodule update
cd ../../../../../../../../
git add packages/sage-middleware/src/sage/middleware/components/sage_mem/neuromem
git commit -m "chore: update neuromem submodule to latest version"
git push
```

#### Making Changes to neuromem

If you need to modify neuromem core functionality:

1. **Make changes in the submodule directory**:
   ```bash
   cd packages/sage-middleware/src/sage/middleware/components/sage_mem/neuromem
   git checkout -b feature/my-feature
   # ... make your changes ...
   git add .
   git commit -m "feat: add new feature"
   git push origin feature/my-feature
   ```

2. **Create PR in neuromem repository**:
   ```bash
   gh pr create --repo intellistream/neuromem --base main-dev --head feature/my-feature
   ```

3. **After PR is merged, update SAGE**:
   ```bash
   cd packages/sage-middleware/src/sage/middleware/components/sage_mem/neuromem
   git checkout main-dev
   git pull origin main-dev
   cd ../../../../../../../../
   git add packages/sage-middleware/src/sage/middleware/components/sage_mem/neuromem
   git commit -m "chore: update neuromem submodule"
   git push
   ```

#### Checking Submodule Status

```bash
# View all submodules and their status
git submodule status

# View neuromem-specific information
cd packages/sage-middleware/src/sage/middleware/components/sage_mem/neuromem
git log --oneline -5
git remote -v
```

### Service Layer Development

For SAGE-specific services (in `services/`), make changes directly in the SAGE repository:

```bash
# Edit services
vim packages/sage-middleware/src/sage/middleware/components/sage_mem/services/neuromem_vdb.py

# Commit to SAGE
git add packages/sage-middleware/src/sage/middleware/components/sage_mem/services/
git commit -m "feat: enhance NeuroMemVDB service"
git push
```

### Testing

```bash
# Run all neuromem tests
pytest packages/sage-middleware/tests/neuromem/ -v

# Run specific test
pytest packages/sage-middleware/tests/neuromem/test_manager.py -v

# Run examples
python examples/memory/rag_memory_manager.py
```

## 📚 Documentation

- **neuromem Core**: See [neuromem/README.md](neuromem/README.md) or visit https://github.com/intellistream/neuromem
- **Service Layer**: Documentation in this README
- **Examples**: Check `examples/` directory
- **Extraction Guide**: See [NEUROMEM_EXTRACTION_GUIDE.md](NEUROMEM_EXTRACTION_GUIDE.md) for how neuromem was extracted
- **Quick Reference**: See [QUICK_REFERENCE.md](QUICK_REFERENCE.md) for submodule management tips

## 🔗 Related Projects

- **neuromem**: https://github.com/intellistream/neuromem - Standalone memory management engine
- **sageFlow**: Similar pattern for workflow management
- **sageDB**: Similar pattern for database operations

## Future Plans

- Enhance neuromem with more index types and storage backends
- Improve integration with SAGE's service framework  
- Add more pre-built services for common RAG patterns

## License

See LICENSE file in the SAGE project root.
