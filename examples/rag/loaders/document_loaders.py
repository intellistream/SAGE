"""
import logging
document_loaders.py
SAGE RAG 示例：文本加载工具
"""

import os
from typing import Dict, List


class TextLoader:
    """
    加载文本文件，每行为一个文档。
    支持简单的分块和元数据。
    """

    def __init__(self, filepath: str, encoding: str = "utf-8"):
        self.filepath = filepath
        self.encoding = encoding

    def load(self) -> List[Dict]:
        """
        加载文本文件，返回文档列表，每个文档为 dict: {"content": ..., "metadata": ...}
        """
        documents = []
        if not os.path.exists(self.filepath):
            raise FileNotFoundError(f"File not found: {self.filepath}")
        with open(self.filepath, "r", encoding=self.encoding) as f:
            for idx, line in enumerate(f):
                text = line.strip()
                if text:
                    documents.append(
                        {
                            "content": text,
                            "metadata": {"line": idx + 1, "source": self.filepath},
                        }
                    )
        return documents


# 用法示例：
# loader = TextLoader('data/qa_knowledge_base.txt')
# docs = loader.load()
# logging.info(docs[0]["content"])
