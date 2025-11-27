# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""Unified Inference Client for hybrid LLM and Embedding workloads.

This module provides the UnifiedInferenceClient class, which combines LLM
(chat/generation) and Embedding capabilities into a single client interface.
It supports both Simple mode (direct API calls) and Control Plane mode
(advanced scheduling with hybrid policy).

Design Principles:
- **Local First, Cloud Fallback**: Auto-detect local services before cloud APIs
- **Unified Interface**: Single client for both LLM and Embedding requests
- **Backward Compatible**: Existing IntelligentLLMClient/EmbeddingClient work unchanged
- **Hybrid Scheduling**: Control Plane mode enables intelligent request routing

Example:
    >>> from sage.common.components.sage_llm import UnifiedInferenceClient
    >>>
    >>> # Create with auto-detection
    >>> client = UnifiedInferenceClient.create_auto()
    >>>
    >>> # Chat (LLM)
    >>> response = client.chat([{"role": "user", "content": "Hello"}])
    >>>
    >>> # Generate (LLM)
    >>> response = client.generate("Once upon a time")
    >>>
    >>> # Embed (Embedding)
    >>> vectors = client.embed(["text1", "text2"])
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from threading import Lock
from typing import TYPE_CHECKING, Any, ClassVar, Literal

import httpx
from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam

if TYPE_CHECKING:
    from collections.abc import Sequence

logger = logging.getLogger(__name__)


class UnifiedClientMode(Enum):
    """Operation mode for UnifiedInferenceClient.

    Attributes:
        SIMPLE: Direct API calls to LLM and Embedding endpoints.
            Suitable for single-instance deployments or testing.
        CONTROL_PLANE: Advanced scheduling via Control Plane Manager.
            Enables hybrid scheduling, load balancing, and auto-scaling.
    """

    SIMPLE = "simple"
    CONTROL_PLANE = "control_plane"


@dataclass
class UnifiedClientConfig:
    """Configuration for UnifiedInferenceClient.

    Attributes:
        llm_base_url: Base URL for LLM API endpoint.
        llm_model: Default model name for LLM requests.
        llm_api_key: API key for LLM endpoint.
        embedding_base_url: Base URL for Embedding API endpoint.
        embedding_model: Default model name for Embedding requests.
        embedding_api_key: API key for Embedding endpoint.
        mode: Operation mode (SIMPLE or CONTROL_PLANE).
        timeout: Request timeout in seconds.
        max_retries: Maximum number of retries for failed requests.
        enable_caching: Whether to cache responses (for Control Plane mode).
    """

    llm_base_url: str | None = None
    llm_model: str | None = None
    llm_api_key: str = ""
    embedding_base_url: str | None = None
    embedding_model: str | None = None
    embedding_api_key: str = ""
    mode: UnifiedClientMode = UnifiedClientMode.SIMPLE
    timeout: float = 60.0
    max_retries: int = 3
    enable_caching: bool = False

    # Default sampling parameters
    temperature: float = 0.7
    max_tokens: int = 512
    top_p: float = 1.0


