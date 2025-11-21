"""
Document Storage Feature Demo
=============================

This example demonstrates the document storage functionality in SAGE's neuromem component.

Features shown:
1. Basic document storage (insert, retrieve)
2. Metadata management
3. Vector-based semantic search
4. Hybrid search (vectors + metadata filtering)
5. Persistence (save/load from disk)

Author: SAGE Team
Date: 2024-01-22
"""

import json
import os
from typing import Any

from sage.middleware.components.sage_mem.neuromem.memory_manager import MemoryManager


def example_1_basic_storage():
    """Example 1: Basic document storage and retrieval"""
    print("\n" + "=" * 60)
    print("Example 1: Basic Document Storage")
    print("=" * 60)

    # Create manager with custom data directory
    data_dir = ".sage/examples/document_storage/example_1"
    manager = MemoryManager(data_dir=data_dir)

    # Create a document collection
    config = {
        "name": "basic_docs",
        "backend_type": "VDB",
        "description": "Basic document collection",
    }
    collection = manager.create_collection(config)

    # Prepare sample documents
    documents = [
        "Python是一种广泛使用的高级编程语言，以其简洁的语法和强大的功能而闻名。",
        "机器学习是人工智能的一个分支，通过算法让计算机从数据中学习。",
        "深度学习使用多层神经网络来处理复杂的数据表示和特征提取。",
        "自然语言处理（NLP）是计算机科学和人工智能的一个领域。",
        "Transformer架构革新了自然语言处理，成为现代大语言模型的基础。",
    ]

    metadatas = [
        {"topic": "编程语言", "difficulty": "初级", "source": "教材"},
        {"topic": "人工智能", "difficulty": "中级", "source": "论文"},
        {"topic": "人工智能", "difficulty": "高级", "source": "论文"},
        {"topic": "人工智能", "difficulty": "中级", "source": "教程"},
        {"topic": "人工智能", "difficulty": "高级", "source": "论文"},
    ]

    # Batch insert documents
    collection.batch_insert_data(documents, metadatas)
    print(f"✅ 已插入 {len(documents)} 个文档")

    # Retrieve all documents
    all_docs = collection.retrieve(with_metadata=True)
    print(f"\n所有文档数量: {len(all_docs)}")

    # Retrieve with metadata filtering
    print("\n📌 检索 topic='人工智能' 的文档:")
    ai_docs = collection.retrieve(with_metadata=True, topic="人工智能")
    for i, doc in enumerate(ai_docs, 1):
        print(f"  {i}. {doc['text'][:50]}...")
        print(f"     难度: {doc['metadata']['difficulty']}")

    # Retrieve with custom filter function
    print("\n📌 检索高级难度的文档:")
    advanced_docs = collection.retrieve(
        with_metadata=True, metadata_filter_func=lambda m: m.get("difficulty") == "高级"
    )
    for i, doc in enumerate(advanced_docs, 1):
        print(f"  {i}. {doc['text'][:50]}...")

    # Save to disk
    manager.store_collection("basic_docs")
    print(f"\n💾 文档已保存到: {data_dir}")


