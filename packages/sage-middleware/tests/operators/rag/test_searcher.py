"""
Unit tests for sage.middleware.operators.rag.searcher module.
Tests BochaWebSearch operator.
"""

from unittest.mock import Mock, patch

import pytest

try:
    from sage.middleware.operators.rag.searcher import BochaWebSearch

    SEARCHER_AVAILABLE = True
except ImportError as e:
    SEARCHER_AVAILABLE = False
    pytestmark = pytest.mark.skip(f"Searcher module not available: {e}")


@pytest.mark.unit
class TestBochaWebSearch:
    """Test BochaWebSearch operator."""

    def test_initialization_with_api_key(self):
        """Test BochaWebSearch initialization with valid config."""
        if not SEARCHER_AVAILABLE:
            pytest.skip("Searcher not available")

        config = {
            "api_key": "test_key_12345",  # pragma: allowlist secret
            "count": 5,
            "page": 1,
            "summary": True,
        }

        searcher = BochaWebSearch(config)
        assert searcher.api_key == "test_key_12345"  # pragma: allowlist secret
        assert searcher.count == 5
        assert searcher.page == 1
        assert searcher.summary is True
        assert searcher.url == "https://api.bochaai.com/v1/web-search"

    def test_initialization_without_api_key(self):
        """Test BochaWebSearch initialization fails without api_key."""
        if not SEARCHER_AVAILABLE:
            pytest.skip("Searcher not available")

        config = {"count": 10}

        with pytest.raises(ValueError, match="requires an 'api_key'"):
            BochaWebSearch(config)

    def test_initialization_with_defaults(self):
        """Test BochaWebSearch uses default values."""
        if not SEARCHER_AVAILABLE:
            pytest.skip("Searcher not available")

        config = {"api_key": "test_key"}  # pragma: allowlist secret

        searcher = BochaWebSearch(config)
        assert searcher.count == 10  # Default
        assert searcher.page == 1  # Default
        assert searcher.summary is True  # Default

    @patch("sage.middleware.operators.rag.searcher.requests.post")
    def test_execute_successful_search(self, mock_post):
        """Test execute with successful API response."""
        if not SEARCHER_AVAILABLE:
            pytest.skip("Searcher not available")

        # Mock successful response
        mock_response = Mock()
        mock_response.json.return_value = {
            "results": [
                {"title": "Result 1", "url": "http://example.com/1"},
                {"title": "Result 2", "url": "http://example.com/2"},
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        config = {"api_key": "test_key"}  # pragma: allowlist secret
        searcher = BochaWebSearch(config)

        result = searcher.execute("test query")

        assert "results" in result
        assert len(result["results"]) == 2
        mock_post.assert_called_once()

    @patch("sage.middleware.operators.rag.searcher.requests.post")
    def test_execute_with_custom_params(self, mock_post):
        """Test execute sends correct payload with custom parameters."""
        if not SEARCHER_AVAILABLE:
            pytest.skip("Searcher not available")

        mock_response = Mock()
        mock_response.json.return_value = {"results": []}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        config = {
            "api_key": "custom_key",  # pragma: allowlist secret
            "count": 20,
            "page": 2,
            "summary": False,
        }
        searcher = BochaWebSearch(config)

        searcher.execute("custom query")

        # Verify the payload
        call_args = mock_post.call_args
        payload = call_args[1]["json"]
        assert payload["query"] == "custom query"
        assert payload["count"] == 20
        assert payload["page"] == 2
        assert payload["summary"] is False

    @patch("sage.middleware.operators.rag.searcher.requests.post")
    def test_execute_api_error(self, mock_post):
        """Test execute handles API errors gracefully."""
        if not SEARCHER_AVAILABLE:
            pytest.skip("Searcher not available")

        # Mock API error
        mock_post.side_effect = Exception("API connection failed")

        config = {"api_key": "test_key"}  # pragma: allowlist secret
        searcher = BochaWebSearch(config)

        result = searcher.execute("test query")

        # Should return empty dict on error
        assert result == {}

    @patch("sage.middleware.operators.rag.searcher.requests.post")
    def test_execute_http_error(self, mock_post):
        """Test execute handles HTTP errors."""
        if not SEARCHER_AVAILABLE:
            pytest.skip("Searcher not available")

        # Mock HTTP error
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = Exception("404 Not Found")
        mock_post.return_value = mock_response

        config = {"api_key": "test_key"}  # pragma: allowlist secret
        searcher = BochaWebSearch(config)

        result = searcher.execute("test query")

        assert result == {}

    @patch("sage.middleware.operators.rag.searcher.requests.post")
    def test_execute_invalid_json_response(self, mock_post):
        """Test execute handles invalid JSON response."""
        if not SEARCHER_AVAILABLE:
            pytest.skip("Searcher not available")

        # Mock invalid JSON
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_post.return_value = mock_response

        config = {"api_key": "test_key"}  # pragma: allowlist secret
        searcher = BochaWebSearch(config)

        result = searcher.execute("test query")

        assert result == {}

    @patch("sage.middleware.operators.rag.searcher.requests.post")
    def test_execute_with_empty_query(self, mock_post):
        """Test execute with empty query string."""
        if not SEARCHER_AVAILABLE:
            pytest.skip("Searcher not available")

        mock_response = Mock()
        mock_response.json.return_value = {"results": []}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        config = {"api_key": "test_key"}  # pragma: allowlist secret
        searcher = BochaWebSearch(config)

        result = searcher.execute("")

        assert "results" in result
        # Check empty query was sent
        call_args = mock_post.call_args
        assert call_args[1]["json"]["query"] == ""

    @patch("sage.middleware.operators.rag.searcher.requests.post")
    def test_authorization_header(self, mock_post):
        """Test that authorization header is correctly set."""
        if not SEARCHER_AVAILABLE:
            pytest.skip("Searcher not available")

        mock_response = Mock()
        mock_response.json.return_value = {}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        config = {"api_key": "secret_api_key"}  # pragma: allowlist secret
        searcher = BochaWebSearch(config)

        searcher.execute("test")

        # Verify headers
        call_args = mock_post.call_args
        headers = call_args[1]["headers"]
        assert headers["Authorization"] == "secret_api_key"  # pragma: allowlist secret
        assert headers["Content-Type"] == "application/json"
