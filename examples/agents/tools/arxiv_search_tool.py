# examples/agents/tools/arxiv_mcp_tool.py
from __future__ import annotations

import logging
import re
import time
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
        # 设置更像真实浏览器的请求头
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Cache-Control": "max-age=0",
            }
        )

    # === MCP 入口 ===
    def call(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        query: str = (arguments.get("query") or "").strip()
        if not query:
            raise ValueError("`query` is required and must be a non-empty string.")

        # 清理查询字符串，移除可能导致问题的字符
        query = self._clean_query(query)

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
                    "title": f"Survey of LLM Agents ({i + 1})",
                    "authors": "Alice, Bob",
                    "link": f"https://arxiv.org/abs/2509.{1234 + i}",
                    "abstract": "(mock) An overview of LLM-based agents, planning, and tool use.",
                }
                for i in range(k)
            ]
            return {"output": demo, "meta": {"query": query, "offline_mock": True}}

    def _clean_query(self, query: str) -> str:
        """清理查询字符串，避免可能导致服务器错误的字符"""
        import re

        # 替换可能导致问题的词汇组合
        problematic_patterns = {
            r"\bvs\b": "versus",
            r"\bcompare?\b": "analysis",
            r"\bcomparison\b": "analysis",
            r"\bdifferent\b": "analysis",
            r"\bdifference\b": "analysis",
        }

        for pattern, replacement in problematic_patterns.items():
            query = re.sub(pattern, replacement, query, flags=re.IGNORECASE)

        # 移除多余的空格和特殊字符
        query = re.sub(r"\s+", " ", query)  # 多个空格变成单个空格
        query = re.sub(
            r"[^\w\s\-\+\.]", " ", query
        )  # 只保留字母数字、空格、连字符、加号、点号
        query = query.strip()

        # 限制查询长度
        if len(query) > 100:
            query = query[:100]

        return query

    # === 具体抓取 ===
    def _search_arxiv(
        self, query: str, size: int, max_results: int, with_abstract: bool
    ) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        start = 0
        retry_count = 0
        max_retries = 3
        base_delay = 1.5  # 基础延迟时间

        while len(results) < max_results:
            # 在每次请求前添加延迟，避免过于频繁的请求
            if start > 0 or retry_count > 0:
                time.sleep(base_delay)

            params = {
                "searchtype": "all",
                "query": query,
                "abstracts": "show",
                "order": "",
                "size": str(size),
                "start": str(start),
            }

            try:
                # 如果是重试，增加额外延迟
                if retry_count > 0:
                    time.sleep(2**retry_count)  # 指数退避：2s, 4s, 8s

                resp = self.session.get(self.base_url, params=params, timeout=20)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.content, "html.parser")
                retry_count = 0  # 重置重试计数

            except requests.exceptions.HTTPError as e:
                if (
                    e.response.status_code in [500, 503, 429]
                    and retry_count < max_retries
                ):
                    logging.warning(
                        f"[arxiv_search] HTTP {e.response.status_code} error, retrying ({retry_count + 1}/{max_retries}) after delay..."
                    )
                    retry_count += 1
                    continue
                else:
                    raise  # 重试次数用完或其他错误

            except Exception as e:
                if retry_count < max_retries:
                    logging.warning(
                        f"[arxiv_search] Request failed, retrying ({retry_count + 1}/{max_retries}): {e}"
                    )
                    retry_count += 1
                    continue
                else:
                    raise
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
