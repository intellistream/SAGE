# SAGE Integrations

**Layer**: L3 (Core - Algorithm Library)\
**Purpose**: Third-party service integrations

## Overview

This module provides standardized integrations with third-party services including:

- Vector databases (Milvus, ChromaDB)
- LLM providers (OpenAI, Hugging Face)
- Other AI services and APIs

## Components

### Vector Databases

- **milvus.py**: Milvus vector database integration
- **chroma.py**: ChromaDB vector database integration

### LLM Providers

- **openai.py**: OpenAI API utilities
- **openaiclient.py**: OpenAI client wrapper
- **huggingface.py**: Hugging Face model hub integration

## Usage

```python
from sage.libs.integrations import openai, milvus, chroma

# Use integrations as needed
```

## Design Principles

1. **Abstraction**: Provide unified interfaces for similar services
1. **Error Handling**: Gracefully handle API failures
1. **Configuration**: Use environment variables and config files
1. **Testing**: Mock external services in tests

## Dependencies

External services required:

- OpenAI API key (for openai modules)
- Milvus server (for milvus module)
- ChromaDB (for chroma module)
- Hugging Face token (for huggingface module)
