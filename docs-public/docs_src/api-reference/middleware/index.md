# sage-middleware API

Domain-specific components and operators for RAG, LLM, memory, and database systems.

**Layer**: L4 (Domain Components)

## Overview

`sage-middleware` provides high-level domain-specific components:

- **Operators**: Pre-built RAG and LLM operators for pipelines
- **Components**: NeuroMem (memory), SageDB, SageFlow, SageTSDB, SageRefiner
- **Services**: Memory services, vector databases, embeddings
- **C++ Extensions**: High-performance SONG GPU acceleration

## Modules

### Operators

#### RAG Operators

::: sage.middleware.operators.rag
    options:
      show_root_heading: true
      members:
        - OpenAIGenerator
        - ChromaRetriever
        - MilvusRetriever
        - QAPromptor
        - RefinerOperator

#### LLM Operators

::: sage.middleware.operators.llm
    options:
      show_root_heading: true
      members:
        - VLLMGenerator
        - VLLMEmbedding
        - OpenAIOperator

#### Tool Operators

::: sage.middleware.operators.tools
    options:
      show_root_heading: true
      members:
        - SearcherOperator
        - ImageCaptionerOperator

### Components

#### NeuroMem (Memory Service)

::: sage.middleware.components.sage_mem.neuromem
    options:
      show_root_heading: true
      members:
        - NeuroMem
        - MemoryService

NeuroMem provides intelligent memory management with vector storage:

```python
from sage.middleware.components.sage_mem import NeuroMem

# Initialize memory service
memory = NeuroMem(
    embedding_service="openai",
    vector_db="chroma"
)

# Store memory
memory.store(
    content="Paris is the capital of France",
    metadata={"source": "geography"}
)

# Recall memory
results = memory.recall(
    query="What is the capital of France?",
    top_k=3
)
```

#### SageDB

::: sage.middleware.components.sage_db
    options:
      show_root_heading: true
      members:
        - SageDB
        - DatabaseService

#### SageFlow

::: sage.middleware.components.sage_flow
    options:
      show_root_heading: true
      members:
        - SageFlow

#### SageTSDB (Time Series Database)

::: sage.middleware.components.sage_tsdb
    options:
      show_root_heading: true
      members:
        - SageTSDB

#### SageRefiner

::: sage.middleware.components.sage_refiner
    options:
      show_root_heading: true
      members:
        - SageRefiner

### Multimodal Storage ⭐ NEW

Support for storing and retrieving multimodal data (text, images, audio):

```python
from sage.middleware.components.sage_mem import MultimodalStorage

storage = MultimodalStorage(
    vector_db="chroma",
    embedding_service="openai"
)

# Store multimodal content
storage.store(
    content=image_bytes,
    content_type="image",
    metadata={"description": "A cat"}
)

# Retrieve by semantic query
results = storage.search(
    query="pictures of animals",
    top_k=5
)
```

### AutoStop Service

Remote service lifecycle management:

```python
from sage.middleware.services import AutoStopService

# Create service with auto-shutdown
service = AutoStopService(
    timeout_seconds=300,  # Auto-stop after 5 min idle
    mode="remote"
)

# Service automatically stops when idle
```

## Quick Examples

### Using RAG Operators in Pipeline

```python
from sage.kernel.api.local_environment import LocalStreamEnvironment
from sage.middleware.operators.rag import (
    QAPromptor,
    ChromaRetriever,
    OpenAIGenerator
)

env = LocalStreamEnvironment("rag_pipeline")

# Build RAG pipeline with middleware operators
stream = (env
    .from_source(questions)
    .map(QAPromptor, {
        "template": "Question: {question}\nContext: {context}\nAnswer:"
    })
    .map(ChromaRetriever, {
        "collection_name": "documents",
        "top_k": 3
    })
    .map(OpenAIGenerator, {
        "model": "gpt-4",
        "temperature": 0.7
    })
    .sink(output)
)

env.execute()
```

### Using vLLM Service

```python
from sage.middleware.operators.llm import VLLMGenerator
from sage.common.config.ports import SagePorts

# Use local vLLM service with SagePorts
generator = VLLMGenerator(
    model_name="Qwen/Qwen2.5-7B-Instruct",
    base_url=f"http://localhost:{SagePorts.BENCHMARK_LLM}/v1"
)

# In pipeline
stream = env.from_source(prompts).map(generator).sink(output)
```

## C++ Extensions

High-performance components built with C++:

### SONG GPU Acceleration

SONG (Self-Organizing Navigable Greedy) graph for fast ANN search:

```python
from sage.middleware.components.extensions import song_gpu

# Create SONG index
index = song_gpu.create_index(
    dimension=384,
    metric="cosine"
)

# Add vectors
index.add(vectors)

# Search
results = index.search(query_vector, k=10)
```

**Build Requirements:**
- CMake 3.18+
- CUDA Toolkit (for GPU support)
- OpenBLAS / LAPACK

## Module Organization

```
sage.middleware/
├── operators/                  # Pipeline operators
│   ├── rag/                   # RAG operators
│   ├── llm/                   # LLM operators
│   └── tools/                 # Tool operators
├── components/                 # Core components
│   ├── sage_mem/              # NeuroMem memory service
│   │   ├── neuromem/          # Memory management
│   │   └── multimodal/        # Multimodal storage
│   ├── sage_db/               # Database service
│   ├── sage_flow/             # Flow engine
│   ├── sage_tsdb/             # Time series DB
│   ├── sage_refiner/          # Refiner service
│   └── song/                  # SONG GPU (C++ extension)
└── services/                   # Service utilities
    └── autostop/              # Auto-stop service
```

## Component Guides

- [NeuroMem Guide](../../guides/packages/sage-middleware/components/neuromem.md)
- [SageDB Guide](../../guides/packages/sage-middleware/components/sage_db.md)
- [Middleware Overview](../../guides/packages/sage-middleware/overview.md)

## Service APIs

- [Service Introduction](../../guides/packages/sage-middleware/service/service_intro.md)
- [Memory Service](../../guides/packages/sage-middleware/service/memory/memory_service.md)
- [Vector Databases](../../guides/packages/sage-middleware/service/neuromem/vdb/vdb.md)

## See Also

- [Middleware Instrumentation](../../guides/packages/sage-middleware/middleware_instrument.md)
- [GPU Acceleration](../../guides/packages/sage-middleware/hardware/gpu_acceleration.md)
- [Service API](../../guides/packages/sage-middleware/api/service_api.md)
