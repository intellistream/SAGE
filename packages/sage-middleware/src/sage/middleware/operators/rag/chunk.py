"""Compatibility shim for RAG chunking operators.

The canonical implementations now live in ``sage.libs.rag.chunk``. This file
keeps the old import path available for middleware operators and third-party
code until the next minor release.
"""

from sage.libs.rag.chunk import (  # noqa: F401
    CharacterSplitter,
    SentenceTransformersTokenTextSplitter,
)

__all__ = ["CharacterSplitter", "SentenceTransformersTokenTextSplitter"]
