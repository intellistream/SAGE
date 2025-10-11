"""RAG Pipeline Implementations.

This module contains various RAG pipeline implementations for benchmarking:

Retrieval Methods:
- Dense retrieval (embedding-based)
- Sparse retrieval (BM25, sparse vectors)
- Hybrid retrieval (combining dense + sparse)

Vector Databases:
- Milvus (dense, sparse, hybrid)
- ChromaDB (local vector database)
- FAISS (efficient similarity search)

Advanced Features:
- Multimodal fusion (text + image + video)
- Reranking strategies
- Query refinement
- Distributed processing (Ray)

Each pipeline can be run independently for testing or used in benchmark experiments.
"""

__all__ = []
