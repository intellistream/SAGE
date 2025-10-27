# sage-middleware API

Domain-specific components and operators for RAG, LLM, memory, and database systems.

**Layer**: L4 (Domain Components)

## Overview

`sage-middleware` provides high-level domain-specific components:

- **Operators**: Pre-built RAG and LLM operators for pipelines
- **Components**: NeuroMem (memory), SageDB, SageFlow, SageTSDB
- **Services**: Memory services, vector databases, embeddings

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

#### SageDB

::: sage.middleware.components.sage_db
    options:
      show_root_heading: true
      members:
        - SageDB
        - DatabaseService

## Quick Examples

### Using RAG Operators

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

### Using NeuroMem

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

### Using vLLM Service

```python
from sage.middleware.operators.llm import VLLMGenerator

# Use local vLLM service
generator = VLLMGenerator(
    model_name="meta-llama/Llama-2-13b-chat-hf",
    base_url="http://localhost:8000/v1"
)

# In pipeline
stream = env.from_source(prompts).map(generator).sink(output)
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
