# High-Performance Vector Database Insertion

## Overview

This document describes strategies for improving vector database insertion performance when working with large datasets (100K+ or 1M+ records) in SAGE.

## Recommended Approach: EmbeddingService

SAGE provides `EmbeddingService` with built-in batch processing and caching for high-performance embedding generation. This is the recommended approach for large-scale data insertion.

### Quick Start

```python
from sage.common.components.sage_embedding import EmbeddingService

# Configure service
config = {
    "method": "hf",
    "model": "BAAI/bge-small-zh-v1.5",
    "batch_size": 32,
    "cache_enabled": True,
}

service = EmbeddingService(config)
service.setup()

# Batch embed texts
texts = ["text 1", "text 2", ...]
result = service.embed(texts, batch_size=64, return_stats=True)

vectors = result["vectors"]
```

### Key Features

- **Batch Processing**: Process texts in configurable batches
- **LRU Caching**: Avoid redundant embedding computation
- **Multiple Backends**: HuggingFace, OpenAI, Jina, vLLM, etc.
- **vLLM Integration**: High-throughput for production scale

## Performance Tips

1. **Choose appropriate batch size**:
   - CPU: batch_size=16-32
   - GPU: batch_size=64-128
   - vLLM: batch_size=256+

2. **Enable caching** for datasets with repeated texts

3. **Use vLLM** for production-scale deployments (100K+ texts)

## Documentation

- [Full Guide](docs/dev-notes/cross-layer/parallel-batch-insertion.md)
- [Examples](examples/tutorials/L4-middleware/memory_service/parallel_batch_insertion_example.py)
- [EmbeddingService Demo](examples/tutorials/L3-libs/embeddings/embedding_service_demo.py)

## Future Improvements

Parallel storage operations for neuromem `VDBMemoryCollection.batch_insert_data()` 
are planned for implementation in the [neuromem repository](https://github.com/intellistream/neuromem).

## Related Issues

- Fixes #392: Vector database parallel insertion support
