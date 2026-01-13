"""Embedding Service for SAGE.

Layer: L1 (Foundation - Common Components)

This service provides a unified interface for all embedding methods,
including local models (HuggingFace) and API-based services (OpenAI, Jina, etc.).

Note: This service component is designed to be used by L2 (Platform) and higher layers.

Configuration Schema:
---------------------
services:
  embedding:
    class: sage.common.components.sage_embedding.EmbeddingService
    config:
      # Engine type: sagellm (local), openai (API), etc.
      engine: "sagellm"  # Default: sagellm (uses sentence-transformers locally)

      # Embedding method: "hf", "openai", "jina", etc.
      method: "hf"

      # Model name/path (HuggingFace model ID or local path)
      model: "BAAI/bge-small-zh-v1.5"

      # API key for cloud services (openai, jina, etc.)
      api_key: null

      # Custom API endpoint
      base_url: null

      # Batch size for embedding
      batch_size: 32

      # Normalize vectors to unit length
      normalize: true

      # Enable embedding cache (LRU)
      cache_enabled: false
      cache_size: 10000

      # Additional method-specific config
      config: {}

Engine Types:
-------------
- sagellm: Local embedding using sentence-transformers (default, recommended)
- openai: OpenAI embedding API
- (others): Passed through to EmbeddingFactory via method parameter
"""

from __future__ import annotations

import logging
import threading
import warnings
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import numpy as np

from sage.common.components.sage_embedding import EmbeddingFactory, EmbeddingRegistry
from sage.common.service import BaseService

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingServiceConfig:
    """Configuration for EmbeddingService.

    Attributes:
        engine: Engine type for embedding generation.
            - "sagellm": Local embedding using sentence-transformers (default)
            - "openai": OpenAI embedding API
            - Others: Passed to EmbeddingFactory via method parameter
        method: Embedding method ("hf", "openai", "jina", etc.)
        model: Model name/path (HuggingFace model ID or local path)
        api_key: API key for cloud services
        base_url: Custom API endpoint
        batch_size: Default batch size for embedding
        normalize: Normalize vectors to unit length
        cache_enabled: Enable embedding cache
        cache_size: LRU cache size
        config: Method-specific configs
    """

    engine: str = "sagellm"  # sagellm/vllm/openai/...
    method: str = "hf"  # "hf", "openai", "jina", "vllm", etc.
    model: str | None = None  # Model name/path
    api_key: str | None = None  # API key for cloud services
    base_url: str | None = None  # Custom API endpoint
    batch_size: int = 32  # Default batch size
    normalize: bool = True  # Normalize vectors
    cache_enabled: bool = False  # Enable embedding cache
    cache_size: int = 10000  # LRU cache size

    # Method-specific configs
    config: dict[str, Any] = field(default_factory=dict)

    # vLLM-specific (if engine == "vllm")
    vllm_service_name: str | None = None  # Name of vLLM service to use
    vllm_auto_download: bool = False
    vllm_engine_config: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EmbeddingServiceConfig:
        """Create config from dictionary."""
        # Handle legacy configs: if method is specified but engine is not,
        # infer engine from method for backward compatibility
        engine = data.get("engine")
        method = data.get("method", "hf")

        if engine is None:
            # Legacy config without engine field
            if method == "vllm":
                engine = "vllm"
            else:
                engine = "sagellm"  # Default to sagellm for local embedding

        return cls(
            engine=engine,
            method=method,
            model=data.get("model"),
            api_key=data.get("api_key"),
            base_url=data.get("base_url"),
            batch_size=int(data.get("batch_size", 32)),
            normalize=bool(data.get("normalize", True)),
            cache_enabled=bool(data.get("cache_enabled", False)),
            cache_size=int(data.get("cache_size", 10000)),
            config=dict(data.get("config", {})),
            vllm_service_name=data.get("vllm_service_name"),
            vllm_auto_download=bool(data.get("vllm_auto_download", False)),
            vllm_engine_config=dict(data.get("vllm_engine_config", {})),
        )


