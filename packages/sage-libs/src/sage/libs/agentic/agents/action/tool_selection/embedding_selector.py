"""
Embedding-based tool selector.

Uses embedding models and vector similarity search for tool selection.
"""

import logging
from typing import Optional

import numpy as np

from .base import BaseToolSelector, SelectorResources
from .retriever.vector_index import VectorIndex
from .schemas import (
    EmbeddingSelectorConfig,
    SelectorConfig,
    ToolPrediction,
    ToolSelectionQuery,
)

logger = logging.getLogger(__name__)


class EmbeddingSelector(BaseToolSelector):
    """
    Embedding-based tool selector using vector similarity.

    Uses embedding service to encode queries and tools, then performs
    similarity search using VectorIndex.

    Optimized for large-scale tool selection (1000+ tools).
    """

    def __init__(self, config: EmbeddingSelectorConfig, resources: SelectorResources):
        """
        Initialize embedding selector.

        Args:
            config: Embedding selector configuration
            resources: Shared resources including embedding_client

        Raises:
            ValueError: If embedding_client is not provided in resources
        """
        super().__init__(config, resources)
        self.config: EmbeddingSelectorConfig = config

        # Validate embedding client
        if not resources.embedding_client:
            raise ValueError(
                "EmbeddingSelector requires embedding_client in SelectorResources. "
                "Please provide an EmbeddingService instance."
            )

        self.embedding_client = resources.embedding_client

        # Initialize vector index
        self._index: Optional[VectorIndex] = None
        self._tool_texts: dict[str, str] = {}
        self._embedding_dimension: Optional[int] = None

        # Preprocess tools
        self._preprocess_tools()

    @classmethod
    def from_config(
        cls, config: SelectorConfig, resources: SelectorResources
    ) -> "EmbeddingSelector":
        """Create embedding selector from config."""
        if not isinstance(config, EmbeddingSelectorConfig):
            raise TypeError(f"Expected EmbeddingSelectorConfig, got {type(config).__name__}")
        return cls(config, resources)  # type: ignore[arg-type]

    def _preprocess_tools(self) -> None:
        """Preprocess all tools and build vector index."""
        try:
            tools_loader = self.resources.tools_loader

            # Collect all tool texts
            tool_ids = []
            tool_texts = []

            for tool in tools_loader.iter_all():
                text = self._build_tool_text(tool)
                self._tool_texts[tool.tool_id] = text
                tool_ids.append(tool.tool_id)
                tool_texts.append(text)

            if not tool_texts:
                self.logger.warning("No tools found to preprocess")
                return

            self.logger.info(f"Embedding {len(tool_texts)} tools...")

            # Embed all tools in batch
            embeddings = self._embed_texts(tool_texts)

            # Infer dimension from embeddings
            self._embedding_dimension = embeddings.shape[1]

            # Build vector index
            self._index = VectorIndex(
                dimension=self._embedding_dimension, metric=self.config.similarity_metric
            )

            # Add all vectors to index
            self._index.add_batch(
                vector_ids=tool_ids,
                vectors=embeddings,
                metadata=[{"text": text} for text in tool_texts],
            )

            self.logger.info(
                f"Built vector index with {len(tool_ids)} tools "
                f"(dimension={self._embedding_dimension}, metric={self.config.similarity_metric})"
            )

        except Exception as e:
            self.logger.error(f"Error preprocessing tools: {e}")
            raise

    def _build_tool_text(self, tool) -> str:
        """
        Build searchable text from tool metadata.

        Args:
            tool: Tool object with metadata

        Returns:
            Concatenated text representation
        """
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

        # Include parameter descriptions if available
        if hasattr(tool, "parameters") and tool.parameters:
            if isinstance(tool.parameters, dict):
                for param_name, param_info in tool.parameters.items():
                    if isinstance(param_info, dict) and "description" in param_info:
                        parts.append(f"{param_name}: {param_info['description']}")

        return " ".join(parts)

    def _embed_texts(self, texts: list[str]) -> np.ndarray:
        """
        Embed texts using embedding client.

        Args:
            texts: List of texts to embed

        Returns:
            Array of embeddings (shape: N x D)
        """
        try:
            # Use embedding client to embed texts
            # The client should handle batching internally
            embeddings = self.embedding_client.embed(
                texts=texts,
                model=self.config.embedding_model
                if self.config.embedding_model != "default"
                else None,
                batch_size=self.config.batch_size,
            )

            # Convert to numpy array if not already
            embeddings = np.asarray(embeddings)

            # Ensure 2D shape
            if embeddings.ndim == 1:
                embeddings = embeddings.reshape(1, -1)

            return embeddings

        except Exception as e:
            self.logger.error(f"Error embedding texts: {e}")
            raise

    def _select_impl(self, query: ToolSelectionQuery, top_k: int) -> list[ToolPrediction]:
        """
        Select tools using embedding similarity.

        Args:
            query: Tool selection query
            top_k: Number of tools to select

        Returns:
            List of tool predictions sorted by similarity
        """
        if self._index is None:
            self.logger.error("Vector index not initialized")
            return []

        try:
            # Embed query
            query_embedding = self._embed_texts([query.instruction])
            query_vector = query_embedding[0]  # Get single vector

            # Filter candidates if specified
            candidate_ids = None
            if query.candidate_tools:
                candidate_ids = set(query.candidate_tools)
                # Only search among candidates that exist in index
                candidate_ids = candidate_ids & set(self._index._ids)
                if not candidate_ids:
                    self.logger.warning(f"No valid candidates for query {query.sample_id}")
                    return []

            # Search vector index
            # Returns list of (vector_id, score) tuples
            results = self._index.search(
                query_vector=query_vector,
                top_k=top_k,
                filter_ids=list(candidate_ids) if candidate_ids else None,
            )

            # Convert to ToolPrediction format
            predictions = []
            for tool_id, score in results:
                # Normalize score to [0, 1] range
                # For euclidean, VectorIndex returns negative distances
                # Convert to similarity: higher is better
                if self.config.similarity_metric == "euclidean":
                    # Negative distance -> convert to positive similarity
                    score = max(0.0, 1.0 / (1.0 + abs(score)))
                else:
                    # Cosine and dot are already similarities
                    score = max(0.0, min(1.0, float(score)))

                predictions.append(
                    ToolPrediction(
                        tool_id=tool_id,
                        score=score,
                        metadata={
                            "similarity_metric": self.config.similarity_metric,
                            "embedding_model": self.config.embedding_model,
                        },
                    )
                )

            # Filter by minimum similarity threshold if specified
            if hasattr(self.config, "similarity_threshold"):
                threshold = self.config.similarity_threshold
                predictions = [p for p in predictions if p.score >= threshold]

            return predictions

        except Exception as e:
            self.logger.error(f"Error in embedding selection for {query.sample_id}: {e}")
            raise

    def get_embedding_dimension(self) -> Optional[int]:
        """Get embedding dimension."""
        return self._embedding_dimension

    def get_index_size(self) -> int:
        """Get number of tools in index."""
        return len(self._index._ids) if self._index else 0

    def get_stats(self) -> dict:
        """Get selector statistics."""
        stats = super().get_stats()
        stats.update(
            {
                "embedding_dimension": self._embedding_dimension,
                "index_size": self.get_index_size(),
                "similarity_metric": self.config.similarity_metric,
                "embedding_model": self.config.embedding_model,
            }
        )
        return stats
