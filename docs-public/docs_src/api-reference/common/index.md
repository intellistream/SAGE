# sage-common API

Common utilities, data types, and base classes used across all SAGE packages.

**Layer**: L1 (Foundation)

## Overview

`sage-common` provides foundational components that all other SAGE packages depend on:

- Core data types and type system
- Configuration management
- Logging utilities
- Base exceptions
- Common decorators and utilities
- Model registry and embedding services

## Modules

### Core

::: sage.common.core
    options:
      show_root_heading: true
      show_source: true

### Components

#### Embedding Services

::: sage.common.components.sage_embedding
    options:
      show_root_heading: true
      members:
        - EmbeddingService
        - EmbeddingFactory

#### vLLM Integration

::: sage.common.components.sage_vllm
    options:
      show_root_heading: true
      members:
        - VLLMService

### Configuration

::: sage.common.config
    options:
      show_root_heading: true
      show_source: true

### Utilities

#### Logging

::: sage.common.utils.logging
    options:
      show_root_heading: true
      members:
        - setup_logger
        - get_logger

## Quick Examples

### Using Embedding Service

```python
from sage.common.components.sage_embedding import EmbeddingFactory

# Create embedding service
embedding = EmbeddingFactory.create_embedding(
    provider="openai",
    model_name="text-embedding-3-small"
)

# Encode text
vector = embedding.encode("Hello, world!")
print(f"Embedding dimension: {len(vector)}")
```

### Configuration Management

```python
from sage.common.config import SAGEConfig

# Load configuration
config = SAGEConfig.load("config.yaml")

# Access settings
api_key = config.get("openai_api_key")
```

## See Also

- [Package Architecture](../../concepts/architecture/package-structure.md)
- [Common Utilities Guide](../../guides/packages/sage-common/overview.md)
