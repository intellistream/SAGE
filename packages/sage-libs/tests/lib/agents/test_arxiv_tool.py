"""
Core unit tests for the ArxivSearchTool.

This covers essential functionality and integration with SAGE components.
For usage examples, see examples/agents/tools/demo_arxiv_search.py
"""

from unittest.mock import patch

import pytest

# Import the tool from examples since it's an example tool
try:
    from examples.agents.tools.arxiv_search_tool import ArxivSearchTool

    ARXIV_TOOL_AVAILABLE = True
except ImportError:
    ARXIV_TOOL_AVAILABLE = False
    pytestmark = pytest.mark.skip("ArxivSearchTool not available")


@pytest.mark.unit
class TestArxivSearchToolCore:
    """Core functionality tests for ArxivSearchTool."""

    def setup_method(self):
        """Set up test fixtures."""
        if not ARXIV_TOOL_AVAILABLE:
            pytest.skip("ArxivSearchTool not available")
        self.tool = ArxivSearchTool()

    def test_tool_initialization(self):
        """Test that ArxivSearchTool initializes correctly."""
        if not ARXIV_TOOL_AVAILABLE:
            pytest.skip("ArxivSearchTool not available")

        assert self.tool.name == "arxiv_search"
        assert "Search arXiv papers" in self.tool.description
        assert self.tool.base_url == "https://arxiv.org/search/"
        assert self.tool.valid_sizes == [25, 50, 100, 200]
        assert "User-Agent" in self.tool.session.headers

    def test_input_schema_validation(self):
        """Test that input schema is properly defined."""
        if not ARXIV_TOOL_AVAILABLE:
            pytest.skip("ArxivSearchTool not available")

        schema = self.tool.input_schema

        # Required fields
        assert "query" in schema["required"]

        # Properties validation
        props = schema["properties"]
        assert props["query"]["type"] == "string"
        assert props["size"]["type"] == "integer"
        assert props["max_results"]["minimum"] == 1
        assert props["max_results"]["maximum"] == 100
        assert props["with_abstract"]["type"] == "boolean"

    def test_call_with_missing_query(self):
        """Test that call() raises ValueError when query is missing."""
        if not ARXIV_TOOL_AVAILABLE:
            pytest.skip("ArxivSearchTool not available")

        with pytest.raises(ValueError, match="`query` is required"):
            self.tool.call({})

        with pytest.raises(ValueError, match="`query` is required"):
            self.tool.call({"query": ""})

        with pytest.raises(ValueError, match="`query` is required"):
            self.tool.call({"query": "   "})

    def test_parameter_normalization(self):
        """Test that parameters are normalized correctly."""
        if not ARXIV_TOOL_AVAILABLE:
            pytest.skip("ArxivSearchTool not available")

        with patch.object(self.tool, "_search_arxiv") as mock_search:
            mock_search.return_value = []

            # Test size normalization (invalid size -> closest valid)
            self.tool.call({"query": "test", "size": 30})  # Should use 25
            mock_search.assert_called_with(
                query="test", size=25, max_results=10, with_abstract=True
            )

            # Test max_results bounds
            self.tool.call({"query": "test", "max_results": 150})  # Should cap at 100
            mock_search.assert_called_with(
                query="test", size=25, max_results=100, with_abstract=True
            )

    def test_network_error_fallback(self):
        """Test that network errors trigger offline fallback."""
        if not ARXIV_TOOL_AVAILABLE:
            pytest.skip("ArxivSearchTool not available")

        import requests

        with patch("requests.Session.get") as mock_get:
            mock_get.side_effect = requests.RequestException("Network error")

            with patch("logging.error") as mock_log:
                result = self.tool.call({"query": "test", "max_results": 3})

                # Should return mock data
                assert result["output"]
                assert len(result["output"]) == 3
                assert result["meta"]["offline_mock"] is True

                # Should log the error
                mock_log.assert_called_once()


@pytest.mark.unit
class TestArxivSearchToolIntegration:
    """Integration tests for ArxivSearchTool with SAGE components."""

    def test_tool_integration_with_registry(self):
        """Test that the tool can be registered and called through MCPRegistry."""
        if not ARXIV_TOOL_AVAILABLE:
            pytest.skip("ArxivSearchTool not available")

        from sage.libs.agents.action.mcp_registry import MCPRegistry

        registry = MCPRegistry()
        tool = ArxivSearchTool()
        registry.register(tool)

        # Mock the actual search to avoid network calls
        with patch.object(tool, "_search_arxiv") as mock_search:
            mock_search.return_value = [
                {"title": "Test", "authors": "Test", "link": "test", "abstract": "test"}
            ]

            result = registry.call("arxiv_search", {"query": "machine learning"})
            assert result["output"]
            assert result["meta"]["query"] == "machine learning"

    def test_tool_schema_compatibility(self):
        """Test that the tool schema is compatible with MCP standards."""
        if not ARXIV_TOOL_AVAILABLE:
            pytest.skip("ArxivSearchTool not available")

        tool = ArxivSearchTool()

        # Verify required MCP tool attributes
        assert hasattr(tool, "name")
        assert hasattr(tool, "description")
        assert hasattr(tool, "input_schema")
        assert hasattr(tool, "call")

        # Verify schema structure
        schema = tool.input_schema
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "required" in schema
