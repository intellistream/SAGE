"""
SAGE RAG - Usage Examples

This file demonstrates how to use the SAGE RAG (Retrieval-Augmented Generation) toolkit.

Layer: L3 (Core - Algorithm Library)
"""


def example_document_loading():
    """
    Example 1: Loading documents

    Demonstrates how to load documents from various sources using
    the document loaders.
    """
    print("=" * 60)
    print("Example 1: Loading Documents")
    print("=" * 60)

    try:
        from sage.libs.rag.document_loaders import JSONLoader, PDFLoader, TextLoader

        print("\n✓ Available document loaders:")
        print("  - TextLoader: Load plain text files")
        print("  - PDFLoader: Load PDF documents")
        print("  - JSONLoader: Load structured JSON data")

        # Example: Loading text files
        print("\nExample: Loading a text file")
        print(
            """
        loader = TextLoader("documents/article.txt")
        documents = loader.load()
        for doc in documents:
            print(f"Content: {doc.content[:100]}...")
        """
        )

    except ImportError as e:
        print(f"✗ Import error: {e}")
        print("Some document loaders may require additional dependencies")


def example_rag_pipeline():
    """
    Example 2: Building a RAG pipeline

    Demonstrates how to build a complete RAG pipeline with
    document loading, embedding, retrieval, and generation.
    """
    print("\n" + "=" * 60)
    print("Example 2: Building a RAG Pipeline")
    print("=" * 60)

    try:
        from sage.libs.rag.pipeline import RAGPipeline

        print("\n✓ RAG Pipeline components:")
        print("  1. Document Loader: Load source documents")
        print("  2. Text Splitter: Split into chunks")
        print("  3. Embedder: Generate embeddings")
        print("  4. Vector Store: Store and index embeddings")
        print("  5. Retriever: Find relevant chunks")
        print("  6. Generator: Generate answers")

        print("\nExample pipeline setup:")
        print(
            """
        from sage.libs.rag.pipeline import RAGPipeline
        from sage.libs.rag.document_loaders import TextLoader

        # Create pipeline
        pipeline = RAGPipeline(
            loader=TextLoader("knowledge_base/"),
            chunk_size=512,
            embedding_model="all-MiniLM-L6-v2",
            llm_model="gpt-3.5-turbo"
        )

        # Build index
        pipeline.build_index()

        # Query
        answer = pipeline.query("What is SAGE?")
        print(answer)
        """
        )

    except ImportError as e:
        print(f"✗ Import error: {e}")


def example_vector_stores():
    """
    Example 3: Using vector stores

    Demonstrates how to use different vector store backends
    for storing and retrieving embeddings.
    """
    print("\n" + "=" * 60)
    print("Example 3: Vector Store Integration")
    print("=" * 60)

    print("\n✓ Supported vector stores:")
    print("  - Milvus: Distributed vector database")
    print("  - Chroma: Lightweight in-memory store")
    print("  - FAISS: Facebook AI Similarity Search")

    print("\nExample: Using Milvus")
    print(
        """
    from sage.libs.integrations.milvus import MilvusBackend
    from sage.libs.rag.pipeline import RAGPipeline

    # Create Milvus backend
    milvus = MilvusBackend(
        host="localhost",
        port=19530,
        collection_name="documents"
    )

    # Use in RAG pipeline
    pipeline = RAGPipeline(vector_store=milvus)
    """
    )

    print("\nExample: Using ChromaDB")
    print(
        """
    from sage.libs.integrations.chroma import ChromaBackend

    # Create Chroma backend
    chroma = ChromaBackend(
        persist_directory="./chroma_db",
        collection_name="documents"
    )

    # Add documents
    chroma.add_documents(documents, embeddings)

    # Search
    results = chroma.search(query_embedding, top_k=5)
    """
    )


def example_profiling():
    """
    Example 4: RAG performance profiling

    Demonstrates how to profile and optimize RAG pipelines
    using the built-in profiler.
    """
    print("\n" + "=" * 60)
    print("Example 4: RAG Pipeline Profiling")
    print("=" * 60)

    try:
        from sage.libs.rag.profiler import RAGProfiler

        print("\n✓ RAG Profiler capabilities:")
        print("  - Measure retrieval latency")
        print("  - Track generation time")
        print("  - Monitor memory usage")
        print("  - Analyze relevance scores")

        print("\nExample profiling:")
        print(
            """
        from sage.libs.rag.profiler import RAGProfiler
        from sage.libs.rag.pipeline import RAGPipeline

        # Create profiler
        profiler = RAGProfiler()

        # Profile pipeline
        with profiler.profile("rag_query"):
            pipeline = RAGPipeline(...)
            answer = pipeline.query("Sample question")

        # Get metrics
        metrics = profiler.get_metrics()
        print(f"Retrieval time: {metrics['retrieval_ms']}ms")
        print(f"Generation time: {metrics['generation_ms']}ms")
        print(f"Total time: {metrics['total_ms']}ms")
        """
        )

    except ImportError as e:
        print(f"✗ Import error: {e}")


def example_advanced_retrieval():
    """
    Example 5: Advanced retrieval strategies

    Demonstrates advanced retrieval techniques like hybrid search,
    reranking, and query expansion.
    """
    print("\n" + "=" * 60)
    print("Example 5: Advanced Retrieval Strategies")
    print("=" * 60)

    print("\n✓ Advanced retrieval techniques:")
    print("  - Hybrid search: Combine dense + sparse retrieval")
    print("  - Reranking: Post-process retrieval results")
    print("  - Query expansion: Enhance queries with synonyms")
    print("  - Multi-hop retrieval: Iterative retrieval")

    print("\nExample: Hybrid search")
    print(
        """
    # Combine dense (embedding) and sparse (BM25) retrieval
    dense_results = vector_store.search(query_embedding, top_k=20)
    sparse_results = bm25_index.search(query_text, top_k=20)

    # Merge and rerank
    combined = merge_results(dense_results, sparse_results)
    reranked = reranker.rerank(query, combined, top_k=5)
    """
    )

    print("\nExample: Query expansion")
    print(
        """
    # Expand query with synonyms and related terms
    original_query = "machine learning algorithms"
    expanded_query = query_expander.expand(original_query)
    # Result: "machine learning algorithms ML AI models neural networks"

    # Use expanded query for retrieval
    results = vector_store.search(expanded_query, top_k=10)
    """
    )


def run_all_examples():
    """Run all examples in sequence."""
    print("\n" + "=" * 60)
    print("SAGE RAG - Complete Examples")
    print("=" * 60)

    example_document_loading()
    example_rag_pipeline()
    example_vector_stores()
    example_profiling()
    example_advanced_retrieval()

    print("\n" + "=" * 60)
    print("✓ All examples completed")
    print("=" * 60)
    print("\nFor more information:")
    print("- See rag/README.md for detailed documentation")
    print("- Check examples/ for complete working examples")
    print("- Visit docs/ for RAG best practices")


if __name__ == "__main__":
    run_all_examples()
