# Parallel Batch Insertion for Vector Database

## Overview

This document describes the architecture and usage of **ParallelVDBService** for high-performance parallel batch insertion into VDB, supporting 100K+ or 1M+ records.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                       ParallelVDBService                             │
│            (sage-middleware/components/sage_mem/services/)           │
├─────────────────────────────────────────────────────────────────────┤
│  parallel_batch_insert(texts, index_name, metadatas, batch_size)    │
│      ↓                                                               │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │            ThreadPoolExecutor (max_workers)                 │    │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐        │    │
│  │  │ Batch 1 │  │ Batch 2 │  │ Batch 3 │  │ Batch N │        │    │
│  │  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘        │    │
│  │       ↓            ↓            ↓            ↓              │    │
│  │  EmbeddingService.embed() (批量生成向量)                     │    │
│  │       ↓            ↓            ↓            ↓              │    │
│  │  VDBCollection.insert() (串行存储每个batch内的数据)          │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

### Design Principles

1. **neuromem remains single-threaded**: No thread pools inside neuromem
2. **Parallelization at SAGE layer**: ThreadPoolExecutor in middleware
3. **Batch-level parallelism**: Multiple batches processed concurrently
4. **Serial within batch**: Each batch embeds and inserts sequentially

## Quick Start

### Basic Usage

```python
from sage.middleware.components.sage_mem.neuromem.memory_collection import VDBMemoryCollection
from sage.middleware.components.sage_mem.services import ParallelVDBService

# Step 1: Create collection and index
collection = VDBMemoryCollection(config={"name": "my_collection"})
collection.create_index(config={
    "name": "main_index",
    "dim": 384,
    "backend_type": "FAISS",
})

# Step 2: Create ParallelVDBService
service = ParallelVDBService(
    collection=collection,
    embedding_config={
        "method": "hf",
        "model": "BAAI/bge-small-zh-v1.5",
        "batch_size": 64,
        "normalize": True,
        "cache_enabled": True,
    },
    max_workers=4,           # Parallel worker threads
    default_batch_size=1000, # Texts per storage batch
)
service.setup()

# Step 3: Parallel insert
texts = [f"Document {i}: content..." for i in range(100000)]
result = service.parallel_batch_insert(
    texts=texts,
    index_name="main_index",
    batch_size=1000,
)

print(f"Inserted {result.total_inserted} docs in {result.elapsed_seconds:.2f}s")
print(f"Throughput: {result.throughput_per_second:.0f} docs/sec")

service.cleanup()
```

### Convenience Function

For one-shot insertions:

```python
from sage.middleware.components.sage_mem.services import parallel_insert_to_vdb

result = parallel_insert_to_vdb(
    texts=texts,
    collection=collection,
    index_name="main_index",
    embedding_config={"method": "hf", "model": "BAAI/bge-small-zh-v1.5"},
    max_workers=4,
    batch_size=1000,
)
```

## Configuration Guide

### Embedding Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `method` | required | "hf", "openai", "jina", "vllm", "mockembedder" |
| `model` | - | Model name/path (e.g., "BAAI/bge-small-zh-v1.5") |
| `batch_size` | 32 | Texts per embedding batch (GPU batch) |
| `normalize` | True | Normalize vectors to unit length |
| `cache_enabled` | False | Enable LRU caching |
| `cache_size` | 10000 | Maximum cache entries |

### ParallelVDBService Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `max_workers` | 4 | Number of parallel worker threads |
| `default_batch_size` | 500 | Texts per storage batch |

### Recommended Settings by Dataset Size

| Dataset Size | Workers | Storage Batch | Embedding Batch | Est. Throughput |
|--------------|---------|---------------|-----------------|-----------------|
| < 10K        | 2       | 500           | 32              | ~500 docs/sec   |
| 10K - 100K   | 4       | 1000          | 64              | ~800 docs/sec   |
| 100K - 1M    | 8       | 2000          | 128             | ~1000 docs/sec  |
| > 1M         | 8       | 2000          | 256 (vLLM)      | ~2000+ docs/sec |

## Advanced Usage

### With Metadata

```python
texts = ["doc1", "doc2", "doc3"]
metadatas = [
    {"category": "A", "priority": 1},
    {"category": "B", "priority": 2},
    {"category": "A", "priority": 3},
]

result = service.parallel_batch_insert(
    texts=texts,
    index_name="main_index",
    metadatas=metadatas,
)
```

### Error Handling

```python
result = service.parallel_batch_insert(texts, index_name="main_index")

if result.total_failed > 0:
    print(f"Warning: {result.total_failed} documents failed")
    for batch in result.batch_results:
        if batch.get("failed", 0) > 0:
            print(f"  Batch {batch['batch_idx']}: {batch['errors']}")
```

### vLLM Backend for Production

```python
service = ParallelVDBService(
    collection=collection,
    embedding_config={
        "method": "vllm",
        "vllm_service_name": "embedding_vllm",  # Pre-configured vLLM service
        "batch_size": 256,
    },
    max_workers=8,
    default_batch_size=2000,
)
```

## EmbeddingService (Foundation)

ParallelVDBService uses `EmbeddingService` internally for batch embedding:

```python
from sage.common.components.sage_embedding import EmbeddingService

config = {
    "method": "hf",
    "model": "BAAI/bge-small-zh-v1.5",
    "batch_size": 64,
    "cache_enabled": True,
}

service = EmbeddingService(config)
service.setup()

result = service.embed(texts, batch_size=128, return_stats=True)
vectors = result["vectors"]
```

## Troubleshooting

### Out of Memory

**Problem**: GPU/CPU runs out of memory

**Solutions**:
1. Reduce embedding `batch_size`: 64 → 32 → 16
2. Reduce storage `batch_size`: 1000 → 500
3. Reduce `max_workers`: 4 → 2

### Slow Performance

**Problem**: Throughput lower than expected

**Solutions**:
1. Increase `max_workers` (up to CPU cores)
2. Increase `batch_size` for better GPU utilization
3. Enable caching if texts repeat
4. Use vLLM backend for production scale

### Partial Failures

**Problem**: Some documents fail to insert

**Solution**: Check `result.batch_results` for errors:
```python
for batch in result.batch_results:
    if batch["failed"] > 0:
        print(f"Batch {batch['batch_idx']}: {batch['errors']}")
```

## API Reference

### ParallelVDBService

```python
class ParallelVDBService(BaseService):
    def __init__(
        self,
        collection: VDBMemoryCollection,
        embedding_config: dict[str, Any],
        max_workers: int = 4,
        default_batch_size: int = 500,
    ): ...

    def setup(self) -> None: ...
    def cleanup(self) -> None: ...

    def parallel_batch_insert(
        self,
        texts: list[str],
        index_name: str,
        metadatas: list[dict] | None = None,
        batch_size: int | None = None,
        show_progress: bool = True,
    ) -> ParallelInsertResult: ...
```

### ParallelInsertResult

```python
@dataclass
class ParallelInsertResult:
    total_texts: int
    total_inserted: int
    total_failed: int
    elapsed_seconds: float
    throughput_per_second: float
    batch_results: list[dict]

    def to_dict(self) -> dict: ...
```

## Related Resources

- [EmbeddingService Documentation](../l1-common/embedding-service.md)
- [VDBMemoryCollection Guide](../../guides/packages/sage-middleware/service/neuromem/vdb/vdb.md)
- [Issue #392](https://github.com/intellistream/SAGE/issues/392)