class EmbeddingService(BaseService):
    """Unified embedding service for SAGE.

    This service provides a consistent interface for all embedding methods:
    - Local models (sagellm engine with sentence-transformers)
    - API-based services (OpenAI, Jina, Zhipu, Cohere, etc.)
    - Hash-based and mock embeddings (for testing)

    Engine Types:
        - sagellm: Local embedding using sentence-transformers (default, recommended)
        - openai: OpenAI embedding API (requires api_key)
        - (others): Passed through to EmbeddingFactory

    Examples:
        # Local embedding with sagellm (recommended):
        services:
          embedding:
            class: sage.common.components.sage_embedding.EmbeddingService
            config:
              engine: "sagellm"
              model: "BAAI/bge-small-zh-v1.5"
              batch_size: 32
              normalize: true

        # Legacy config (still supported):
        services:
          embedding:
            class: sage.common.components.sage_embedding.EmbeddingService
            config:
              method: "hf"
              model: "BAAI/bge-small-zh-v1.5"

        # In pipeline/operator:
        result = self.call_service("embedding", texts=["hello", "world"])
        vectors = result["vectors"]  # List[List[float]]
    """

    def __init__(self, config: dict[str, Any]):
        super().__init__()
        self.config = EmbeddingServiceConfig.from_dict(config)
        self._embedder: Any | None = None  # BaseEmbedding instance or None
        self._st_model: SentenceTransformer | None = None  # sentence-transformers model
        self._lock = threading.RLock()
        self._cache: dict[str, list[float]] | None = None
        self._dimension: int | None = None

    # ------------------------------------------------------------------
    # SAGE lifecycle hooks
    # ------------------------------------------------------------------
    def setup(self) -> None:
        """Initialize the embedding service."""
        self.logger.info(
            f"EmbeddingService setup starting: engine={self.config.engine}, "
            f"method={self.config.method}, model={self.config.model}"
        )

        with self._lock:
            if self.config.engine == "sagellm":
                # Use sagellm engine: local embedding with sentence-transformers
                self._setup_sagellm_engine()
            elif self.config.engine == "vllm":
                # Use vLLM service for embeddings (deprecated)
                warnings.warn(
                    "engine='vllm' is deprecated. Use engine='sagellm' for local embedding "
                    "or configure a remote embedding service.",
                    DeprecationWarning,
                    stacklevel=2,
                )
                self._setup_vllm_engine()
            elif self.config.engine == "openai":
                # Use OpenAI API
                self._setup_openai_engine()
            else:
                # Fallback to EmbeddingFactory for other methods
                self._setup_factory_engine()

            # Setup cache if enabled
            if self.config.cache_enabled:
                self._cache = {}
                self.logger.info(f"Embedding cache enabled: size={self.config.cache_size}")

        self.logger.info("EmbeddingService setup complete")

    def _setup_sagellm_engine(self) -> None:
        """Setup sagellm engine using sentence-transformers."""
        model_name = self.config.model or "BAAI/bge-small-zh-v1.5"

        try:
            from sentence_transformers import SentenceTransformer

            self.logger.info(f"Loading sentence-transformers model: {model_name}")
            self._st_model = SentenceTransformer(model_name)
            # Get dimension from model
            test_embedding = self._st_model.encode(["test"], convert_to_numpy=True)
            self._dimension = test_embedding.shape[1]
            self.logger.info(
                f"sentence-transformers model loaded: {model_name}, dim={self._dimension}"
            )
        except ImportError as e:
            raise ImportError(
                "sentence-transformers is required for sagellm engine. "
                "Install with: pip install sentence-transformers"
            ) from e

    def _setup_vllm_engine(self) -> None:
        """Setup vLLM engine (deprecated)."""
        if not self.config.vllm_service_name:
            raise ValueError("vLLM engine requires 'vllm_service_name' in config")
        self.logger.info(f"Using vLLM service: {self.config.vllm_service_name}")
        # Don't create embedder - will use service call

    def _setup_openai_engine(self) -> None:
        """Setup OpenAI embedding engine."""
        kwargs: dict[str, Any] = {}
        if self.config.model:
            kwargs["model"] = self.config.model
        if self.config.api_key:
            kwargs["api_key"] = self.config.api_key
        if self.config.base_url:
            kwargs["base_url"] = self.config.base_url
        kwargs.update(self.config.config)

        self._embedder = EmbeddingFactory.create("openai", **kwargs)
        self._dimension = self._embedder.get_dim()
        self.logger.info(f"OpenAI embedding initialized: dim={self._dimension}")

    def _setup_factory_engine(self) -> None:
        """Setup embedding using EmbeddingFactory (fallback)."""
        kwargs = dict(self.config.config)
        if self.config.model:
            kwargs["model"] = self.config.model
        if self.config.api_key:
            kwargs["api_key"] = self.config.api_key
        if self.config.base_url:
            kwargs["base_url"] = self.config.base_url

        self._embedder = EmbeddingFactory.create(self.config.method, **kwargs)
        self._dimension = self._embedder.get_dim()
        self.logger.info(f"Embedding model loaded via factory: dim={self._dimension}")

    def cleanup(self) -> None:
        """Clean up resources."""
        with self._lock:
            if self._embedder is not None:
                if hasattr(self._embedder, "cleanup"):
                    self._embedder.cleanup()  # type: ignore
                self._embedder = None
            if self._st_model is not None:
                # sentence-transformers doesn't have explicit cleanup
                self._st_model = None
            if self._cache is not None:
                self._cache.clear()
                self._cache = None
            self.logger.info("EmbeddingService cleanup complete")

    # ------------------------------------------------------------------
    # Public service API
    # ------------------------------------------------------------------
    def process(self, payload: dict[str, Any]) -> Any:
        """Process embedding requests.

        Payload format:
            {
                "task": "embed",  # or "info", "list_methods"
                "inputs": str | List[str],  # Text(s) to embed
                "options": {
                    "normalize": bool,
                    "batch_size": int,
                    "return_stats": bool,
                }
            }
        """
        task = (payload or {}).get("task", "embed")
        inputs = (payload or {}).get("inputs")
        options = (payload or {}).get("options", {})

        if task == "embed":
            if inputs is None:
                raise ValueError("'inputs' is required for task 'embed'")
            return self.embed(inputs, **options)
        if task == "info":
            return self.get_info()
        if task == "list_methods":
            return self.list_methods()
        if task == "get_dimension":
            return {"dimension": self.get_dimension()}

        raise ValueError(f"Unsupported task '{task}'")

    def embed(
        self,
        texts: str | list[str],
        *,
        normalize: bool | None = None,
        batch_size: int | None = None,
        return_stats: bool = False,
    ) -> dict[str, Any]:
        """Generate embeddings for text(s).

        Args:
            texts: Single text or list of texts
            normalize: Override config normalize setting
            batch_size: Override config batch_size
            return_stats: Include embedding statistics

        Returns:
            {
                "vectors": List[List[float]],
                "dimension": int,
                "count": int,
                "method": str,
                "model": str,
                "stats": {...}  # if return_stats=True
            }
        """
        # Normalize inputs
        if isinstance(texts, str):
            texts = [texts]
        elif not isinstance(texts, list):
            texts = list(texts)

        if not texts:
            return {
                "vectors": [],
                "dimension": self.get_dimension(),
                "count": 0,
                "engine": self.config.engine,
                "method": self.config.method,
                "model": self.config.model,
            }

        # Ensure setup has been called
        if self.config.engine == "sagellm" and self._st_model is None:
            raise RuntimeError("EmbeddingService not setup. Call setup() first.")
        if self.config.engine == "vllm" and not self.config.vllm_service_name:
            raise RuntimeError("vLLM engine requires vllm_service_name")
        if self.config.engine not in ("sagellm", "vllm") and self._embedder is None:
            raise RuntimeError("EmbeddingService not setup. Call setup() first.")

        normalize = normalize if normalize is not None else self.config.normalize
        batch_size = batch_size or self.config.batch_size

        # Check cache
        cached_results = []
        uncached_texts = []
        uncached_indices = []

        if self.config.cache_enabled and self._cache is not None:
            for i, text in enumerate(texts):
                if text in self._cache:
                    cached_results.append((i, self._cache[text]))
                else:
                    uncached_texts.append(text)
                    uncached_indices.append(i)
        else:
            uncached_texts = texts
            uncached_indices = list(range(len(texts)))

        # Generate embeddings for uncached texts
        vectors = [None] * len(texts)

        if uncached_texts:
            if self.config.engine == "sagellm":
                # Use sentence-transformers for local embedding
                assert self._st_model is not None
                uncached_vectors = self._embed_with_sentence_transformers(
                    uncached_texts, normalize, batch_size
                )
            elif self.config.engine == "vllm":
                # Use vLLM service
                if not self.config.vllm_service_name:
                    raise ValueError("vllm_service_name is required for vLLM engine")
                result = self.call_service(
                    self.config.vllm_service_name,
                    payload={
                        "task": "embed",
                        "inputs": uncached_texts,
                        "options": {
                            "normalize": normalize,
                            "batch_size": batch_size,
                        },
                    },
                )
                uncached_vectors = result["vectors"]
            else:
                # Use standard embedder (factory-based)
                assert self._embedder is not None
                uncached_vectors = self._embed_with_factory(
                    uncached_texts, normalize, batch_size
                )

            # Update cache and results
            for idx, text, vec in zip(
                uncached_indices, uncached_texts, uncached_vectors, strict=False
            ):
                vectors[idx] = vec
                if self.config.cache_enabled and self._cache is not None:
                    # LRU eviction
                    if len(self._cache) >= self.config.cache_size:
                        self._cache.pop(next(iter(self._cache)))
                    self._cache[text] = vec

        # Add cached results
        for idx, vec in cached_results:
            vectors[idx] = vec

        # Build response
        first_vector: list[float] | None = vectors[0] if vectors else None
        dimension = len(first_vector) if first_vector is not None else self.get_dimension()

        result = {
            "vectors": vectors,
            "dimension": dimension,
            "count": len(vectors),
            "engine": self.config.engine,
            "method": self.config.method,
            "model": self.config.model or self.config.method,
        }

        if return_stats:
            result["stats"] = {
                "cached": len(cached_results),
                "computed": len(uncached_texts),
                "cache_hit_rate": len(cached_results) / len(texts) if texts else 0.0,
            }

        return result

    def get_dimension(self) -> int:
        """Get embedding dimension."""
        if self._dimension is not None:
            return self._dimension

        if self.config.engine == "sagellm":
            # sentence-transformers: get dimension from model
            if self._st_model is not None:
                test_embedding = self._st_model.encode(["test"], convert_to_numpy=True)
                self._dimension = test_embedding.shape[1]
            else:
                self._dimension = 768  # Default for BERT-based models
        elif self.config.engine == "vllm":
            # Query vLLM service
            if not self.config.vllm_service_name:
                raise ValueError("vllm_service_name is required for vLLM engine")
            result = self.call_service(
                self.config.vllm_service_name,
                payload={"task": "embed", "inputs": "test"},
            )
            self._dimension = result.get("dimension", 768)
        elif self._embedder is not None:
            self._dimension = self._embedder.get_dim()
        else:
            self._dimension = 768  # Default

        assert self._dimension is not None
        return self._dimension

    def get_info(self) -> dict[str, Any]:
        """Get embedding service information."""
        info: dict[str, Any] = {
            "engine": self.config.engine,
            "method": self.config.method,
            "model": self.config.model,
            "dimension": self.get_dimension(),
            "batch_size": self.config.batch_size,
            "normalize": self.config.normalize,
            "cache_enabled": self.config.cache_enabled,
        }

        if self.config.cache_enabled and self._cache is not None:
            cache_stats: dict[str, int] = {
                "size": len(self._cache),
                "capacity": self.config.cache_size,
            }
            info["cache_stats"] = cache_stats

        if self.config.engine == "vllm":
            info["vllm_service"] = self.config.vllm_service_name

        return info

    def list_methods(self) -> list[dict[str, Any]]:
        """List all available embedding methods."""
        methods = []

        # Add sagellm (local) method first
        methods.append(
            {
                "name": "sagellm",
                "description": "Local embedding with sentence-transformers (recommended)",
                "requires_api_key": False,
                "requires_model_download": True,
                "status": "available",
                "engine": "sagellm",
            }
        )

        # Add registered methods from EmbeddingRegistry
        for method in EmbeddingRegistry.list_methods():
            info = EmbeddingRegistry.get_model_info(method)
            if info:
                # Determine status based on requirements
                if info.requires_api_key:
                    status = "needs_api_key"
                elif info.requires_model_download:
                    status = "needs_download"
                else:
                    status = "available"

                methods.append(
                    {
                        "name": method,
                        "description": info.description,
                        "requires_api_key": info.requires_api_key,
                        "requires_model_download": info.requires_model_download,
                        "status": status,
                        "engine": method,  # Use method name as engine
                    }
                )

        # Add vLLM method (deprecated)
        methods.append(
            {
                "name": "vllm",
                "description": "High-performance vLLM embedding service (deprecated, use sagellm)",
                "requires_api_key": False,
                "requires_model_download": True,
                "status": "deprecated",
                "engine": "vllm",
            }
        )

        return methods

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _embed_with_sentence_transformers(
        self, texts: list[str], normalize: bool, batch_size: int
    ) -> list[list[float]]:
        """Generate embeddings using sentence-transformers."""
        assert self._st_model is not None

        all_vectors: list[list[float]] = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            # sentence-transformers handles batching internally
            embeddings = self._st_model.encode(
                batch,
                convert_to_numpy=True,
                normalize_embeddings=normalize,
            )
            # Convert numpy array to list of lists
            all_vectors.extend(embeddings.tolist())

        return all_vectors

    def _embed_with_factory(
        self, texts: list[str], normalize: bool, batch_size: int
    ) -> list[list[float]]:
        """Generate embeddings using EmbeddingFactory embedder."""
        assert self._embedder is not None

        uncached_vectors: list[list[float]] = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            if len(batch) == 1:
                vec = self._embedder.embed(batch[0])
                if normalize:
                    vec = self._normalize_vector(vec)
                uncached_vectors.append(vec)
            else:
                batch_vecs = self._embedder.embed_batch(batch)
                if normalize:
                    batch_vecs = [self._normalize_vector(v) for v in batch_vecs]
                uncached_vectors.extend(batch_vecs)

        return uncached_vectors
    def _normalize_vector(self, vec: list[float]) -> list[float]:
        """Normalize a vector to unit length."""
        array = np.array(vec, dtype=np.float32)
        norm = np.linalg.norm(array)
        if norm > 0:
            array = array / norm
        return array.tolist()


__all__ = ["EmbeddingService", "EmbeddingServiceConfig"]
