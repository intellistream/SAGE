"""Embedding Service for SAGE.

This service provides a unified interface for all embedding methods,
including local models (HuggingFace), API-based (OpenAI, Jina, etc.),
and vLLM-based embedding models.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Union

import numpy as np

from sage.kernel.api.service.base_service import BaseService
from sage.common.components.sage_embedding import EmbeddingFactory, EmbeddingRegistry


@dataclass
class EmbeddingServiceConfig:
    """Configuration for EmbeddingService."""

    method: str  # "hf", "openai", "jina", "vllm", etc.
    model: Optional[str] = None  # Model name/path
    api_key: Optional[str] = None  # API key for cloud services
    base_url: Optional[str] = None  # Custom API endpoint
    batch_size: int = 32  # Default batch size
    normalize: bool = True  # Normalize vectors
    cache_enabled: bool = False  # Enable embedding cache
    cache_size: int = 10000  # LRU cache size
    
    # Method-specific configs
    config: Dict[str, Any] = field(default_factory=dict)
    
    # vLLM-specific (if method == "vllm")
    vllm_service_name: Optional[str] = None  # Name of vLLM service to use
    vllm_auto_download: bool = False
    vllm_engine_config: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EmbeddingServiceConfig":
        """Create config from dictionary."""
        return cls(
            method=data["method"],
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
    - Local models (HuggingFace transformers)
    - API-based services (OpenAI, Jina, Zhipu, Cohere, etc.)
    - vLLM-powered embedding models (high performance)
    - Hash-based and mock embeddings (for testing)
    
    Examples:
        # In config:
        services:
          embedding:
            class: sage.common.components.sage_embedding.EmbeddingService
            config:
              method: "hf"
              model: "BAAI/bge-small-zh-v1.5"
              batch_size: 32
              normalize: true
        
        # In pipeline/operator:
        result = self.call_service("embedding", texts=["hello", "world"])
        vectors = result["vectors"]  # List[List[float]]
        
        # Using vLLM backend:
        services:
                    vllm:
                        class: sage.common.components.sage_vllm.VLLMService
            config:
              model_id: "BAAI/bge-base-en-v1.5"
              embedding_model_id: "BAAI/bge-base-en-v1.5"
          
          embedding:
            class: sage.common.components.sage_embedding.EmbeddingService
            config:
              method: "vllm"
              vllm_service_name: "vllm"
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__()
        self.config = EmbeddingServiceConfig.from_dict(config)
        self._embedder = None
        self._lock = threading.RLock()
        self._cache: Optional[Dict[str, List[float]]] = None
        self._dimension: Optional[int] = None

    # ------------------------------------------------------------------
    # SAGE lifecycle hooks
    # ------------------------------------------------------------------
    def setup(self) -> None:
        """Initialize the embedding service."""
        self.logger.info(f"EmbeddingService setup starting: method={self.config.method}")
        
        with self._lock:
            if self.config.method == "vllm":
                # Use vLLM service for embeddings
                if not self.config.vllm_service_name:
                    raise ValueError("vLLM method requires 'vllm_service_name' in config")
                self.logger.info(f"Using vLLM service: {self.config.vllm_service_name}")
                # Don't create embedder - will use service call
            else:
                # Create standard embedder
                kwargs = dict(self.config.config)
                if self.config.model:
                    kwargs["model"] = self.config.model
                if self.config.api_key:
                    kwargs["api_key"] = self.config.api_key
                if self.config.base_url:
                    kwargs["base_url"] = self.config.base_url
                
                self._embedder = EmbeddingFactory.create(self.config.method, **kwargs)
                self._dimension = self._embedder.get_dimension()
                self.logger.info(f"Embedding model loaded: dim={self._dimension}")
            
            # Setup cache if enabled
            if self.config.cache_enabled:
                from functools import lru_cache
                self._cache = {}
                self.logger.info(f"Embedding cache enabled: size={self.config.cache_size}")
        
        self.logger.info("EmbeddingService setup complete")

    def cleanup(self) -> None:
        """Clean up resources."""
        with self._lock:
            if self._embedder is not None:
                if hasattr(self._embedder, "cleanup"):
                    self._embedder.cleanup()
                self._embedder = None
            if self._cache is not None:
                self._cache.clear()
                self._cache = None
            self.logger.info("EmbeddingService cleanup complete")

    # ------------------------------------------------------------------
    # Public service API
    # ------------------------------------------------------------------
    def process(self, payload: Dict[str, Any]) -> Any:
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
        texts: Union[str, List[str]],
        *,
        normalize: Optional[bool] = None,
        batch_size: Optional[int] = None,
        return_stats: bool = False,
    ) -> Dict[str, Any]:
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
                "method": self.config.method,
                "model": self.config.model,
            }
        
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
            if self.config.method == "vllm":
                # Use vLLM service
                result = self.call_service(
                    self.config.vllm_service_name,
                    payload={
                        "task": "embed",
                        "inputs": uncached_texts,
                        "options": {
                            "normalize": normalize,
                            "batch_size": batch_size,
                        }
                    }
                )
                uncached_vectors = result["vectors"]
            else:
                # Use standard embedder
                uncached_vectors = []
                for i in range(0, len(uncached_texts), batch_size):
                    batch = uncached_texts[i:i + batch_size]
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
            
            # Update cache and results
            for idx, text, vec in zip(uncached_indices, uncached_texts, uncached_vectors):
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
        result = {
            "vectors": vectors,
            "dimension": len(vectors[0]) if vectors and vectors[0] else self.get_dimension(),
            "count": len(vectors),
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
        
        if self.config.method == "vllm":
            # Query vLLM service
            result = self.call_service(
                self.config.vllm_service_name,
                payload={"task": "embed", "inputs": "test"}
            )
            self._dimension = result.get("dimension", 768)
        elif self._embedder is not None:
            self._dimension = self._embedder.get_dimension()
        else:
            self._dimension = 768  # Default
        
        return self._dimension

    def get_info(self) -> Dict[str, Any]:
        """Get embedding service information."""
        info = {
            "method": self.config.method,
            "model": self.config.model,
            "dimension": self.get_dimension(),
            "batch_size": self.config.batch_size,
            "normalize": self.config.normalize,
            "cache_enabled": self.config.cache_enabled,
        }
        
        if self.config.cache_enabled and self._cache is not None:
            info["cache_stats"] = {
                "size": len(self._cache),
                "capacity": self.config.cache_size,
            }
        
        if self.config.method == "vllm":
            info["vllm_service"] = self.config.vllm_service_name
        
        return info

    def list_methods(self) -> List[Dict[str, Any]]:
        """List all available embedding methods."""
        methods = []
        for method in EmbeddingRegistry.list_methods():
            info = EmbeddingRegistry.get_model_info(method)
            if info:
                methods.append({
                    "name": method,
                    "description": info.description,
                    "requires_api_key": info.requires_api_key,
                    "requires_model_download": info.requires_model_download,
                    "status": info.status.value,
                })
        
        # Add vLLM method
        methods.append({
            "name": "vllm",
            "description": "High-performance vLLM embedding service",
            "requires_api_key": False,
            "requires_model_download": True,
            "status": "available",
        })
        
        return methods

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _normalize_vector(self, vec: List[float]) -> List[float]:
        """Normalize a vector to unit length."""
        array = np.array(vec, dtype=np.float32)
        norm = np.linalg.norm(array)
        if norm > 0:
            array = array / norm
        return array.tolist()


__all__ = ["EmbeddingService", "EmbeddingServiceConfig"]
