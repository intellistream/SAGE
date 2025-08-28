"""
document_loaders.py
SAGE RAG 示例：文本加载工具,支持多种格式的文档加载工具
"""
import logging
import warnings
from bs4 import BeautifulSoup  # 用于HTML/Markdown内容提取
import markdown  # 用于Markdown解析
import pdfplumber  # 用于PDF解析
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Union
import re
import os


# 抑制pdfplumber的特定警告
warnings.filterwarnings(
    "ignore", message="Could get FontBBox from font descriptor")
logging.getLogger('pdfplumber').setLevel(logging.ERROR)


class BaseLoader(ABC):
    """文档加载器基类，定义统一接口"""

    @abstractmethod
    def load(self) -> Dict:
        """加载文档，返回包含内容和元数据的字典"""
        pass

    @staticmethod
    def _get_metadata(filepath: str) -> Dict:
        """获取文件基本元数据"""
        return {
            "source": filepath,
            "file_size": os.path.getsize(filepath),
            "last_modified": os.path.getmtime(filepath)
        }


class TextLoader(BaseLoader):
    """加载纯文本文件"""

    def __init__(self, filepath: str, encoding: str = "utf-8"):
        self.filepath = filepath
        self.encoding = encoding

    def load(self) -> Dict:
        if not os.path.exists(self.filepath):
            raise FileNotFoundError(f"File not found: {self.filepath}")

        with open(self.filepath, "r", encoding=self.encoding) as f:
            content = f.read()

        return {
            "content": content,
            "metadata": {**self._get_metadata(self.filepath), "type": "text"}
        }


class PDFLoader(BaseLoader):
    """加载PDF文件"""

    def __init__(self, filepath: str):
        self.filepath = filepath

    def load(self) -> Dict:
        if not os.path.exists(self.filepath):
            raise FileNotFoundError(f"File not found: {self.filepath}")

        content = ""
        try:
            with pdfplumber.open(self.filepath) as pdf:
                for i, page in enumerate(pdf.pages):
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            content += f"--- 第 {i+1} 页 ---\n{page_text}\n\n"
                        else:
                            content += f"--- 第 {i+1} 页 (无文本内容) ---\n"
                    except Exception as page_error:
                        content += f"--- 第 {i+1} 页 (解析错误: {page_error}) ---\n"
        except Exception as e:
            return {
                "content": f"PDF文件解析失败: {e}",
                "metadata": {**self._get_metadata(self.filepath), "type": "pdf", "error": str(e)}
            }

        return {
            "content": content.strip(),
            "metadata": {**self._get_metadata(self.filepath), "type": "pdf"}
        }


class MarkdownLoader(BaseLoader):
    """加载Markdown文件"""

    def __init__(self, filepath: str, encoding: str = "utf-8"):
        self.filepath = filepath
        self.encoding = encoding

    def load(self) -> Dict:
        if not os.path.exists(self.filepath):
            raise FileNotFoundError(f"File not found: {self.filepath}")

        with open(self.filepath, "r", encoding=self.encoding) as f:
            md_content = f.read()

        # 转换为HTML然后提取纯文本
        html = markdown.markdown(md_content)
        soup = BeautifulSoup(html, "html.parser")
        content = soup.get_text()

        return {
            "content": content,
            "metadata": {**self._get_metadata(self.filepath), "type": "markdown"}
        }


class DocumentLoader:
    """统一文档加载器，根据文件扩展名自动选择适当的加载器"""

    @staticmethod
    def get_loader(filepath: str) -> BaseLoader:
        """根据文件扩展名获取适当的加载器"""
        ext = os.path.splitext(filepath)[1].lower()

        if ext == ".txt":
            return TextLoader(filepath)
        elif ext == ".pdf":
            return PDFLoader(filepath)
        elif ext in [".md", ".markdown"]:
            return MarkdownLoader(filepath)
        else:
            raise ValueError(f"Unsupported file format: {ext}")

    @staticmethod
    def load(filepath: str) -> Dict:
        """加载文档的统一入口"""
        loader = DocumentLoader.get_loader(filepath)
        return loader.load()
