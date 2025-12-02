# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""Unified API Server for LLM and Embedding inference.

This module provides a unified OpenAI-compatible API server that serves both
LLM (chat/completion) and Embedding endpoints. It integrates with the sageLLM
Control Plane for intelligent request scheduling and resource management.

Key Features:
- OpenAI-compatible API endpoints:
  - POST /v1/chat/completions - Chat completions
  - POST /v1/completions - Text completions
  - POST /v1/embeddings - Text embeddings
  - GET /v1/models - List available models
  - GET /health - Health check
- Integration with Control Plane for hybrid scheduling
- Support for multiple backend instances (LLM, Embedding, Mixed)
- Graceful startup and shutdown

Example:
    >>> from sage.common.components.sage_llm.unified_api_server import (
    ...     UnifiedAPIServer,
    ...     UnifiedServerConfig,
    ... )
    >>>
    >>> config = UnifiedServerConfig(
    ...     host="0.0.0.0",
    ...     port=8000,
    ...     llm_models=["Qwen/Qwen2.5-7B-Instruct"],
    ...     embedding_models=["BAAI/bge-m3"],
    ... )
    >>> server = UnifiedAPIServer(config)
    >>> server.start()  # Blocking call
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, AsyncGenerator, Literal

logger = logging.getLogger(__name__)

# Type stubs for conditional imports - helps type checkers understand optional deps
if TYPE_CHECKING:
    import aiohttp
    import uvicorn
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import StreamingResponse
    from pydantic import BaseModel, Field

# Optional imports - server can run without all dependencies
try:
    import uvicorn
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import StreamingResponse
    from pydantic import BaseModel, Field

    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    logger.warning("FastAPI/uvicorn not available. Install with: pip install fastapi uvicorn")

try:
    import aiohttp

    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

try:
    from sage.common.components.sage_llm.sageLLM.control_plane import (
        ControlPlaneManager,
        ExecutionInstanceType,
    )

    CONTROL_PLANE_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency wiring
    CONTROL_PLANE_AVAILABLE = False
    ControlPlaneManager = None  # type: ignore[assignment]
    ExecutionInstanceType = None  # type: ignore[assignment]


# =============================================================================
# Configuration
# =============================================================================


class SchedulingPolicyType(str, Enum):
    """Available scheduling policies for the Control Plane."""

    FIFO = "fifo"
    PRIORITY = "priority"
    SLO_AWARE = "slo_aware"
    COST_OPTIMIZED = "cost_optimized"
    ADAPTIVE = "adaptive"
    HYBRID = "hybrid"


@dataclass
class BackendInstanceConfig:
    """Configuration for a backend inference instance.

    Attributes:
        host: Hostname or IP address of the instance.
        port: Port number of the instance.
        model_name: Name of the model loaded on this instance.
        instance_type: Type of instance (llm, embedding, llm_embedding).
        max_concurrent_requests: Maximum concurrent requests for this instance.
        api_key: Optional API key for authentication.
    """

    host: str = "localhost"
    port: int = 8000
    model_name: str = ""
    instance_type: Literal["llm", "embedding", "llm_embedding"] = "llm"
    max_concurrent_requests: int = 100
    api_key: str | None = None

    @property
    def base_url(self) -> str:
        """Get the base URL for this instance."""
        return f"http://{self.host}:{self.port}"


@dataclass
class UnifiedServerConfig:
    """Configuration for the Unified API Server.

    Attributes:
        host: Server host address.
        port: Server port.
        llm_backends: List of LLM backend instance configurations.
        embedding_backends: List of Embedding backend instance configurations.
        scheduling_policy: Scheduling policy for request routing.
        enable_control_plane: Whether to use Control Plane for scheduling.
        enable_cors: Whether to enable CORS middleware.
        cors_origins: List of allowed CORS origins.
        log_level: Logging level for the server.
        request_timeout: Default request timeout in seconds.
    """

    host: str = "0.0.0.0"
    port: int = 8000
    llm_backends: list[BackendInstanceConfig] = field(default_factory=list)
    embedding_backends: list[BackendInstanceConfig] = field(default_factory=list)
    scheduling_policy: SchedulingPolicyType = SchedulingPolicyType.ADAPTIVE
    enable_control_plane: bool = False
    enable_cors: bool = True
    cors_origins: list[str] = field(default_factory=lambda: ["*"])
    log_level: str = "info"
    request_timeout: float = 300.0

    def __post_init__(self) -> None:
        """Set up default backends if none provided."""
        # Add default LLM backend if none specified
        if not self.llm_backends:
            llm_port = int(os.getenv("SAGE_LLM_PORT", "8001"))
            self.llm_backends.append(
                BackendInstanceConfig(
                    host="localhost",
                    port=llm_port,
                    model_name=os.getenv("SAGE_CHAT_MODEL", ""),
                    instance_type="llm",
                )
            )

        # Add default Embedding backend if none specified
        if not self.embedding_backends:
            embed_port = int(os.getenv("SAGE_EMBEDDING_PORT", "8090"))
            self.embedding_backends.append(
                BackendInstanceConfig(
                    host="localhost",
                    port=embed_port,
                    model_name=os.getenv("SAGE_EMBEDDING_MODEL", ""),
                    instance_type="embedding",
                )
            )


