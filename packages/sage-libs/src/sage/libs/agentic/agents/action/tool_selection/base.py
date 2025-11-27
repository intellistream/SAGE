"""
Base classes and protocols for tool selection.

Defines the ToolSelector protocol and abstract base class.
"""

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Optional, Protocol

from .schemas import SelectorConfig, ToolPrediction, ToolSelectionQuery

if TYPE_CHECKING:
    from sage.common.components.sage_embedding.protocols import EmbeddingProtocol

logger = logging.getLogger(__name__)


class SelectorResources:
    """
    Container for shared resources needed by selectors.

    Attributes:
        tools_loader: DataLoader for tool metadata
        embedding_client: Optional embedding service client (must conform to EmbeddingProtocol)
        logger: Logger instance
        cache: Optional cache instance
    """

    def __init__(
        self,
        tools_loader: Any,
        embedding_client: Optional["EmbeddingProtocol"] = None,
        logger: Optional[logging.Logger] = None,
        cache: Optional[Any] = None,
    ):
        """
        Initialize resources.

        Args:
            tools_loader: Tool metadata loader (from DataManager)
            embedding_client: Optional embedding service (must have embed(texts, model) interface)
            logger: Optional logger instance
            cache: Optional cache instance
        """
        self.tools_loader = tools_loader
        self.embedding_client = embedding_client
        self.logger = logger or logging.getLogger(__name__)
        self.cache = cache


class ToolSelectorProtocol(Protocol):
    """Protocol defining the tool selector interface."""

    name: str

    @classmethod
    def from_config(
        cls, config: SelectorConfig, resources: SelectorResources
    ) -> "ToolSelectorProtocol":
        """
        Create selector instance from config and resources.

        Args:
            config: Selector configuration
            resources: Shared resources

        Returns:
            Initialized selector instance
        """
        ...

    def select(
        self, query: ToolSelectionQuery, top_k: Optional[int] = None
    ) -> list[ToolPrediction]:
        """
        Select top-k relevant tools for the given query.

        Args:
            query: Tool selection query
            top_k: Number of tools to select (overrides config if provided)

        Returns:
            List of tool predictions, sorted by score (descending)
        """
        ...


class BaseToolSelector(ABC):
    """
    Abstract base class for tool selectors.

    Provides common functionality and enforces the protocol.
    """

    def __init__(self, config: SelectorConfig, resources: SelectorResources):
        """
        Initialize base selector.

        Args:
            config: Selector configuration
            resources: Shared resources
        """
        self.config = config
        self.resources = resources
        self.logger = resources.logger
        self.name = config.name

        # Statistics
        self._query_count = 0
        self._cache_hits = 0

    @classmethod
    @abstractmethod
    def from_config(
        cls, config: SelectorConfig, resources: SelectorResources
    ) -> "BaseToolSelector":
        """
        Create selector from config.

        Args:
            config: Selector configuration
            resources: Shared resources

        Returns:
            Initialized selector instance
        """
        return cls(config, resources)

    @abstractmethod
    def _select_impl(self, query: ToolSelectionQuery, top_k: int) -> list[ToolPrediction]:
        """
        Implementation-specific selection logic.

        Args:
            query: Tool selection query
            top_k: Number of tools to select

        Returns:
            List of tool predictions
        """
        pass

    def select(
        self, query: ToolSelectionQuery, top_k: Optional[int] = None
    ) -> list[ToolPrediction]:
        """
        Select top-k relevant tools.

        Args:
            query: Tool selection query
            top_k: Number of tools to select (overrides config)

        Returns:
            List of tool predictions, sorted by score (descending)
        """
        k = top_k if top_k is not None else self.config.top_k
        self._query_count += 1

        try:
            # Check cache if enabled
            if self.config.cache_enabled and self.resources.cache:
                cache_key = self._get_cache_key(query, k)
                cached = self.resources.cache.get(cache_key)
                if cached is not None:
                    self._cache_hits += 1
                    self.logger.debug(f"Cache hit for query {query.sample_id}")
                    return cached

            # Perform selection
            predictions = self._select_impl(query, k)

            # Filter by minimum score
            if self.config.min_score > 0:
                predictions = [p for p in predictions if p.score >= self.config.min_score]

            # Sort by score descending
            predictions = sorted(predictions, key=lambda p: p.score, reverse=True)

            # Limit to top-k
            predictions = predictions[:k]

            # Cache result if enabled
            if self.config.cache_enabled and self.resources.cache:
                self.resources.cache.set(cache_key, predictions)

            return predictions

        except Exception as e:
            self.logger.error(f"Error in tool selection for {query.sample_id}: {e}")
            raise

    def _get_cache_key(self, query: ToolSelectionQuery, top_k: int) -> str:
        """Generate cache key for query."""
        return f"{self.name}:{query.sample_id}:{top_k}:{hash(query.instruction)}"

    def get_stats(self) -> dict:
        """Get selector statistics."""
        return {
            "query_count": self._query_count,
            "cache_hits": self._cache_hits,
            "cache_hit_rate": self._cache_hits / max(self._query_count, 1),
        }
