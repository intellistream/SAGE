"""
Example: Using GraphMemoryCollection for Knowledge Graph-based Memory

This example demonstrates how to use GraphMemoryCollection to build and query
a knowledge graph for memory management in RAG applications.

Key features:
- Creating graph-based memory collections
- Adding nodes (concepts/entities) and edges (relationships)
- Graph traversal for context retrieval
- Persistence (save/load)
"""

import os
import shutil

from sage.middleware.components.sage_mem import GraphMemoryCollection, MemoryManager


def example_basic_graph_collection():
    """
    Basic example: Creating and using a graph memory collection directly.
    """
    print("\n" + "=" * 70)
    print("Example 1: Basic Graph Collection Usage")
    print("=" * 70)

    # Create a graph collection
    collection = GraphMemoryCollection("knowledge_graph")

    # Create an index for the graph
    collection.create_index({"name": "concepts"})

    # Add nodes representing concepts or entities
    collection.add_node(
        "ai",
        "Artificial Intelligence is the simulation of human intelligence by machines",
        metadata={"type": "field", "level": "top"},
    )

    collection.add_node(
        "ml",
        "Machine Learning is a subset of AI focusing on learning from data",
        metadata={"type": "field", "level": "mid"},
    )

    collection.add_node(
        "dl",
        "Deep Learning uses neural networks with multiple layers",
        metadata={"type": "field", "level": "mid"},
    )

    collection.add_node(
        "nlp",
        "Natural Language Processing focuses on human language understanding",
        metadata={"type": "field", "level": "mid"},
    )

    collection.add_node(
        "transformers",
        "Transformers are a type of neural network architecture",
        metadata={"type": "technology", "level": "low"},
    )

    # Add edges representing relationships
    # Higher weight = stronger relationship
    collection.add_edge("ai", "ml", weight=1.0)  # ML is a core part of AI
    collection.add_edge("ai", "nlp", weight=0.9)  # NLP is a major AI subfield
    collection.add_edge("ml", "dl", weight=0.95)  # DL is a key ML technique
    collection.add_edge("nlp", "transformers", weight=0.9)  # Transformers are key for NLP
    collection.add_edge("dl", "transformers", weight=0.8)  # Transformers use DL

    # Retrieve neighbors of a concept
    print("\n1. Get neighbors of 'AI':")
    neighbors = collection.get_neighbors("ai", k=5)
    for neighbor in neighbors:
        print(f"  - {neighbor['node_id']}: {neighbor['data'][:50]}...")

    # Graph traversal to find related concepts
    print("\n2. Traverse graph from 'AI' (depth=2):")
    traversal = collection.retrieve_by_graph("ai", max_depth=2, max_nodes=5)
    for item in traversal:
        print(f"  - Depth {item['depth']}: {item['node_id']} - {item['data'][:50]}...")

    # Retrieve by metadata
    print("\n3. Retrieve all mid-level concepts:")
    mid_level = collection.retrieve(with_metadata=True, level="mid")
    for item in mid_level:
        print(f"  - {item['text'][:60]}...")

    return collection


def example_knowledge_graph_rag():
    """
    Example: Building a knowledge graph for RAG with document relationships.
    """
    print("\n" + "=" * 70)
    print("Example 2: Knowledge Graph for RAG")
    print("=" * 70)

    collection = GraphMemoryCollection("rag_knowledge_graph")
    collection.create_index({"name": "documents"})

    # Add document nodes
    docs = {
        "intro_rag": "RAG combines retrieval and generation for better LLM responses",
        "vector_db": "Vector databases enable semantic search using embeddings",
        "embeddings": "Embeddings are dense vector representations of text",
        "chunking": "Chunking splits documents into smaller, manageable pieces",
        "retrieval": "Retrieval finds relevant information from a knowledge base",
        "generation": "Generation uses LLMs to create responses based on context",
    }

    for doc_id, content in docs.items():
        collection.add_node(doc_id, content, metadata={"type": "document"})

    # Create relationships based on conceptual connections
    collection.add_edge("intro_rag", "retrieval", weight=1.0)
    collection.add_edge("intro_rag", "generation", weight=1.0)
    collection.add_edge("retrieval", "vector_db", weight=0.9)
    collection.add_edge("retrieval", "embeddings", weight=0.8)
    collection.add_edge("vector_db", "embeddings", weight=0.9)
    collection.add_edge("chunking", "retrieval", weight=0.7)

    # Query: Find all documents related to RAG
    print("\n1. Documents related to 'intro_rag':")
    related = collection.retrieve_by_graph("intro_rag", max_depth=2, max_nodes=6)
    for doc in related:
        print(f"  - [{doc['depth']}] {doc['node_id']}: {doc['data']}")

    # Get direct connections to retrieval
    print("\n2. Direct neighbors of 'retrieval':")
    retrieval_neighbors = collection.get_neighbors("retrieval", k=5)
    for neighbor in retrieval_neighbors:
        print(f"  - {neighbor['node_id']}: {neighbor['data']}")

    return collection