# =============================================================================
# Request/Response Models (Pydantic)
# =============================================================================

if FASTAPI_AVAILABLE:

    class ChatMessage(BaseModel):
        """A single chat message."""

        role: str = Field(..., description="Role of the message sender (system/user/assistant)")
        content: str = Field(..., description="Content of the message")
        name: str | None = Field(None, description="Optional name of the sender")

    class ChatCompletionRequest(BaseModel):
        """Request body for /v1/chat/completions endpoint."""

        model: str = Field(..., description="Model to use for completion")
        messages: list[ChatMessage] = Field(..., description="List of messages in the conversation")
        temperature: float = Field(0.7, ge=0, le=2, description="Sampling temperature")
        top_p: float = Field(1.0, ge=0, le=1, description="Top-p sampling parameter")
        max_tokens: int | None = Field(None, description="Maximum tokens to generate")
        stream: bool = Field(False, description="Whether to stream the response")
        stop: str | list[str] | None = Field(None, description="Stop sequences")
        presence_penalty: float = Field(0, description="Presence penalty")
        frequency_penalty: float = Field(0, description="Frequency penalty")
        user: str | None = Field(None, description="User identifier")

    class CompletionRequest(BaseModel):
        """Request body for /v1/completions endpoint."""

        model: str = Field(..., description="Model to use for completion")
        prompt: str | list[str] = Field(..., description="Prompt(s) to complete")
        max_tokens: int | None = Field(16, description="Maximum tokens to generate")
        temperature: float = Field(1.0, ge=0, le=2, description="Sampling temperature")
        top_p: float = Field(1.0, ge=0, le=1, description="Top-p sampling parameter")
        stream: bool = Field(False, description="Whether to stream the response")
        stop: str | list[str] | None = Field(None, description="Stop sequences")
        echo: bool = Field(False, description="Whether to echo the prompt")
        user: str | None = Field(None, description="User identifier")

    class EmbeddingRequest(BaseModel):
        """Request body for /v1/embeddings endpoint."""

        input: str | list[str] = Field(..., description="Text(s) to embed")
        model: str = Field(..., description="Model to use for embedding")
        encoding_format: str = Field("float", description="Encoding format (float or base64)")
        user: str | None = Field(None, description="User identifier")

    class ModelInfo(BaseModel):
        """Information about an available model."""

        id: str
        object: str = "model"
        created: int = Field(default_factory=lambda: int(time.time()))
        owned_by: str = "sage"
        permission: list[dict[str, Any]] = Field(default_factory=list)
        root: str | None = None
        parent: str | None = None

    class EngineStartRequest(BaseModel):
        """Request body for Control Plane engine startup."""

        model_id: str = Field(..., description="Model identifier to launch")
        tensor_parallel_size: int = Field(
            1,
            ge=1,
            description="Number of GPUs to allocate for tensor parallelism",
        )
        pipeline_parallel_size: int = Field(1, ge=1, description="Pipeline stages")
        port: int | None = Field(
            None,
            description="Preferred port for the new engine (auto-select if omitted)",
        )
        host: str = Field("localhost", description="Host where the engine is reachable")
        instance_type: str = Field(
            "GENERAL",
            description="ExecutionInstanceType name (e.g., GENERAL, PREFILLING)",
        )
        max_concurrent_requests: int = Field(256, ge=1, description="Scheduling limit")
        required_memory_gb: float | None = Field(
            None,
            gt=0,
            description="Optional per-GPU memory requirement override (GB)",
        )
        engine_label: str | None = Field(
            None,
            description="Optional friendly label stored with the engine",
        )
        extra_args: list[str] | None = Field(
            None,
            description="Additional CLI args passed to the vLLM process",
        )
        metadata: dict[str, Any] | None = Field(
            None,
            description="Optional metadata attached to the registered instance",
        )
        engine_kind: str = Field(
            "llm",
            description="Runtime kind of engine (llm or embedding)",
        )
        use_gpu: bool | None = Field(
            None,
            description="GPU usage override. None=default (LLM uses GPU, Embedding does not), "
            "True=force GPU, False=force no GPU",
        )


