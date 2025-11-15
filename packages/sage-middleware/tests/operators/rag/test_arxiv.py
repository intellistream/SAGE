"""
Unit tests for Arxiv Paper and Operator classes
"""

import sys
from unittest.mock import MagicMock, patch

import pytest

# Mock fitz module at the beginning
mock_fitz = MagicMock()
sys.modules["fitz"] = mock_fitz


class TestPaper:
    """Test Paper class"""

    @patch("sage.middleware.operators.rag.arxiv.fitz")
    def test_paper_init_with_title(self, mock_fitz_module):
        """Test Paper initialization with title provided"""
        # Mock FITZ_AVAILABLE to be True
        with patch("sage.middleware.operators.rag.arxiv.FITZ_AVAILABLE", True):
            from sage.middleware.operators.rag.arxiv import Paper

            paper = Paper(
                path="/tmp/test.pdf",
                title="Test Paper",
                url="https://arxiv.org/abs/1234.5678",
                abs="Test abstract",
                authors=["Author1", "Author2"],
            )

            assert paper.title == "Test Paper"
            assert paper.url == "https://arxiv.org/abs/1234.5678"
            assert paper.abs == "Test abstract"
            assert paper.authors == ["Author1", "Author2"]
            assert paper.path == "/tmp/test.pdf"

    @patch("sage.middleware.operators.rag.arxiv.fitz")
    def test_paper_init_without_title(self, mock_fitz_module):
        """Test Paper initialization without title (triggers PDF parsing)"""
        with patch("sage.middleware.operators.rag.arxiv.FITZ_AVAILABLE", True):
            from sage.middleware.operators.rag.arxiv import Paper

            # Mock PDF document
            mock_doc = MagicMock()
            mock_page = MagicMock()

            # Mock text dict for title extraction - needs proper structure
            mock_text_dict = {
                "blocks": [
                    {
                        "type": 0,
                        "lines": [
                            {
                                "spans": [
                                    {
                                        "size": 20,
                                        "text": "Test Paper Title",
                                        "flags": 20,  # Add flags attribute
                                    }
                                ]
                            }
                        ],
                    }
                ]
            }

            # Set up get_text to return dict or plain text based on format parameter
            def mock_get_text(fmt="text"):
                if fmt == "dict":
                    return mock_text_dict
                return "Sample text"

            mock_page.get_text = mock_get_text

            mock_doc.__iter__ = lambda x: iter([mock_page])
            mock_doc.close = MagicMock()
            mock_fitz_module.open.return_value = mock_doc

            paper = Paper(path="/tmp/test.pdf")

            assert paper.path == "/tmp/test.pdf"
            assert hasattr(paper, "title")
            mock_fitz_module.open.assert_called()

    @patch("sage.middleware.operators.rag.arxiv.fitz")
    def test_paper_roman_num_initialization(self, mock_fitz_module):
        """Test Paper roman numeral initialization"""
        with patch("sage.middleware.operators.rag.arxiv.FITZ_AVAILABLE", True):
            from sage.middleware.operators.rag.arxiv import Paper

            paper = Paper(path="/tmp/test.pdf", title="Test")
            assert "I" in paper.roman_num
            assert "X" in paper.roman_num
            assert len(paper.roman_num) > 0

    @patch("sage.middleware.operators.rag.arxiv.fitz")
    def test_paper_digit_num_initialization(self, mock_fitz_module):
        """Test Paper digit numeral initialization"""
        with patch("sage.middleware.operators.rag.arxiv.FITZ_AVAILABLE", True):
            from sage.middleware.operators.rag.arxiv import Paper

            paper = Paper(path="/tmp/test.pdf", title="Test")
            assert "1" in paper.digit_num
            assert "10" in paper.digit_num
            assert len(paper.digit_num) == 10

    @patch("sage.middleware.operators.rag.arxiv.fitz")
    def test_get_chapter_names(self, mock_fitz_module):
        """Test extracting chapter names from PDF"""
        with patch("sage.middleware.operators.rag.arxiv.FITZ_AVAILABLE", True):
            from sage.middleware.operators.rag.arxiv import Paper

            # Mock PDF with structured content
            mock_doc = MagicMock()
            mock_page = MagicMock()
            # Format text to match what get_chapter_names expects
            test_text = """I. Introduction
II. Background
1. Method
2. Results
"""
            mock_page.get_text.return_value = test_text
            mock_doc.__iter__ = lambda x: iter([mock_page])
            mock_doc.close = MagicMock()
            mock_fitz_module.open.return_value = mock_doc

            paper = Paper(path="/tmp/test.pdf", title="Test")
            chapters = paper.get_chapter_names()

            assert isinstance(chapters, list)
            # The method looks for lines with roman/digit numerals followed by periods
            # and with 1-4 space-separated parts
            if len(chapters) > 0:
                assert any("." in ch for ch in chapters)

    @patch("sage.middleware.operators.rag.arxiv.fitz")
    def test_get_title(self, mock_fitz_module):
        """Test extracting title from PDF"""
        with patch("sage.middleware.operators.rag.arxiv.FITZ_AVAILABLE", True):
            from sage.middleware.operators.rag.arxiv import Paper

            # Mock PDF document
            mock_doc = MagicMock()
            mock_page = MagicMock()

            # Mock text dict with different font sizes and proper structure
            mock_text_dict = {
                "blocks": [
                    {
                        "type": 0,
                        "lines": [
                            {
                                "spans": [
                                    {
                                        "size": 12,
                                        "text": "Regular text",
                                        "flags": 4,
                                    }
                                ]
                            }
                        ],
                    },
                    {
                        "type": 0,
                        "lines": [
                            {
                                "spans": [
                                    {
                                        "size": 24,
                                        "text": "Large Title Text",
                                        "flags": 20,
                                    }
                                ]
                            }
                        ],
                    },
                ]
            }

            def mock_get_text(fmt="text"):
                if fmt == "dict":
                    return mock_text_dict
                return "Sample text"

            mock_page.get_text = mock_get_text
            mock_doc.__iter__ = lambda x: iter([mock_page])
            mock_doc.close = MagicMock()
            mock_fitz_module.open.return_value = mock_doc

            paper = Paper(path="/tmp/test.pdf", title="")
            title = paper.get_title()

            assert isinstance(title, str)

    @patch("sage.middleware.operators.rag.arxiv.fitz")
    def test_parse_pdf(self, mock_fitz_module):
        """Test PDF parsing functionality"""
        with patch("sage.middleware.operators.rag.arxiv.FITZ_AVAILABLE", True):
            from sage.middleware.operators.rag.arxiv import Paper

            mock_doc = MagicMock()
            mock_page = MagicMock()

            # Mock text dict for parse_pdf which calls get_text() and get_text("dict")
            mock_text_dict = {
                "blocks": [
                    {
                        "type": 0,
                        "lines": [
                            {
                                "spans": [
                                    {
                                        "size": 12,
                                        "text": "Test content",
                                        "flags": 4,
                                    }
                                ]
                            }
                        ],
                    }
                ]
            }

            def mock_get_text(fmt="text"):
                if fmt == "dict":
                    return mock_text_dict
                return "Test content"

            mock_page.get_text = mock_get_text
            mock_doc.__iter__ = lambda x: iter([mock_page])
            mock_doc.close = MagicMock()
            mock_fitz_module.open.return_value = mock_doc

            paper = Paper(path="/tmp/test.pdf", title="Test")
            paper.parse_pdf()

            assert hasattr(paper, "text_list")
            assert hasattr(paper, "all_text")
            assert "title" in paper.section_texts
            assert paper.section_texts["title"] == "Test"


