"""
Test for parallel batch insertion feature in VDBMemoryCollection.
Tests the new batch_size parameter and parallel insertion capabilities.
"""

import time

from sage.middleware.components.sage_mem.neuromem.memory_collection.vdb_collection import (
    VDBMemoryCollection,
)


def test_parallel_batch_insert():
    """Test parallel batch insertion with large dataset"""
    print("\n" + "=" * 70)
    print("Testing Parallel Batch Insertion")
    print("=" * 70)

    # Create collection
    config = {"name": "test_parallel_collection"}
    collection = VDBMemoryCollection(config=config)

    # Generate test data - simulating large dataset
    num_items = 100  # Use smaller number for quick testing
    texts = [f"测试文本 {i}: 这是第{i}条测试数据用于验证并行插入功能" for i in range(num_items)]
    metadatas = [{"id": i, "type": "test", "batch": i // 10} for i in range(num_items)]

    print(f"\n1. Testing parallel batch_insert_data with {num_items} items")
    print("-" * 70)

    # Test parallel insertion
    start_time = time.time()
    collection.batch_insert_data(texts, metadatas, parallel=True, num_workers=4)
    parallel_time = time.time() - start_time
    print(f"✓ Parallel insertion completed in {parallel_time:.3f} seconds")

    # Verify data was inserted
    all_ids = collection.get_all_ids()
    print(f"✓ Verified {len(all_ids)} items in storage")
    assert len(all_ids) == num_items, f"Expected {num_items} items, got {len(all_ids)}"

    print("\n2. Testing batch embedding with init_index")
    print("-" * 70)

    # Create index
    index_config = {
        "name": "test_index",
        "embedding_model": "mockembedder",
        "dim": 128,
        "backend_type": "FAISS",
        "description": "测试索引",
        "index_parameter": {},
    }
    collection.create_index(config=index_config)

    # Initialize index with batch encoding
    start_time = time.time()
    result = collection.init_index("test_index", batch_size=32)
    batch_encoding_time = time.time() - start_time
    print(f"✓ Batch encoding and indexing completed in {batch_encoding_time:.3f} seconds")
    print(f"✓ Indexed {result} vectors")
    assert result == num_items, f"Expected {num_items} vectors, got {result}"

    print("\n3. Testing retrieval after parallel insertion")
    print("-" * 70)

    # Test retrieval
    results = collection.retrieve(
        raw_data="测试文本",
        index_name="test_index",
        topk=5,
        with_metadata=True,
    )

    print(f"✓ Retrieved {len(results)} results")  # type: ignore[arg-type]
    assert len(results) > 0, "Should retrieve some results"  # type: ignore[arg-type]

    # Verify metadata
    for i, result in enumerate(results[:3]):  # type: ignore[arg-type]
        print(f"  Result {i+1}:")
        print(f"    Text: {result['text'][:50]}...")  # type: ignore[index]
        print(f"    Metadata: {result['metadata']}")  # type: ignore[index]

    print("\n" + "=" * 70)
    print("✅ All parallel insertion tests passed!")
    print("=" * 70)


def test_sequential_vs_parallel():
    """Compare sequential vs parallel insertion performance"""
    print("\n" + "=" * 70)
    print("Performance Comparison: Sequential vs Parallel")
    print("=" * 70)

    num_items = 50  # Smaller for quick test

    # Test sequential insertion
    print(f"\n1. Sequential insertion of {num_items} items")
    print("-" * 70)
    config_seq = {"name": "test_sequential"}
    collection_seq = VDBMemoryCollection(config=config_seq)
    texts = [f"Sequential test {i}" for i in range(num_items)]

    start_time = time.time()
    collection_seq.batch_insert_data(texts, parallel=False)
    sequential_time = time.time() - start_time
    print(f"✓ Sequential time: {sequential_time:.3f} seconds")

    # Test parallel insertion
    print(f"\n2. Parallel insertion of {num_items} items")
    print("-" * 70)
    config_par = {"name": "test_parallel"}
    collection_par = VDBMemoryCollection(config=config_par)

    start_time = time.time()
    collection_par.batch_insert_data(texts, parallel=True, num_workers=4)
    parallel_time = time.time() - start_time
    print(f"✓ Parallel time: {parallel_time:.3f} seconds")

    # Verify both have same data
    assert len(collection_seq.get_all_ids()) == len(collection_par.get_all_ids())
    print(f"\n✓ Both methods inserted {num_items} items correctly")

    print("\n" + "=" * 70)
    print("✅ Performance comparison test passed!")
    print("=" * 70)


def test_batch_size_parameter():
    """Test different batch_size parameters for init_index"""
    print("\n" + "=" * 70)
    print("Testing Batch Size Parameter")
    print("=" * 70)

    config = {"name": "test_batch_size"}
    collection = VDBMemoryCollection(config=config)

    # Insert test data
    num_items = 60
    texts = [f"Batch size test {i}" for i in range(num_items)]
    collection.batch_insert_data(texts, parallel=True)

    # Create index
    index_config = {
        "name": "test_index",
        "embedding_model": "mockembedder",
        "dim": 128,
        "backend_type": "FAISS",
        "description": "测试批处理大小",
    }
    collection.create_index(config=index_config)

    # Test with different batch sizes
    batch_sizes = [16, 32, 64]
    for batch_size in batch_sizes:
        print(f"\nTesting batch_size={batch_size}")
        print("-" * 70)

        # Reset index for each test
        collection.delete_index("test_index")
        collection.create_index(config=index_config)

        start_time = time.time()
        result = collection.init_index("test_index", batch_size=batch_size)
        elapsed = time.time() - start_time

        print(f"✓ Indexed {result} vectors in {elapsed:.3f}s with batch_size={batch_size}")
        assert result == num_items, f"Expected {num_items} vectors"

    print("\n" + "=" * 70)
    print("✅ Batch size parameter test passed!")
    print("=" * 70)


if __name__ == "__main__":
    test_parallel_batch_insert()
    test_sequential_vs_parallel()
    test_batch_size_parameter()
    print("\n" + "=" * 70)
    print("🎉 ALL TESTS PASSED!")
    print("=" * 70)
