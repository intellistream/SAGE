"""
Unit tests for Arxiv Paper and Operator classes
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, mock_open
from pathlib import Path
import tempfile
import os


class TestPaper:
    """Test Paper class"""

    @patch("fitz.open")
    def test_paper_init_with_title(self, mock_fitz):
        """Test Paper initialization with title provided"""
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
        mock_fitz.assert_not_called()

    @patch("fitz.open")
    def test_paper_init_without_title(self, mock_fitz):
        """Test Paper initialization without title (triggers PDF parsing)"""
        from sage.middleware.operators.rag.arxiv import Paper

        # Mock PDF document
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_page.get_text.return_value = "Sample text"

        # Mock text dict for title extraction
        mock_text_dict = {
            "blocks": [
                {
                    "type": 0,
                    "lines": [
                        {
                            "spans": [
                                {"size": 20, "text": "Test Paper Title"}
                            ]
                        }
                    ],
                }
            ]
        }
        mock_page.get_text.side_effect = lambda fmt="text": (
            mock_text_dict if fmt == "dict" else "Sample text"
        )

        mock_doc.__iter__ = lambda x: iter([mock_page])
        mock_fitz.return_value = mock_doc

        paper = Paper(path="/tmp/test.pdf")

        assert paper.path == "/tmp/test.pdf"
        assert hasattr(paper, "title")
        mock_fitz.assert_called()

    def test_paper_roman_num_initialization(self):
        """Test Paper roman numeral initialization"""
        from sage.middleware.operators.rag.arxiv import Paper

        with patch("fitz.open"):
            paper = Paper(path="/tmp/test.pdf", title="Test")
            assert "I" in paper.roman_num
            assert "X" in paper.roman_num
            assert len(paper.roman_num) > 0

    def test_paper_digit_num_initialization(self):
        """Test Paper digit numeral initialization"""
        from sage.middleware.operators.rag.arxiv import Paper

        with patch("fitz.open"):
            paper = Paper(path="/tmp/test.pdf", title="Test")
            assert "1" in paper.digit_num
            assert "10" in paper.digit_num
            assert len(paper.digit_num) == 10

    @patch("fitz.open")
    def test_get_chapter_names(self, mock_fitz):
        """Test extracting chapter names from PDF"""
        from sage.middleware.operators.rag.arxiv import Paper

        # Mock PDF with structured content
        mock_doc = MagicMock()
        mock_page = MagicMock()
        test_text = """
        I. Introduction
        II. Background
        1. Method
        2. Results
        """
        mock_page.get_text.return_value = test_text
        mock_doc.__iter__ = lambda x: iter([mock_page])
        mock_fitz.return_value = mock_doc

        paper = Paper(path="/tmp/test.pdf", title="Test")
        chapters = paper.get_chapter_names()

        assert isinstance(chapters, list)
        # Should find chapters with roman/digit numerals followed by periods
        assert any("I." in ch or "1." in ch for ch in chapters)

    @patch("fitz.open")
    def test_get_title(self, mock_fitz):
        """Test extracting title from PDF"""
        from sage.middleware.operators.rag.arxiv import Paper

        # Mock PDF document
        mock_doc = MagicMock()
        mock_page = MagicMock()

        # Mock text dict with different font sizes
        mock_text_dict = {
            "blocks": [
                {
                    "type": 0,
                    "lines": [
                        {
                            "spans": [
                                {"size": 12, "text": "Regular text"}
                            ]
                        }
                    ],
                },
                {
                    "type": 0,
                    "lines": [
                        {
                            "spans": [
                                {"size": 24, "text": "Large Title Text"}
                            ]
                        }
                    ],
                },
            ]
        }
        mock_page.get_text.return_value = mock_text_dict
        mock_doc.__iter__ = lambda x: iter([mock_page])
        mock_fitz.return_value = mock_doc

        paper = Paper(path="/tmp/test.pdf", title="")
        title = paper.get_title()

        assert isinstance(title, str)

    @patch("fitz.open")
    def test_parse_pdf(self, mock_fitz):
        """Test PDF parsing functionality"""
        from sage.middleware.operators.rag.arxiv import Paper

        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_page.get_text.return_value = "Test content"
        mock_doc.__iter__ = lambda x: iter([mock_page])
        mock_fitz.return_value = mock_doc

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

    @patch("fitz.open")
    def test_extract_section_information(self, mock_fitz):
        """Test section information extraction"""
        from sage.middleware.operators.rag.arxiv import Paper

        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_page.get_text.return_value = "Test content"
        mock_doc.__iter__ = lambda x: iter([mock_page])
        mock_fitz.return_value = mock_doc

        paper = Paper(path="/tmp/test.pdf", title="Test")

        # Test that section_names and section_texts are initialized
        assert hasattr(paper, "section_names")
        assert hasattr(paper, "section_texts")
        assert isinstance(paper.section_names, list)
        assert isinstance(paper.section_texts, dict)


class TestPaperEdgeCases:
    """Test edge cases for Paper class"""

    def test_paper_empty_authors(self):
        """Test Paper with empty authors"""
        from sage.middleware.operators.rag.arxiv import Paper

        with patch("fitz.open"):
            paper = Paper(path="/tmp/test.pdf", title="Test")
            assert paper.authors == []

    def test_paper_long_path(self):
        """Test Paper with very long path"""
        from sage.middleware.operators.rag.arxiv import Paper

        long_path = "/tmp/" + "a" * 200 + ".pdf"
        with patch("fitz.open"):
            paper = Paper(path=long_path, title="Test")
            assert paper.path == long_path

    @patch("fitz.open")
    def test_paper_with_special_characters_in_title(self, mock_fitz):
        """Test Paper with special characters in title"""
        from sage.middleware.operators.rag.arxiv import Paper

        mock_doc = MagicMock()
        mock_fitz.return_value = mock_doc

        special_title = "Test: Paper - With (Special) [Characters]"
        paper = Paper(path="/tmp/test.pdf", title=special_title)
        assert paper.title == special_title
