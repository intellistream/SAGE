"""
Document loaders for RAG pipelines.

SAGE RAG - Document loading utilities for various file formats.

This is a pure algorithm module (L3) - no dependencies on middleware or
external services. These are simple utilities for loading documents.
"""

import os
from pathlib import Path
from typing import Any


class TextLoader:
    """Load plain text files."""

    def __init__(self, filepath: str, encoding: str = "utf-8", chunk_separator: str | None = None):
        self.filepath = filepath
        self.encoding = encoding
        self.chunk_separator = chunk_separator

    def load(self) -> dict[str, Any]:
        if not os.path.exists(self.filepath):
            raise FileNotFoundError(f"File not found: {self.filepath}")
        with open(self.filepath, encoding=self.encoding) as f:
            text = f.read()
        return {"content": text, "metadata": {"source": self.filepath, "type": "txt"}}


class PDFLoader:
    """Load PDF documents using PyPDF2."""

    def __init__(self, filepath: str):
        self.filepath = filepath

    def load(self) -> dict[str, Any]:
        try:
            from PyPDF2 import PdfReader
        except ImportError:
            raise ImportError("Please install PyPDF2: pip install PyPDF2")

        reader = PdfReader(self.filepath)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
        return {
            "content": text,
            "metadata": {
                "source": self.filepath,
                "type": "pdf",
                "pages": len(reader.pages),
            },
        }


class DocxLoader:
    """Load Word documents (.docx)."""

    def __init__(self, filepath: str):
        self.filepath = filepath

    def load(self) -> dict[str, Any]:
        try:
            import docx
        except ImportError:
            raise ImportError("Please install python-docx: pip install python-docx")
        if not os.path.exists(self.filepath):
            raise FileNotFoundError(f"File not found: {self.filepath}")
        doc = docx.Document(self.filepath)
        text = "\n".join([para.text for para in doc.paragraphs])
        return {"content": text, "metadata": {"source": self.filepath, "type": "docx"}}


class DocLoader:
    """
    Load legacy Word documents (.doc).

    Note: Only available on Windows; Linux/Mac users should convert to .docx first.
    """

    def __init__(self, filepath: str):
        self.filepath = filepath

    def load(self) -> dict[str, Any]:
        try:
            import win32com.client  # type: ignore[import-untyped]
        except ImportError:
            raise ImportError("Please install pywin32 (Windows only): pip install pywin32")
        if not os.path.exists(self.filepath):
            raise FileNotFoundError(f"File not found: {self.filepath}")
        word = win32com.client.Dispatch("Word.Application")
        word.Visible = False
        doc = word.Documents.Open(str(Path(self.filepath).resolve()))
        text = doc.Content.Text
        doc.Close()
        word.Quit()
        return {"content": text, "metadata": {"source": self.filepath, "type": "doc"}}


class MarkdownLoader:
    """
    Load Markdown files, preserving original text.

    Optional: Can be extended to integrate markdown2/mistune for plain text conversion.
    """

    def __init__(self, filepath: str, encoding: str = "utf-8"):
        self.filepath = filepath
        self.encoding = encoding

    def load(self) -> dict[str, Any]:
        if not os.path.exists(self.filepath):
            raise FileNotFoundError(f"File not found: {self.filepath}")
        with open(self.filepath, encoding=self.encoding) as f:
            text = f.read()
        return {"content": text, "metadata": {"source": self.filepath, "type": "md"}}


class LoaderFactory:
    """
    Factory class that selects the appropriate loader based on file extension.

    Usage:
        doc = LoaderFactory.load("examples/data/qa_knowledge_base.txt")
        print(doc["content"])
    """

    _loader_map: dict[
        str, type[TextLoader | PDFLoader | DocxLoader | DocLoader | MarkdownLoader]
    ] = {
        ".txt": TextLoader,
        ".pdf": PDFLoader,
        ".docx": DocxLoader,
        ".doc": DocLoader,
        ".md": MarkdownLoader,
        ".markdown": MarkdownLoader,
    }

    @classmethod
    def load(cls, filepath: str) -> dict[str, Any]:
        ext = Path(filepath).suffix.lower()
        loader_cls = cls._loader_map.get(ext)
        if loader_cls is None:
            raise ValueError(f"Unsupported file extension: {ext}")
        loader = loader_cls(filepath)
        return loader.load()


__all__ = [
    "TextLoader",
    "PDFLoader",
    "DocxLoader",
    "DocLoader",
    "MarkdownLoader",
    "LoaderFactory",
]
