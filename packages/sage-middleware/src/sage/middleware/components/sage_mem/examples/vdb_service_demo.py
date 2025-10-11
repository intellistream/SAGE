"""
Example demonstrating NeuroMemVDB service usage

This example shows how to use the NeuroMemVDB convenience class
for managing vector database operations.
"""

from sage.common.utils.logging.custom_logger import CustomLogger
from sage.middleware.components.sage_mem import NeuroMemVDB

logger = CustomLogger()


def main():
    logger.info("Initializing NeuroMemVDB service...")
    vdb = NeuroMemVDB()

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

    # Create and initialize index
    logger.info("Creating and initializing index...")
    index_config = {
        "name": "global_index",
        "embedding_model": "mockembedder",
        "dim": 128,
        "backend_type": "FAISS",
        "description": "Global index for all data",
    }
    vdb.create_index(collection_name, index_config)
    vdb.init_index(collection_name, "global_index")

    # Store to disk
    logger.info("Storing collection to disk...")
    vdb.store()

    # Perform retrieval
    query = "Tell me about programming languages"
    logger.info(f"Retrieving results for query: '{query}'")
    results = vdb.retrieve(
        query,
        topk=2,
        collection_name=collection_name,
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