def example_with_memory_manager():
    """
    Example: Using GraphMemoryCollection through MemoryManager.
    """
    print("\n" + "=" * 70)
    print("Example 3: Using Graph Collection with MemoryManager")
    print("=" * 70)

    # Create a memory manager
    manager = MemoryManager()

    # Create a graph collection via manager
    config = {
        "name": "research_graph",
        "backend_type": "graph",
        "description": "Research paper citation graph",
    }

    collection = manager.create_collection(config)

    # Create index
    collection.create_index({"name": "papers"})  # type: ignore[union-attr]

    # Add research papers as nodes
    papers = {
        "attention_paper": "Attention is All You Need - Transformer architecture",
        "bert_paper": "BERT: Pre-training of Deep Bidirectional Transformers",
        "gpt_paper": "Improving Language Understanding by Generative Pre-Training",
        "rag_paper": "Retrieval-Augmented Generation for Knowledge-Intensive Tasks",
    }

    for paper_id, description in papers.items():
        collection.add_node(  # type: ignore[union-attr]
            paper_id,
            description,
            metadata={"type": "paper"},
        )

    # Add citation relationships
    collection.add_edge("bert_paper", "attention_paper", weight=1.0)  # type: ignore[union-attr]  # BERT cites Attention
    collection.add_edge("gpt_paper", "attention_paper", weight=1.0)  # type: ignore[union-attr]  # GPT cites Attention
    collection.add_edge("rag_paper", "bert_paper", weight=0.8)  # type: ignore[union-attr]  # RAG cites BERT
    collection.add_edge("rag_paper", "gpt_paper", weight=0.7)  # type: ignore[union-attr]  # RAG cites GPT

    print("\n1. Papers citing 'attention_paper':")
    # Note: We need to get incoming neighbors for citations
    index = collection.indexes["papers"]  # type: ignore[union-attr]
    citing_papers = index.get_incoming_neighbors("attention_paper", k=10)  # type: ignore[union-attr]
    for paper_id in citing_papers:
        data = index.get_node_data(paper_id)  # type: ignore[union-attr]
        print(f"  - {paper_id}: {data}")

    # Store the collection
    print("\n2. Storing collection to disk...")
    manager.store_collection("research_graph")
    print("   ✓ Collection saved")

    # Delete from memory and reload
    print("\n3. Reloading collection from disk...")
    del manager
    manager = MemoryManager()
    loaded_collection = manager.get_collection("research_graph")
    print("   ✓ Collection loaded")

    # Verify loaded data
    print("\n4. Verifying loaded data:")
    neighbors = loaded_collection.get_neighbors("attention_paper", k=5)  # type: ignore[union-attr]
    print(f"   Found {len(neighbors)} records after reload")  # type: ignore[arg-type]

    # Cleanup
    manager.delete_collection("research_graph")

    return manager


def main():
    """Run all examples."""
    print("\n" + "=" * 70)
    print("GraphMemoryCollection Examples")
    print("=" * 70)

    # Run examples
    example_basic_graph_collection()
    example_knowledge_graph_rag()
    example_with_memory_manager()

    print("\n" + "=" * 70)
    print("All examples completed successfully!")
    print("=" * 70)

    # Cleanup
    from sage.middleware.components.sage_mem.neuromem.utils.path_utils import (
        get_default_data_dir,
    )

    data_dir = get_default_data_dir()
    if os.path.exists(data_dir):
        shutil.rmtree(os.path.dirname(data_dir))
        print(f"\n✓ Cleaned up test data directory: {data_dir}")


if __name__ == "__main__":
    main()
