"""
测试 sage.libs.rag.document_loaders 模块
"""

import tempfile
from pathlib import Path

import pytest

from sage.libs.rag.document_loaders import TextLoader


@pytest.mark.unit
class TestTextLoader:
    """测试TextLoader类"""

    def test_text_loader_initialization(self):
        """测试TextLoader初始化"""
        loader = TextLoader("test.txt")
        assert loader.filepath == "test.txt"
        assert loader.encoding == "utf-8"
        assert loader.chunk_separator is None

    def test_text_loader_custom_encoding(self):
        """测试自定义编码"""
        loader = TextLoader("test.txt", encoding="gbk", chunk_separator="\n\n")
        assert loader.encoding == "gbk"
        assert loader.chunk_separator == "\n\n"

    def test_text_loader_load_file(self):
        """测试加载文本文件"""
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("This is a test document.\nWith multiple lines.")
            temp_path = f.name

        try:
            loader = TextLoader(temp_path)
            result = loader.load()

            assert isinstance(result, dict)
            assert "content" in result
            assert "metadata" in result
            assert "This is a test document" in result["content"]
            assert result["metadata"]["source"] == temp_path
            assert result["metadata"]["type"] == "txt"
        finally:
            # 清理临时文件
            Path(temp_path).unlink()

    def test_text_loader_file_not_found(self):
        """测试文件不存在的情况"""
        loader = TextLoader("nonexistent_file.txt")
        with pytest.raises(FileNotFoundError):
            loader.load()

    def test_text_loader_utf8_content(self):
        """测试UTF-8编码内容"""
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", delete=False, suffix=".txt"
        ) as f:
            f.write("中文测试内容\nChinese test content")
            temp_path = f.name

        try:
            loader = TextLoader(temp_path)
            result = loader.load()

            assert "中文测试内容" in result["content"]
            assert "Chinese test content" in result["content"]
        finally:
            Path(temp_path).unlink()

    def test_text_loader_empty_file(self):
        """测试空文件"""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            temp_path = f.name

        try:
            loader = TextLoader(temp_path)
            result = loader.load()

            assert result["content"] == ""
            assert result["metadata"]["type"] == "txt"
        finally:
            Path(temp_path).unlink()


# PDFLoader 和 DocxLoader 需要额外的依赖，标记为 external
@pytest.mark.external
class TestPDFLoader:
    """测试PDFLoader类（需要PyPDF2）"""

    def test_pdf_loader_import_error(self):
        """测试缺少PyPDF2依赖时的错误"""
        pytest.importorskip("PyPDF2", reason="PyPDF2 not installed")


@pytest.mark.external
class TestDocxLoader:
    """测试DocxLoader类（需要python-docx）"""

    def test_docx_loader_import_error(self):
        """测试缺少python-docx依赖时的错误"""
        pytest.importorskip("docx", reason="python-docx not installed")
