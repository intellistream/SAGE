"""Retrieval-Augmented Generation building blocks for SAGE Libs.

Layer: L3 (Algorithm Library)
This module provides RAG components and utilities:
- loaders: Document loaders for various formats
- chunk: Text chunking and segmentation
- types: Common type definitions for RAG

For full RAG pipelines and orchestration, use sage.middleware.operators.rag.

Components planned for future enhancement:
- retrievers: Retriever interfaces (vector, keyword, hybrid)
- rerankers: Reranking algorithms
- context_builders: Context assembly and budget-aware truncation
- post_processing: Citation alignment, de-duplication
"""

from . import chunk, document_loaders, types
from .chunk import CharacterSplitter, SentenceTransformersTokenTextSplitter
from .document_loaders import (
    DocLoader,
    DocxLoader,
    LoaderFactory,
    MarkdownLoader,
    PDFLoader,
    TextLoader,
)

__all__ = [
    # Chunking utilities
    "CharacterSplitter",
    "SentenceTransformersTokenTextSplitter",
    "chunk",
    # Document loaders
    "TextLoader",
    "PDFLoader",
    "DocxLoader",
    "DocLoader",
    "MarkdownLoader",
    "LoaderFactory",
    "document_loaders",
    # Type definitions
    "types",
]
