"""
Hybrid tool selector.

Combines keyword and embedding-based selection strategies using score fusion.
"""

import logging
from typing import Optional

from .base import BaseToolSelector, SelectorResources
from .embedding_selector import EmbeddingSelector
from .keyword_selector import KeywordSelector
from .schemas import (
    EmbeddingSelectorConfig,
    KeywordSelectorConfig,
    SelectorConfig,
    ToolPrediction,
    ToolSelectionQuery,
)

logger = logging.getLogger(__name__)


class HybridSelectorConfig(SelectorConfig):
    """Configuration for hybrid selector."""

    name: str = "hybrid"
    keyword_weight: float = 0.4
    embedding_weight: float = 0.6
    keyword_method: str = "bm25"
    embedding_model: str = "default"
    fusion_method: str = "weighted_sum"  # weighted_sum, max, reciprocal_rank


class HybridSelector(BaseToolSelector):
    """
    Hybrid tool selector combining keyword and embedding strategies.

    Uses score fusion to combine results from both approaches:
    - Keyword matching: Fast, works well for exact matches
    - Embedding similarity: Better semantic understanding

    Fusion methods:
    - weighted_sum: Linear combination of normalized scores
    - max: Maximum score from either method
    - reciprocal_rank: Reciprocal Rank Fusion (RRF)
    """

    def __init__(self, config: HybridSelectorConfig, resources: SelectorResources):
        """
        Initialize hybrid selector.

        Args:
            config: Hybrid selector configuration
            resources: Shared resources including embedding_client

        Note:
            If embedding_client is not available, falls back to keyword-only mode.
        """
        super().__init__(config, resources)
        self.config: HybridSelectorConfig = config

        # Initialize keyword selector
        keyword_config = KeywordSelectorConfig(
            name="keyword",
            method=config.keyword_method,
            top_k=config.top_k * 2,  # Get more candidates for fusion
        )
        self._keyword_selector = KeywordSelector(keyword_config, resources)

        # Initialize embedding selector if client available
        self._embedding_selector: Optional[EmbeddingSelector] = None
        self._embedding_available = False

        if resources.embedding_client:
            try:
                embedding_config = EmbeddingSelectorConfig(
                    name="embedding",
                    embedding_model=config.embedding_model,
                    top_k=config.top_k * 2,
                )
                self._embedding_selector = EmbeddingSelector(embedding_config, resources)
                self._embedding_available = True
                self.logger.info("Hybrid selector: Embedding + Keyword mode")
            except Exception as e:
                self.logger.warning(f"Could not initialize embedding selector: {e}")
                self.logger.info("Hybrid selector: Keyword-only mode")
        else:
            self.logger.info("Hybrid selector: Keyword-only mode (no embedding client)")

    @classmethod
    def from_config(cls, config: SelectorConfig, resources: SelectorResources) -> "HybridSelector":
        """Create hybrid selector from config."""
        if not isinstance(config, HybridSelectorConfig):
            # Convert generic config to HybridSelectorConfig
            config = HybridSelectorConfig(
                name=config.name,
                top_k=config.top_k,
                min_score=config.min_score,
                cache_enabled=config.cache_enabled,
                params=config.params,
            )
        return cls(config, resources)

    def _select_impl(self, query: ToolSelectionQuery, top_k: int) -> list[ToolPrediction]:
        """
        Select tools using hybrid approach.

        Args:
            query: Tool selection query
            top_k: Number of tools to select

        Returns:
            List of tool predictions from fused scores
        """
        # Get keyword results
        keyword_results = self._keyword_selector._select_impl(query, top_k * 2)
        keyword_scores = {p.tool_id: p.score for p in keyword_results}

        # Get embedding results if available
        embedding_scores = {}
        if self._embedding_available and self._embedding_selector:
            try:
                embedding_results = self._embedding_selector._select_impl(query, top_k * 2)
                embedding_scores = {p.tool_id: p.score for p in embedding_results}
            except Exception as e:
                self.logger.warning(f"Embedding selection failed, using keyword only: {e}")

        # Fuse scores
        all_tool_ids = set(keyword_scores.keys()) | set(embedding_scores.keys())
        fused_predictions = []

        for tool_id in all_tool_ids:
            kw_score = keyword_scores.get(tool_id, 0.0)
            emb_score = embedding_scores.get(tool_id, 0.0)

            if self.config.fusion_method == "weighted_sum":
                # Normalize and combine
                if self._embedding_available:
                    final_score = (
                        self.config.keyword_weight * kw_score
                        + self.config.embedding_weight * emb_score
                    )
                else:
                    final_score = kw_score

            elif self.config.fusion_method == "max":
                final_score = max(kw_score, emb_score)

            elif self.config.fusion_method == "reciprocal_rank":
                # RRF: 1/(k+rank)
                k = 60  # Standard RRF constant
                kw_rank = self._get_rank(tool_id, keyword_results)
                emb_rank = (
                    self._get_rank(tool_id, embedding_results)
                    if self._embedding_available
                    else float("inf")
                )

                kw_rrf = 1.0 / (k + kw_rank) if kw_rank < float("inf") else 0
                emb_rrf = 1.0 / (k + emb_rank) if emb_rank < float("inf") else 0

                final_score = kw_rrf + emb_rrf
            else:
                final_score = kw_score

            fused_predictions.append(
                ToolPrediction(
                    tool_id=tool_id,
                    score=min(final_score, 1.0),
                    metadata={
                        "keyword_score": kw_score,
                        "embedding_score": emb_score,
                        "fusion_method": self.config.fusion_method,
                    },
                )
            )

        # Sort by fused score
        fused_predictions.sort(key=lambda p: p.score, reverse=True)

        return fused_predictions[:top_k]

    def _get_rank(self, tool_id: str, predictions: list[ToolPrediction]) -> float:
        """Get rank of tool_id in predictions list (1-indexed)."""
        for i, p in enumerate(predictions):
            if p.tool_id == tool_id:
                return i + 1
        return float("inf")

    def get_stats(self) -> dict:
        """Get selector statistics."""
        stats = super().get_stats()
        stats.update(
            {
                "embedding_available": self._embedding_available,
                "fusion_method": self.config.fusion_method,
                "keyword_weight": self.config.keyword_weight,
                "embedding_weight": self.config.embedding_weight,
            }
        )
        return stats