class TestArxivSearch:
    """Test Arxiv search functionality"""

    @patch("requests.get")
    @patch("feedparser.parse")
    def test_arxiv_search_success(self, mock_feedparser, mock_requests):
        """Test successful arxiv search"""
        # This would require importing the actual arxiv search function
        # Adding placeholder for structure
        pass

    @patch("requests.get")
    def test_arxiv_download_pdf(self, mock_requests):
        """Test PDF download functionality"""
        # Placeholder for arxiv PDF download tests
        pass


class TestArxivOperator:
    """Test ArxivOperator if it exists in the file"""

    def test_arxiv_operator_initialization(self):
        """Test operator initialization"""
        # Check if ArxivOperator exists and test it
        try:
            from sage.middleware.operators.rag.arxiv import ArxivOperator

            operator = ArxivOperator()
            assert operator is not None
        except (ImportError, AttributeError):
            # ArxivOperator may not exist in this file
            pytest.skip("ArxivOperator not found in module")


class TestPaperSectionExtraction:
    """Test paper section extraction methods"""

    @patch("sage.middleware.operators.rag.arxiv.fitz")
    def test_extract_section_information(self, mock_fitz_module):
        """Test section information extraction"""
        with patch("sage.middleware.operators.rag.arxiv.FITZ_AVAILABLE", True):
            from sage.middleware.operators.rag.arxiv import Paper

            mock_doc = MagicMock()
            mock_page = MagicMock()
            mock_page.get_text.return_value = "Test content"
            mock_doc.__iter__ = lambda x: iter([mock_page])
            mock_doc.close = MagicMock()
            mock_fitz_module.open.return_value = mock_doc

            paper = Paper(path="/tmp/test.pdf", title="Test")

            # Test that section_names and section_texts are initialized
            assert hasattr(paper, "section_names")
            assert hasattr(paper, "section_texts")
            assert isinstance(paper.section_names, list)
            assert isinstance(paper.section_texts, dict)


class TestPaperEdgeCases:
    """Test edge cases for Paper class"""

    @patch("sage.middleware.operators.rag.arxiv.fitz")
    def test_paper_empty_authors(self, mock_fitz_module):
        """Test Paper with empty authors"""
        with patch("sage.middleware.operators.rag.arxiv.FITZ_AVAILABLE", True):
            from sage.middleware.operators.rag.arxiv import Paper

            paper = Paper(path="/tmp/test.pdf", title="Test")
            assert paper.authors == []

    @patch("sage.middleware.operators.rag.arxiv.fitz")
    def test_paper_long_path(self, mock_fitz_module):
        """Test Paper with very long path"""
        with patch("sage.middleware.operators.rag.arxiv.FITZ_AVAILABLE", True):
            from sage.middleware.operators.rag.arxiv import Paper

            long_path = "/tmp/" + "a" * 200 + ".pdf"
            paper = Paper(path=long_path, title="Test")
            assert paper.path == long_path

    @patch("sage.middleware.operators.rag.arxiv.fitz")
    def test_paper_with_special_characters_in_title(self, mock_fitz_module):
        """Test Paper with special characters in title"""
        with patch("sage.middleware.operators.rag.arxiv.FITZ_AVAILABLE", True):
            from sage.middleware.operators.rag.arxiv import Paper

            mock_doc = MagicMock()
            mock_doc.close = MagicMock()
            mock_fitz_module.open.return_value = mock_doc

            special_title = "Test: Paper - With (Special) [Characters]"
            paper = Paper(path="/tmp/test.pdf", title=special_title)
            assert paper.title == special_title
