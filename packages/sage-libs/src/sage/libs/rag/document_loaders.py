"""
document_loaders.py
SAGE RAG 示例：文本加载工具
"""
import os
from typing import List, Dict

class TextLoader:
    """
    加载文本文件，每行为一个文档。
    支持简单的分块和元数据。
    """
    def __init__(self, filepath: str, encoding: str = "utf-8", chunk_separator: str = None):
        self.filepath = filepath
        self.encoding = encoding
        self.chunk_separator = chunk_separator

    def load(self) -> Dict:
        """
        加载文本文件，返回一个完整的 document 对象: {"content": ..., "metadata": ...}
        """
        if not os.path.exists(self.filepath):
            raise FileNotFoundError(f"File not found: {self.filepath}")
        with open(self.filepath, "r", encoding=self.encoding) as f:
            text = f.read()
        document = {
            "content": text,
            "metadata": {"source": self.filepath}
        }
        return document

# loader = TextLoader('data/qa_knowledge_base.txt')
# doc = loader.load()
# print(doc["content"])
