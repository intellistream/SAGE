"""Compatibility shim for RAG document loaders.

The actual loader implementations have moved to ``sage.libs.rag.document_loaders``
so that lower layers can reuse them without depending on middleware.
"""

from sage.libs.rag.document_loaders import (  # noqa: F401
    DocLoader,
    DocxLoader,
    LoaderFactory,
    MarkdownLoader,
    PDFLoader,
    TextLoader,
)

__all__ = [
    "TextLoader",
    "PDFLoader",
    "DocxLoader",
    "DocLoader",
    "MarkdownLoader",
    "LoaderFactory",
]
