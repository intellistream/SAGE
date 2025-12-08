from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sage.middleware.operators.agentic.refined_searcher import RefinedSearcherOperator


class TestRefinedSearcherOperator:
    @pytest.fixture
    def mock_tool(self):
        tool = MagicMock()
        tool.name = "mock_search"
        tool.run = AsyncMock(return_value=[{"source": "mock", "content": "result"}])
        return tool

    def test_initialization(self, mock_tool):
        operator = RefinedSearcherOperator(tools=[mock_tool])
        assert operator.name == "search_internet"
        assert operator.bot is not None

    def test_call_missing_query(self, mock_tool):
        operator = RefinedSearcherOperator(tools=[mock_tool])

        # Call with empty arguments
        result = operator.call({})

        # Expect empty results instead of error, as per implementation
        assert result == {"results": []}

    @patch("asyncio.run")
    def test_call_valid_query(self, mock_asyncio_run, mock_tool):
        operator = RefinedSearcherOperator(tools=[mock_tool])

        # Mock execute to return a result
        mock_asyncio_run.return_value = {"results": ["some result"]}

        result = operator.call({"query": "test"})

        assert result == {"results": ["some result"]}
        # Verify execute was called (indirectly via asyncio.run)
        mock_asyncio_run.assert_called_once()
