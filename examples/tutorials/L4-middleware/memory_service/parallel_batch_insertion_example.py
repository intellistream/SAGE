"""
Example: High-Performance Parallel VDB Insertion

This example demonstrates how to use ParallelVDBService for efficient
parallel batch insertion of large datasets (100K+ documents) into VDB.

Architecture:
    ParallelVDBService (SAGE middleware layer)
        ↓
    ThreadPoolExecutor (configurable workers)
        ↓
    [Batch 1] [Batch 2] ... [Batch N]  (parallel)
        ↓         ↓            ↓
    EmbeddingService.embed()  (batch vectors)
        ↓         ↓            ↓
    VDBCollection.insert()    (serial per batch)

Key Design Decisions:
- neuromem remains single-threaded (no internal thread pools)
- Parallelization happens at SAGE middleware layer
- Each batch is processed independently by a worker thread
- Within each batch: embed texts (batch) -> insert vectors (serial)
"""

import os


def example_parallel_vdb_insertion():
    """Example 1: Parallel VDB insertion with ParallelVDBService."""
    print("\n" + "=" * 70)
    print("Example 1: Parallel VDB Insertion")
    print("=" * 70)

    from sage.middleware.components.sage_mem.neuromem.memory_collection import (
        VDBMemoryCollection,
    )
    from sage.middleware.components.sage_mem.services import ParallelVDBService

    # Step 1: Create VDB collection and index
    collection = VDBMemoryCollection(config={"name": "parallel_example"})
    collection.create_index(
        config={
            "name": "main_index",
            "dim": 128,  # MockEmbedder default dimension
            "backend_type": "FAISS",
            "description": "Main index for parallel insertion",
        }
    )
    print("Created collection and index")

    # Step 2: Create ParallelVDBService
    service = ParallelVDBService(
        collection=collection,
        embedding_config={
            "method": "mockembedder",  # Use mock for demo; replace with "hf" for real use
            "batch_size": 32,  # Embedding batch size
            "normalize": True,
            "cache_enabled": True,
            "cache_size": 10000,
        },
        max_workers=4,  # Parallel worker threads
        default_batch_size=100,  # Texts per storage batch
    )
    service.setup()
    print("ParallelVDBService initialized")

    # Step 3: Generate test data
    num_documents = 500
    texts = [
        f"Document {i}: This is sample content for parallel insertion testing."
        for i in range(num_documents)
    ]
    metadatas = [{"doc_id": i, "category": f"cat_{i % 5}"} for i in range(num_documents)]

    print(f"\nInserting {num_documents} documents in parallel...")

    # Step 4: Parallel batch insert
    result = service.parallel_batch_insert(
        texts=texts,
        index_name="main_index",
        metadatas=metadatas,
        batch_size=100,  # Process 100 texts per batch
        show_progress=True,
    )

    # Step 5: Print results
    print("\n Results:")
    print(f"  Total texts: {result.total_texts}")
    print(f"  Successfully inserted: {result.total_inserted}")
    print(f"  Failed: {result.total_failed}")
    print(f"  Elapsed time: {result.elapsed_seconds:.2f}s")
    print(f"  Throughput: {result.throughput_per_second:.0f} docs/sec")

    service.cleanup()
    print("\nService cleaned up")


def example_convenience_function():
    """Example 2: Using the convenience function."""
    print("\n" + "=" * 70)
    print("Example 2: Convenience Function")
    print("=" * 70)

    from sage.middleware.components.sage_mem.neuromem.memory_collection import (
        VDBMemoryCollection,
    )
    from sage.middleware.components.sage_mem.services import parallel_insert_to_vdb

    # Create collection
    collection = VDBMemoryCollection(config={"name": "convenience_example"})
    collection.create_index(
        config={
            "name": "main_index",
            "dim": 128,
            "backend_type": "FAISS",
        }
    )

    # One-shot parallel insertion
    texts = [f"Quick document {i}" for i in range(200)]

    print(f"Inserting {len(texts)} documents...")

    result = parallel_insert_to_vdb(
        texts=texts,
        collection=collection,
        index_name="main_index",
        embedding_config={"method": "mockembedder"},
        max_workers=2,
        batch_size=50,
    )

    print(f"Inserted {result.total_inserted} documents in {result.elapsed_seconds:.2f}s")


