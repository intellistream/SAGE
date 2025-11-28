"""
Keyword-based tool selector.

Implements TF-IDF and token overlap strategies for tool selection.
"""

import logging
import re
from collections import Counter

import numpy as np

from .base import BaseToolSelector, SelectorResources
from .schemas import KeywordSelectorConfig, ToolPrediction, ToolSelectionQuery

logger = logging.getLogger(__name__)


# Common English stopwords
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "has",
    "he",
    "in",
    "is",
    "it",
    "its",
    "of",
    "on",
    "that",
    "the",
    "to",
    "was",
    "will",
    "with",
    "this",
    "but",
    "they",
    "have",
}


class KeywordSelector(BaseToolSelector):
    """
    Keyword-based tool selector using TF-IDF or token overlap.

    Fast baseline selector with O(N) complexity.
    """

    def __init__(self, config: KeywordSelectorConfig, resources: SelectorResources):
        """
        Initialize keyword selector.

        Args:
            config: Keyword selector configuration
            resources: Shared resources
        """
        super().__init__(config, resources)
        self.config: KeywordSelectorConfig = config

        # Precompute tool text representations
        self._tool_texts: dict[str, str] = {}
        self._tool_tokens: dict[str, set[str]] = {}
        self._idf_scores: dict[str, float] = {}

        self._preprocess_tools()

    @classmethod
    def from_config(
        cls, config: KeywordSelectorConfig, resources: SelectorResources
    ) -> "KeywordSelector":
        """Create keyword selector from config."""
        return cls(config, resources)

    def _preprocess_tools(self) -> None:
        """Preprocess all tools and compute IDF scores."""
        try:
            # Get all tools from loader
            tools_loader = self.resources.tools_loader

            # Build tool texts
            for tool in tools_loader.iter_all():
                text = self._build_tool_text(tool)
                self._tool_texts[tool.tool_id] = text
                self._tool_tokens[tool.tool_id] = self._tokenize(text)

            # Compute IDF scores (needed for both TF-IDF and BM25)
            if self.config.method in ("tfidf", "bm25"):
                self._compute_idf()

            self.logger.info(f"Preprocessed {len(self._tool_texts)} tools")

        except Exception as e:
            self.logger.error(f"Error preprocessing tools: {e}")
            raise

    def _build_tool_text(self, tool) -> str:
        """Build searchable text from tool metadata."""
        parts = [tool.name]

        if hasattr(tool, "description") and tool.description:
            parts.append(tool.description)

        if hasattr(tool, "capabilities") and tool.capabilities:
            if isinstance(tool.capabilities, list):
                parts.extend(tool.capabilities)
            else:
                parts.append(str(tool.capabilities))

        if hasattr(tool, "category") and tool.category:
            parts.append(tool.category)

        return " ".join(parts)

    def _tokenize(self, text: str) -> set[str]:
        """Tokenize text into set of tokens."""
        if self.config.lowercase:
            text = text.lower()

        # Split on non-alphanumeric
        tokens = re.findall(r"\b[a-z0-9_]+\b", text, re.IGNORECASE)

        # Remove stopwords if enabled
        if self.config.remove_stopwords:
            tokens = [t for t in tokens if t.lower() not in STOPWORDS]

        # Generate n-grams if needed
        if self.config.ngram_range[1] > 1:
            ngrams = []
            for n in range(self.config.ngram_range[0], self.config.ngram_range[1] + 1):
                for i in range(len(tokens) - n + 1):
                    ngrams.append("_".join(tokens[i : i + n]))
            tokens.extend(ngrams)

        return set(tokens)

    def _compute_idf(self) -> None:
        """Compute IDF scores for all tokens."""
        # Count document frequency for each token
        df = Counter()
        total_docs = len(self._tool_tokens)

        for tokens in self._tool_tokens.values():
            df.update(tokens)

        # Compute IDF: log(N / df)
        for token, freq in df.items():
            self._idf_scores[token] = np.log(total_docs / freq)

    def _select_impl(self, query: ToolSelectionQuery, top_k: int) -> list[ToolPrediction]:
        """
        Select tools using keyword matching.

        Args:
            query: Tool selection query
            top_k: Number of tools to select

        Returns:
            List of tool predictions
        """
        # Tokenize query
        query_tokens = self._tokenize(query.instruction)

        if not query_tokens:
            self.logger.warning(f"No tokens in query {query.sample_id}")
            return []

        # Filter candidates
        candidate_ids = (
            set(query.candidate_tools) if query.candidate_tools else set(self._tool_texts.keys())
        )

        # Score each candidate
        scores = []
        for tool_id in candidate_ids:
            if tool_id not in self._tool_tokens:
                continue

            if self.config.method == "tfidf":
                score = self._tfidf_score(query_tokens, tool_id)
            elif self.config.method == "overlap":
                score = self._overlap_score(query_tokens, tool_id)
            elif self.config.method == "bm25":
                score = self._bm25_score(query_tokens, tool_id)
            else:
                raise ValueError(f"Unknown method: {self.config.method}")

            scores.append((tool_id, score))

        # Sort by score and take top-k
        scores.sort(key=lambda x: x[1], reverse=True)
        scores = scores[:top_k]

        # Create predictions
        predictions = [
            ToolPrediction(
                tool_id=tool_id,
                score=min(score, 1.0),  # Normalize to [0, 1]
                metadata={"method": self.config.method},
            )
            for tool_id, score in scores
        ]

        return predictions

    def _tfidf_score(self, query_tokens: set[str], tool_id: str) -> float:
        """Compute TF-IDF score."""
        tool_tokens = self._tool_tokens[tool_id]
        common = query_tokens & tool_tokens

        if not common:
            return 0.0

        # Sum IDF scores for matching tokens
        score = sum(self._idf_scores.get(token, 0.0) for token in common)

        # Normalize by query length
        score /= len(query_tokens)

        return score

    def _overlap_score(self, query_tokens: set[str], tool_id: str) -> float:
        """Compute token overlap score (Jaccard similarity)."""
        tool_tokens = self._tool_tokens[tool_id]

        if not query_tokens or not tool_tokens:
            return 0.0

        intersection = len(query_tokens & tool_tokens)
        union = len(query_tokens | tool_tokens)

        return intersection / union if union > 0 else 0.0

    def _bm25_score(self, query_tokens: set[str], tool_id: str) -> float:
        """Compute BM25 score (simplified)."""
        tool_tokens = self._tool_tokens[tool_id]
        common = query_tokens & tool_tokens

        if not common:
            return 0.0

        # BM25 parameters
        k1 = 1.5
        b = 0.75

        # Average document length
        avg_len = np.mean([len(tokens) for tokens in self._tool_tokens.values()])
        doc_len = len(tool_tokens)

        score = 0.0
        for token in common:
            idf = self._idf_scores.get(token, 0.0)
            tf = 1  # Binary TF

            # BM25 formula
            numerator = tf * (k1 + 1)
            denominator = tf + k1 * (1 - b + b * doc_len / avg_len)

            score += idf * (numerator / denominator)

        return score