# =============================================================================
# Unified API Server
# =============================================================================


class UnifiedAPIServer:
    """Unified OpenAI-compatible API server for LLM and Embedding inference.

    This server provides a single entry point for both LLM (chat/completion)
    and Embedding requests, routing them to appropriate backend instances
    based on the request type and configured scheduling policy.

    Features:
    - OpenAI-compatible REST API
    - Support for multiple backend instances
    - Health monitoring and failover
    - Optional Control Plane integration for advanced scheduling
    - Streaming support for chat completions

    Example:
        >>> server = UnifiedAPIServer(UnifiedServerConfig(port=8000))
        >>> server.start()  # Starts blocking server

        # Or use async context manager
        >>> async with server:
        ...     # Server is running
        ...     pass
    """

    def __init__(self, config: UnifiedServerConfig | None = None) -> None:
        """Initialize the Unified API Server.

        Args:
            config: Server configuration. If None, uses defaults.
        """
        if not FASTAPI_AVAILABLE:
            raise RuntimeError(
                "FastAPI and uvicorn are required. Install with: pip install fastapi uvicorn"
            )

        self.config = config or UnifiedServerConfig()
        self._app: FastAPI | None = None
        self._server: uvicorn.Server | None = None
        self._running = False
        self._http_session: aiohttp.ClientSession | None = None
        self._control_plane_manager: ControlPlaneManager | None = None

        # Track available models
        self._llm_models: dict[str, BackendInstanceConfig] = {}
        self._embedding_models: dict[str, BackendInstanceConfig] = {}

        # Build model mappings
        self._build_model_mappings()

        if self.config.enable_control_plane:
            self._initialize_control_plane_manager()

        logger.info(
            "UnifiedAPIServer initialized with %d LLM backends and %d Embedding backends",
            len(self.config.llm_backends),
            len(self.config.embedding_backends),
        )

    def _build_model_mappings(self) -> None:
        """Build mappings from model names to backend configurations."""
        for backend in self.config.llm_backends:
            if backend.model_name:
                self._llm_models[backend.model_name] = backend

        for backend in self.config.embedding_backends:
            if backend.model_name:
                self._embedding_models[backend.model_name] = backend

    def _initialize_control_plane_manager(self) -> None:
        """Initialize Control Plane Manager if dependencies are available."""

        if not CONTROL_PLANE_AVAILABLE:
            logger.warning(
                "enable_control_plane is True but Control Plane components are unavailable"
            )
            return

        try:
            self._control_plane_manager = ControlPlaneManager(
                scheduling_policy=self.config.scheduling_policy.value,
                routing_strategy="load_balanced",
                enable_pd_separation=True,
                mode="http",
            )
            logger.info("Control Plane Manager initialized for Unified API Server")
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("Failed to initialize Control Plane Manager: %s", exc)
            self._control_plane_manager = None

    def _create_app(self) -> FastAPI:
        """Create and configure the FastAPI application."""

        @asynccontextmanager
        async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
            """Manage server lifecycle."""
            # Startup
            logger.info("Starting Unified API Server...")
            self._http_session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.config.request_timeout)
            )
            self._running = True
            if self._control_plane_manager:
                await self._control_plane_manager.start()
            yield
            # Shutdown
            logger.info("Shutting down Unified API Server...")
            self._running = False
            if self._control_plane_manager:
                await self._control_plane_manager.stop()
            if self._http_session:
                await self._http_session.close()
                self._http_session = None

        app = FastAPI(
            title="SAGE Unified Inference API",
            description="OpenAI-compatible API for LLM and Embedding inference",
            version="1.0.0",
            lifespan=lifespan,
        )

        # Add CORS middleware if enabled
        if self.config.enable_cors:
            app.add_middleware(
                CORSMiddleware,
                allow_origins=self.config.cors_origins,
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )

        # Register routes
        self._register_routes(app)

        return app

    def _register_routes(self, app: FastAPI) -> None:
        """Register API routes on the FastAPI app."""

        @app.get("/")
        async def root() -> dict[str, Any]:
            """Root endpoint with server info."""
            endpoints: dict[str, Any] = {
                "chat": "/v1/chat/completions",
                "completions": "/v1/completions",
                "embeddings": "/v1/embeddings",
                "models": "/v1/models",
                "health": "/health",
            }

            if self._control_plane_manager:
                endpoints["management"] = {
                    "start_engine": "/v1/management/engines",
                    "stop_engine": "/v1/management/engines/{engine_id}",
                    "cluster_status": "/v1/management/status",
                }

            return {
                "service": "SAGE Unified API Server",
                "status": "running" if self._running else "starting",
                "endpoints": endpoints,
            }

        @app.get("/health")
        async def health_check() -> dict[str, Any]:
            """Health check endpoint."""
            llm_count = len(self.config.llm_backends)
            embed_count = len(self.config.embedding_backends)
            llm_healthy = llm_count > 0
            embed_healthy = embed_count > 0

            status = "ok"
            if not llm_healthy or not embed_healthy:
                status = "degraded"
            if not llm_healthy and not embed_healthy:
                status = "unavailable"

            response = {
                "status": status,
                "timestamp": datetime.now().isoformat(),
                "backends": {
                    "llm": {"healthy": llm_healthy, "count": llm_count},
                    "embedding": {
                        "healthy": embed_healthy,
                        "count": embed_count,
                    },
                },
            }

            if self._control_plane_manager:
                response["control_plane"] = {
                    "enabled": True,
                    "policy": self.config.scheduling_policy.value,
                }

            return response

        @app.get("/v1/models")
        async def list_models() -> dict[str, Any]:
            """List available models (OpenAI compatible)."""
            models = []

            # Add LLM models
            for model_name, backend in self._llm_models.items():
                models.append(
                    {
                        "id": model_name,
                        "object": "model",
                        "created": int(time.time()),
                        "owned_by": "sage",
                        "type": "llm",
                        "backend": f"{backend.host}:{backend.port}",
                    }
                )

            # Add Embedding models
            for model_name, backend in self._embedding_models.items():
                models.append(
                    {
                        "id": model_name,
                        "object": "model",
                        "created": int(time.time()),
                        "owned_by": "sage",
                        "type": "embedding",
                        "backend": f"{backend.host}:{backend.port}",
                    }
                )

            return {"object": "list", "data": models}

        @app.post("/v1/chat/completions")
        async def chat_completions(request: ChatCompletionRequest) -> Any:
            """Create chat completion (OpenAI compatible)."""
            backend = self._get_llm_backend(request.model)
            if not backend:
                raise HTTPException(
                    status_code=404,
                    detail=f"Model '{request.model}' not found. Available models: {list(self._llm_models.keys())}",
                )

            # Forward to backend
            try:
                if request.stream:
                    return await self._stream_chat_completion(backend, request)
                else:
                    return await self._forward_chat_completion(backend, request)
            except Exception as e:
                logger.error(f"Chat completion error: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @app.post("/v1/completions")
        async def completions(request: CompletionRequest) -> Any:
            """Create text completion (OpenAI compatible)."""
            backend = self._get_llm_backend(request.model)
            if not backend:
                raise HTTPException(
                    status_code=404,
                    detail=f"Model '{request.model}' not found. Available models: {list(self._llm_models.keys())}",
                )

            try:
                if request.stream:
                    return await self._stream_completion(backend, request)
                else:
                    return await self._forward_completion(backend, request)
            except Exception as e:
                logger.error(f"Completion error: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @app.post("/v1/embeddings")
        async def embeddings(request: EmbeddingRequest) -> dict[str, Any]:
            """Create embeddings (OpenAI compatible)."""
            backend = self._get_embedding_backend(request.model)
            if not backend:
                raise HTTPException(
                    status_code=404,
                    detail=f"Embedding model '{request.model}' not found. Available models: {list(self._embedding_models.keys())}",
                )

            try:
                return await self._forward_embedding(backend, request)
            except Exception as e:
                logger.error(f"Embedding error: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @app.post("/v1/management/engines")
        async def management_start_engine(request: EngineStartRequest) -> dict[str, Any]:
            """Start a new managed engine via Control Plane."""

            manager = self._require_control_plane_manager()
            instance_type = self._parse_instance_type(request.instance_type)
            try:
                engine_info = manager.request_engine_startup(
                    model_id=request.model_id,
                    tensor_parallel_size=request.tensor_parallel_size,
                    pipeline_parallel_size=request.pipeline_parallel_size,
                    port=request.port,
                    instance_host=request.host,
                    instance_type=instance_type,
                    max_concurrent_requests=request.max_concurrent_requests,
                    extra_spawn_args=request.extra_args,
                    required_memory_gb=request.required_memory_gb,
                    engine_label=request.engine_label,
                    metadata=request.metadata,
                    engine_kind=request.engine_kind,
                    use_gpu=request.use_gpu,
                )
            except ValueError as exc:  # Invalid arguments
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            except RuntimeError as exc:  # Resource contention
                raise HTTPException(status_code=409, detail=str(exc)) from exc
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.error("Engine startup failed: %s", exc)
                raise HTTPException(status_code=500, detail=str(exc)) from exc

            return self._format_engine_start_response(engine_info)

        @app.delete("/v1/management/engines/{engine_id}")
        async def management_stop_engine(engine_id: str) -> dict[str, Any]:
            """Stop a managed engine via Control Plane."""

            manager = self._require_control_plane_manager()
            try:
                result = manager.request_engine_shutdown(engine_id)
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.error("Engine shutdown failed: %s", exc)
                raise HTTPException(status_code=500, detail=str(exc)) from exc

            if not result.get("stopped"):
                raise HTTPException(
                    status_code=409,
                    detail=f"Engine '{engine_id}' could not be stopped",
                )
            return result

        @app.get("/v1/management/status")
        async def management_cluster_status() -> dict[str, Any]:
            """Retrieve aggregated Control Plane cluster status."""

            manager = self._require_control_plane_manager()
            try:
                return manager.get_cluster_status()
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.error("Failed to collect cluster status: %s", exc)
                raise HTTPException(status_code=500, detail=str(exc)) from exc

    def _get_llm_backend(self, model: str) -> BackendInstanceConfig | None:
        """Get the backend configuration for an LLM model.

        Args:
            model: Model name to look up.

        Returns:
            Backend configuration if found, None otherwise.
        """
        # Exact match
        if model in self._llm_models:
            return self._llm_models[model]

        # If no exact match and we have backends, use the first one
        if self.config.llm_backends:
            return self.config.llm_backends[0]

        return None

    def _get_embedding_backend(self, model: str) -> BackendInstanceConfig | None:
        """Get the backend configuration for an embedding model.

        Args:
            model: Model name to look up.

        Returns:
            Backend configuration if found, None otherwise.
        """
        # Exact match
        if model in self._embedding_models:
            return self._embedding_models[model]

        # If no exact match and we have backends, use the first one
        if self.config.embedding_backends:
            return self.config.embedding_backends[0]

        return None

    async def _check_backends_health(self, backends: list[BackendInstanceConfig]) -> bool:
        """Check if any backend in the list is healthy.

        Args:
            backends: List of backend configurations to check.

        Returns:
            True if at least one backend is healthy.
        """
        if not self._http_session or not backends:
            return False

        for backend in backends:
            try:
                url = f"{backend.base_url}/health"
                async with self._http_session.get(
                    url, timeout=aiohttp.ClientTimeout(total=2)
                ) as resp:
                    if resp.status == 200:
                        return True
            except Exception:
                continue

        return False

    async def _forward_chat_completion(
        self, backend: BackendInstanceConfig, request: ChatCompletionRequest
    ) -> dict[str, Any]:
        """Forward a chat completion request to the backend.

        Args:
            backend: Backend instance configuration.
            request: Chat completion request.

        Returns:
            Response from the backend.
        """
        if not self._http_session:
            raise RuntimeError("HTTP session not initialized")

        url = f"{backend.base_url}/v1/chat/completions"
        headers = {"Content-Type": "application/json"}
        if backend.api_key:
            headers["Authorization"] = f"Bearer {backend.api_key}"

        payload = request.model_dump(exclude_none=True)

        async with self._http_session.post(url, json=payload, headers=headers) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                raise HTTPException(status_code=resp.status, detail=error_text)
            return await resp.json()

    async def _stream_chat_completion(
        self, backend: BackendInstanceConfig, request: ChatCompletionRequest
    ) -> StreamingResponse:
        """Stream a chat completion response from the backend.

        Args:
            backend: Backend instance configuration.
            request: Chat completion request.

        Returns:
            Streaming response.
        """
        if not self._http_session:
            raise RuntimeError("HTTP session not initialized")

        url = f"{backend.base_url}/v1/chat/completions"
        headers = {"Content-Type": "application/json"}
        if backend.api_key:
            headers["Authorization"] = f"Bearer {backend.api_key}"

        payload = request.model_dump(exclude_none=True)

        async def generate() -> AsyncGenerator[bytes, None]:
            async with self._http_session.post(url, json=payload, headers=headers) as resp:  # type: ignore[union-attr]
                if resp.status != 200:
                    error_text = await resp.text()
                    yield f"data: {error_text}\n\n".encode()
                    return

                async for chunk in resp.content.iter_any():
                    yield chunk

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
        )

    async def _forward_completion(
        self, backend: BackendInstanceConfig, request: CompletionRequest
    ) -> dict[str, Any]:
        """Forward a completion request to the backend.

        Args:
            backend: Backend instance configuration.
            request: Completion request.

        Returns:
            Response from the backend.
        """
        if not self._http_session:
            raise RuntimeError("HTTP session not initialized")

        url = f"{backend.base_url}/v1/completions"
        headers = {"Content-Type": "application/json"}
        if backend.api_key:
            headers["Authorization"] = f"Bearer {backend.api_key}"

        payload = request.model_dump(exclude_none=True)

        async with self._http_session.post(url, json=payload, headers=headers) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                raise HTTPException(status_code=resp.status, detail=error_text)
            return await resp.json()

    async def _stream_completion(
        self, backend: BackendInstanceConfig, request: CompletionRequest
    ) -> StreamingResponse:
        """Stream a completion response from the backend.

        Args:
            backend: Backend instance configuration.
            request: Completion request.

        Returns:
            Streaming response.
        """
        if not self._http_session:
            raise RuntimeError("HTTP session not initialized")

        url = f"{backend.base_url}/v1/completions"
        headers = {"Content-Type": "application/json"}
        if backend.api_key:
            headers["Authorization"] = f"Bearer {backend.api_key}"

        payload = request.model_dump(exclude_none=True)

        async def generate() -> AsyncGenerator[bytes, None]:
            async with self._http_session.post(url, json=payload, headers=headers) as resp:  # type: ignore[union-attr]
                if resp.status != 200:
                    error_text = await resp.text()
                    yield f"data: {error_text}\n\n".encode()
                    return

                async for chunk in resp.content.iter_any():
                    yield chunk

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
        )

    async def _forward_embedding(
        self, backend: BackendInstanceConfig, request: EmbeddingRequest
    ) -> dict[str, Any]:
        """Forward an embedding request to the backend.

        Args:
            backend: Backend instance configuration.
            request: Embedding request.

        Returns:
            Response from the backend.
        """
        if not self._http_session:
            raise RuntimeError("HTTP session not initialized")

        url = f"{backend.base_url}/v1/embeddings"
        headers = {"Content-Type": "application/json"}
        if backend.api_key:
            headers["Authorization"] = f"Bearer {backend.api_key}"

        payload = request.model_dump(exclude_none=True)

        async with self._http_session.post(url, json=payload, headers=headers) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                raise HTTPException(status_code=resp.status, detail=error_text)
            return await resp.json()

    def _format_engine_start_response(self, engine_info: dict[str, Any]) -> dict[str, Any]:
        """Flatten engine metadata for API consumers while preserving nested copy."""

        payload: dict[str, Any] = {"engine": engine_info}
        payload.update(engine_info)

        engine_id = engine_info.get("engine_id")
        if engine_id:
            payload.setdefault("id", engine_id)

        payload.setdefault("status", engine_info.get("status", "STARTING"))
        return payload

    def _require_control_plane_manager(self) -> ControlPlaneManager:
        """Return the active Control Plane manager or raise an HTTP error."""

        if not self._control_plane_manager:
            raise HTTPException(
                status_code=503,
                detail=(
                    "Control Plane management API is disabled. "
                    "Set UnifiedServerConfig.enable_control_plane=True to use it."
                ),
            )
        return self._control_plane_manager

    def _parse_instance_type(self, type_name: str) -> ExecutionInstanceType:
        """Convert a string into an ExecutionInstanceType enum value."""

        if ExecutionInstanceType is None:  # pragma: no cover - defensive guard
            raise HTTPException(status_code=503, detail="ExecutionInstanceType unavailable")

        try:
            return ExecutionInstanceType[type_name.upper()]
        except KeyError as exc:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Invalid instance_type. Expected one of "
                    f"{[t.name for t in ExecutionInstanceType]}"
                ),
            ) from exc

    @property
    def app(self) -> FastAPI:
        """Get the FastAPI application instance."""
        if self._app is None:
            self._app = self._create_app()
        return self._app

    def start(self, block: bool = True) -> None:
        """Start the API server.

        Args:
            block: If True, block until server is stopped.
                   If False, start server in background.
        """
        logger.info(f"Starting Unified API Server on {self.config.host}:{self.config.port}")

        config = uvicorn.Config(
            app=self.app,
            host=self.config.host,
            port=self.config.port,
            log_level=self.config.log_level,
        )

        self._server = uvicorn.Server(config)

        if block:
            self._server.run()
        else:
            # Run in background
            import threading

            thread = threading.Thread(target=self._server.run, daemon=True)
            thread.start()

            # Wait for server to start
            while not self._running:
                time.sleep(0.1)

    async def start_async(self) -> None:
        """Start the API server asynchronously."""
        logger.info(f"Starting Unified API Server on {self.config.host}:{self.config.port}")

        config = uvicorn.Config(
            app=self.app,
            host=self.config.host,
            port=self.config.port,
            log_level=self.config.log_level,
        )

        self._server = uvicorn.Server(config)
        await self._server.serve()

    def stop(self) -> None:
        """Stop the API server."""
        logger.info("Stopping Unified API Server...")
        self._running = False
        if self._server:
            self._server.should_exit = True

    def is_running(self) -> bool:
        """Check if the server is running.

        Returns:
            True if server is running.
        """
        return self._running

    def get_status(self) -> dict[str, Any]:
        """Get server status.

        Returns:
            Dictionary with server status information.
        """
        return {
            "running": self._running,
            "host": self.config.host,
            "port": self.config.port,
            "base_url": f"http://{self.config.host}:{self.config.port}",
            "llm_backends": len(self.config.llm_backends),
            "embedding_backends": len(self.config.embedding_backends),
            "llm_models": list(self._llm_models.keys()),
            "embedding_models": list(self._embedding_models.keys()),
            "control_plane_enabled": bool(self._control_plane_manager),
        }

    async def __aenter__(self) -> UnifiedAPIServer:
        """Async context manager entry."""
        # Start server in background
        import threading

        config = uvicorn.Config(
            app=self.app,
            host=self.config.host,
            port=self.config.port,
            log_level=self.config.log_level,
        )
        self._server = uvicorn.Server(config)

        thread = threading.Thread(target=self._server.run, daemon=True)
        thread.start()

        # Wait for server to be ready
        while not self._running:
            await asyncio.sleep(0.1)

        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        self.stop()

    def __enter__(self) -> UnifiedAPIServer:
        """Context manager entry - starts server in background."""
        self.start(block=False)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.stop()


