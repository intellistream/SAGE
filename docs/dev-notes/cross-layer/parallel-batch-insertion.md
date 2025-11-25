# Parallel Batch Insertion for Vector Database

## Overview

This document describes strategies for improving vector database insertion performance when working with large datasets (100K+ or 1M+ records).

## Recommended Approach: Using EmbeddingService

For large-scale data insertion, SAGE provides the `EmbeddingService` which already supports batch processing and caching. This is the recommended approach for high-performance embedding generation.

### Using EmbeddingService for Batch Embedding

```python
from sage.common.components.sage_embedding import EmbeddingService

# Configure EmbeddingService with batch processing
config = {
    "method": "hf",
    "model": "BAAI/bge-small-zh-v1.5",
    "batch_size": 32,           # Built-in batch processing
    "normalize": True,
    "cache_enabled": True,      # LRU cache for repeated texts
    "cache_size": 10000,
}

service = EmbeddingService(config)
service.setup()

# Batch embed texts
texts = ["text 1", "text 2", ..., "text 100000"]
result = service.embed(
    texts,
    batch_size=64,              # Override batch size if needed
    return_stats=True,          # Get cache hit statistics
)

vectors = result["vectors"]     # List of embedding vectors
dimension = result["dimension"] # Embedding dimension
stats = result["stats"]         # Cache hit rate, etc.
```

### EmbeddingService Features

1. **Built-in Batch Processing**: Automatically processes texts in configurable batches
2. **LRU Caching**: Cache embeddings to avoid redundant computation
3. **Multiple Backends**: Supports HuggingFace, OpenAI, Jina, vLLM, etc.
4. **vLLM Integration**: High-throughput embedding for large-scale deployments

### EmbeddingService Configuration Options

| Parameter | Default | Description |
|-----------|---------|-------------|
| `method` | - | Embedding method: "hf", "openai", "jina", "vllm", etc. |
| `model` | - | Model name/path |
| `batch_size` | 32 | Number of texts per batch |
| `normalize` | True | Normalize vectors to unit length |
| `cache_enabled` | False | Enable LRU caching |
| `cache_size` | 10000 | Maximum cache entries |

## Performance Strategies

### 1. Batch Processing with EmbeddingService

Use the built-in batch processing:

```python
# Large batch for GPU efficiency
result = service.embed(texts, batch_size=128)

# Smaller batch for memory-constrained environments
result = service.embed(texts, batch_size=16)
```

### 2. Enable Caching for Repeated Texts

```python
config = {
    "method": "hf",
    "model": "BAAI/bge-small-zh-v1.5",
    "cache_enabled": True,
    "cache_size": 50000,
}
```

### 3. Use vLLM for High Throughput

For very large datasets, use vLLM backend:

```yaml
services:
  vllm:
    class: sage.common.components.sage_vllm.VLLMService
    config:
      model_id: "BAAI/bge-base-en-v1.5"

  embedding:
    class: sage.common.components.sage_embedding.EmbeddingService
    config:
      method: "vllm"
      vllm_service_name: "vllm"
      batch_size: 256
```

## Performance Comparison

| Method | Throughput | Latency | Use Case |
|--------|-----------|---------|----------|
| Sequential (single text) | ~50/s | 20ms | Small datasets |
| Batch (HF, batch_size=32) | ~500/s | 10ms | Medium datasets |
| Batch (HF, batch_size=128) | ~1000/s | 5ms | Large datasets with GPU |
| vLLM | ~2000+/s | 3ms | Production scale |

## Best Practices

1. **Choose appropriate batch size**: Balance memory usage and throughput
2. **Enable caching**: If you have repeated texts in your dataset
3. **Use vLLM for production**: When handling 100K+ documents regularly
4. **Monitor cache hit rates**: Use `return_stats=True` to optimize caching

## Example: Large Dataset Embedding

```python
from sage.common.components.sage_embedding import EmbeddingService

# Setup service for large-scale embedding
config = {
    "method": "hf",
    "model": "BAAI/bge-small-zh-v1.5",
    "batch_size": 64,
    "normalize": True,
    "cache_enabled": True,
    "cache_size": 100000,
}

service = EmbeddingService(config)
service.setup()

# Process 100K documents
texts = [f"Document {i}: content..." for i in range(100000)]

print("Embedding 100,000 documents...")
result = service.embed(texts, batch_size=128, return_stats=True)

print(f"Embedded {result['count']} documents")
print(f"Dimension: {result['dimension']}")
print(f"Cache hit rate: {result['stats']['cache_hit_rate']:.2%}")

# Use vectors with VDBMemoryCollection
vectors = result["vectors"]
```

## Troubleshooting

### Out of Memory Errors

**Problem**: GPU/CPU runs out of memory during batch encoding

**Solution**: Reduce batch size
```python
result = service.embed(texts, batch_size=16)
```

### Slow Performance

**Problem**: Embedding is slower than expected

**Solutions**:
1. Increase batch size for better GPU utilization
2. Enable caching for repeated texts
3. Use vLLM backend for very large datasets

### Cache Not Working

**Problem**: High cache miss rate

**Solution**: Ensure cache is enabled and sized appropriately:
```python
config = {
    "cache_enabled": True,
    "cache_size": 100000,  # Increase for large datasets
}
```

## Future Improvements

The following features are planned for the neuromem submodule to further improve performance:

1. **Parallel Storage Operations**: Concurrent I/O for batch_insert_data
2. **Integration with EmbeddingService**: Use centralized embedding service
3. **Streaming Insertion**: Process data in chunks without loading all into memory

These features will be implemented in the [neuromem repository](https://github.com/intellistream/neuromem) and integrated into SAGE.