def example_2_semantic_search():
    """Example 2: Semantic search with vector indexing"""
    print("\n" + "=" * 60)
    print("Example 2: Semantic Search (Vector Indexing)")
    print("=" * 60)

    data_dir = ".sage/examples/document_storage/example_2"
    manager = MemoryManager(data_dir=data_dir)

    # Create collection
    collection = manager.create_collection(
        {"name": "semantic_docs", "backend_type": "VDB", "description": "Semantic search collection"}
    )

    # Insert documents
    documents = [
        "如何使用Python进行数据分析和可视化？",
        "深度学习模型的训练需要大量的标注数据。",
        "Transformer模型在自然语言处理任务中表现优异。",
        "Python的pandas库是数据处理的强大工具。",
        "BERT模型通过预训练和微调实现了优秀的NLP性能。",
        "数据可视化帮助我们更好地理解数据的模式和趋势。",
    ]

    metadatas = [
        {"category": "数据分析", "year": 2023},
        {"category": "深度学习", "year": 2023},
        {"category": "NLP", "year": 2023},
        {"category": "数据分析", "year": 2024},
        {"category": "NLP", "year": 2024},
        {"category": "数据分析", "year": 2024},
    ]

    collection.batch_insert_data(documents, metadatas)
    print(f"✅ 已插入 {len(documents)} 个文档")

    # Create semantic index
    index_config = {
        "name": "semantic_index",
        "embedding_model": "mockembedder",  # Use mock embedder for demo
        "dim": 128,
        "backend_type": "FAISS",
        "description": "Semantic search index",
    }

    collection.create_index(index_config)
    collection.init_index("semantic_index")
    print("✅ 语义索引创建完成")

    # Semantic search
    queries = ["Python数据处理", "自然语言处理模型", "如何训练深度学习"]

    for query in queries:
        print(f"\n🔍 查询: '{query}'")
        results = collection.retrieve(
            raw_data=query, index_name="semantic_index", topk=3, threshold=0.1, with_metadata=True
        )

        if results:
            for i, result in enumerate(results, 1):
                print(f"  {i}. {result['text']}")
                print(f"     类别: {result['metadata']['category']}, 年份: {result['metadata']['year']}")
                print(f"     相似度: {result.get('score', 'N/A'):.4f}")
        else:
            print("  未找到相关结果")

    # Save
    manager.store_collection("semantic_docs")
    print(f"\n💾 数据已保存到: {data_dir}")


def example_3_hybrid_search():
    """Example 3: Hybrid search (semantic + metadata filtering)"""
    print("\n" + "=" * 60)
    print("Example 3: Hybrid Search (Semantic + Metadata)")
    print("=" * 60)

    data_dir = ".sage/examples/document_storage/example_3"
    manager = MemoryManager(data_dir=data_dir)

    # Create collection
    collection = manager.create_collection(
        {"name": "hybrid_docs", "backend_type": "VDB", "description": "Hybrid search collection"}
    )

    # Insert technical documents with rich metadata
    documents = [
        "Python 3.10引入了模式匹配功能，使代码更简洁。",
        "TensorFlow 2.0提供了更易用的高级API。",
        "PyTorch在学术界广受欢迎，特别是在深度学习研究中。",
        "Rust语言提供了内存安全保证，适合系统编程。",
        "Go语言的并发模型基于CSP理论，简单高效。",
        "JavaScript ES2023增加了新的数组方法。",
    ]

    metadatas = [
        {"language": "Python", "version": "3.10", "category": "language", "year": 2021},
        {"language": "Python", "version": "2.0", "category": "framework", "year": 2019},
        {"language": "Python", "version": "1.x", "category": "framework", "year": 2016},
        {"language": "Rust", "version": "1.x", "category": "language", "year": 2015},
        {"language": "Go", "version": "1.x", "category": "language", "year": 2009},
        {"language": "JavaScript", "version": "ES2023", "category": "language", "year": 2023},
    ]

    collection.batch_insert_data(documents, metadatas)

    # Create index
    collection.create_index(
        {
            "name": "tech_index",
            "embedding_model": "mockembedder",
            "dim": 128,
            "backend_type": "FAISS",
        }
    )
    collection.init_index("tech_index")
    print("✅ 技术文档索引创建完成")

    # Hybrid search 1: Python related + recent years
    print("\n🔍 混合查询1: Python相关 AND 2020年后")
    results = collection.retrieve(
        raw_data="Python深度学习框架",
        index_name="tech_index",
        topk=5,
        with_metadata=True,
        metadata_filter_func=lambda m: m.get("language") == "Python" and m.get("year", 0) >= 2020,
    )

    for i, result in enumerate(results, 1):
        print(f"  {i}. {result['text']}")
        print(f"     语言: {result['metadata']['language']}, 年份: {result['metadata']['year']}")

    # Hybrid search 2: Programming languages only
    print("\n🔍 混合查询2: 编程语言类别")
    results = collection.retrieve(
        raw_data="现代编程语言特性",
        index_name="tech_index",
        topk=5,
        with_metadata=True,
        metadata_filter_func=lambda m: m.get("category") == "language",
    )

    for i, result in enumerate(results, 1):
        print(f"  {i}. {result['text'][:60]}...")
        print(f"     语言: {result['metadata']['language']}")

    manager.store_collection("hybrid_docs")


