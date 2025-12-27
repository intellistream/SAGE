# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""Backward compatibility adapters for unified inference client.

This module provides adapter classes (LLMClientAdapter and EmbeddingClientAdapter)
that inherit from UnifiedInferenceClient and provide specialized interfaces
for LLM-only or Embedding-only use cases.

Example:
    >>> # Unified client (recommended)
    >>> from sage.llm import UnifiedInferenceClient
    >>> client = UnifiedInferenceClient.create()
    >>> response = client.chat([{"role": "user", "content": "Hello"}])
    >>> vectors = client.embed(["text1", "text2"])
    >>>
    >>> # LLM-focused adapter (legacy compatibility)
    >>> from sage.llm import LLMClientAdapter
    >>> adapter = LLMClientAdapter.create()
    >>> response = adapter.chat([{"role": "user", "content": "Hello"}])
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Any

from sage.llm.unified_client import (
    InferenceResult,
    UnifiedInferenceClient,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class LLMClientAdapter(UnifiedInferenceClient):
    """Adapter providing LLM-focused interface.

    This adapter wraps UnifiedInferenceClient to provide a specialized interface
    for LLM-only use cases. It:

    1. Provides convenient factory methods (create, create_auto)
    2. Exposes legacy properties (model_name, base_url, api_key)
    3. Inherits all UnifiedInferenceClient capabilities

    Example:
        >>> adapter = LLMClientAdapter.create()
        >>> response = adapter.chat([{"role": "user", "content": "Hello"}])
        >>>
        >>> # Also supports embedding (inherited from UnifiedInferenceClient)
        >>> vectors = adapter.embed(["text"])
    """

    def __init__(
        self,
        model_name: str | None = None,
        base_url: str | None = None,
        api_key: str = "",
        timeout: float = 60.0,
        max_retries: int = 3,
        **kwargs: Any,
    ) -> None:
        """Initialize the LLM client adapter.

        Args:
            model_name: Default model name for requests.
            base_url: Base URL for the LLM API endpoint.
            api_key: API key for authentication.
            timeout: Request timeout in seconds.
            max_retries: Maximum number of retries for failed requests.
            **kwargs: Additional arguments passed to UnifiedInferenceClient.
        """
        # Map old parameter names to new ones
        super().__init__(
            llm_base_url=base_url,
            llm_model=model_name,
            llm_api_key=api_key,
            timeout=timeout,
            max_retries=max_retries,
            **kwargs,
        )

        # Store original parameters for backward compatibility
        self._model_name = model_name
        self._base_url = base_url
        self._api_key = api_key

    # Legacy properties for backward compatibility
    @property
    def model_name(self) -> str | None:
        """Get the model name (legacy property)."""
        return self.config.llm_model

    @property
    def base_url(self) -> str | None:
        """Get the base URL (legacy property)."""
        return self.config.llm_base_url

    @property
    def api_key(self) -> str:
        """Get the API key (legacy property)."""
        return self.config.llm_api_key

    @classmethod
    def create_auto(
        cls,
        *,
        timeout: float = 60.0,
        **kwargs: Any,
    ) -> LLMClientAdapter:
        """Create adapter (deprecated alias for create).

        .. deprecated::
            Use :meth:`create` instead. This method will be removed in a future version.

        Args:
            timeout: Request timeout in seconds.
            **kwargs: Additional arguments.

        Returns:
            Configured LLMClientAdapter instance.
        """
        import warnings

        warnings.warn(
            "create_auto() is deprecated, use create() instead",
            DeprecationWarning,
            stacklevel=2,
        )
        return cls.create(timeout=timeout, **kwargs)

    @classmethod
    def create(
        cls,
        *,
        control_plane_url: str | None = None,
        default_llm_model: str | None = None,
        llm_api_key: str | None = None,
        timeout: float = 60.0,
        max_retries: int = 3,
        **kwargs: Any,
    ) -> LLMClientAdapter:
        """Create adapter pointing to the Control Plane/Gateway only.

        Args:
            control_plane_url: Optional explicit Control Plane URL.
            default_llm_model: Default model name for LLM requests.
            llm_api_key: Optional API key override.
            timeout: Request timeout in seconds.
            max_retries: Maximum retries for failed requests.
            **kwargs: Additional arguments passed to the adapter constructor.

        Returns:
            Configured LLMClientAdapter instance bound to the control plane.
        """

        base_client = UnifiedInferenceClient.create(
            control_plane_url=control_plane_url,
            default_llm_model=default_llm_model,
            llm_api_key=llm_api_key,
            timeout=timeout,
        )

        return cls(
            model_name=base_client.config.llm_model,
            base_url=base_client.config.llm_base_url,
            api_key=base_client.config.llm_api_key or "",
            timeout=timeout,
            max_retries=max_retries,
            **kwargs,
        )


class EmbeddingClientAdapter(UnifiedInferenceClient):
    """Adapter to provide IntelligentEmbeddingClient-compatible interface.

    This adapter wraps UnifiedInferenceClient to provide backward compatibility
    with the existing IntelligentEmbeddingClient API. It:

    1. Maintains the same method signatures as IntelligentEmbeddingClient
    2. Uses UnifiedInferenceClient internally for actual operations
    3. Supports both API and embedded modes

    Example:
        >>> # Works exactly like IntelligentEmbeddingClient
        >>> adapter = EmbeddingClientAdapter.create()
        >>> vectors = adapter.embed(["text1", "text2"])
        >>>
        >>> # API mode
        >>> adapter = EmbeddingClientAdapter.create_api(
        ...     base_url="http://localhost:8090/v1",
        ...     model="BAAI/bge-m3",
        ... )
        >>>
        >>> # Embedded mode (in-process)
        >>> adapter = EmbeddingClientAdapter.create_embedded(
        ...     model="BAAI/bge-small-zh-v1.5",
        ... )
    """

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        api_key: str = "",
        mode: str = "api",
        timeout: float = 60.0,
        **kwargs: Any,
    ) -> None:
        """Initialize the embedding client adapter.

        Args:
            base_url: Base URL for the embedding API endpoint.
            model: Default model name for embedding requests.
            api_key: API key for authentication.
            mode: Operation mode ("api" or "embedded").
            timeout: Request timeout in seconds.
            **kwargs: Additional arguments passed to UnifiedInferenceClient.
        """
        super().__init__(
            embedding_base_url=base_url,
            embedding_model=model,
            embedding_api_key=api_key,
            timeout=timeout,
            **kwargs,
        )

        self._mode = mode
        self._embedded_embedder: Any = None

        # Initialize embedded mode if requested
        if mode == "embedded" and model:
            # Skip heavy model load during test runs to avoid long downloads
            in_test = os.getenv("PYTEST_CURRENT_TEST") or os.getenv("SAGE_TEST_MODE") == "true"
            if in_test:
                logger.info("Test mode detected, skipping embedded embedder initialization")
            else:
                self._init_embedded_mode(model)

    def _init_embedded_mode(self, model: str) -> None:
        """Initialize embedded mode with HuggingFace model."""
        try:
            from ..sage_embedding import EmbeddingFactory

            self._embedded_embedder = EmbeddingFactory.create(
                "hf",
                model=model,
            )
            self._embedding_available = True
            logger.info("Embedded embedding mode initialized with model: %s", model)
        except Exception as e:
            logger.warning("Failed to initialize embedded mode: %s", e)
            self._embedding_available = False

    # Legacy properties
    @property
    def model(self) -> str | None:
        """Get the model name (legacy property)."""
        return self.config.embedding_model

    @property
    def base_url(self) -> str | None:
        """Get the base URL (legacy property)."""
        return self.config.embedding_base_url

    def embed(
        self,
        texts: str | list[str],
        *,
        model: str | None = None,
        **kwargs: Any,
    ) -> list[list[float]] | InferenceResult:
        """Generate embeddings (with embedded mode support).

        Args:
            texts: Single text or list of texts to embed.
            model: Model to use (defaults to configured model).
            **kwargs: Additional parameters.

        Returns:
            List of embedding vectors.
        """
        # Normalize input
        if isinstance(texts, str):
            texts = [texts]

        # Use embedded mode if available
        if self._mode == "embedded" and self._embedded_embedder:
            return [self._embedded_embedder.embed(text) for text in texts]

        # Otherwise use parent's API-based implementation
        return super().embed(texts, model=model, **kwargs)

    @classmethod
    def create_auto(
        cls,
        *,
        timeout: float = 60.0,
        **kwargs: Any,
    ) -> EmbeddingClientAdapter:
        """Create adapter (deprecated alias for create).

        .. deprecated::
            Use :meth:`create` instead. This method will be removed in a future version.

        Args:
            timeout: Request timeout in seconds.
            **kwargs: Additional arguments.

        Returns:
            Configured EmbeddingClientAdapter instance.
        """
        import warnings

        warnings.warn(
            "create_auto() is deprecated, use create() instead",
            DeprecationWarning,
            stacklevel=2,
        )
        return cls.create(timeout=timeout, **kwargs)

    @classmethod
    def create(
        cls,
        *,
        control_plane_url: str | None = None,
        default_embedding_model: str | None = None,
        embedding_api_key: str | None = None,
        timeout: float = 60.0,
        **kwargs: Any,
    ) -> EmbeddingClientAdapter:
        """Create adapter pointing to the Control Plane/Gateway only.

        Args:
            control_plane_url: Optional explicit Control Plane URL.
            default_embedding_model: Default embedding model name.
            embedding_api_key: Optional API key override.
            timeout: Request timeout in seconds.
            **kwargs: Additional arguments passed to the adapter constructor.

        Returns:
            Configured EmbeddingClientAdapter instance bound to the control plane.
        """

        base_client = UnifiedInferenceClient.create(
            control_plane_url=control_plane_url,
            default_embedding_model=default_embedding_model,
            embedding_api_key=embedding_api_key,
            timeout=timeout,
        )

        return cls(
            base_url=base_client.config.embedding_base_url,
            model=base_client.config.embedding_model,
            api_key=base_client.config.embedding_api_key or "",
            mode="api",
            timeout=timeout,
            **kwargs,
        )

    @classmethod
    def create_api(
        cls,
        base_url: str,
        model: str | None = None,
        api_key: str = "",
        timeout: float = 60.0,
        **kwargs: Any,
    ) -> EmbeddingClientAdapter:
        """Create adapter with explicit API configuration.

        Args:
            base_url: Base URL for the embedding API endpoint.
            model: Model name to use.
            api_key: API key for authentication.
            timeout: Request timeout in seconds.
            **kwargs: Additional arguments.

        Returns:
            Configured EmbeddingClientAdapter instance.
        """
        return cls(
            base_url=base_url,
            model=model,
            api_key=api_key,
            mode="api",
            timeout=timeout,
            **kwargs,
        )

    @classmethod
    def create_embedded(
        cls,
        model: str,
        timeout: float = 60.0,
        **kwargs: Any,
    ) -> EmbeddingClientAdapter:
        """Create adapter with embedded (in-process) mode.

        This mode loads the embedding model directly into the current process
        using HuggingFace transformers, without requiring an external server.

        Args:
            model: HuggingFace model name to load.
            timeout: Request timeout in seconds (not used in embedded mode).
            **kwargs: Additional arguments.

        Returns:
            Configured EmbeddingClientAdapter instance.
        """
        return cls(
            model=model,
            mode="embedded",
            timeout=timeout,
            **kwargs,
        )