# =============================================================================
# Factory functions
# =============================================================================


def create_unified_server(
    host: str = "0.0.0.0",
    port: int = 8000,
    llm_model: str | None = None,
    llm_backend_url: str | None = None,
    embedding_model: str | None = None,
    embedding_backend_url: str | None = None,
    scheduling_policy: str = "adaptive",
) -> UnifiedAPIServer:
    """Create a UnifiedAPIServer with simple configuration.

    This is a convenience function for creating a server with minimal
    configuration. For more advanced setups, use UnifiedServerConfig directly.

    Args:
        host: Server host address.
        port: Server port.
        llm_model: LLM model name.
        llm_backend_url: URL of the LLM backend (e.g., "http://localhost:8001").
        embedding_model: Embedding model name.
        embedding_backend_url: URL of the embedding backend.
        scheduling_policy: Scheduling policy name.

    Returns:
        Configured UnifiedAPIServer instance.

    Example:
        >>> server = create_unified_server(
        ...     port=8000,
        ...     llm_model="Qwen/Qwen2.5-7B-Instruct",
        ...     llm_backend_url="http://localhost:8001",
        ...     embedding_model="BAAI/bge-m3",
        ...     embedding_backend_url="http://localhost:8090",
        ... )
        >>> server.start()
    """
    llm_backends = []
    embedding_backends = []

    # Parse LLM backend
    if llm_backend_url:
        # Parse URL like "http://localhost:8001"
        from urllib.parse import urlparse

        parsed = urlparse(llm_backend_url)
        llm_backends.append(
            BackendInstanceConfig(
                host=parsed.hostname or "localhost",
                port=parsed.port or 8001,
                model_name=llm_model or "",
                instance_type="llm",
            )
        )

    # Parse Embedding backend
    if embedding_backend_url:
        from urllib.parse import urlparse

        parsed = urlparse(embedding_backend_url)
        embedding_backends.append(
            BackendInstanceConfig(
                host=parsed.hostname or "localhost",
                port=parsed.port or 8090,
                model_name=embedding_model or "",
                instance_type="embedding",
            )
        )

    policy = (
        SchedulingPolicyType(scheduling_policy)
        if scheduling_policy
        else SchedulingPolicyType.ADAPTIVE
    )

    config = UnifiedServerConfig(
        host=host,
        port=port,
        llm_backends=llm_backends if llm_backends else [],
        embedding_backends=embedding_backends if embedding_backends else [],
        scheduling_policy=policy,
    )

    return UnifiedAPIServer(config)


