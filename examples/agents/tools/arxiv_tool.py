# examples/agents/tools/arxiv_mcp_tool.py
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List

import requests
from bs4 import BeautifulSoup
from bs4.element import Tag


class ArxivSearchTool:
    """
    MCP 工具：arxiv_search
    - 接口三要素：
        name = "arxiv_search"
        description = "Search arXiv papers; return a list of {title, authors, link, abstract}."
        input_schema = {...}
    - 入口：
        call({"query": "...", "size": 25, "max_results": 2}) -> {"output": [...], "meta": {...}}
    """

    name = "arxiv_search"
    description = (
        "Search arXiv papers; return a list of {title, authors, link, abstract}."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query for arXiv."},
            "size": {
                "type": "integer",
                "enum": [25, 50, 100, 200],
                "default": 25,
                "description": "Results per page on arXiv.",
            },
            "max_results": {
                "type": "integer",
                "minimum": 1,
                "maximum": 100,
                "default": 10,
                "description": "Maximum number of papers to return (<=100).",
            },
            "with_abstract": {
                "type": "boolean",
                "default": True,
                "description": "Whether to include abstract in results.",
            },
        },
        "required": ["query"],
        "additionalProperties": False,
    }

    def __init__(self):
        self.base_url = "https://arxiv.org/search/"
        self.valid_sizes = [25, 50, 100, 200]
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "SAGE-Agent/1.0 (+https://example.com; contact: ops@example.com)"
            }
        )

    # === MCP 入口 ===
    def call(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        query: str = (arguments.get("query") or "").strip()
        if not query:
            raise ValueError("`query` is required and must be a non-empty string.")

        size: int = int(arguments.get("size", 25) or 25)
        if size not in self.valid_sizes:
            size = min(self.valid_sizes, key=lambda x: abs(x - size))

        max_results: int = int(arguments.get("max_results", 10) or 10)
        max_results = max(1, min(max_results, 100))

        with_abs: bool = bool(arguments.get("with_abstract", True))

        try:
            items = self._search_arxiv(
                query=query, size=size, max_results=max_results, with_abstract=with_abs
            )
            return {
                "output": items,
                "meta": {"query": query, "size": size, "max_results": max_results},
            }
        except Exception as e:
            logging.error(f"[arxiv_search] online search failed: {e}")
            # 离线兜底：返回 mock，保证示例可跑
            k = max_results
            demo = [
                {
                    "title": f"Survey of LLM Agents ({i+1})",
                    "authors": "Alice, Bob",
                    "link": f"https://arxiv.org/abs/2509.{1234+i}",
                    "abstract": "(mock) An overview of LLM-based agents, planning, and tool use.",
                }
                for i in range(k)
            ]
            return {"output": demo, "meta": {"query": query, "offline_mock": True}}

    # === 具体抓取 ===
    def _search_arxiv(
        self, query: str, size: int, max_results: int, with_abstract: bool
    ) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        start = 0
        while len(results) < max_results:
            params = {
                "searchtype": "all",
                "query": query,
                "abstracts": "show",
                "order": "",
                "size": str(size),
                "start": str(start),
            }
            resp = self.session.get(self.base_url, params=params, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.content, "html.parser")
            papers = soup.find_all("li", class_="arxiv-result")  # type: ignore
            if not papers:
                break

            for paper in papers:
                if len(results) >= max_results:
                    break

                title_elem = paper.find("p", class_="title")  # type: ignore
                title = title_elem.text.strip() if title_elem else "No title"

                authors_elem = paper.find("p", class_="authors")  # type: ignore
                authors = authors_elem.text.strip() if authors_elem else "No authors"
                authors = re.sub(r"^Authors:\s*", "", authors)
                authors = re.sub(r"\s+", " ", authors).strip()

                abstract = ""
                if with_abstract:
                    abstract_elem = paper.find("span", class_="abstract-full")  # type: ignore
                    abstract = (
                        (abstract_elem.text.strip() if abstract_elem else "")
                        .replace("△ Less", "")
                        .strip()
                    )

                link_elem = paper.find("p", class_="list-title")  # type: ignore
                link_tag = link_elem.find("a") if isinstance(link_elem, Tag) else None  # type: ignore
                link = (
                    link_tag["href"]
                    if isinstance(link_tag, Tag) and link_tag.has_attr("href")
                    else ""
                )

                results.append(
                    {
                        "title": title,
                        "authors": authors,
                        "abstract": abstract,
                        "link": link or "https://arxiv.org",
                    }
                )

            start += size

        return results[:max_results]
