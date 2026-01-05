from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sage.studio.tools.arxiv_search import ArxivSearchTool


@pytest.mark.asyncio
class TestArxivSearchTool:
    async def test_init(self):
        tool = ArxivSearchTool()
        assert tool.name == "arxiv_search"
        assert tool.args_schema is not None

    @patch("sage.studio.tools.arxiv_search.aiohttp.ClientSession")
    async def test_search_directly(self, mock_session_cls):
        # Mock aiohttp response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text.return_value = """
        <html>
            <li class="arxiv-result">
                <p class="title">Test Paper Title</p>
                <p class="authors"><a href="#">Author One</a>, <a href="#">Author Two</a></p>
                <span class="abstract-full">This is a test abstract.</span>
                <p class="list-title"><a href="https://arxiv.org/abs/1234.5678">arXiv:1234.5678</a></p>
            </li>
        </html>
        """
        mock_response.__aenter__.return_value = mock_response
        mock_response.__aexit__.return_value = None

        # session.get() returns a context manager, not a coroutine
        mock_session = MagicMock()
        mock_session.get.return_value = mock_response
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        mock_session_cls.return_value = mock_session

        tool = ArxivSearchTool()
        # Force fallback implementation by ensuring _impl is None
        tool._impl = None

        results = await tool.run(query="test", max_results=1)

        assert results["status"] == "success"
        data = results["result"]
        assert len(data) == 1
        assert data[0]["title"] == "Test Paper Title"
        assert data[0]["authors"] == ["Author One", "Author Two"]
        assert data[0]["abstract"] == "This is a test abstract."
        assert data[0]["link"] == "https://arxiv.org/abs/1234.5678"

    async def test_validation_error(self):
        tool = ArxivSearchTool()
        # Missing query
        result = await tool.run(max_results=5)
        assert result["status"] == "error"
        assert "参数验证失败" in result["error"]
