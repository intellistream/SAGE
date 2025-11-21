"""
Example: Using Parallel Batch Insertion for Large-Scale Vector Database

This example demonstrates how to use the new parallel batch insertion feature
to efficiently insert large datasets into a vector database.
"""

from sage.middleware.components.sage_mem.neuromem.memory_collection.vdb_collection import (
    VDBMemoryCollection,
)


def example_basic_parallel_insertion():
    """Basic example of parallel batch insertion"""
    print("\n" + "=" * 70)
    print("Example 1: Basic Parallel Batch Insertion")
    print("=" * 70)

    # Step 1: Create collection
    config = {"name": "example_collection"}
    collection = VDBMemoryCollection(config=config)
    print("✓ Created collection: example_collection")

    # Step 2: Prepare data (simulate large dataset)
    num_docs = 1000
    texts = [
        f"这是第{i}篇文档，内容是关于机器学习和人工智能的研究。" for i in range(num_docs)
    ]
    metadatas = [
        {"doc_id": i, "category": f"category_{i % 10}", "priority": i % 3}
        for i in range(num_docs)
    ]
    print(f"✓ Prepared {num_docs} documents")

    # Step 3: Insert with parallel processing (NEW!)
    print("\nInserting documents with parallel processing...")
    collection.batch_insert_data(
        texts,
        metadatas,
        parallel=True,  # Enable parallel processing
        num_workers=8,  # Use 8 worker threads
    )
    print(f"✓ Inserted {num_docs} documents in parallel")

    # Step 4: Create and initialize index with batch encoding (NEW!)
    index_config = {
        "name": "main_index",
        "embedding_model": "default",  # Uses sentence-transformers/all-MiniLM-L6-v2
        "dim": 384,
        "backend_type": "FAISS",
        "description": "Main search index",
    }
    collection.create_index(config=index_config)
    print("✓ Created index configuration")

    print("\nBuilding index with batch encoding...")
    collection.init_index(
        "main_index",
        batch_size=64,  # Process 64 texts at a time (NEW!)
    )
    print("✓ Index built with batch processing")

    # Step 5: Search
    query = "机器学习"
    results = collection.retrieve(query, "main_index", topk=5, with_metadata=True)

    print(f"\nSearch results for '{query}':")
    for i, result in enumerate(results, 1):  # type: ignore[arg-type]
        print(f"{i}. {result['text'][:50]}...")  # type: ignore[index]
        print(f"   Metadata: {result['metadata']}")  # type: ignore[index]

    print("\n✅ Basic example completed successfully!")


def example_large_dataset_with_filtering():
    """Example with filtering and custom batch sizes"""
    print("\n" + "=" * 70)
    print("Example 2: Large Dataset with Metadata Filtering")
    print("=" * 70)

    # Create collection
    config = {"name": "filtered_collection"}
    collection = VDBMemoryCollection(config=config)
    print("✓ Created collection")

    # Prepare diverse dataset
    num_docs = 500
    categories = ["tech", "science", "business", "health", "education"]
    texts = [
        f"Document {i} about {categories[i % len(categories)]}: detailed content here."
        for i in range(num_docs)
    ]
    metadatas = [
        {
            "id": i,
            "category": categories[i % len(categories)],
            "priority": "high" if i % 3 == 0 else "low",
            "year": 2020 + (i % 5),
        }
        for i in range(num_docs)
    ]

    # Insert with parallel processing
    collection.batch_insert_data(texts, metadatas, parallel=True, num_workers=6)
    print(f"✓ Inserted {num_docs} documents")

    # Create index
    index_config = {
        "name": "tech_index",
        "embedding_model": "default",
        "dim": 384,
        "backend_type": "FAISS",
        "description": "Technology documents index",
    }
    collection.create_index(config=index_config)

    # Initialize index with filtering (only tech and science categories)
    print("\nBuilding index with filtered data...")
    collection.init_index(
        "tech_index",
        batch_size=32,  # Smaller batch size for filtered data
        metadata_filter_func=lambda m: m.get("category") in ["tech", "science"],
    )
    print("✓ Index built with metadata filtering")

    # Search in filtered index
    results = collection.retrieve(
        "technology innovation", "tech_index", topk=3, with_metadata=True
    )

    print("\nSearch results (tech and science only):")
    for i, result in enumerate(results, 1):  # type: ignore[arg-type]
        print(f"{i}. Category: {result['metadata']['category']}")  # type: ignore[index, union-attr]
        print(f"   {result['text'][:60]}...")  # type: ignore[index]

    print("\n✅ Filtered example completed successfully!")