# =============================================================================
# CLI entry point
# =============================================================================


def main() -> None:
    """Command-line entry point for the Unified API Server."""
    import argparse

    parser = argparse.ArgumentParser(description="SAGE Unified Inference API Server")
    parser.add_argument("--host", default="0.0.0.0", help="Server host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Server port (default: 8000)")
    parser.add_argument("--llm-model", help="LLM model name")
    parser.add_argument("--llm-backend", help="LLM backend URL (e.g., http://localhost:8001)")
    parser.add_argument("--embedding-model", help="Embedding model name")
    parser.add_argument(
        "--embedding-backend", help="Embedding backend URL (e.g., http://localhost:8090)"
    )
    parser.add_argument(
        "--scheduling-policy",
        default="adaptive",
        choices=["fifo", "priority", "slo_aware", "adaptive", "hybrid"],
        help="Scheduling policy (default: adaptive)",
    )
    parser.add_argument(
        "--enable-control-plane",
        action="store_true",
        help="Enable Control Plane for dynamic engine management",
    )
    parser.add_argument("--log-level", default="info", help="Log level (default: info)")

    args = parser.parse_args()

    # Build configuration
    policy = SchedulingPolicyType(args.scheduling_policy)

    llm_backends = []
    embedding_backends = []

    # Parse LLM backend
    if args.llm_backend:
        from urllib.parse import urlparse

        parsed = urlparse(args.llm_backend)
        llm_backends.append(
            BackendInstanceConfig(
                host=parsed.hostname or "localhost",
                port=parsed.port or 8001,
                model_name=args.llm_model or "",
                instance_type="llm",
            )
        )

    # Parse Embedding backend
    if args.embedding_backend:
        from urllib.parse import urlparse

        parsed = urlparse(args.embedding_backend)
        embedding_backends.append(
            BackendInstanceConfig(
                host=parsed.hostname or "localhost",
                port=parsed.port or 8090,
                model_name=args.embedding_model or "",
                instance_type="embedding",
            )
        )

    config = UnifiedServerConfig(
        host=args.host,
        port=args.port,
        llm_backends=llm_backends if llm_backends else [],
        embedding_backends=embedding_backends if embedding_backends else [],
        scheduling_policy=policy,
        enable_control_plane=args.enable_control_plane,
        log_level=args.log_level,
    )

    server = UnifiedAPIServer(config)

    try:
        server.start(block=True)
    except KeyboardInterrupt:
        logger.info("Received interrupt, shutting down...")
        server.stop()


if __name__ == "__main__":
    main()
