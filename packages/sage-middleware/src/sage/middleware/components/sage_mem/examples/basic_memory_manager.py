"""
Basic example demonstrating MemoryManager usage

This example shows how to:
1. Create a VDB memory collection
2. Insert data into the collection
3. Create an index
4. Retrieve data from the collection
"""

import numpy as np

from sage.common.components.sage_embedding.embedding_api import apply_embedding_model
from sage.common.utils.logging.custom_logger import CustomLogger
from sage.middleware.components.sage_mem import MemoryManager

# Use .sage directory for test data storage
manager_path = ".sage/examples/sage_mem/basic_memory"

config = {
    "name": "BasicVDBCollection",
    "backend_type": "VDB",
    "description": "Basic VDB memory collection example",
    "index_config": {
        "name": "demo_index",
        "embedding_model": "mockembedder",
        "dim": 128,
        "backend_type": "FAISS",
        "description": "Demo FAISS index",
        "index_parameter": {},
    },
}


def normalize_vector(vector):
    """Normalize a vector using L2 normalization."""
    if hasattr(vector, "detach") and hasattr(vector, "cpu"):
        vector = vector.detach().cpu().numpy()
    if isinstance(vector, list):
        vector = np.array(vector)
    if not isinstance(vector, np.ndarray):
        vector = np.array(vector)
    vector = vector.astype(np.float32)
    norm = np.linalg.norm(vector)
    if norm > 0:
        vector = vector / norm
    return vector


def main():
    logger = CustomLogger()

    # Initialize embedding model
    embedding_model = apply_embedding_model("mockembedder")

    # Create memory manager
    logger.info(f"Creating memory manager at: {manager_path}")
    manager = MemoryManager(manager_path)

    # Check if collection exists
    collection_name = config["name"]
    if manager.has_collection(collection_name):
        logger.info(f"Loading existing collection: {collection_name}")
        collection = manager.get_collection(collection_name)
    else:
        logger.info(f"Creating new collection: {collection_name}")
        collection = manager.create_collection(config)

        # Insert sample data
        texts = [
            "Python is a high-level programming language.",
            "Machine learning is a subset of artificial intelligence.",
            "Natural language processing helps computers understand human language.",
        ]
        metadatas = [
            {"source": "doc1", "topic": "programming"},
            {"source": "doc2", "topic": "ai"},
            {"source": "doc3", "topic": "nlp"},
        ]

        logger.info("Inserting sample data...")
        collection.batch_insert_data(texts, metadatas)

        # Create index
        logger.info("Creating index...")
        collection.create_index(config["index_config"])

        # Initialize index with vectors
        logger.info("Initializing index...")
        vectors = [normalize_vector(embedding_model.encode(text)) for text in texts]
        item_ids = collection.get_all_ids()
        collection.init_index("demo_index", vectors, item_ids)

        # Store collection to disk
        logger.info("Storing collection to disk...")
        manager.store_collection()

    # Perform retrieval
    query = "What is machine learning?"
    logger.info(f"Retrieving results for query: '{query}'")
    query_vector = normalize_vector(embedding_model.encode(query))
    results = collection.retrieve(
        query_vector=query_vector,
        index_name="demo_index",
        topk=2,
        threshold=0.0,
        with_metadata=True,
    )

    # Print results
    print("\n" + "=" * 60)
    print(f"Query: {query}")
    print("=" * 60)
    for i, result in enumerate(results, 1):
        print(f"\nResult {i}:")
        print(f"  Text: {result.get('text', 'N/A')}")
        print(f"  Score: {result.get('score', 'N/A')}")
        print(f"  Metadata: {result.get('metadata', {})}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
