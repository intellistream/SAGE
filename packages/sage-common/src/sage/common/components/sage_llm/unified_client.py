# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""Unified Inference Client for hybrid LLM and Embedding workloads.

This module provides the UnifiedInferenceClient class, which combines LLM
(chat/generation) and Embedding capabilities into a single client interface.
All requests are managed through the Control Plane for intelligent scheduling.

Design Principles:
- **Control Plane First**: All requests go through Control Plane for unified management
- **Unified Interface**: Single client for both LLM and Embedding requests
- **Single Entry Point**: Use `create()` as the only way to instantiate the client
- **Hybrid Scheduling**: Intelligent request routing and load balancing

Example:
    >>> from sage.common.components.sage_llm import UnifiedInferenceClient
    >>>
    >>> # Create with auto-detection (recommended)
    >>> client = UnifiedInferenceClient.create()
    >>>
    >>> # Create connecting to external Control Plane
    >>> client = UnifiedInferenceClient.create(control_plane_url="http://localhost:8000/v1")
    >>>
    >>> # Create with embedded Control Plane
    >>> client = UnifiedInferenceClient.create(embedded=True)
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

import atexit
import importlib
import logging
import os
import time
from dataclasses import dataclass, field
from threading import Event, Lock, Thread
from typing import TYPE_CHECKING, Any, ClassVar, Literal

import httpx
from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam

# 抑制 httpx 的 INFO 日志（每次 HTTP 请求都会打印，非常吵）
logging.getLogger("httpx").setLevel(logging.WARNING)

if TYPE_CHECKING:
    from collections.abc import Sequence

logger = logging.getLogger(__name__)


