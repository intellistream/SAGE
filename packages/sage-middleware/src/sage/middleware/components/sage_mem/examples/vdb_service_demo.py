"""
Example demonstrating NeuroMemVDB service usage

This example shows how to use the NeuroMemVDB convenience class
for managing vector database operations.
"""

import numpy as np

from sage.common.components.sage_embedding.embedding_api import apply_embedding_model
from sage.common.utils.logging.custom_logger import CustomLogger
from sage.middleware.components.sage_mem import NeuroMemVDB

logger = CustomLogger()


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
    logger.info("Initializing NeuroMemVDB service...")
    vdb = NeuroMemVDB()

    # Initialize embedding model
    embedding_model = apply_embedding_model("mockembedder")

    # Register a collection
    collection_name = "demo_vdb_collection"
    config = {
        "embedding_model": "mockembedder",
        "dim": 128,
        "description": "Demo VDB collection for service example",
    }

    logger.info(f"Registering collection: {collection_name}")
    vdb.register_collection(collection_name, config)

    # Insert data
    logger.info("Inserting sample data...")
    sample_data = [
        "The quick brown fox jumps over the lazy dog.",
        "Python is a versatile programming language.",
        "Vector databases enable semantic search.",
    ]

    for text in sample_data:
        vdb.insert(text, metadata={"source": "demo"})

    # Create and initialize index directly on the collection
    logger.info("Creating and initializing index...")
    collection = vdb.online_register_collection.get(collection_name)
    if collection:
        index_config = {
            "name": "global_index",
            "embedding_model": "mockembedder",
            "dim": 128,
            "backend_type": "FAISS",
            "description": "Global index for all data",
        }
        collection.create_index(index_config)

        # Generate vectors and initialize index
        vectors = [normalize_vector(embedding_model.encode(text)) for text in sample_data]
        item_ids = collection.get_all_ids()
        collection.init_index("global_index", vectors, item_ids)

    # Store to disk
    logger.info("Storing collection to disk...")
    vdb.store_to_disk()

    # Perform retrieval
    query = "Tell me about programming languages"
    logger.info(f"Retrieving results for query: '{query}'")
    query_vector = normalize_vector(embedding_model.encode(query))
    # Use vdb.retrieve which prints results directly
    vdb.retrieve(query_vector, topk=2, index_name="global_index")

    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
