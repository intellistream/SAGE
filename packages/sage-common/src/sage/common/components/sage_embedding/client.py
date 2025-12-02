"""Intelligent Embedding Client with auto-detection and fallback support.

Layer: L1 (Foundation - Common Components)

This module provides a unified embedding client that:
- Auto-detects local embedding services (OpenAI-compatible endpoints)
- Falls back to in-process HuggingFace models if no server available
- Supports OpenAI-compatible embedding APIs
- Provides consistent batch interface (EmbeddingProtocol)

Architecture:
    - L1 component: Can be used by all higher layers
    - No dependencies on L2+ layers
    - Minimal external dependencies

Usage Modes:
    1. API Mode: Connect to embedding server (OpenAI-compatible)
    2. Embedded Mode: Load model in-process (fallback)

Example:
    >>> from sage.common.components.sage_embedding.client import IntelligentEmbeddingClient
    >>>
    >>> # Auto-detect: local server → embedded fallback
    >>> client = IntelligentEmbeddingClient.create()
    >>> vectors = client.embed(["Hello", "World"])
    >>>
    >>> # Explicit API mode
    >>> client = IntelligentEmbeddingClient(
    ...     base_url="http://localhost:8090/v1",
    ...     model="BAAI/bge-m3"
    ... )
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional
from urllib import request

logger = logging.getLogger(__name__)


class IntelligentEmbeddingClient:
    """Intelligent embedding client with auto-detection and fallback.

    Supports two modes:
    1. **API Mode**: Connect to OpenAI-compatible embedding server
       - Local embedding_server.py
       - Remote embedding services

    2. **Embedded Mode**: Load model in-process
       - HuggingFace models
       - No server required
       - Higher memory usage

    Detection Priority (create_auto):
        1. User-configured endpoint (SAGE_EMBEDDING_BASE_URL)
        2. Local embedding server on port 8090 (default)
        3. Local embedding server on port 8080
        4. Embedded mode with default model
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: str = "BAAI/bge-m3",
        api_key: str = "",
        timeout: int = 30,
        mode: str = "auto",  # "api", "embedded", "auto"
        **kwargs: Any,
    ):
        """Initialize embedding client.

        Args:
            base_url: OpenAI-compatible API endpoint (for API mode)
            model: Model name (used in both modes)
            api_key: API key (usually not needed for local server)
            timeout: Request timeout in seconds
            mode: "api" (server), "embedded" (in-process), "auto" (detect)
            **kwargs: Additional arguments
        """
        self.model = model
        self.base_url = base_url
        self.api_key = api_key or "empty"
        self.timeout = timeout
        self.mode = mode
        self._client: Any = None
        self._dimension: Optional[int] = None

        if mode == "api" and base_url:
            self._init_api_mode(base_url)
        elif mode == "embedded":
            self._init_embedded_mode()
        # "auto" mode: defer initialization to create_auto()

    def _init_api_mode(self, base_url: str) -> None:
        """Initialize API mode with OpenAI client."""
        try:
            from openai import OpenAI
        except ImportError as e:
            raise ImportError(
                "openai package required for API mode. Install: pip install openai"
            ) from e

        self._client = OpenAI(
            base_url=base_url,
            api_key=self.api_key,
            timeout=self.timeout,
        )
        self.mode = "api"
        logger.info(f"✅ Embedding client (API): {self.model} @ {base_url}")

    def _init_embedded_mode(self) -> None:
        """Initialize embedded mode with in-process model."""
        from .factory import EmbeddingFactory
        from .protocols import EmbeddingClientAdapter

        raw_embedder = EmbeddingFactory.create("hf", model=self.model)
        self._client = EmbeddingClientAdapter(raw_embedder)
        self._dimension = raw_embedder.get_dim()
        self.mode = "embedded"
        logger.info(f"📦 Embedding client (embedded): {self.model}")

    @classmethod
    def create_auto(
        cls,
        model: str = "BAAI/bge-m3",
        fallback_model: str = "BAAI/bge-small-zh-v1.5",
        **kwargs: Any,
    ) -> IntelligentEmbeddingClient:
        """Create client with auto-detection.

        Detection order:
        1. SAGE_EMBEDDING_BASE_URL environment variable
        2. Local server at localhost:8090
        3. Local server at localhost:8080
        4. Embedded mode with fallback_model

        Args:
            model: Model name for API mode
            fallback_model: Model for embedded fallback (smaller for speed)
            **kwargs: Additional arguments

        Returns:
            Configured IntelligentEmbeddingClient
        """
        # 1. Check environment variable
        env_url = os.environ.get("SAGE_EMBEDDING_BASE_URL")
        if env_url:
            logger.info(f"Using SAGE_EMBEDDING_BASE_URL: {env_url}")
            return cls(base_url=env_url, model=model, mode="api", **kwargs)

        # 2. Try local servers
        local_ports = [8090, 8080]
        for port in local_ports:
            url = f"http://localhost:{port}/v1"
            if cls._check_endpoint(url):
                logger.info(f"Detected local embedding server at port {port}")
                return cls(base_url=url, model=model, mode="api", **kwargs)

        # 3. Fallback to embedded mode
        logger.info(f"No embedding server found, using embedded mode: {fallback_model}")
        client = cls(model=fallback_model, mode="embedded", **kwargs)
        return client

    @classmethod
    def create_api(
        cls,
        base_url: str,
        model: str = "BAAI/bge-m3",
        **kwargs: Any,
    ) -> IntelligentEmbeddingClient:
        """Create client in API mode (explicit server connection).

        Args:
            base_url: OpenAI-compatible API endpoint
            model: Model name
            **kwargs: Additional arguments

        Returns:
            API-mode IntelligentEmbeddingClient
        """
        return cls(base_url=base_url, model=model, mode="api", **kwargs)

    @classmethod
    def create_embedded(
        cls,
        model: str = "BAAI/bge-small-zh-v1.5",
        **kwargs: Any,
    ) -> IntelligentEmbeddingClient:
        """Create client in embedded mode (in-process model).

        Args:
            model: HuggingFace model name
            **kwargs: Additional arguments

        Returns:
            Embedded-mode IntelligentEmbeddingClient
        """
        return cls(model=model, mode="embedded", **kwargs)

    @staticmethod
    def _check_endpoint(base_url: str, timeout: float = 2.0) -> bool:
        """Check if embedding endpoint is available."""
        try:
            # Try /v1/models endpoint (OpenAI compatible)
            url = base_url.rstrip("/")
            if not url.endswith("/v1"):
                url = url + "/v1" if not url.endswith("/") else url + "v1"
            models_url = url.rstrip("/v1") + "/v1/models"

            req = request.Request(models_url, method="GET")
            req.add_header("Content-Type", "application/json")

            with request.urlopen(req, timeout=timeout) as response:
                return response.status == 200
        except Exception:
            return False

    def embed(self, texts: list[str], model: Optional[str] = None) -> list[list[float]]:
        """Embed multiple texts.

        Args:
            texts: List of texts to embed
            model: Optional model override (API mode only)

        Returns:
            List of embedding vectors
        """
        if self.mode == "api":
            return self._embed_api(texts, model)
        else:
            return self._embed_embedded(texts)

    def _embed_api(self, texts: list[str], model: Optional[str] = None) -> list[list[float]]:
        """Embed using API mode."""
        if self._client is None:
            raise RuntimeError("Client not initialized. Use create_auto() or specify base_url.")

        use_model = model or self.model
        response = self._client.embeddings.create(
            input=texts,
            model=use_model,
        )

        # Extract vectors from response
        vectors = [item.embedding for item in response.data]
        return vectors

    def _embed_embedded(self, texts: list[str]) -> list[list[float]]:
        """Embed using embedded mode."""
        if self._client is None:
            raise RuntimeError("Embedded client not initialized.")

        return self._client.embed(texts)

    def get_dim(self) -> int:
        """Get embedding dimension.

        Returns:
            Embedding dimension
        """
        if self._dimension is not None:
            return self._dimension

        if self.mode == "embedded" and self._client is not None:
            return self._client.get_dim()

        # For API mode, infer from a sample embedding
        sample = self.embed(["test"])
        self._dimension = len(sample[0]) if sample else 0
        return self._dimension

    def __repr__(self) -> str:
        if self.mode == "api":
            return f"IntelligentEmbeddingClient(mode=api, model={self.model}, url={self.base_url})"
        else:
            return f"IntelligentEmbeddingClient(mode=embedded, model={self.model})"


# Convenience function
def get_embedding_client(**kwargs: Any) -> IntelligentEmbeddingClient:
    """Get an intelligent embedding client with auto-detection.

    This is a convenience function that calls IntelligentEmbeddingClient.create().

    Returns:
        Configured IntelligentEmbeddingClient
    """
    return IntelligentEmbeddingClient.create(**kwargs)