class UnifiedClientMode:
    """Operation mode for UnifiedInferenceClient.

    Note: This class is kept for backward compatibility but only CONTROL_PLANE
    mode is supported. All requests go through Control Plane for unified management.

    Attributes:
        CONTROL_PLANE: Advanced scheduling via Control Plane Manager.
            Enables hybrid scheduling, load balancing, and auto-scaling.
    """

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
        timeout: Request timeout in seconds.
        max_retries: Maximum number of retries for failed requests.
        enable_caching: Whether to cache responses.
    """

    llm_base_url: str | None = None
    llm_model: str | None = None
    llm_api_key: str = ""
    embedding_base_url: str | None = None
    embedding_model: str | None = None
    embedding_api_key: str = ""
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
    and Embedding requests. All requests are managed through the Control Plane
    for intelligent scheduling, load balancing, and resource management.

    **IMPORTANT**: Use `create()` as the only entry point to instantiate this client.
    Direct instantiation via `__init__` is not supported.

    Features:
    - Intelligent request routing via Control Plane
    - Multi-instance support (multiple LLM/Embedding backends)
    - Load balancing across instances
    - Auto-scaling based on demand
    - SLO-aware request routing

    The client follows a "local first, cloud fallback" strategy:
    1. Check for explicitly configured endpoints (env vars)
    2. Try local vLLM server (ports from SagePorts)
    3. Try local embedding server (ports from SagePorts)
    4. Fall back to cloud APIs (DashScope, etc.)

    Attributes:
        config: Client configuration.
        llm_client: OpenAI client for LLM requests.
        embedding_client: Client for embedding requests.

    Example:
        >>> # Auto-detection (recommended)
        >>> client = UnifiedInferenceClient.create()
        >>>
        >>> # Connect to external Control Plane
        >>> client = UnifiedInferenceClient.create(
        ...     control_plane_url="http://localhost:8000/v1"
        ... )
        >>>
        >>> # Embedded Control Plane mode
        >>> client = UnifiedInferenceClient.create(embedded=True)
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
        timeout: float = 60.0,
        max_retries: int = 3,
        config: UnifiedClientConfig | None = None,
    ) -> None:
        """Initialize the unified inference client.

        NOTE: For UnifiedInferenceClient itself, use `create()` to instantiate.
        Subclasses can be instantiated directly.

        Args:
            llm_base_url: Base URL for LLM API endpoint.
            llm_model: Default model name for LLM requests.
            llm_api_key: API key for LLM endpoint.
            embedding_base_url: Base URL for Embedding API endpoint.
            embedding_model: Default model name for Embedding requests.
            embedding_api_key: API key for Embedding endpoint.
            timeout: Request timeout in seconds.
            max_retries: Maximum number of retries for failed requests.
            config: Full configuration object (overrides individual params).

        Raises:
            RuntimeError: If UnifiedInferenceClient is instantiated directly
                instead of via create(). Subclasses are allowed.
        """
        # Only block direct instantiation of UnifiedInferenceClient itself.
        # Subclasses (like LLMClientAdapter, EmbeddingClientAdapter) are allowed.
        if type(self) is UnifiedInferenceClient:
            raise RuntimeError(
                "UnifiedInferenceClient cannot be instantiated directly. "
                "Use UnifiedInferenceClient.create() instead."
            )
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
                timeout=timeout,
                max_retries=max_retries,
            )

        # Initialize clients based on mode
        self._llm_client: OpenAI | None = None
        self._embedding_client: OpenAI | httpx.Client | None = None
        self._control_plane_manager: Any = None
        self._control_plane_policy: Any = None

        # Track availability
        self._llm_available = False
        self._embedding_available = False

        # Backend discovery configuration
        self._management_base_url: str | None = None
        self._backend_refresh_interval: float = 30.0  # seconds
        self._backend_refresh_enabled: bool = False

        # Multi-backend support for failover
        self._llm_backends: list[dict[str, Any]] = []
        self._embedding_backends: list[dict[str, Any]] = []
        self._backends_lock = Lock()

        # Background refresh thread
        self._refresh_thread: Thread | None = None
        self._refresh_stop_event = Event()

        # Initialize Control Plane mode
        self._init_control_plane_mode()

    def _init_clients(self) -> None:
        """Initialize LLM and Embedding clients for API calls."""
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
        - Unified management of all inference requests
        """
        # Initialize OpenAI clients for direct API calls
        self._init_clients()

        # Store Control Plane specific config for future routing
        self._control_plane_config = {
            "llm_backends": [self.config.llm_base_url] if self.config.llm_base_url else [],
            "embedding_backends": (
                [self.config.embedding_base_url] if self.config.embedding_base_url else []
            ),
            "scheduling_policy": "hybrid",
        }

        try:
            manager_module = importlib.import_module(
                "sage.common.components.sage_llm.sageLLM.control_plane.manager"
            )
            policy_module = importlib.import_module(
                "sage.common.components.sage_llm.sageLLM.control_plane.strategies.hybrid_policy"
            )

            control_plane_manager_cls = manager_module.ControlPlaneManager
            hybrid_policy_cls = policy_module.HybridSchedulingPolicy
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Control Plane dependencies unavailable: %s. "
                "Client will still work but without advanced scheduling.",
                exc,
            )
            return

        try:
            # Lazily instantiate manager and policy to ensure dependencies work.
            self._control_plane_manager = control_plane_manager_cls(
                scheduling_policy=self._control_plane_config["scheduling_policy"]
            )
            self._control_plane_policy = hybrid_policy_cls()
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Control Plane initialization failed: %s. "
                "Client will still work but without advanced scheduling.",
                exc,
            )
            return

        logger.info(
            "Control Plane mode initialized (LLM backends: %d, Embedding backends: %d)",
            len(self._control_plane_config["llm_backends"]),
            len(self._control_plane_config["embedding_backends"]),
        )

    # ==================== Backend Discovery ====================

    def enable_backend_discovery(
        self,
        management_base_url: str | None = None,
        refresh_interval: float = 30.0,
    ) -> None:
        """Enable dynamic backend discovery with automatic refresh.

        When enabled, the client will periodically query the Control Plane
        for available backends and update routing accordingly. This allows
        the client to discover newly started engines and handle backend
        failures automatically.

        Args:
            management_base_url: Base URL for the Control Plane management API.
                Defaults to http://localhost:8000/v1 if not provided.
            refresh_interval: How often to refresh the backend list (seconds).
                Defaults to 30 seconds.

        Example:
            >>> client = UnifiedInferenceClient.create()
            >>> client.enable_backend_discovery(refresh_interval=15.0)
        """
        if self._backend_refresh_enabled:
            logger.warning("Backend discovery is already enabled")
            return

        self._management_base_url = self._normalize_management_base(management_base_url)
        self._backend_refresh_interval = max(5.0, refresh_interval)  # Minimum 5 seconds
        self._backend_refresh_enabled = True

        # Do initial refresh
        self._refresh_backends()

        # Start background refresh thread
        self._refresh_stop_event.clear()
        self._refresh_thread = Thread(
            target=self._backend_refresh_loop,
            name="UnifiedClient-BackendRefresh",
            daemon=True,
        )
        self._refresh_thread.start()

        # Register cleanup on exit
        atexit.register(self.disable_backend_discovery)

        logger.info(
            "Backend discovery enabled (management_url=%s, interval=%.1fs)",
            self._management_base_url,
            self._backend_refresh_interval,
        )

    def disable_backend_discovery(self) -> None:
        """Disable dynamic backend discovery and stop the refresh thread."""
        if not self._backend_refresh_enabled:
            return

        self._backend_refresh_enabled = False
        self._refresh_stop_event.set()

        if self._refresh_thread and self._refresh_thread.is_alive():
            self._refresh_thread.join(timeout=5.0)
            self._refresh_thread = None

        logger.info("Backend discovery disabled")

    def _backend_refresh_loop(self) -> None:
        """Background loop that periodically refreshes the backend list."""
        while not self._refresh_stop_event.is_set():
            try:
                self._refresh_backends()
            except Exception as e:
                logger.warning("Backend refresh failed: %s", e)

            # Wait for next refresh interval or stop event
            self._refresh_stop_event.wait(timeout=self._backend_refresh_interval)

    def _refresh_backends(self) -> None:
        """Fetch and update the list of available backends from Control Plane.

        This method queries the /v1/management/backends endpoint and updates
        the internal backend lists. It also handles switching to healthy
        backends if the current one becomes unavailable.
        """
        if not self._management_base_url:
            return

        url = f"{self._management_base_url}/management/backends"
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(url)
                response.raise_for_status()
                data = response.json()
        except httpx.RequestError as e:
            logger.debug("Failed to fetch backends from %s: %s", url, e)
            return
        except httpx.HTTPStatusError as e:
            logger.debug("Backend list request failed (%d): %s", e.response.status_code, e)
            return
        except ValueError:
            logger.debug("Invalid JSON response from backends endpoint")
            return

        llm_backends = data.get("llm_backends", [])
        embedding_backends = data.get("embedding_backends", [])

        with self._backends_lock:
            old_llm_count = len(self._llm_backends)
            old_embed_count = len(self._embedding_backends)

            self._llm_backends = llm_backends
            self._embedding_backends = embedding_backends

            # Log changes
            new_llm_count = len(llm_backends)
            new_embed_count = len(embedding_backends)

            if new_llm_count != old_llm_count or new_embed_count != old_embed_count:
                logger.info(
                    "Backend list updated: LLM %d->%d, Embedding %d->%d",
                    old_llm_count,
                    new_llm_count,
                    old_embed_count,
                    new_embed_count,
                )

        # Check if current backends are still healthy and switch if needed
        self._update_clients_from_discovered_backends()

    def _update_clients_from_discovered_backends(self) -> None:
        """Update LLM and Embedding clients based on discovered backends.

        If the current backend is unhealthy, this method will attempt to
        switch to a healthy alternative.
        """
        with self._backends_lock:
            # Update LLM client if needed
            healthy_llm = [b for b in self._llm_backends if b.get("is_healthy", False)]
            if healthy_llm:
                # Check if current LLM is still healthy
                current_url = self.config.llm_base_url
                current_healthy = any(b.get("base_url") == current_url for b in healthy_llm)

                if not current_healthy and self._llm_available:
                    # Current backend is unhealthy, switch to first healthy one
                    new_backend = healthy_llm[0]
                    self._switch_llm_backend(new_backend)
            elif self._llm_backends and not healthy_llm:
                # All LLM backends are unhealthy
                logger.warning("All LLM backends are unhealthy")
                self._llm_available = False

            # Update Embedding client if needed
            healthy_embed = [b for b in self._embedding_backends if b.get("is_healthy", False)]
            if healthy_embed:
                current_url = self.config.embedding_base_url
                current_healthy = any(b.get("base_url") == current_url for b in healthy_embed)

                if not current_healthy and self._embedding_available:
                    new_backend = healthy_embed[0]
                    self._switch_embedding_backend(new_backend)
            elif self._embedding_backends and not healthy_embed:
                logger.warning("All Embedding backends are unhealthy")
                self._embedding_available = False

    def _switch_llm_backend(self, backend: dict[str, Any]) -> None:
        """Switch to a new LLM backend.

        Args:
            backend: Backend info dict with base_url and model_name.
        """
        new_url = backend.get("base_url")
        new_model = backend.get("model_name")

        if not new_url:
            return

        logger.info(
            "Switching LLM backend: %s -> %s",
            self.config.llm_base_url,
            new_url,
        )

        try:
            self._llm_client = OpenAI(
                base_url=new_url,
                api_key=self.config.llm_api_key or "not-needed",
                timeout=self.config.timeout,
                max_retries=self.config.max_retries,
            )
            self.config.llm_base_url = new_url
            if new_model:
                self.config.llm_model = new_model
            self._llm_available = True
        except Exception as e:
            logger.error("Failed to switch LLM backend to %s: %s", new_url, e)
            self._llm_available = False

    def _switch_embedding_backend(self, backend: dict[str, Any]) -> None:
        """Switch to a new Embedding backend.

        Args:
            backend: Backend info dict with base_url and model_name.
        """
        new_url = backend.get("base_url")
        new_model = backend.get("model_name")

        if not new_url:
            return

        logger.info(
            "Switching Embedding backend: %s -> %s",
            self.config.embedding_base_url,
            new_url,
        )

        try:
            self._embedding_client = OpenAI(
                base_url=new_url,
                api_key=self.config.embedding_api_key or "not-needed",
                timeout=self.config.timeout,
                max_retries=self.config.max_retries,
            )
            self.config.embedding_base_url = new_url
            if new_model:
                self.config.embedding_model = new_model
            self._embedding_available = True
        except Exception as e:
            logger.error("Failed to switch Embedding backend to %s: %s", new_url, e)
            self._embedding_available = False

    def get_discovered_backends(self) -> dict[str, Any]:
        """Get the current list of discovered backends.

        Returns:
            Dictionary with llm_backends and embedding_backends lists.
        """
        with self._backends_lock:
            return {
                "llm_backends": list(self._llm_backends),
                "embedding_backends": list(self._embedding_backends),
                "discovery_enabled": self._backend_refresh_enabled,
                "management_url": self._management_base_url,
            }

    def _try_llm_failover(self) -> bool:
        """Attempt to switch to a healthy LLM backend.

        Returns:
            True if successfully switched to a new backend, False otherwise.
        """
        # First, refresh the backend list
        if self._management_base_url:
            self._refresh_backends()

        with self._backends_lock:
            # Find healthy backends excluding the current one
            current_url = self.config.llm_base_url
            healthy_backends = [
                b
                for b in self._llm_backends
                if b.get("is_healthy", False) and b.get("base_url") != current_url
            ]

            if not healthy_backends:
                # No alternative healthy backends available
                logger.warning("No healthy LLM backends available for failover")
                return False

            # Switch to the first healthy alternative
            new_backend = healthy_backends[0]
            self._switch_llm_backend(new_backend)
            return self._llm_available

    def _try_embedding_failover(self) -> bool:
        """Attempt to switch to a healthy Embedding backend.

        Returns:
            True if successfully switched to a new backend, False otherwise.
        """
        # First, refresh the backend list
        if self._management_base_url:
            self._refresh_backends()

        with self._backends_lock:
            # Find healthy backends excluding the current one
            current_url = self.config.embedding_base_url
            healthy_backends = [
                b
                for b in self._embedding_backends
                if b.get("is_healthy", False) and b.get("base_url") != current_url
            ]

            if not healthy_backends:
                logger.warning("No healthy Embedding backends available for failover")
                return False

            new_backend = healthy_backends[0]
            self._switch_embedding_backend(new_backend)
            return self._embedding_available

    # ==================== Factory Methods ====================

    @classmethod
    def create(
        cls,
        *,
        control_plane_url: str | None = None,
        embedded: bool = False,
        default_llm_model: str | None = None,
        default_embedding_model: str | None = None,
        scheduling_policy: str = "adaptive",
        timeout: float = 60.0,
        prefer_local: bool = True,
        llm_ports: Sequence[int] | None = None,
        embedding_ports: Sequence[int] | None = None,
    ) -> UnifiedInferenceClient:
        """Create a UnifiedInferenceClient instance.

        This is the **only** entry point for creating client instances.
        All requests are managed through the Control Plane.

        Usage modes:
        1. Auto-detection (default): Automatically detect local/cloud endpoints
        2. External Control Plane: Connect to an existing Control Plane server
        3. Embedded Control Plane: Start an embedded Control Plane for this process

        Args:
            control_plane_url: URL of an external Control Plane to connect to.
                If provided, the client will route requests through this endpoint.
                Example: "http://localhost:8000/v1"
            embedded: If True, start an embedded Control Plane for this process.
                Mutually exclusive with control_plane_url.
            default_llm_model: Default model name for LLM requests.
            default_embedding_model: Default model name for Embedding requests.
            scheduling_policy: Scheduling policy to use ("adaptive", "fifo",
                "priority", "slo_aware", "cost_optimized").
            timeout: Request timeout in seconds.
            prefer_local: If True, prefer local servers over cloud APIs.
            llm_ports: Ports to check for local LLM servers. If None, uses SagePorts.
            embedding_ports: Ports to check for local Embedding servers. If None, uses SagePorts.

        Returns:
            Configured UnifiedInferenceClient instance.

        Raises:
            ValueError: If both control_plane_url and embedded=True are provided.

        Example:
            >>> # Auto-detection (recommended for most cases)
            >>> client = UnifiedInferenceClient.create()
            >>>
            >>> # Connect to external Control Plane
            >>> client = UnifiedInferenceClient.create(
            ...     control_plane_url="http://localhost:8000/v1"
            ... )
            >>>
            >>> # Embedded Control Plane
            >>> client = UnifiedInferenceClient.create(embedded=True)
            >>>
            >>> # With specific models
            >>> client = UnifiedInferenceClient.create(
            ...     default_llm_model="Qwen/Qwen2.5-7B-Instruct",
            ...     default_embedding_model="BAAI/bge-m3",
            ... )
        """
        # Validate mutually exclusive options
        if control_plane_url and embedded:
            raise ValueError(
                "Cannot specify both control_plane_url and embedded=True. "
                "Choose one mode or omit both for auto-detection."
            )

        # Import SagePorts for default values
        from sage.common.config.ports import SagePorts

        if llm_ports is None:
            llm_ports = SagePorts.get_llm_ports()
        if embedding_ports is None:
            embedding_ports = SagePorts.get_embedding_ports()

        # Determine endpoints based on mode
        llm_base_url: str | None = None
        llm_model: str | None = default_llm_model
        llm_api_key: str = ""
        embedding_base_url: str | None = None
        embedding_model: str | None = default_embedding_model
        embedding_api_key: str = ""

        if control_plane_url:
            # Use external Control Plane URL for both LLM and Embedding
            llm_base_url = control_plane_url
            embedding_base_url = control_plane_url
            logger.info("Using external Control Plane: %s", control_plane_url)
        elif embedded:
            # Embedded mode: will be initialized during _init_control_plane_mode
            logger.info("Using embedded Control Plane mode")
            # Still detect endpoints for the embedded Control Plane to use
            llm_base_url, llm_model_detected, llm_api_key = cls._detect_llm_endpoint(
                prefer_local=prefer_local,
                ports=llm_ports,
            )
            embedding_base_url, embedding_model_detected, embedding_api_key = (
                cls._detect_embedding_endpoint(
                    prefer_local=prefer_local,
                    ports=embedding_ports,
                )
            )
            llm_model = llm_model or llm_model_detected
            embedding_model = embedding_model or embedding_model_detected
        else:
            # Auto-detection mode (default)
            # Check for unified base URL
            unified_base_url = os.environ.get("SAGE_UNIFIED_BASE_URL")
            if unified_base_url:
                logger.info("Using unified base URL from environment: %s", unified_base_url)
                llm_base_url = unified_base_url
                embedding_base_url = unified_base_url
                llm_model = llm_model or os.environ.get("SAGE_UNIFIED_MODEL")
                embedding_model = embedding_model or os.environ.get("SAGE_UNIFIED_MODEL")
                llm_api_key = os.environ.get("SAGE_UNIFIED_API_KEY", "")
                embedding_api_key = os.environ.get("SAGE_UNIFIED_API_KEY", "")
            else:
                # Detect LLM endpoint
                llm_base_url, llm_model_detected, llm_api_key = cls._detect_llm_endpoint(
                    prefer_local=prefer_local,
                    ports=llm_ports,
                )
                # Detect Embedding endpoint
                embedding_base_url, embedding_model_detected, embedding_api_key = (
                    cls._detect_embedding_endpoint(
                        prefer_local=prefer_local,
                        ports=embedding_ports,
                    )
                )
                llm_model = llm_model or llm_model_detected
                embedding_model = embedding_model or embedding_model_detected

        # Create the instance using a private subclass to bypass the direct instantiation check
        instance = _CreatableUnifiedClient(
            llm_base_url=llm_base_url,
            llm_model=llm_model,
            llm_api_key=llm_api_key,
            embedding_base_url=embedding_base_url,
            embedding_model=embedding_model,
            embedding_api_key=embedding_api_key,
            timeout=timeout,
        )

        return instance

    @classmethod
    def create_for_model(
        cls,
        model_id: str,
        *,
        management_base_url: str | None = None,
        tensor_parallel_size: int = 1,
        required_memory_gb: float | None = None,
        engine_label: str | None = None,
        extra_spawn_args: list[str] | None = None,
        wait_timeout: float = 120.0,
        poll_interval: float = 2.0,
        auto_start: bool = True,
        prefer_existing: bool = True,
    ) -> UnifiedInferenceClient:
        """Create a client bound to a managed engine resolved by model name.

        This helper talks to the Control Plane management API (default
        ``http://localhost:8000/v1/management``) to locate an existing engine
        that already serves ``model_id``. If no engine is running and
        ``auto_start`` is True, it will request a new engine startup and wait
        until the engine is reachable before returning a configured client.

        Args:
            model_id: Target model name registered with the Control Plane.
            management_base_url: Base URL of the Unified API server
                (e.g. ``http://localhost:8000/v1``). Defaults to the local
                gateway port if omitted.
            tensor_parallel_size: Requested tensor parallelism when starting
                a new engine.
            required_memory_gb: Explicit per-GPU memory reservation for the
                engine request. Control Plane heuristics are used if omitted.
            engine_label: Optional label recorded with the engine metadata.
            extra_spawn_args: Additional CLI args forwarded to vLLM.
            wait_timeout: Maximum seconds to wait for the engine to reach a
                RUNNING/STARTING state after spawning.
            poll_interval: Interval (seconds) between status polls.
            auto_start: Whether to spawn a new engine when no running engine
                matches the requested model.
            prefer_existing: If False, forces creation of a new engine even if
                a compatible engine is already tracked.

        Returns:
            UnifiedInferenceClient wired to the resolved engine endpoint.

        Raises:
            RuntimeError: When the management API is unreachable, no engine
                can be allocated, or the new engine never reaches RUNNING.
        """

        resolved_base = cls._normalize_management_base(management_base_url)
        engine_info = cls._ensure_engine_for_model(
            model_id=model_id,
            management_base=resolved_base,
            tensor_parallel_size=tensor_parallel_size,
            required_memory_gb=required_memory_gb,
            engine_label=engine_label,
            extra_spawn_args=extra_spawn_args,
            wait_timeout=wait_timeout,
            poll_interval=poll_interval,
            auto_start=auto_start,
            prefer_existing=prefer_existing,
        )

        llm_base_url = cls._build_engine_base_url(engine_info)
        return cls.create(
            control_plane_url=llm_base_url,
            default_llm_model=model_id,
        )

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
            **kwargs: Arguments passed to create() for new instances.

        Returns:
            Cached or newly created UnifiedInferenceClient instance.
        """
        with cls._lock:
            if instance_key not in cls._instances:
                cls._instances[instance_key] = cls.create(**kwargs)
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
            "  sage llm serve --model <model_name> --port 8901\n"
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
            "  sage llm serve --with-embedding --embedding-model <model_name> --embedding-port 8090\n"
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
            RuntimeError: If no LLM backend is available after failover attempts.
            Exception: If API call fails.

        Example:
            >>> client = UnifiedInferenceClient.create()
            >>> response = client.chat([
            ...     {"role": "user", "content": "What is 2+2?"}
            ... ])
            >>> print(response)
            "2+2 equals 4."
        """
        if not self._llm_available:
            # Try failover if backend discovery is enabled
            if self._backend_refresh_enabled:
                self._try_llm_failover()
            if not self._llm_available:
                raise RuntimeError(
                    "No LLM backend available. "
                    "Check configuration or start a local server with 'sage llm serve'."
                )

        return_result = kwargs.pop("return_result", False)
        start_time = time.time()

        # All requests go through Control Plane (direct API call path)
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

        # Try request with failover on connection errors
        last_error: Exception | None = None
        max_failover_attempts = 3

        for attempt in range(max_failover_attempts):
            try:
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
                            "completion_tokens": (
                                response.usage.completion_tokens if response.usage else 0
                            ),
                            "total_tokens": response.usage.total_tokens if response.usage else 0,
                        },
                        latency_ms=latency_ms,
                    )

                return content

            except Exception as e:
                last_error = e
                # Check if this is a connection error that warrants failover
                error_str = str(e).lower()
                is_connection_error = any(
                    keyword in error_str
                    for keyword in ["connection", "timeout", "refused", "unreachable"]
                )

                if is_connection_error and self._backend_refresh_enabled:
                    logger.warning(
                        "LLM request failed (attempt %d/%d): %s. Attempting failover...",
                        attempt + 1,
                        max_failover_attempts,
                        e,
                    )
                    if self._try_llm_failover():
                        # Successfully switched to new backend, retry
                        continue
                # Non-connection error or failover failed, raise immediately
                raise

        # All attempts exhausted
        if last_error:
            raise last_error
        raise RuntimeError("LLM request failed after all failover attempts")

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
            >>> client = UnifiedInferenceClient.create()
            >>> text = client.generate("Once upon a time")
            >>> print(text)
        """
        if not self._llm_available:
            raise RuntimeError(
                "LLM endpoint not available. Check configuration or start a local server."
            )

        return_result = kwargs.pop("return_result", False)
        start_time = time.time()

        # All requests go through Control Plane
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
            RuntimeError: If no Embedding backend is available after failover attempts.

        Example:
            >>> client = UnifiedInferenceClient.create()
            >>> vectors = client.embed(["Hello", "World"])
            >>> print(len(vectors))
            2
            >>> print(len(vectors[0]))  # Embedding dimension
            768
        """
        if not self._embedding_available:
            # Try failover if backend discovery is enabled
            if self._backend_refresh_enabled:
                self._try_embedding_failover()
            if not self._embedding_available:
                raise RuntimeError(
                    "No Embedding backend available. "
                    "Check configuration or start a local embedding server."
                )

        # Normalize input
        if isinstance(texts, str):
            texts = [texts]

        return_result = kwargs.pop("return_result", False)
        start_time = time.time()

        # All requests go through Control Plane
        actual_model = model or self.config.embedding_model
        if not actual_model:
            actual_model = self._get_default_embedding_model()

        if self._embedding_client is None:
            raise RuntimeError("Embedding client not initialized")

        # Use hasattr for duck typing - allows both OpenAI client and mocks
        if not hasattr(self._embedding_client, "embeddings"):
            raise RuntimeError("Embedding client does not have embeddings attribute")

        # Try request with failover on connection errors
        last_error: Exception | None = None
        max_failover_attempts = 3

        for attempt in range(max_failover_attempts):
            try:
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

            except Exception as e:
                last_error = e
                error_str = str(e).lower()
                is_connection_error = any(
                    keyword in error_str
                    for keyword in ["connection", "timeout", "refused", "unreachable"]
                )

                if is_connection_error and self._backend_refresh_enabled:
                    logger.warning(
                        "Embedding request failed (attempt %d/%d): %s. Attempting failover...",
                        attempt + 1,
                        max_failover_attempts,
                        e,
                    )
                    if self._try_embedding_failover():
                        continue
                raise

        if last_error:
            raise last_error
        raise RuntimeError("Embedding request failed after all failover attempts")

    # ==================== Helper Methods ====================

    @classmethod
    def _normalize_management_base(cls, base_url: str | None) -> str:
        """Return a normalized Control Plane base URL ending with /v1."""

        if base_url:
            normalized = base_url.rstrip("/")
        else:
            from sage.common.config.ports import SagePorts  # Lazy import to avoid cycles

            normalized = f"http://localhost:{SagePorts.GATEWAY_DEFAULT}/v1"

        if not normalized.endswith("/v1"):
            normalized = f"{normalized}/v1"
        return normalized.rstrip("/")

    @classmethod
    def _ensure_engine_for_model(
        cls,
        *,
        model_id: str,
        management_base: str,
        tensor_parallel_size: int,
        required_memory_gb: float | None,
        engine_label: str | None,
        extra_spawn_args: list[str] | None,
        wait_timeout: float,
        poll_interval: float,
        auto_start: bool,
        prefer_existing: bool,
    ) -> dict[str, Any]:
        """Find or create an engine that serves the requested model."""

        cluster_status = cls._fetch_cluster_status(management_base)
        engine = None if not prefer_existing else cls._find_engine_entry(cluster_status, model_id)
        if engine:
            return engine

        if not auto_start:
            raise RuntimeError(
                f"No managed engine found for model '{model_id}'. "
                "Enable auto_start or provision one via 'sage llm engine start'."
            )

        response = cls._start_engine_via_management(
            management_base,
            model_id=model_id,
            tensor_parallel_size=tensor_parallel_size,
            required_memory_gb=required_memory_gb,
            engine_label=engine_label,
            extra_spawn_args=extra_spawn_args,
        )
        engine_id = (
            response.get("engine_id")
            or response.get("id")
            or response.get("engine", {}).get("engine_id")
        )
        if not engine_id:
            raise RuntimeError("Control Plane response did not return an engine_id")

        return cls._wait_for_engine_ready(
            management_base,
            model_id=model_id,
            engine_id=str(engine_id),
            wait_timeout=wait_timeout,
            poll_interval=poll_interval,
        )

    @classmethod
    def _fetch_cluster_status(cls, management_base: str) -> dict[str, Any]:
        url = f"{management_base}/management/status"
        try:
            response = httpx.get(url, timeout=15.0)
            response.raise_for_status()
        except httpx.RequestError as exc:  # pragma: no cover - network failures
            raise RuntimeError(f"Unable to reach Control Plane at {url}: {exc}") from exc
        except httpx.HTTPStatusError as exc:  # pragma: no cover - HTTP errors
            detail = exc.response.text.strip() or exc.response.reason_phrase
            raise RuntimeError(
                f"Control Plane status request failed ({exc.response.status_code}): {detail}"
            ) from exc

        try:
            return response.json()
        except ValueError as exc:
            raise RuntimeError("Control Plane returned invalid JSON for cluster status") from exc

    @classmethod
    def _find_engine_entry(
        cls,
        cluster_status: dict[str, Any],
        model_id: str,
        engine_id: str | None = None,
    ) -> dict[str, Any] | None:
        target = model_id.lower()
        engines = cluster_status.get("engines") or cluster_status.get("engine_instances") or []
        for entry in engines:
            if not isinstance(entry, dict):
                continue

            entry_id = str(entry.get("engine_id") or entry.get("id") or "")
            if engine_id and entry_id == engine_id:
                return entry

            models = [
                entry.get("model_id"),
                entry.get("model_name"),
                entry.get("model"),
            ]
            if any(isinstance(value, str) and value.lower() == target for value in models):
                status = str(entry.get("status") or entry.get("state") or "RUNNING").upper()
                if status in {"RUNNING", "STARTING"}:
                    return entry
        return None

    @classmethod
    def _start_engine_via_management(
        cls,
        management_base: str,
        *,
        model_id: str,
        tensor_parallel_size: int,
        required_memory_gb: float | None,
        engine_label: str | None,
        extra_spawn_args: list[str] | None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model_id": model_id,
            "tensor_parallel_size": tensor_parallel_size,
        }
        if required_memory_gb is not None:
            payload["required_memory_gb"] = required_memory_gb
        if engine_label:
            payload["engine_label"] = engine_label
        if extra_spawn_args:
            payload["extra_args"] = extra_spawn_args

        url = f"{management_base}/management/engines"
        try:
            response = httpx.post(url, json=payload, timeout=30.0)
        except httpx.RequestError as exc:  # pragma: no cover - network failures
            raise RuntimeError(f"Failed to contact Control Plane at {url}: {exc}") from exc

        if response.status_code >= 400:
            detail = cls._safe_error_detail(response)
            raise RuntimeError(
                f"Control Plane rejected engine request ({response.status_code}): {detail}"
            )

        try:
            return response.json()
        except ValueError as exc:
            raise RuntimeError("Control Plane returned invalid JSON when creating engine") from exc

    @staticmethod
    def _safe_error_detail(response: httpx.Response) -> str:
        try:
            payload = response.json()
        except ValueError:
            return response.text.strip() or response.reason_phrase

        if isinstance(payload, dict):
            for key in ("detail", "message", "error"):
                if key in payload:
                    return str(payload[key])
        return str(payload)

    @classmethod
    def _wait_for_engine_ready(
        cls,
        management_base: str,
        *,
        model_id: str,
        engine_id: str,
        wait_timeout: float,
        poll_interval: float,
    ) -> dict[str, Any]:
        deadline = time.time() + max(wait_timeout, 1.0)
        while time.time() < deadline:
            cluster_status = cls._fetch_cluster_status(management_base)
            engine = cls._find_engine_entry(cluster_status, model_id, engine_id=engine_id)
            if engine:
                status = str(engine.get("status") or engine.get("state") or "RUNNING").upper()
                if status in {"RUNNING", "STARTING"}:
                    return engine
                if status in {"FAILED", "STOPPED"}:
                    raise RuntimeError(
                        f"Engine {engine_id} reported terminal status '{status}'. Check logs."
                    )
            time.sleep(max(poll_interval, 0.5))

        raise RuntimeError(
            f"Timed out ({wait_timeout:.0f}s) waiting for engine {engine_id} to become ready"
        )

    @staticmethod
    def _build_engine_base_url(engine_info: dict[str, Any]) -> str:
        host = str(engine_info.get("host") or "localhost")
        port = engine_info.get("port") or engine_info.get("listen_port")
        if port is None:
            raise RuntimeError("Engine metadata is missing port information")
        return f"http://{host}:{int(port)}/v1"

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
        """Check if Control Plane manager is initialized.

        Note: All clients now use Control Plane mode. This property
        indicates whether the Control Plane manager was successfully
        initialized (returns True) or if it's running in degraded mode
        (returns False, still functional but without advanced scheduling).
        """
        return self._control_plane_manager is not None

    def get_status(self) -> dict[str, Any]:
        """Get client status information.

        Returns:
            Dict with status information including:
            - mode: Current operation mode (always "control_plane")
            - control_plane_active: Whether Control Plane manager is initialized
            - llm_available: Whether LLM is available
            - embedding_available: Whether Embedding is available
            - llm_base_url: LLM endpoint URL
            - embedding_base_url: Embedding endpoint URL
        """
        return {
            "mode": UnifiedClientMode.CONTROL_PLANE,
            "control_plane_active": self._control_plane_manager is not None,
            "llm_available": self._llm_available,
            "embedding_available": self._embedding_available,
            "llm_base_url": self.config.llm_base_url,
            "llm_model": self.config.llm_model,
            "embedding_base_url": self.config.embedding_base_url,
            "embedding_model": self.config.embedding_model,
        }


class _CreatableUnifiedClient(UnifiedInferenceClient):
    """Private subclass that allows direct instantiation.

    This class is used internally by UnifiedInferenceClient.create() to bypass
    the direct instantiation check. It should not be used directly.
    """

    pass


# ==================== Convenience Aliases ====================

# For backward compatibility and ease of use
UnifiedClient = UnifiedInferenceClient