def example_large_scale_config():
    """Example 3: Configuration for large-scale insertion (100K+ docs)."""
    print("\n" + "=" * 70)
    print("Example 3: Large-Scale Configuration Guide")
    print("=" * 70)

    config_guide = """
For 100K+ documents, use these recommended settings:

1. EMBEDDING CONFIG:
   embedding_config = {
       "method": "hf",                          # Or "vllm" for production
       "model": "BAAI/bge-small-zh-v1.5",       # Choose based on your needs
       "batch_size": 64,                        # GPU batch size
       "normalize": True,
       "cache_enabled": True,                   # Enable for repeated texts
       "cache_size": 100000,
   }

2. PARALLEL SERVICE CONFIG:
   service = ParallelVDBService(
       collection=collection,
       embedding_config=embedding_config,
       max_workers=4,                           # CPU cores for parallel batches
       default_batch_size=1000,                 # Texts per storage batch
   )

3. INSERTION CALL:
   result = service.parallel_batch_insert(
       texts=texts,
       index_name="main_index",
       batch_size=1000,                         # 1000 texts per batch
       show_progress=True,
   )

4. EXPECTED PERFORMANCE:
   | Dataset Size | Workers | Batch Size | Est. Throughput |
   |--------------|---------|------------|-----------------|
   | 10K          | 2       | 500        | ~500 docs/sec   |
   | 100K         | 4       | 1000       | ~800 docs/sec   |
   | 1M           | 8       | 2000       | ~1000 docs/sec  |

   Note: Actual throughput depends on:
   - Embedding model (HF local vs vLLM vs API)
   - Hardware (GPU, CPU cores, memory)
   - Document length
   - Index configuration

5. FOR PRODUCTION (vLLM backend):
   embedding_config = {
       "method": "vllm",
       "vllm_service_name": "embedding_vllm",
       "batch_size": 256,
   }
"""
    print(config_guide)


def example_error_handling():
    """Example 4: Error handling and batch recovery."""
    print("\n" + "=" * 70)
    print("Example 4: Error Handling")
    print("=" * 70)

    error_guide = """
ParallelVDBService handles errors gracefully:

1. BATCH-LEVEL ISOLATION:
   - Each batch runs independently
   - One batch failure doesn't stop others
   - Failed batches are tracked in result.batch_results

2. CHECKING RESULTS:
   result = service.parallel_batch_insert(texts, index_name="idx")

   if result.total_failed > 0:
       print(f"Warning: {result.total_failed} documents failed")
       for batch in result.batch_results:
           if batch.get("failed", 0) > 0:
               print(f"  Batch {batch['batch_idx']}: {batch['errors']}")

3. RETRY STRATEGY:
   # Identify failed texts and retry
   failed_indices = []
   for batch in result.batch_results:
       if batch.get("failed", 0) > 0:
           start = batch["batch_idx"]
           failed_indices.extend(range(start, start + batch["batch_size"]))

   if failed_indices:
       retry_texts = [texts[i] for i in failed_indices]
       retry_result = service.parallel_batch_insert(
           retry_texts, index_name="idx", batch_size=100
       )

4. COMMON ERRORS:
   - RuntimeError: "not setup" -> Call service.setup() first
   - ValueError: "metadatas length" -> Ensure len(metadatas) == len(texts)
   - Embedding errors -> Check model availability and config
"""
    print(error_guide)


def main():
    """Run all examples."""
    print("\n" + "=" * 70)
    print("PARALLEL VDB INSERTION EXAMPLES")
    print("=" * 70)
    print("\nThis demonstrates high-performance parallel insertion for VDB.")
    print("Key: Parallelization at SAGE layer, neuromem stays single-threaded.")

    is_test_mode = os.getenv("SAGE_TEST_MODE") == "true" or os.getenv("CI") == "true"

    if is_test_mode:
        print("\n Test mode: Showing configuration guides\n")
        example_large_scale_config()
        example_error_handling()
    else:
        try:
            example_parallel_vdb_insertion()
            example_convenience_function()
        except ImportError as e:
            print(f"\nNote: {e}")
            print("Install SAGE to run the examples.")

        example_large_scale_config()
        example_error_handling()

    print("\n" + "=" * 70)
    print("EXAMPLES COMPLETE")
    print("=" * 70)
    print("\nKey takeaways:")
    print("1. Use ParallelVDBService for large-scale insertion")
    print("2. Configure max_workers based on CPU cores")
    print("3. Adjust batch_size based on memory and throughput needs")
    print("4. Use vLLM backend for production scale")
    print("5. Check result.total_failed for error handling")


if __name__ == "__main__":
    main()
