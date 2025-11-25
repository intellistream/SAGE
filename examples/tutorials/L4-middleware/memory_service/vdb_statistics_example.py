#!/usr/bin/env python3
"""
Example: Using VDBMemoryCollection Statistics

This script demonstrates the memory statistics and audit functionality
added to VDBMemoryCollection.
"""

import json
import time

from sage.middleware.components.sage_mem.neuromem.memory_collection.vdb_collection import (
    VDBMemoryCollection,
)


def print_section(title):
    """Print a section header."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def main():
    """Main example function."""
    print_section("VDBMemoryCollection Statistics Example")

    # 1. Create collection
    print("\n1. Creating collection...")
    config = {"name": "statistics_example"}
    collection = VDBMemoryCollection(config=config)
    print("✓ Collection created")

    # 2. Create index
    print("\n2. Creating index...")
    index_config = {
        "name": "example_index",
        "embedding_model": "mockembedder",
        "dim": 128,
        "backend_type": "FAISS",
        "description": "Example index for statistics demo",
        "index_parameter": {},
    }
    collection.create_index(config=index_config)
    print("✓ Index created")

    # Check statistics after index creation
    stats = collection.get_statistics()
    print(f"   Index create count: {stats['index_create_count']}")

    # 3. Insert data
    print("\n3. Inserting data...")
    documents = [
        ("Python is a programming language", {"category": "tech", "priority": "high"}),
        ("Machine learning is a subset of AI", {"category": "tech", "priority": "high"}),
        (
            "Data science combines statistics and programming",
            {"category": "tech", "priority": "medium"},
        ),
        ("Neural networks mimic the human brain", {"category": "ai", "priority": "high"}),
        ("Deep learning uses multiple layers", {"category": "ai", "priority": "medium"}),
    ]

    for text, metadata in documents:
        collection.insert("example_index", text, metadata=metadata)
        time.sleep(0.01)  # Small delay to simulate real usage

    print(f"✓ Inserted {len(documents)} documents")

    # Check statistics after insertion
    stats = collection.get_statistics()
    print(f"   Insert count: {stats['insert_count']}")
    print(f"   Total vectors stored: {stats['total_vectors_stored']}")

    # 4. Batch insert additional data
    print("\n4. Batch inserting more data...")
    batch_texts = [
        "Vector databases store embeddings",
        "Semantic search finds similar content",
        "RAG combines retrieval and generation",
    ]
    collection.batch_insert_data(batch_texts, None)
    collection.init_index("example_index")
    print(f"✓ Batch inserted {len(batch_texts)} documents")

    # 5. Perform retrievals
    print("\n5. Performing retrievals...")
    queries = [
        "programming",
        "artificial intelligence",
        "machine learning",
    ]

    for query in queries:
        results = collection.retrieve(query, "example_index", topk=3)
        print(f"   Query: '{query}' -> {len(results) if results else 0} results")
        time.sleep(0.01)

    # 6. Show memory statistics
    print_section("Memory Statistics")
    memory_stats = collection.get_memory_stats()
    print(json.dumps(memory_stats, indent=2))

    # 7. Show retrieval statistics
    print_section("Retrieval Statistics")
    retrieve_stats = collection.get_retrieve_stats(last_n=5)
    print(f"Total retrievals: {retrieve_stats['total_retrieve_count']}")
    print(f"Average duration: {retrieve_stats['avg_duration']:.4f}s")
    print("\nRecent retrievals:")
    for i, stat in enumerate(retrieve_stats["recent_stats"], 1):
        print(
            f"  {i}. Index: {stat['index_name']}, "
            f"Results: {stat['result_count']}, "
            f"Duration: {stat['duration']:.4f}s"
        )

    # 8. Show index rebuild statistics
    print_section("Index Rebuild Statistics")
    rebuild_stats = collection.get_index_rebuild_stats()
    print(json.dumps(rebuild_stats, indent=2, default=str))

    # 9. Show all statistics
    print_section("Complete Statistics")
    all_stats = collection.get_statistics()
    # Pretty print without retrieve_stats details for brevity
    summary = {
        "insert_count": all_stats["insert_count"],
        "retrieve_count": all_stats["retrieve_count"],
        "index_create_count": all_stats["index_create_count"],
        "index_rebuild_count": all_stats["index_rebuild_count"],
        "total_vectors_stored": all_stats["total_vectors_stored"],
        "retrieve_stats_count": len(all_stats["retrieve_stats"]),
        "index_stats": all_stats["index_stats"],
    }
    print(json.dumps(summary, indent=2, default=str))

    # 10. Demonstrate reset
    print_section("Reset Statistics")
    print("Resetting statistics...")
    collection.reset_statistics()
    stats_after_reset = collection.get_statistics()
    print(f"Insert count after reset: {stats_after_reset['insert_count']}")
    print(f"Retrieve count after reset: {stats_after_reset['retrieve_count']}")
    print("✓ Statistics reset successfully")

    print_section("Example Complete")
    print("✓ All statistics features demonstrated successfully!")


if __name__ == "__main__":
    main()
