"""
SAGE Operators for Article Monitoring System

Implements source, map, filter, and sink operators for the article monitoring pipeline.
"""

from __future__ import annotations

import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Any

from sage.common.core import BatchFunction, MapFunction, SinkFunction


@dataclass
class Article:
    """Article metadata from arXiv."""

    id: str
    title: str
    authors: list[str]
    abstract: str
    published: str
    categories: list[str]
    url: str
    keyword_score: float = 0.0
    semantic_score: float = 0.0
    total_score: float = 0.0


class ArxivSource(BatchFunction):
    """
    BatchFunction source that fetches articles from arXiv API.

    Emits one article at a time as a data packet.
    """

    def __init__(
        self,
        category: str = "cs.AI",
        max_results: int = 10,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.category = category
        self.max_results = max_results
        self.articles: list[dict[str, Any]] = []
        self.index = 0
        self.fetched = False

    def _fetch_articles(self) -> list[dict[str, Any]]:
        """Fetch articles from arXiv API."""
        query = f"cat:{self.category}"
        params = {
            "search_query": query,
            "start": 0,
            "max_results": self.max_results,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }

        url = f"http://export.arxiv.org/api/query?{urllib.parse.urlencode(params)}"

        try:
            with urllib.request.urlopen(url, timeout=10) as response:
                data = response.read().decode("utf-8")
            return self._parse_arxiv_response(data)
        except Exception as e:
            self.logger.warning(f"Error fetching from arXiv: {e}, using mock data")
            return self._get_mock_articles()

    def _parse_arxiv_response(self, xml_data: str) -> list[dict[str, Any]]:
        """Parse arXiv API XML response."""
        articles = []
        root = ET.fromstring(xml_data)
        ns = {"atom": "http://www.w3.org/2005/Atom"}

        for entry in root.findall("atom:entry", ns):
            try:
                article_id = entry.find("atom:id", ns).text.split("/")[-1]
                title = entry.find("atom:title", ns).text.strip()
                abstract = entry.find("atom:summary", ns).text.strip()
                published = entry.find("atom:published", ns).text
                url = entry.find("atom:id", ns).text

                authors = [
                    author.find("atom:name", ns).text for author in entry.findall("atom:author", ns)
                ]

                categories = [cat.attrib["term"] for cat in entry.findall("atom:category", ns)]

                articles.append(
                    {
                        "id": article_id,
                        "title": title,
                        "authors": authors,
                        "abstract": abstract,
                        "published": published,
                        "categories": categories,
                        "url": url,
                    }
                )
            except Exception as e:
                self.logger.warning(f"Error parsing entry: {e}")
                continue

        return articles

    def _get_mock_articles(self) -> list[dict[str, Any]]:
        """Generate mock articles for testing/offline mode."""
        return [
            {
                "id": "2401.00001",
                "title": "Deep Learning for Time Series Forecasting in Stream Processing",
                "authors": ["John Doe", "Jane Smith"],
                "abstract": "We propose a novel deep learning approach for time series forecasting in distributed stream processing systems...",
                "published": "2024-01-01T00:00:00Z",
                "categories": ["cs.LG", "cs.AI"],
                "url": "http://arxiv.org/abs/2401.00001",
            },
            {
                "id": "2401.00002",
                "title": "Semantic Analysis in Natural Language Processing",
                "authors": ["Alice Johnson"],
                "abstract": "This paper explores advanced semantic analysis techniques for NLP tasks using transformer models...",
                "published": "2024-01-01T01:00:00Z",
                "categories": ["cs.CL", "cs.AI"],
                "url": "http://arxiv.org/abs/2401.00002",
            },
            {
                "id": "2401.00003",
                "title": "Distributed Systems for Real-time Stream Processing",
                "authors": ["Bob Chen", "Carol White"],
                "abstract": "We present a distributed architecture for processing data streams in real-time with low latency...",
                "published": "2024-01-01T02:00:00Z",
                "categories": ["cs.DC", "cs.DB"],
                "url": "http://arxiv.org/abs/2401.00003",
            },
            {
                "id": "2401.00004",
                "title": "Machine Learning Pipeline Optimization",
                "authors": ["David Lee"],
                "abstract": "Optimizing machine learning pipelines for better performance and resource utilization in production systems...",
                "published": "2024-01-01T03:00:00Z",
                "categories": ["cs.LG", "cs.AI"],
                "url": "http://arxiv.org/abs/2401.00004",
            },
            {
                "id": "2401.00005",
                "title": "Graph Neural Networks for Social Network Analysis",
                "authors": ["Emma Wilson", "Frank Zhang"],
                "abstract": "Applying graph neural networks to analyze complex social network structures and dynamics...",
                "published": "2024-01-01T04:00:00Z",
                "categories": ["cs.SI", "cs.LG"],
                "url": "http://arxiv.org/abs/2401.00005",
            },
        ]

    def execute(self) -> dict[str, Any] | None:
        """Execute batch function to emit one article at a time."""
        # Fetch articles on first execution
        if not self.fetched:
            self.logger.info(f"Fetching articles from arXiv (category: {self.category})...")
            self.articles = self._fetch_articles()
            self.fetched = True
            self.logger.info(f"Fetched {len(self.articles)} articles")

        # Emit one article per call
        if self.index < len(self.articles):
            article = self.articles[self.index]
            self.index += 1
            return article

        # All articles emitted
        return None


class KeywordFilter(MapFunction):
    """
    MapFunction that filters articles based on keyword matching.

    Returns the article with keyword_score if it passes, otherwise returns None.
    """

    def __init__(self, keywords: list[str], min_score: float = 1.0, **kwargs) -> None:
        super().__init__(**kwargs)
        self.keywords = [kw.lower() for kw in keywords]
        self.min_score = min_score

    def execute(self, data: dict[str, Any]) -> dict[str, Any] | None:
        """Filter article based on keyword matching."""
        text = (data.get("title", "") + " " + data.get("abstract", "")).lower()
        score = sum(1 for kw in self.keywords if kw in text)

        if score >= self.min_score:
            data["keyword_score"] = float(score)
            return data
        return None


class SemanticFilter(MapFunction):
    """
    MapFunction that filters articles based on semantic similarity.

    Uses simplified word overlap as a proxy for semantic similarity.
    """

    def __init__(self, interest_topics: list[str], min_similarity: float = 0.05, **kwargs) -> None:
        super().__init__(**kwargs)
        self.interest_topics = [topic.lower() for topic in interest_topics]
        self.min_similarity = min_similarity

    def execute(self, data: dict[str, Any]) -> dict[str, Any] | None:
        """Filter article based on semantic similarity."""
        text = (data.get("title", "") + " " + data.get("abstract", "")).lower()
        text_words = set(re.findall(r"\w+", text))

        max_similarity = 0.0
        for topic in self.interest_topics:
            topic_words = set(re.findall(r"\w+", topic))
            if not topic_words:
                continue

            # Simple Jaccard similarity
            intersection = len(text_words.intersection(topic_words))
            union = len(text_words.union(topic_words))
            similarity = intersection / union if union > 0 else 0.0
            max_similarity = max(max_similarity, similarity)

        if max_similarity >= self.min_similarity:
            data["semantic_score"] = float(max_similarity * 10)  # Scale for display
            data["total_score"] = data.get("keyword_score", 0) + data["semantic_score"]
            return data
        return None


class ArticleScorer(MapFunction):
    """
    MapFunction that calculates and adds final score to articles.
    """

    def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        """Calculate total score for ranking."""
        keyword_score = data.get("keyword_score", 0.0)
        semantic_score = data.get("semantic_score", 0.0)
        data["total_score"] = keyword_score + semantic_score
        return data


class ArticleRankingSink(SinkFunction):
    """
    SinkFunction that collects and displays ranked articles.
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.articles: list[dict[str, Any]] = []
        self.start_time = time.time()

    def execute(self, data: dict[str, Any]) -> None:
        """Collect article for final ranking."""
        self.articles.append(data)

    def close(self) -> None:
        """Display ranked results when pipeline completes."""
        elapsed = time.time() - self.start_time

        # Sort by total score
        self.articles.sort(key=lambda x: x.get("total_score", 0), reverse=True)

        print("\n" + "=" * 70)
        print(f"📚 Recommended Articles ({len(self.articles)} found)")
        print("=" * 70)

        for i, article in enumerate(self.articles, 1):
            print(f"\n{i}. {article.get('title', 'Unknown')}")
            authors = article.get("authors", [])
            if authors:
                print(f"   Authors: {', '.join(authors[:3])}")
                if len(authors) > 3:
                    print(f"           (+{len(authors) - 3} more)")
            print(
                f"   Score: {article.get('total_score', 0):.2f} "
                f"(keyword: {article.get('keyword_score', 0):.1f}, "
                f"semantic: {article.get('semantic_score', 0):.2f})"
            )
            print(f"   URL: {article.get('url', 'N/A')}")
            abstract = article.get("abstract", "")
            if abstract:
                preview = abstract[:150] + "..." if len(abstract) > 150 else abstract
                print(f"   Abstract: {preview}")

        print("\n" + "=" * 70)
        print(f"✅ Pipeline completed in {elapsed:.2f}s")
        print(f"   Recommended {len(self.articles)} articles")
        print("=" * 70 + "\n")


class ArticleLogSink(SinkFunction):
    """
    SinkFunction that logs each processed article.
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.count = 0

    def execute(self, data: dict[str, Any]) -> None:
        """Log article processing."""
        self.count += 1
        title = data.get("title", "Unknown")
        score = data.get("total_score", 0)
        self.logger.info(f"[{self.count}] Processed: {title[:50]}... (score: {score:.2f})")