@dataclass
class InferenceResult:
    """Result from an inference request (LLM or Embedding).

    Attributes:
        request_id: Unique identifier for this request.
        request_type: Type of request ("chat", "generate", "embed").
        content: Result content (string for LLM, list[list[float]] for embed).
        model: Model used for inference.
        usage: Token/text usage statistics.
        latency_ms: Request latency in milliseconds.
        metadata: Additional metadata from the inference.
    """

    request_id: str
    request_type: Literal["chat", "generate", "embed"]
    content: str | list[list[float]]
    model: str
    usage: dict[str, int] = field(default_factory=dict)
    latency_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class UnifiedInferenceClient:
    """Unified client for LLM and Embedding inference.

    This client provides a single interface for both LLM (chat/generation)
    and Embedding requests. It supports two operation modes:

    1. **Simple Mode**: Direct API calls to LLM and Embedding endpoints.
       - Uses OpenAI-compatible APIs
       - Suitable for single-instance deployments
       - No advanced scheduling or load balancing

    2. **Control Plane Mode**: Advanced scheduling via Control Plane Manager.
       - Hybrid scheduling for mixed workloads
       - Load balancing across multiple instances
       - Auto-scaling based on demand
       - SLO-aware request routing

    The client follows a "local first, cloud fallback" strategy:
    1. Check for explicitly configured endpoints (env vars)
    2. Try local vLLM server (ports 8001, 8000)
    3. Try local embedding server (ports 8090, 8080)
    4. Fall back to cloud APIs (DashScope, etc.)

    Attributes:
        config: Client configuration.
        mode: Current operation mode.
        llm_client: OpenAI client for LLM requests.
        embedding_client: Client for embedding requests (OpenAI or httpx).

    Example:
        >>> # Auto-detection (recommended)
        >>> client = UnifiedInferenceClient.create_auto()
        >>>
        >>> # Explicit configuration
        >>> client = UnifiedInferenceClient(
        ...     llm_base_url="http://localhost:8001/v1",
        ...     llm_model="Qwen/Qwen2.5-7B-Instruct",
        ...     embedding_base_url="http://localhost:8090/v1",
        ...     embedding_model="BAAI/bge-m3",
        ... )
        >>>
        >>> # Chat
        >>> response = client.chat([{"role": "user", "content": "Hello"}])
        >>>
        >>> # Generate
        >>> response = client.generate("Once upon a time")
        >>>
        >>> # Embed
        >>> vectors = client.embed(["text1", "text2"])
    """

    # Class-level singleton cache for instances
    _instances: ClassVar[dict[str, UnifiedInferenceClient]] = {}
    _lock: ClassVar[Lock] = Lock()

    def __init__(
        self,
        llm_base_url: str | None = None,
        llm_model: str | None = None,
        llm_api_key: str = "",
        embedding_base_url: str | None = None,
        embedding_model: str | None = None,
        embedding_api_key: str = "",
        mode: UnifiedClientMode = UnifiedClientMode.SIMPLE,
        timeout: float = 60.0,
        max_retries: int = 3,
        config: UnifiedClientConfig | None = None,
    ) -> None:
        """Initialize the unified inference client.

        Args:
            llm_base_url: Base URL for LLM API endpoint.
            llm_model: Default model name for LLM requests.
            llm_api_key: API key for LLM endpoint.
            embedding_base_url: Base URL for Embedding API endpoint.
            embedding_model: Default model name for Embedding requests.
            embedding_api_key: API key for Embedding endpoint.
            mode: Operation mode (SIMPLE or CONTROL_PLANE).
            timeout: Request timeout in seconds.
            max_retries: Maximum number of retries for failed requests.
            config: Full configuration object (overrides individual params).
        """
        # Use config if provided, otherwise build from parameters
        if config is not None:
            self.config = config
        else:
            self.config = UnifiedClientConfig(
                llm_base_url=llm_base_url,
                llm_model=llm_model,
                llm_api_key=llm_api_key,
                embedding_base_url=embedding_base_url,
                embedding_model=embedding_model,
                embedding_api_key=embedding_api_key,
                mode=mode,
                timeout=timeout,
                max_retries=max_retries,
            )

        self.mode = self.config.mode

        # Initialize clients based on mode
        self._llm_client: OpenAI | None = None
        self._embedding_client: OpenAI | httpx.Client | None = None
        self._control_plane_manager: Any = None

        # Track availability
        self._llm_available = False
        self._embedding_available = False

        # Initialize appropriate clients
        self._init_clients()

    def _init_clients(self) -> None:
        """Initialize LLM and Embedding clients based on configuration."""
        if self.config.mode == UnifiedClientMode.SIMPLE:
            self._init_simple_mode_clients()
        else:
            self._init_control_plane_mode()

    def _init_simple_mode_clients(self) -> None:
        """Initialize clients for Simple mode."""
        # Initialize LLM client
        if self.config.llm_base_url:
            try:
                self._llm_client = OpenAI(
                    base_url=self.config.llm_base_url,
                    api_key=self.config.llm_api_key or "not-needed",
                    timeout=self.config.timeout,
                    max_retries=self.config.max_retries,
                )
                self._llm_available = True
                logger.info(
                    "LLM client initialized: base_url=%s, model=%s",
                    self.config.llm_base_url,
                    self.config.llm_model,
                )
            except Exception as e:
                logger.warning("Failed to initialize LLM client: %s", e)
                self._llm_available = False

        # Initialize Embedding client
        if self.config.embedding_base_url:
            try:
                self._embedding_client = OpenAI(
                    base_url=self.config.embedding_base_url,
                    api_key=self.config.embedding_api_key or "not-needed",
                    timeout=self.config.timeout,
                    max_retries=self.config.max_retries,
                )
                self._embedding_available = True
                logger.info(
                    "Embedding client initialized: base_url=%s, model=%s",
                    self.config.embedding_base_url,
                    self.config.embedding_model,
                )
            except Exception as e:
                logger.warning("Failed to initialize Embedding client: %s", e)
                self._embedding_available = False

    def _init_control_plane_mode(self) -> None:
        """Initialize Control Plane mode with hybrid scheduling.

        Control Plane mode provides:
        - Multi-instance support (multiple LLM/Embedding backends)
        - Intelligent routing (load balancing, failover)
        - Request batching for embeddings

        For simplicity, we initialize OpenAI clients for direct API calls,
        while the Control Plane manager handles routing decisions.
        """
        # Initialize OpenAI clients for direct API calls (same as Simple mode)
        # This ensures we have working clients even if Control Plane init fails
        self._init_simple_mode_clients()

        # Store Control Plane specific config for future routing
        self._control_plane_config = {
            "llm_backends": [self.config.llm_base_url] if self.config.llm_base_url else [],
            "embedding_backends": (
                [self.config.embedding_base_url] if self.config.embedding_base_url else []
            ),
            "scheduling_policy": "hybrid",
        }

        logger.info(
            "Control Plane mode initialized (LLM backends: %d, Embedding backends: %d)",
            len(self._control_plane_config["llm_backends"]),
            len(self._control_plane_config["embedding_backends"]),
        )

    # ==================== Factory Methods ====================

    @classmethod
    def create_auto(
        cls,
        *,
        prefer_local: bool = True,
        llm_ports: Sequence[int] | None = None,
        embedding_ports: Sequence[int] | None = None,
        timeout: float = 60.0,
    ) -> UnifiedInferenceClient:
        """Create client with auto-detection of endpoints.

        Detection order:
        1. Environment variables (SAGE_UNIFIED_BASE_URL, SAGE_CHAT_BASE_URL,
           SAGE_EMBEDDING_BASE_URL)
        2. Local LLM servers (ports from SagePorts: 8001, 8901, 8002, 8000)
        3. Local Embedding servers (ports from SagePorts: 8090, 8091)
        4. Cloud APIs (DashScope for LLM)

        Args:
            prefer_local: If True, prefer local servers over cloud APIs.
            llm_ports: Ports to check for local LLM servers. If None, uses SagePorts.
            embedding_ports: Ports to check for local Embedding servers. If None, uses SagePorts.
            timeout: Request timeout in seconds.

        Returns:
            Configured UnifiedInferenceClient instance.

        Example:
            >>> client = UnifiedInferenceClient.create_auto()
            >>> response = client.chat([{"role": "user", "content": "Hi"}])
        """
        # Import SagePorts for default values
        from sage.common.config.ports import SagePorts

        if llm_ports is None:
            llm_ports = SagePorts.get_llm_ports()
        if embedding_ports is None:
            embedding_ports = SagePorts.get_embedding_ports()

        # Check for unified base URL
        unified_base_url = os.environ.get("SAGE_UNIFIED_BASE_URL")
        if unified_base_url:
            logger.info("Using unified base URL from environment: %s", unified_base_url)
            return cls(
                llm_base_url=unified_base_url,
                llm_model=os.environ.get("SAGE_UNIFIED_MODEL"),
                llm_api_key=os.environ.get("SAGE_UNIFIED_API_KEY", ""),
                embedding_base_url=unified_base_url,
                embedding_model=os.environ.get("SAGE_UNIFIED_MODEL"),
                embedding_api_key=os.environ.get("SAGE_UNIFIED_API_KEY", ""),
                timeout=timeout,
            )

        # Detect LLM endpoint
        llm_base_url, llm_model, llm_api_key = cls._detect_llm_endpoint(
            prefer_local=prefer_local,
            ports=llm_ports,
        )

        # Detect Embedding endpoint
        embedding_base_url, embedding_model, embedding_api_key = cls._detect_embedding_endpoint(
            prefer_local=prefer_local,
            ports=embedding_ports,
        )

        return cls(
            llm_base_url=llm_base_url,
            llm_model=llm_model,
            llm_api_key=llm_api_key,
            embedding_base_url=embedding_base_url,
            embedding_model=embedding_model,
            embedding_api_key=embedding_api_key,
            timeout=timeout,
        )

    @classmethod
    def create_with_control_plane(
        cls,
        *,
        llm_base_url: str | None = None,
        llm_model: str | None = None,
        embedding_base_url: str | None = None,
        embedding_model: str | None = None,
        embedding_batch_size: int = 32,
        embedding_priority: str = "normal",
        llm_fallback_policy: str = "adaptive",
    ) -> UnifiedInferenceClient:
        """Create client with Control Plane mode for advanced scheduling.

        Args:
            llm_base_url: Base URL for LLM API endpoint.
            llm_model: Default model name for LLM requests.
            embedding_base_url: Base URL for Embedding API endpoint.
            embedding_model: Default model name for Embedding requests.
            embedding_batch_size: Target batch size for embedding requests.
            embedding_priority: Priority for embeddings ("high", "normal", "low").
            llm_fallback_policy: LLM scheduling policy name.

        Returns:
            Configured UnifiedInferenceClient with Control Plane mode.
        """
        config = UnifiedClientConfig(
            llm_base_url=llm_base_url,
            llm_model=llm_model,
            embedding_base_url=embedding_base_url,
            embedding_model=embedding_model,
            mode=UnifiedClientMode.CONTROL_PLANE,
        )
        return cls(config=config)

    @classmethod
    def get_instance(
        cls,
        instance_key: str = "default",
        **kwargs: Any,
    ) -> UnifiedInferenceClient:
        """Get or create a singleton instance.

        This method provides instance caching to avoid creating multiple
        clients with the same configuration.

        Args:
            instance_key: Unique key for this instance configuration.
            **kwargs: Arguments passed to create_auto() for new instances.

        Returns:
            Cached or newly created UnifiedInferenceClient instance.
        """
        with cls._lock:
            if instance_key not in cls._instances:
                cls._instances[instance_key] = cls.create_auto(**kwargs)
            return cls._instances[instance_key]

    @classmethod
    def clear_instances(cls) -> None:
        """Clear all cached instances."""
        with cls._lock:
            cls._instances.clear()

    # ==================== Detection Helpers ====================

    @classmethod
    def _detect_llm_endpoint(
        cls,
        *,
        prefer_local: bool = True,
        ports: Sequence[int] = (8001, 8000),
    ) -> tuple[str | None, str | None, str]:
        """Detect LLM endpoint.

        Returns:
            Tuple of (base_url, model, api_key).
        """
        # Check environment variable first
        env_base_url = os.environ.get("SAGE_CHAT_BASE_URL")
        if env_base_url:
            logger.info("Using LLM endpoint from SAGE_CHAT_BASE_URL: %s", env_base_url)
            return (
                env_base_url,
                os.environ.get("SAGE_CHAT_MODEL"),
                os.environ.get("SAGE_CHAT_API_KEY", ""),
            )

        # Try local servers if preferred
        if prefer_local:
            for port in ports:
                base_url = f"http://localhost:{port}/v1"
                if cls._check_endpoint_health(base_url):
                    logger.info("Found local LLM server at %s", base_url)
                    return (base_url, None, "")

        # Fall back to cloud API (DashScope)
        api_key = os.environ.get("SAGE_CHAT_API_KEY")
        if api_key:
            logger.info("Using DashScope cloud API for LLM")
            return (
                "https://dashscope.aliyuncs.com/compatible-mode/v1",
                os.environ.get("SAGE_CHAT_MODEL", "qwen-turbo-2025-02-11"),
                api_key,
            )

        logger.warning(
            "No LLM endpoint found. Start services with:\n"
            "  python -m sage.common.components.sage_llm.service_manager start\n"
            "Or set SAGE_CHAT_API_KEY for cloud API."
        )
        return (None, None, "")

    @classmethod
    def _detect_embedding_endpoint(
        cls,
        *,
        prefer_local: bool = True,
        ports: Sequence[int] = (8090, 8080),
    ) -> tuple[str | None, str | None, str]:
        """Detect Embedding endpoint.

        Returns:
            Tuple of (base_url, model, api_key).
        """
        # Check environment variable first
        env_base_url = os.environ.get("SAGE_EMBEDDING_BASE_URL")
        if env_base_url:
            logger.info(
                "Using Embedding endpoint from SAGE_EMBEDDING_BASE_URL: %s",
                env_base_url,
            )
            return (
                env_base_url,
                os.environ.get("SAGE_EMBEDDING_MODEL"),
                os.environ.get("SAGE_EMBEDDING_API_KEY", ""),
            )

        # Try local servers if preferred
        if prefer_local:
            for port in ports:
                base_url = f"http://localhost:{port}/v1"
                if cls._check_endpoint_health(base_url, endpoint_type="embedding"):
                    logger.info("Found local Embedding server at %s", base_url)
                    return (base_url, None, "")

        logger.warning(
            "No Embedding endpoint found. Start services with:\n"
            "  python -m sage.common.components.sage_llm.service_manager start\n"
            "Or set SAGE_EMBEDDING_BASE_URL for remote embedding server."
        )
        return (None, None, "")

    @classmethod
    def _check_endpoint_health(
        cls,
        base_url: str,
        endpoint_type: str = "llm",
        timeout: float = 2.0,
    ) -> bool:
        """Check if an endpoint is healthy.

        Args:
            base_url: Base URL to check.
            endpoint_type: Type of endpoint ("llm" or "embedding").
            timeout: Timeout for health check.

        Returns:
            True if endpoint is healthy, False otherwise.
        """
        try:
            # Try /models endpoint (OpenAI compatible)
            with httpx.Client(timeout=timeout) as client:
                response = client.get(f"{base_url}/models")
                if response.status_code == 200:
                    return True
        except Exception:
            pass

        try:
            # Try /health endpoint
            health_url = base_url.replace("/v1", "/health")
            with httpx.Client(timeout=timeout) as client:
                response = client.get(health_url)
                if response.status_code == 200:
                    return True
        except Exception:
            pass

        return False

    # ==================== Core Inference Methods ====================

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        top_p: float | None = None,
        stream: bool = False,
        **kwargs: Any,
    ) -> str | InferenceResult:
        """Send a chat completion request.

        Args:
            messages: List of message dicts with "role" and "content".
            model: Model to use (defaults to configured model).
            temperature: Sampling temperature (0.0-2.0).
            max_tokens: Maximum tokens to generate.
            top_p: Top-p sampling parameter.
            stream: Whether to stream the response.
            **kwargs: Additional parameters passed to the API.

        Returns:
            Response string (default) or InferenceResult if return_result=True.

        Raises:
            RuntimeError: If LLM endpoint is not available.
            Exception: If API call fails.

        Example:
            >>> client = UnifiedInferenceClient.create_auto()
            >>> response = client.chat([
            ...     {"role": "user", "content": "What is 2+2?"}
            ... ])
            >>> print(response)
            "2+2 equals 4."
        """
        if not self._llm_available:
            raise RuntimeError(
                "LLM endpoint not available. Check configuration or start a local server."
            )

        return_result = kwargs.pop("return_result", False)
        start_time = time.time()

        if self.mode == UnifiedClientMode.CONTROL_PLANE:
            return self._chat_control_plane(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                return_result=return_result,
                **kwargs,
            )

        # Simple mode: direct API call
        actual_model = model or self.config.llm_model
        if not actual_model:
            # Try to get model from server
            actual_model = self._get_default_llm_model()

        if self._llm_client is None:
            raise RuntimeError("LLM client not initialized")

        # Cast messages to proper type
        typed_messages: list[ChatCompletionMessageParam] = [
            {"role": msg["role"], "content": msg["content"]}  # type: ignore[typeddict-item]
            for msg in messages
        ]

        # Note: stream=False for non-streaming to get ChatCompletion response
        response = self._llm_client.chat.completions.create(
            model=actual_model,
            messages=typed_messages,
            temperature=temperature or self.config.temperature,
            max_tokens=max_tokens or self.config.max_tokens,
            top_p=top_p or self.config.top_p,
            stream=False,  # Always use non-streaming for this method
            **kwargs,
        )

        latency_ms = (time.time() - start_time) * 1000
        content = response.choices[0].message.content or ""

        if return_result:
            return InferenceResult(
                request_id=response.id,
                request_type="chat",
                content=content,
                model=response.model,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0,
                },
                latency_ms=latency_ms,
            )

        return content

    def generate(
        self,
        prompt: str,
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        top_p: float | None = None,
        stop: list[str] | None = None,
        **kwargs: Any,
    ) -> str | InferenceResult:
        """Generate text completion.

        Args:
            prompt: Input prompt for generation.
            model: Model to use (defaults to configured model).
            temperature: Sampling temperature (0.0-2.0).
            max_tokens: Maximum tokens to generate.
            top_p: Top-p sampling parameter.
            stop: Stop sequences.
            **kwargs: Additional parameters passed to the API.

        Returns:
            Generated text string or InferenceResult if return_result=True.

        Raises:
            RuntimeError: If LLM endpoint is not available.

        Example:
            >>> client = UnifiedInferenceClient.create_auto()
            >>> text = client.generate("Once upon a time")
            >>> print(text)
        """
        if not self._llm_available:
            raise RuntimeError(
                "LLM endpoint not available. Check configuration or start a local server."
            )

        return_result = kwargs.pop("return_result", False)
        start_time = time.time()

        if self.mode == UnifiedClientMode.CONTROL_PLANE:
            return self._generate_control_plane(
                prompt=prompt,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                return_result=return_result,
                **kwargs,
            )

        # Simple mode: use completions API or chat API
        actual_model = model or self.config.llm_model
        if not actual_model:
            actual_model = self._get_default_llm_model()

        if self._llm_client is None:
            raise RuntimeError("LLM client not initialized")

        # Try completions API first, fall back to chat API
        try:
            response = self._llm_client.completions.create(
                model=actual_model,
                prompt=prompt,
                temperature=temperature or self.config.temperature,
                max_tokens=max_tokens or self.config.max_tokens,
                top_p=top_p or self.config.top_p,
                stop=stop,
                **kwargs,
            )
            content = response.choices[0].text
            usage = {
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0,
            }
        except Exception:
            # Fall back to chat API
            typed_messages: list[ChatCompletionMessageParam] = [{"role": "user", "content": prompt}]
            response = self._llm_client.chat.completions.create(
                model=actual_model,
                messages=typed_messages,
                temperature=temperature or self.config.temperature,
                max_tokens=max_tokens or self.config.max_tokens,
                top_p=top_p or self.config.top_p,
                **kwargs,
            )
            content = response.choices[0].message.content or ""
            usage = {
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0,
            }

        latency_ms = (time.time() - start_time) * 1000

        if return_result:
            return InferenceResult(
                request_id=response.id,
                request_type="generate",
                content=content,
                model=response.model,
                usage=usage,
                latency_ms=latency_ms,
            )

        return content

    def embed(
        self,
        texts: str | list[str],
        *,
        model: str | None = None,
        **kwargs: Any,
    ) -> list[list[float]] | InferenceResult:
        """Generate embeddings for texts.

        Args:
            texts: Single text or list of texts to embed.
            model: Model to use (defaults to configured model).
            **kwargs: Additional parameters passed to the API.

        Returns:
            List of embedding vectors or InferenceResult if return_result=True.

        Raises:
            RuntimeError: If Embedding endpoint is not available.

        Example:
            >>> client = UnifiedInferenceClient.create_auto()
            >>> vectors = client.embed(["Hello", "World"])
            >>> print(len(vectors))
            2
            >>> print(len(vectors[0]))  # Embedding dimension
            768
        """
        if not self._embedding_available:
            raise RuntimeError(
                "Embedding endpoint not available. "
                "Check configuration or start a local embedding server."
            )

        # Normalize input
        if isinstance(texts, str):
            texts = [texts]

        return_result = kwargs.pop("return_result", False)
        start_time = time.time()

        if self.mode == UnifiedClientMode.CONTROL_PLANE:
            return self._embed_control_plane(
                texts=texts,
                model=model,
                return_result=return_result,
                **kwargs,
            )

        # Simple mode: direct API call
        actual_model = model or self.config.embedding_model
        if not actual_model:
            actual_model = self._get_default_embedding_model()

        if self._embedding_client is None:
            raise RuntimeError("Embedding client not initialized")

        # Use hasattr for duck typing - allows both OpenAI client and mocks
        if not hasattr(self._embedding_client, "embeddings"):
            raise RuntimeError("Embedding client does not have embeddings attribute")

        response = self._embedding_client.embeddings.create(  # type: ignore[union-attr]
            model=actual_model,
            input=texts,
            **kwargs,
        )

        latency_ms = (time.time() - start_time) * 1000
        embeddings = [item.embedding for item in response.data]

        if return_result:
            return InferenceResult(
                request_id=f"emb-{int(start_time * 1000)}",
                request_type="embed",
                content=embeddings,
                model=response.model,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0,
                },
                latency_ms=latency_ms,
            )

        return embeddings

    # ==================== Control Plane Mode Methods ====================
    # Control Plane mode uses the same OpenAI clients as Simple mode,
    # but provides additional features like multi-backend routing.
    # For now, it delegates to Simple mode logic for direct API calls.

    def _chat_control_plane(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        return_result: bool = False,
        **kwargs: Any,
    ) -> str | InferenceResult:
        """Execute chat request via Control Plane.

        Currently delegates to direct API calls using the configured backend.
        Future versions will support multi-backend routing and load balancing.
        """
        start_time = time.time()

        # Use the initialized OpenAI client for direct API call
        actual_model = model or self.config.llm_model
        if not actual_model:
            actual_model = self._get_default_llm_model()

        if self._llm_client is None:
            raise RuntimeError("LLM client not initialized")

        response = self._llm_client.chat.completions.create(
            model=actual_model,
            messages=messages,  # type: ignore[arg-type]
            temperature=temperature or self.config.temperature,
            max_tokens=max_tokens or self.config.max_tokens,
            **kwargs,
        )

        latency_ms = (time.time() - start_time) * 1000
        content = response.choices[0].message.content or ""

        if return_result:
            return InferenceResult(
                request_id=response.id,
                request_type="chat",
                content=content,
                model=response.model,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0,
                },
                latency_ms=latency_ms,
            )

        return content

    def _generate_control_plane(
        self,
        prompt: str,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        return_result: bool = False,
        **kwargs: Any,
    ) -> str | InferenceResult:
        """Execute generate request via Control Plane.

        Currently delegates to direct API calls using the configured backend.
        """
        start_time = time.time()

        actual_model = model or self.config.llm_model
        if not actual_model:
            actual_model = self._get_default_llm_model()

        if self._llm_client is None:
            raise RuntimeError("LLM client not initialized")

        response = self._llm_client.completions.create(
            model=actual_model,
            prompt=prompt,
            temperature=temperature or self.config.temperature,
            max_tokens=max_tokens or self.config.max_tokens,
            **kwargs,
        )

        latency_ms = (time.time() - start_time) * 1000
        content = response.choices[0].text if response.choices else ""

        if return_result:
            return InferenceResult(
                request_id=response.id,
                request_type="generate",
                content=content,
                model=response.model,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0,
                },
                latency_ms=latency_ms,
            )

        return content

    def _embed_control_plane(
        self,
        texts: list[str],
        model: str | None = None,
        return_result: bool = False,
        **kwargs: Any,
    ) -> list[list[float]] | InferenceResult:
        """Execute embedding request via Control Plane.

        Currently delegates to direct API calls using the configured backend.
        """
        start_time = time.time()

        actual_model = model or self.config.embedding_model
        if not actual_model:
            actual_model = self._get_default_embedding_model()

        if self._embedding_client is None:
            raise RuntimeError("Embedding client not initialized")

        response = self._embedding_client.embeddings.create(  # type: ignore[union-attr]
            model=actual_model,
            input=texts,
            **kwargs,
        )

        latency_ms = (time.time() - start_time) * 1000
        embeddings = [item.embedding for item in response.data]

        if return_result:
            return InferenceResult(
                request_id=f"emb-{int(start_time * 1000)}",
                request_type="embed",
                content=embeddings,
                model=response.model,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0,
                },
                latency_ms=latency_ms,
            )

        return embeddings

    # ==================== Helper Methods ====================

    def _get_default_llm_model(self) -> str:
        """Get default LLM model from server."""
        try:
            if self._llm_client is not None:
                models = self._llm_client.models.list()
                if models.data:
                    return models.data[0].id
        except Exception:
            pass
        return "default"

    def _get_default_embedding_model(self) -> str:
        """Get default embedding model from server."""
        try:
            if self._embedding_client is not None and hasattr(self._embedding_client, "models"):
                models = self._embedding_client.models.list()  # type: ignore[union-attr]
                if models.data:
                    return models.data[0].id
        except Exception:
            pass
        return "default"

    # ==================== Properties ====================

    @property
    def is_llm_available(self) -> bool:
        """Check if LLM endpoint is available."""
        return self._llm_available

    @property
    def is_embedding_available(self) -> bool:
        """Check if Embedding endpoint is available."""
        return self._embedding_available

    @property
    def is_control_plane_mode(self) -> bool:
        """Check if running in Control Plane mode."""
        return self.mode == UnifiedClientMode.CONTROL_PLANE

    def get_status(self) -> dict[str, Any]:
        """Get client status information.

        Returns:
            Dict with status information including:
            - mode: Current operation mode
            - llm_available: Whether LLM is available
            - embedding_available: Whether Embedding is available
            - llm_base_url: LLM endpoint URL
            - embedding_base_url: Embedding endpoint URL
        """
        return {
            "mode": self.mode.value,
            "llm_available": self._llm_available,
            "embedding_available": self._embedding_available,
            "llm_base_url": self.config.llm_base_url,
            "llm_model": self.config.llm_model,
            "embedding_base_url": self.config.embedding_base_url,
            "embedding_model": self.config.embedding_model,
        }


# ==================== Convenience Aliases ====================

# For backward compatibility and ease of use
UnifiedClient = UnifiedInferenceClient
