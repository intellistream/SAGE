"""
Tests for RAG document_loaders module

Tests cover:
- TextLoader: File loading, error handling
- PDFLoader: Mock PDF reading
- DocxLoader: Mock docx reading
- MarkdownLoader: File loading
- LoaderFactory: Automatic loader selection
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest


@pytest.mark.unit
class TestTextLoader:
    """Test TextLoader"""

    def test_load_text_file(self):
        """测试加载文本文件"""
        from sage.libs.rag.document_loaders import TextLoader

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("Test content")
            filepath = f.name

        try:
            loader = TextLoader(filepath)
            result = loader.load()

            assert "content" in result
            assert result["content"] == "Test content"
            assert "metadata" in result
            assert result["metadata"]["source"] == filepath
            assert result["metadata"]["type"] == "txt"
        finally:
            Path(filepath).unlink()

    def test_file_not_found(self):
        """测试文件不存在"""
        from sage.libs.rag.document_loaders import TextLoader

        loader = TextLoader("nonexistent.txt")
        with pytest.raises(FileNotFoundError):
            loader.load()

    def test_encoding(self):
        """测试编码"""
        from sage.libs.rag.document_loaders import TextLoader

        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", delete=False, suffix=".txt"
        ) as f:
            f.write("测试内容")
            filepath = f.name

        try:
            loader = TextLoader(filepath, encoding="utf-8")
            result = loader.load()
            assert result["content"] == "测试内容"
        finally:
            Path(filepath).unlink()


@pytest.mark.unit
class TestPDFLoader:
    """Test PDFLoader with mocking"""

    def test_load_pdf(self):
        """测试加载PDF"""
        from sage.libs.rag.document_loaders import PDFLoader

        # Mock PDF reader in sys.modules
        mock_page1 = Mock()
        mock_page1.extract_text.return_value = "Page 1"
        mock_page2 = Mock()
        mock_page2.extract_text.return_value = "Page 2"

        mock_reader = Mock()
        mock_reader.pages = [mock_page1, mock_page2]

        mock_pdf_module = Mock()
        mock_pdf_module.PdfReader.return_value = mock_reader

        with patch.dict("sys.modules", {"PyPDF2": mock_pdf_module}):
            loader = PDFLoader("test.pdf")
            result = loader.load()

            assert "content" in result
            assert result["content"] == "Page 1Page 2"
            assert result["metadata"]["type"] == "pdf"
            assert result["metadata"]["pages"] == 2

    def test_import_error(self):
        """测试缺少PyPDF2"""
        from sage.libs.rag.document_loaders import PDFLoader

        with patch.dict("sys.modules", {"PyPDF2": None}):
            loader = PDFLoader("test.pdf")
            with pytest.raises(ImportError, match="PyPDF2"):
                loader.load()


@pytest.mark.unit
class TestDocxLoader:
    """Test DocxLoader with mocking"""

    def test_load_docx(self):
        """测试加载docx"""
        from sage.libs.rag.document_loaders import DocxLoader

        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as f:
            filepath = f.name

        try:
            # Mock docx document
            mock_para1 = Mock()
            mock_para1.text = "Para 1"
            mock_para2 = Mock()
            mock_para2.text = "Para 2"

            mock_doc = Mock()
            mock_doc.paragraphs = [mock_para1, mock_para2]

            mock_docx_module = Mock()
            mock_docx_module.Document.return_value = mock_doc

            with patch.dict("sys.modules", {"docx": mock_docx_module}):
                loader = DocxLoader(filepath)
                result = loader.load()

                assert "content" in result
                assert result["content"] == "Para 1\nPara 2"
                assert result["metadata"]["type"] == "docx"
        finally:
            Path(filepath).unlink()

    def test_import_error(self):
        """测试缺少python-docx"""
        from sage.libs.rag.document_loaders import DocxLoader

        with patch.dict("sys.modules", {"docx": None}):
            loader = DocxLoader("test.docx")
            with pytest.raises(ImportError, match="python-docx"):
                loader.load()


@pytest.mark.unit
class TestMarkdownLoader:
    """Test MarkdownLoader"""

    def test_load_markdown(self):
        """测试加载Markdown"""
        from sage.libs.rag.document_loaders import MarkdownLoader

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".md") as f:
            f.write("# Title\nContent")
            filepath = f.name

        try:
            loader = MarkdownLoader(filepath)
            result = loader.load()

            assert result["content"] == "# Title\nContent"
            assert result["metadata"]["type"] == "md"
        finally:
            Path(filepath).unlink()

    def test_file_not_found(self):
        """测试文件不存在"""
        from sage.libs.rag.document_loaders import MarkdownLoader

        loader = MarkdownLoader("nonexistent.md")
        with pytest.raises(FileNotFoundError):
            loader.load()


@pytest.mark.unit
class TestLoaderFactory:
    """Test LoaderFactory"""

    def test_load_txt(self):
        """测试工厂加载txt"""
        from sage.libs.rag.document_loaders import LoaderFactory

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("Factory test")
            filepath = f.name

        try:
            result = LoaderFactory.load(filepath)
            assert result["content"] == "Factory test"
            assert result["metadata"]["type"] == "txt"
        finally:
            Path(filepath).unlink()

    def test_unsupported_extension(self):
        """测试不支持的文件类型"""
        from sage.libs.rag.document_loaders import LoaderFactory

        with pytest.raises(ValueError, match="Unsupported"):
            LoaderFactory.load("test.xyz")

    def test_load_pdf_via_factory(self):
        """测试通过工厂加载PDF"""
        from sage.libs.rag.document_loaders import LoaderFactory

        mock_page = Mock()
        mock_page.extract_text.return_value = "PDF content"

        mock_reader = Mock()
        mock_reader.pages = [mock_page]

        mock_pdf_module = Mock()
        mock_pdf_module.PdfReader.return_value = mock_reader

        with patch.dict("sys.modules", {"PyPDF2": mock_pdf_module}):
            result = LoaderFactory.load("test.pdf")
            assert result["metadata"]["type"] == "pdf"
