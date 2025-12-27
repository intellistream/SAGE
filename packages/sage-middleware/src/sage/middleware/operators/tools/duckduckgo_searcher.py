"""
DuckDuckGo web search tool (no API key required).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field

from sage.libs.foundation.tools.tool import BaseTool

logger = logging.getLogger(__name__)


class DuckDuckGoSearchInput(BaseModel):
    query: str = Field(..., description="Search query text")
    max_results: int = Field(5, description="Number of results to return", ge=1, le=20)


class DuckDuckGoSearcher(BaseTool):
    """Simple HTML-based DuckDuckGo searcher.

    Uses the public HTML endpoint (no API key) and extracts title/link/snippet.
    Intended for lightweight research fallback when no commercial search API is configured.
    """

    def __init__(self):
        super().__init__(
            tool_name="duckduckgo_search",
            tool_description="Search the web via DuckDuckGo (HTML endpoint). Returns title, link, and snippet.",
            input_types={"query": "str - search query", "max_results": "int - number of results"},
            output_type="list",
            demo_commands=[
                "search for latest vector database papers",
                "find recent ML system posts",
            ],
            require_llm_engine=False,
        )

    async def execute(self, query: str, max_results: int = 5) -> list[dict[str, Any]]:
        url = "https://duckduckgo.com/html"
        params = {"q": query, "kl": "us-en"}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=params, timeout=15) as resp:
                    if resp.status != 200:
                        logger.warning("DuckDuckGo returned status %s", resp.status)
                        return []
                    html = await resp.text()
        except Exception as exc:  # noqa: BLE001
            logger.error("DuckDuckGo search failed: %s", exc)
            return []

        soup = BeautifulSoup(html, "html.parser")
        results: list[dict[str, Any]] = []

        for result in soup.select("div.result"):
            if len(results) >= max_results:
                break

            link_tag = result.select_one("a.result__a")
            snippet_tag = result.select_one("a.result__snippet") or result.select_one(
                "div.result__snippet"
            )

            title = link_tag.get_text(strip=True) if link_tag else ""
            href = link_tag.get("href") if link_tag else ""
            snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""

            if not href:
                continue

            results.append(
                {
                    "title": title,
                    "link": href,
                    "content": snippet,
                    "source": "duckduckgo",
                }
            )

        return results

    def call(self, arguments: dict) -> Any:
        """Sync wrapper used by MCP/AgentRuntime."""
        query = arguments.get("query")
        if not query:
            return []

        max_results = arguments.get("max_results", 5)

        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                return asyncio.run(self.execute(query, max_results=max_results))
        except RuntimeError:
            return asyncio.run(self.execute(query, max_results=max_results))

        return asyncio.run(self.execute(query, max_results=max_results))
