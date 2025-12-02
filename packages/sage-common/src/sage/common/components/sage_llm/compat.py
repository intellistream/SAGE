# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""Specialized adapters for LLM and Embedding clients.

This module provides adapter classes that extend UnifiedInferenceClient
for specialized use cases (LLM-only or Embedding-only operations).

The adapters ensure that:
1. Specialized interfaces are available for specific use cases
2. Full functionality of UnifiedInferenceClient is inherited
3. Additional convenience methods are provided

Example:
    >>> # LLM-focused usage
    >>> from sage.common.components.sage_llm import LLMClientAdapter
    >>> client = LLMClientAdapter.create()
    >>> response = client.chat([{"role": "user", "content": "Hello"}])
    >>>
    >>> # Embedding-focused usage
    >>> from sage.common.components.sage_llm import EmbeddingClientAdapter
    >>> client = EmbeddingClientAdapter.create()
    >>> vectors = client.embed(["text1", "text2"])
    >>>
    >>> # Or use the unified client directly (recommended)
    >>> from sage.common.components.sage_llm import UnifiedInferenceClient
    >>> client = UnifiedInferenceClient.create()
    >>> response = client.chat([{"role": "user", "content": "Hello"}])
    >>> vectors = client.embed(["text1", "text2"])
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from .unified_client import (
    InferenceResult,
    UnifiedInferenceClient,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class LLMClientAdapter(UnifiedInferenceClient):
    """Adapter for LLM-focused operations.

    This adapter extends UnifiedInferenceClient with a focus on LLM operations.
    It provides the same interface as UnifiedInferenceClient but with LLM-specific
    defaults and convenience methods.

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
        # Allow init for adapter classes
        UnifiedInferenceClient._allow_init = True
        try:
            # Map old parameter names to new ones
            super().__init__(
                llm_base_url=base_url,
                llm_model=model_name,
                llm_api_key=api_key,
                timeout=timeout,
                max_retries=max_retries,
                **kwargs,
            )
        finally:
            UnifiedInferenceClient._allow_init = False

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
        """Create adapter with auto-detection.

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
        timeout: float = 60.0,
        **kwargs: Any,
    ) -> LLMClientAdapter:
        """Create adapter with auto-detection.

        Args:
            timeout: Request timeout in seconds.
            **kwargs: Additional arguments.

        Returns:
            Configured LLMClientAdapter instance.
        """
        # Use parent's detection logic
        llm_base_url, llm_model, llm_api_key = cls._detect_llm_endpoint(
            prefer_local=True,
            ports=(8001, 8000),
        )

        return cls(
            model_name=llm_model,
            base_url=llm_base_url,
            api_key=llm_api_key,
            timeout=timeout,
            **kwargs,
        )


class EmbeddingClientAdapter(UnifiedInferenceClient):
    """Adapter for Embedding-focused operations.

    This adapter extends UnifiedInferenceClient with a focus on Embedding operations.
    It provides the same interface as UnifiedInferenceClient but with embedding-specific
    defaults and convenience methods.

    Example:
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
        # Allow init for adapter classes
        UnifiedInferenceClient._allow_init = True
        try:
            super().__init__(
                embedding_base_url=base_url,
                embedding_model=model,
                embedding_api_key=api_key,
                timeout=timeout,
                **kwargs,
            )
        finally:
            UnifiedInferenceClient._allow_init = False

        self._mode = mode
        self._embedded_embedder: Any = None

        # Initialize embedded mode if requested
        if mode == "embedded" and model:
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
        fallback_model: str = "BAAI/bge-small-zh-v1.5",
        timeout: float = 60.0,
        **kwargs: Any,
    ) -> EmbeddingClientAdapter:
        """Create adapter with auto-detection.

        .. deprecated::
            Use :meth:`create` instead. This method will be removed in a future version.

        Args:
            fallback_model: Model to use for embedded mode if no server found.
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
        return cls.create(fallback_model=fallback_model, timeout=timeout, **kwargs)

    @classmethod
    def create(
        cls,
        *,
        fallback_model: str = "BAAI/bge-small-zh-v1.5",
        timeout: float = 60.0,
        **kwargs: Any,
    ) -> EmbeddingClientAdapter:
        """Create adapter with auto-detection.

        Detection order:
        1. SAGE_EMBEDDING_BASE_URL environment variable
        2. Local embedding server (ports 8090, 8080)
        3. Embedded mode with fallback_model

        Args:
            fallback_model: Model to use for embedded mode if no server found.
            timeout: Request timeout in seconds.
            **kwargs: Additional arguments.

        Returns:
            Configured EmbeddingClientAdapter instance.
        """
        # Try to detect API endpoint
        base_url, model, api_key = cls._detect_embedding_endpoint(
            prefer_local=True,
            ports=(8090, 8080),
        )

        if base_url:
            return cls(
                base_url=base_url,
                model=model,
                api_key=api_key,
                mode="api",
                timeout=timeout,
                **kwargs,
            )

        # Fall back to embedded mode
        logger.info(
            "No embedding server found, using embedded mode with model: %s",
            fallback_model,
        )
        return cls.create_embedded(model=fallback_model, timeout=timeout, **kwargs)

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
