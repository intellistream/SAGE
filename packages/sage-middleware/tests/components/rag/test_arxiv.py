"""
测试 sage.middleware.operators.rag.arxiv 模块
"""


import pytest

# 尝试导入arxiv模块
pytest_plugins = []

try:
    from sage.middleware.operators.rag.arxiv import Paper  # noqa: F401

    ARXIV_AVAILABLE = True
except ImportError as e:
    ARXIV_AVAILABLE = False
    pytestmark = pytest.mark.skip(f"Arxiv module not available: {e}")


@pytest.mark.unit
class TestPaper:
    """测试Paper类"""

    def test_paper_import(self):
        """测试Paper导入"""
        if not ARXIV_AVAILABLE:
            pytest.skip("Arxiv module not available")

        from sage.middleware.operators.rag.arxiv import Paper

        assert Paper is not None

    def test_paper_initialization_with_title(self):
        """测试Paper带标题初始化"""
        if not ARXIV_AVAILABLE:
            pytest.skip("Arxiv module not available")

        paper = Paper(
            path="/path/to/paper.pdf",
            title="Test Paper Title",
            url="https://arxiv.org/abs/1234.5678",
            abs="Abstract text",
            authors=["Author 1", "Author 2"]
        )

        assert paper.title == "Test Paper Title"
        assert paper.url == "https://arxiv.org/abs/1234.5678"
        assert paper.abs == "Abstract text"
        assert paper.authors == ["Author 1", "Author 2"]


@pytest.mark.unit
class TestArxivPDFDownloader:
    """测试ArxivPDFDownloader类"""

    def test_arxiv_pdf_downloader_import(self):
        """测试ArxivPDFDownloader导入"""
        if not ARXIV_AVAILABLE:
            pytest.skip("Arxiv module not available")

        from sage.middleware.operators.rag.arxiv import ArxivPDFDownloader
        assert ArxivPDFDownloader is not None


@pytest.mark.unit
class TestArxivPDFParser:
    """测试ArxivPDFParser类"""

    def test_arxiv_pdf_parser_import(self):
        """测试ArxivPDFParser导入"""
        if not ARXIV_AVAILABLE:
            pytest.skip("Arxiv module not available")

        from sage.middleware.operators.rag.arxiv import ArxivPDFParser
        assert ArxivPDFParser is not None


@pytest.mark.integration
class TestArxivIntegration:
    """Arxiv模块集成测试"""

    @pytest.mark.skipif(not ARXIV_AVAILABLE, reason="Arxiv module not available")
    def test_paper_basic_functionality(self):
        """测试Paper基本功能"""
        # 基本的Paper对象创建和属性访问
        paper = Paper(
            path="/test/path.pdf",
            title="Test Title",
            url="https://example.com",
            abs="Test abstract"
        )

        assert paper.title == "Test Title"
        assert paper.path == "/test/path.pdf"
        assert paper.abs == "Test abstract"