def example_performance_optimization():
    """Example showing different optimization strategies"""
    print("\n" + "=" * 70)
    print("Example 3: Performance Optimization Strategies")
    print("=" * 70)

    import time

    # Prepare test data
    num_docs = 200
    texts = [f"Performance test document {i} with content." for i in range(num_docs)]

    # Strategy 1: Default settings (good for most cases)
    print("\n1. Default settings (recommended for most cases)")
    config1 = {"name": "default_strategy"}
    coll1 = VDBMemoryCollection(config=config1)

    start = time.time()
    coll1.batch_insert_data(texts)  # Uses default: parallel=True, num_workers=4
    elapsed1 = time.time() - start
    print(f"   Time: {elapsed1:.3f}s with default settings")

    # Strategy 2: High parallelism (for I/O-bound workloads)
    print("\n2. High parallelism (for fast storage)")
    config2 = {"name": "high_parallel"}
    coll2 = VDBMemoryCollection(config=config2)

    start = time.time()
    coll2.batch_insert_data(texts, parallel=True, num_workers=12)
    elapsed2 = time.time() - start
    print(f"   Time: {elapsed2:.3f}s with 12 workers")

    # Strategy 3: Sequential (for debugging or small batches)
    print("\n3. Sequential (for compatibility/debugging)")
    config3 = {"name": "sequential"}
    coll3 = VDBMemoryCollection(config=config3)

    start = time.time()
    coll3.batch_insert_data(texts, parallel=False)
    elapsed3 = time.time() - start
    print(f"   Time: {elapsed3:.3f}s with sequential processing")

    # Strategy 4: Optimized for GPU embeddings
    print("\n4. Large batch size (for GPU embeddings)")
    index_config = {
        "name": "gpu_index",
        "embedding_model": "default",
        "dim": 384,
        "backend_type": "FAISS",
    }
    coll1.create_index(config=index_config)

    start = time.time()
    coll1.init_index("gpu_index", batch_size=128)  # Large batch for GPU
    elapsed4 = time.time() - start
    print(f"   Time: {elapsed4:.3f}s with batch_size=128")

    print("\n✅ Performance optimization examples completed!")
    print(f"\nPerformance summary:")
    print(f"  Default:      {elapsed1:.3f}s")
    print(f"  High parallel: {elapsed2:.3f}s ({elapsed1/elapsed2:.1f}x)")
    print(f"  Sequential:   {elapsed3:.3f}s ({elapsed3/elapsed1:.1f}x slower)")


def example_memory_efficient():
    """Example for memory-constrained environments"""
    print("\n" + "=" * 70)
    print("Example 4: Memory-Efficient Configuration")
    print("=" * 70)

    config = {"name": "memory_efficient"}
    collection = VDBMemoryCollection(config=config)

    # Large dataset
    num_docs = 1000
    texts = [f"Memory-efficient document {i}" for i in range(num_docs)]

    # Use moderate parallelism to reduce memory pressure
    print("\nUsing memory-efficient settings...")
    collection.batch_insert_data(
        texts,
        parallel=True,
        num_workers=2,  # Fewer workers = less memory
    )
    print(f"✓ Inserted {num_docs} documents with 2 workers")

    # Small batch size for embedding to reduce GPU/CPU memory
    index_config = {
        "name": "efficient_index",
        "embedding_model": "default",
        "dim": 384,
        "backend_type": "FAISS",
    }
    collection.create_index(config=index_config)

    collection.init_index(
        "efficient_index",
        batch_size=16,  # Small batch = less memory usage
    )
    print("✓ Index built with small batch size (16)")

    print("\n✅ Memory-efficient example completed!")
    print("   Tip: Adjust num_workers and batch_size based on your system resources")


if __name__ == "__main__":
    print("=" * 70)
    print("PARALLEL BATCH INSERTION EXAMPLES")
    print("=" * 70)

    # Run all examples
    example_basic_parallel_insertion()
    example_large_dataset_with_filtering()
    example_performance_optimization()
    example_memory_efficient()

    print("\n" + "=" * 70)
    print("🎉 ALL EXAMPLES COMPLETED SUCCESSFULLY!")
    print("=" * 70)
    print("\nKey Takeaways:")
    print("1. Use parallel=True (default) for faster insertion")
    print("2. Adjust num_workers (default: 4) based on your I/O performance")
    print("3. Use batch_size=32-64 for CPU, 64-128 for GPU embeddings")
    print("4. Reduce batch_size and num_workers for memory-constrained systems")
    print("5. All new parameters are optional - existing code works without changes!")