def example_4_update_delete():
    """Example 4: Document updates and deletion"""
    print("\n" + "=" * 60)
    print("Example 4: Document Updates and Deletion")
    print("=" * 60)

    data_dir = ".sage/examples/document_storage/example_4"
    manager = MemoryManager(data_dir=data_dir)

    collection = manager.create_collection(
        {"name": "mutable_docs", "backend_type": "VDB", "description": "Mutable document collection"}
    )

    # Initial documents
    docs = ["文档1: 初始内容", "文档2: 待更新内容", "文档3: 将被删除"]
    metas = [{"status": "active"}, {"status": "active"}, {"status": "deprecated"}]

    collection.batch_insert_data(docs, metas)
    print(f"✅ 初始文档数: {len(collection.get_all_ids())}")

    # Show all documents
    print("\n初始文档:")
    all_docs = collection.retrieve(with_metadata=True)
    for doc in all_docs:
        print(f"  - {doc['text']}, 状态: {doc['metadata']['status']}")

    # Update a document
    doc_id = collection._get_stable_id(docs[1])
    collection.text_storage.store(doc_id, "文档2: 已更新的内容")
    collection.metadata_storage.store(doc_id, {"status": "updated", "version": 2})
    print("\n✏️ 更新了文档2")

    # Show after update
    print("\n更新后的文档:")
    all_docs = collection.retrieve(with_metadata=True)
    for doc in all_docs:
        print(f"  - {doc['text']}, 状态: {doc['metadata']['status']}")

    # Delete deprecated documents
    deprecated_ids = collection.filter_ids(
        collection.get_all_ids(), metadata_filter_func=lambda m: m.get("status") == "deprecated"
    )

    for doc_id in deprecated_ids:
        collection.text_storage.delete(doc_id)
        collection.metadata_storage.delete(doc_id)

    print(f"\n🗑️ 删除了 {len(deprecated_ids)} 个废弃文档")
    print(f"剩余文档数: {len(collection.get_all_ids())}")

    # Show final state
    print("\n最终文档:")
    all_docs = collection.retrieve(with_metadata=True)
    for doc in all_docs:
        print(f"  - {doc['text']}")

    manager.store_collection("mutable_docs")


def example_5_persistence():
    """Example 5: Data persistence and recovery"""
    print("\n" + "=" * 60)
    print("Example 5: Data Persistence and Recovery")
    print("=" * 60)

    data_dir = ".sage/examples/document_storage/example_5"

    # Step 1: Create and save
    print("\n📝 步骤1: 创建并保存数据")
    manager1 = MemoryManager(data_dir=data_dir)
    collection1 = manager1.create_collection(
        {"name": "persistent_docs", "backend_type": "VDB", "description": "Persistent collection"}
    )

    docs = [
        "持久化测试文档1",
        "持久化测试文档2",
        "持久化测试文档3",
    ]
    metas = [{"id": 1}, {"id": 2}, {"id": 3}]

    collection1.batch_insert_data(docs, metas)
    manager1.store_collection("persistent_docs")
    print(f"✅ 已保存 {len(docs)} 个文档到: {data_dir}")

    # Step 2: Load from disk
    print("\n📂 步骤2: 从磁盘加载数据")
    manager2 = MemoryManager(data_dir=data_dir)
    collection2 = manager2.get_collection("persistent_docs")

    if collection2:
        loaded_docs = collection2.retrieve(with_metadata=True)
        print(f"✅ 成功加载 {len(loaded_docs)} 个文档")

        for doc in loaded_docs:
            print(f"  - {doc['text']}, ID: {doc['metadata']['id']}")
    else:
        print("❌ 加载失败")


def main():
    """Run all examples"""
    print("\n" + "=" * 60)
    print("SAGE Document Storage Feature Demo")
    print("=" * 60)

    # Run all examples
    example_1_basic_storage()
    example_2_semantic_search()
    example_3_hybrid_search()
    example_4_update_delete()
    example_5_persistence()

    print("\n" + "=" * 60)
    print("✅ All examples completed successfully!")
    print("=" * 60)
    print("\n数据保存在: .sage/examples/document_storage/")
    print("可以使用以下命令查看:")
    print("  ls -la .sage/examples/document_storage/")


if __name__ == "__main__":
    main()
