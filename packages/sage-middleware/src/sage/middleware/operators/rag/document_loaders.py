"""
document_loaders.py
SAGE RAG 示例：文本加载工具
"""

import os
from pathlib import Path
from typing import Any


class TextLoader:
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
    def __init__(self, filepath: str):
        self.filepath = filepath

    def load(self) -> dict[str, Any]:
        try:
            import docx
        except ImportError:
            raise ImportError("请先安装 python-docx: pip install python-docx")
        if not os.path.exists(self.filepath):
            raise FileNotFoundError(f"File not found: {self.filepath}")
        doc = docx.Document(self.filepath)
        text = "\n".join([para.text for para in doc.paragraphs])
        return {"content": text, "metadata": {"source": self.filepath, "type": "docx"}}


class DocLoader:
    """
    仅 Windows 下可用；Linux/Mac 建议用其他工具转成 docx。
    """

    def __init__(self, filepath: str):
        self.filepath = filepath

    def load(self) -> dict[str, Any]:
        try:
            import win32com.client  # type: ignore[import-untyped]
        except ImportError:
            raise ImportError("请先安装 pywin32 (仅 Windows 支持): pip install pywin32")
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
    加载 Markdown 文件，保留原始文本。
    （可选：后续可以集成 markdown2 / mistune 转换成纯文本）
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
    工厂类，根据文件扩展名选择对应的 Loader。
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


"""
# 自动识别并加载
doc =LoaderFactory.load("examples/data/qa_knowledge_base.txt")
print(doc["content"])

doc = LoaderFactory.load("examples/data/qa_knowledge_base.pdf")
print(doc["metadata"])

doc = LoaderFactory.load("examples/data/qa_knowledge_base.docx")
print(doc["content"])


doc = LoaderFactory.load("examples/data/qa_knowledge_base.md")
print(doc["content"])
"""
