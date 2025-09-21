import logging
import os
import sys

import numpy as np

# Add the build directory to the path
sys.path.append("/home/shuhao/SAGE/sage_ext/sage_db/build")

try:
    import sage_db_py
    from sage_db import SageDatabase

    logging.info("✅ Import successful!")
except ImportError as e:
    logging.info(f"❌ Import failed: {e}")
    logging.info("Make sure to build the module first with ./build.sh")
    sys.exit(1)


def test_python_api():
    """Test the Python API wrapper"""
    logging.info("\n🐍 Testing Python API...")

    # Create database
    db = SageDatabase(dimension=64)

    # Add single vector
    vector = np.random.random(64).astype(np.float32)
    metadata = {"text": "test vector", "category": "example"}

    vector_id = db.add_vector(vector, metadata)
    logging.info(f"Added vector with ID: {vector_id}")

    # Add batch
    batch_vectors = np.random.random((10, 64)).astype(np.float32)
    batch_metadata = [{"text": f"vector_{i}", "batch": "test"} for i in range(10)]

    batch_ids = db.add_batch(batch_vectors, batch_metadata)
    logging.info(f"Added batch of {len(batch_ids)} vectors")

    # Search
    query = np.random.random(64).astype(np.float32)
    results = db.search(query, k=3)

    logging.info(f"Search returned {len(results)} results:")
    for i, result in enumerate(results):
        logging.info(f"  {i+1}. ID: {result['id']}, Distance: {result['distance']:.4f}")
        logging.info(f"      Metadata: {result['metadata']}")

    # Metadata search
    category_results = db.find_by_metadata("category", "example")
    logging.info(f"Found {len(category_results)} vectors with category='example'")

    logging.info("✅ Python API test passed!")


def test_pybind11_interface():
    """Test the direct pybind11 interface"""
    logging.info("\n🔧 Testing pybind11 interface...")

    # Test vector store
    vector_store = sage_db_py.VectorStore(32)

    # Add vectors
    vec1 = np.array([1.0] * 32, dtype=np.float32)
    vec2 = np.array([2.0] * 32, dtype=np.float32)

    id1 = vector_store.add(vec1)
    id2 = vector_store.add(vec2)

    logging.info(f"Added vectors with IDs: {id1}, {id2}")
    logging.info(f"Vector store size: {vector_store.size()}")

    # Search
    query = np.array([1.1] * 32, dtype=np.float32)
    results = vector_store.search(query, 2)

    logging.info(f"Search results: {len(results)} items")
    for result in results:
        logging.info(f"  ID: {result['id']}, Distance: {result['distance']:.4f}")

    # Test metadata store
    metadata_store = sage_db_py.MetadataStore()

    metadata_store.set(id1, {"name": "first", "type": "test"})
    metadata_store.set(id2, {"name": "second", "type": "test"})

    meta1 = metadata_store.get(id1)
    logging.info(f"Metadata for ID {id1}: {meta1}")

    type_matches = metadata_store.find_by_key_value("type", "test")
    logging.info(f"Found {len(type_matches)} vectors with type='test'")

    logging.info("✅ pybind11 interface test passed!")


def benchmark_python():
    """Simple performance test"""
    logging.info("\n📊 Python performance benchmark...")

    import time

    dimension = 128
    num_vectors = 1000

    db = SageDatabase(dimension=dimension)

    # Generate random data
    vectors = np.random.random((num_vectors, dimension)).astype(np.float32)
    metadata = [{"id": str(i), "batch": "benchmark"} for i in range(num_vectors)]

    # Time batch addition
    start_time = time.time()
    ids = db.add_batch(vectors, metadata)
    add_time = time.time() - start_time

    logging.info(f"Added {num_vectors} vectors in {add_time:.3f} seconds")
    logging.info(f"Rate: {num_vectors / add_time:.1f} vectors/second")

    # Time searches
    num_queries = 100
    query_vectors = np.random.random((num_queries, dimension)).astype(np.float32)

    start_time = time.time()
    for query in query_vectors:
        results = db.search(query, k=10)
    search_time = time.time() - start_time

    logging.info(f"Performed {num_queries} searches in {search_time:.3f} seconds")
    logging.info(f"Rate: {num_queries / search_time:.1f} searches/second")

    logging.info("✅ Performance benchmark completed!")


if __name__ == "__main__":
    logging.info("🧪 SAGE DB Python Test Suite")
    logging.info("============================")

    try:
        test_python_api()
        test_pybind11_interface()
        benchmark_python()

        logging.info("\n🎉 All Python tests passed!")

    except Exception as e:
        logging.info(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
