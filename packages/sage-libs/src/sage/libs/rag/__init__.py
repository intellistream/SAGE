"""Retrieval-Augmented Generation building blocks for SAGE Libs.

Layer: L3 (Algorithm Library)
This module provides basic RAG components (loaders, chunkers, types).
For RAG pipelines and orchestration, use sage.middleware.operators.rag.
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
