# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""Control Plane management routes for SAGE Gateway.

This module provides HTTP endpoints for managing LLM and Embedding engines
through the sageLLM Control Plane. It handles engine lifecycle operations
including registration, startup, shutdown, and health monitoring.

Key Endpoints:
- POST /v1/management/engines - Start a new managed engine
- POST /v1/management/engines/register - Register an external engine
- GET /v1/management/engines - List all registered engines
- DELETE /v1/management/engines/{engine_id} - Stop an engine
- GET /v1/management/status - Get cluster status
- GET /v1/management/backends - List available backends
- GET /v1/management/gpu - Get GPU resource information
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Type checking imports
if TYPE_CHECKING:
    from sage.llm.control_plane import ControlPlaneManager, ExecutionInstanceType

# Optional imports for Control Plane
try:
    from sage.llm.control_plane import ControlPlaneManager as _ControlPlaneManager
    from sage.llm.control_plane import ExecutionInstanceType as _ExecutionInstanceType

    CONTROL_PLANE_AVAILABLE = True
except ImportError:
    CONTROL_PLANE_AVAILABLE = False
    _ControlPlaneManager = None  # type: ignore[assignment, misc]
    _ExecutionInstanceType = None  # type: ignore[assignment, misc]


# =============================================================================
# Request/Response Models
# =============================================================================


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
        description=(
            "GPU usage override. None=default (LLM uses GPU, Embedding does not), "
            "True=force GPU, False=force no GPU"
        ),
    )
    # Finetune-specific parameters
    dataset_path: str | None = Field(
        None,
        description="Path to training dataset (required for engine_kind=finetune)",
    )
    output_dir: str | None = Field(
        None,
        description="Output directory for checkpoints (required for engine_kind=finetune)",
    )
    lora_rank: int = Field(8, ge=1, description="LoRA rank for fine-tuning")
    lora_alpha: int = Field(16, ge=1, description="LoRA alpha scaling factor")
    learning_rate: float = Field(5e-5, gt=0, description="Learning rate for training")
    epochs: int = Field(3, ge=1, description="Number of training epochs")
    batch_size: int = Field(4, ge=1, description="Training batch size")
    gradient_accumulation_steps: int = Field(4, ge=1, description="Gradient accumulation steps")
    max_seq_length: int = Field(2048, ge=1, description="Maximum sequence length")
    use_flash_attention: bool = Field(True, description="Use Flash Attention 2")
    quantization_bits: int | None = Field(
        4,
        description="Quantization bits (4, 8, or None for full precision)",
    )
    auto_download: bool = Field(True, description="Auto-download base model if not found")


class EngineRegisterRequest(BaseModel):
    """Request body for registering an externally started engine.

    This allows engines that were started outside the Control Plane
    (e.g., manually or by external orchestration) to register themselves
    for discovery and health monitoring.
    """

    engine_id: str = Field(..., description="Unique identifier for the engine")
    model_id: str = Field(..., description="Model loaded on this engine")
    host: str = Field("localhost", description="Host where the engine is reachable")
    port: int = Field(..., description="Port the engine is listening on")
    engine_kind: str = Field(
        "llm",
        description="Runtime kind of engine (llm or embedding)",
    )
    metadata: dict[str, Any] | None = Field(
        None,
        description="Optional metadata attached to the engine",
    )


# =============================================================================
# Router
# =============================================================================

control_plane_router = APIRouter(prefix="/v1/management", tags=["Control Plane"])

# Global Control Plane Manager reference (set by init_control_plane())
_control_plane_manager: ControlPlaneManager | None = None


def init_control_plane(
    scheduling_policy: str = "adaptive",
    routing_strategy: str = "load_balanced",
    enable_pd_separation: bool = True,
) -> bool:
    """Initialize the Control Plane Manager.

    Args:
        scheduling_policy: Scheduling policy for request routing.
        routing_strategy: Strategy for routing requests to backends.
        enable_pd_separation: Enable prefill/decode separation.

    Returns:
        True if initialization succeeded, False otherwise.
    """
    global _control_plane_manager

    if not CONTROL_PLANE_AVAILABLE or _ControlPlaneManager is None:
        logger.warning(
            "Control Plane components not available. "
            "Ensure sageLLM submodule is properly initialized."
        )
        return False

    try:
        _control_plane_manager = _ControlPlaneManager(
            scheduling_policy=scheduling_policy,
            routing_strategy=routing_strategy,
            enable_pd_separation=enable_pd_separation,
            mode="http",
        )
        logger.info("Control Plane Manager initialized for SAGE Gateway")
        return True
    except Exception as exc:
        logger.error("Failed to initialize Control Plane Manager: %s", exc)
        _control_plane_manager = None
        return False


async def start_control_plane() -> None:
    """Start the Control Plane Manager (called during app startup)."""
    if _control_plane_manager:
        await _control_plane_manager.start()
        logger.info("Control Plane Manager started")

        # Discover and register existing engines (actual running vLLM processes)
        if _control_plane_manager.lifecycle_manager:
            try:
                discovered = _control_plane_manager.lifecycle_manager.discover_running_engines()
                if discovered:
                    logger.info(
                        "Auto-discovered %d running engines: %s",
                        len(discovered),
                        ", ".join(e["engine_id"] for e in discovered),
                    )
            except Exception as e:
                logger.warning("Failed to discover running engines: %s", e)

        # NOTE: We intentionally do NOT auto-register models from config/models.json
        # The Control Plane should only track actually running engines, not static config.
        # config/models.json is used by Studio as a "model template" for UI display only.
        # Engines should be registered via:
        #   1. sage llm engine start <model> --engine-kind llm
        #   2. discover_running_engines() for already-running vLLM processes
        #   3. POST /v1/management/engines/register for external engines


async def stop_control_plane() -> None:
    """Stop the Control Plane Manager (called during app shutdown)."""
    if _control_plane_manager:
        await _control_plane_manager.stop()
        logger.info("Control Plane Manager stopped")


def get_control_plane_manager() -> ControlPlaneManager | None:
    """Get the current Control Plane Manager instance."""
    return _control_plane_manager


def _require_control_plane_manager() -> ControlPlaneManager:
    """Return the active Control Plane manager or raise an HTTP error."""
    if not _control_plane_manager:
        raise HTTPException(
            status_code=503,
            detail=(
                "Control Plane management API is not available. "
                "Ensure Gateway was started with Control Plane enabled."
            ),
        )
    return _control_plane_manager


def _parse_instance_type(type_name: str) -> ExecutionInstanceType:
    """Convert a string into an ExecutionInstanceType enum value."""
    if _ExecutionInstanceType is None:
        raise HTTPException(status_code=503, detail="ExecutionInstanceType unavailable")

    try:
        return _ExecutionInstanceType[type_name.upper()]
    except KeyError as exc:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid instance_type. Expected one of {[t.name for t in _ExecutionInstanceType]}"
            ),
        ) from exc


def _format_engine_start_response(engine_info: dict[str, Any]) -> dict[str, Any]:
    """Flatten engine metadata for API consumers while preserving nested copy."""
    payload: dict[str, Any] = {"engine": engine_info}
    payload.update(engine_info)

    engine_id = engine_info.get("engine_id")
    if engine_id:
        payload.setdefault("id", engine_id)

    payload.setdefault("status", engine_info.get("status", "STARTING"))
    return payload


# =============================================================================
# Endpoints
# =============================================================================


@control_plane_router.get("")
async def control_plane_root() -> dict[str, Any]:
    """Control Plane management API root."""
    return {
        "service": "SAGE Gateway Control Plane",
        "status": "available" if _control_plane_manager else "unavailable",
        "endpoints": {
            "engines": "/v1/management/engines",
            "start_engine": "POST /v1/management/engines",
            "register_engine": "POST /v1/management/engines/register",
            "stop_engine": "DELETE /v1/management/engines/{engine_id}",
            "status": "/v1/management/status",
            "backends": "/v1/management/backends",
            "gpu": "/v1/management/gpu",
        },
    }


@control_plane_router.post("/engines")
async def start_engine(request: EngineStartRequest) -> dict[str, Any]:
    """Start a new managed engine via Control Plane.

    This endpoint requests the Control Plane to spawn a new LLM, Embedding,
    or Finetune engine with the specified configuration. The engine will be
    automatically registered and monitored.

    For finetune engines, dataset_path and output_dir are required.

    Returns:
        Engine information including ID, port, and initial state.
    """
    manager = _require_control_plane_manager()

    # Handle finetune engines separately
    if request.engine_kind == "finetune":
        if not request.dataset_path:
            raise HTTPException(
                status_code=400,
                detail="dataset_path is required for finetune engines",
            )
        if not request.output_dir:
            raise HTTPException(
                status_code=400,
                detail="output_dir is required for finetune engines",
            )

        try:
            engine_info = manager.start_finetune_engine(
                model_id=request.model_id,
                dataset_path=request.dataset_path,
                output_dir=request.output_dir,
                lora_rank=request.lora_rank,
                lora_alpha=request.lora_alpha,
                learning_rate=request.learning_rate,
                epochs=request.epochs,
                batch_size=request.batch_size,
                gradient_accumulation_steps=request.gradient_accumulation_steps,
                max_seq_length=request.max_seq_length,
                use_flash_attention=request.use_flash_attention,
                quantization_bits=request.quantization_bits,
                auto_download=request.auto_download,
                engine_label=request.engine_label,
                metadata=request.metadata,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except ImportError as exc:
            raise HTTPException(
                status_code=501,
                detail=str(exc),
            ) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except Exception as exc:
            logger.error("Finetune engine startup failed: %s", exc)
            raise HTTPException(status_code=500, detail=str(exc)) from exc

        return _format_engine_start_response(engine_info)

    # Handle LLM/Embedding engines
    instance_type = _parse_instance_type(request.instance_type)

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
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("Engine startup failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return _format_engine_start_response(engine_info)


@control_plane_router.post("/engines/register")
async def register_engine(request: EngineRegisterRequest) -> dict[str, Any]:
    """Register an externally started engine with the Control Plane.

    This endpoint allows engines that were started outside the Control
    Plane (e.g., manually or by external orchestration) to register
    themselves for discovery, health monitoring, and graceful shutdown.

    The engine will start in STARTING state and transition to READY
    after successful health checks.

    Returns:
        Engine registration information including state.
    """
    manager = _require_control_plane_manager()

    try:
        engine_info = manager.register_engine(
            engine_id=request.engine_id,
            model_id=request.model_id,
            host=request.host,
            port=request.port,
            engine_kind=request.engine_kind,
            metadata=request.metadata,
        )
        return engine_info.to_dict()
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("Engine registration failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@control_plane_router.get("/engines")
async def list_engines() -> dict[str, Any]:
    """List all registered engines with their states.

    Returns:
        Dictionary with list of registered engines and their states.
    """
    manager = _require_control_plane_manager()

    try:
        engines = manager.list_registered_engines()
        return {
            "engines": [e.to_dict() for e in engines],
            "count": len(engines),
        }
    except Exception as exc:
        logger.error("Failed to list engines: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@control_plane_router.delete("/engines/{engine_id}")
async def stop_engine(
    engine_id: str,
    drain: bool = Query(
        default=False,
        description="If true, gracefully drain the engine before stopping",
    ),
) -> dict[str, Any]:
    """Stop a managed engine via Control Plane.

    Args:
        engine_id: The ID of the engine to stop.
        drain: If True, gracefully drain the engine before stopping.
            The engine will stop accepting new requests but finish
            processing existing ones.

    Returns:
        Result of the stop operation.
    """
    manager = _require_control_plane_manager()

    try:
        if drain:
            success = await manager.stop_engine_gracefully(engine_id)
            return {
                "engine_id": engine_id,
                "stopped": success,
                "drained": True,
            }
        else:
            result = manager.request_engine_shutdown(engine_id)
            if not result.get("stopped"):
                raise HTTPException(
                    status_code=409,
                    detail=f"Engine '{engine_id}' could not be stopped",
                )
            return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Engine shutdown failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@control_plane_router.post("/engines/prune")
async def prune_engines() -> dict[str, Any]:
    """Remove all STOPPED/FAILED engine records from the registry.

    This endpoint cleans up stale engine records that are no longer running.
    Running engines are not affected.

    Returns:
        Count of pruned engines.
    """
    manager = _require_control_plane_manager()

    try:
        pruned = manager.prune_stopped_engines()
        return {"pruned_count": pruned, "status": "success"}
    except Exception as exc:
        logger.error("Engine prune failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@control_plane_router.get("/status")
async def cluster_status() -> dict[str, Any]:
    """Retrieve aggregated Control Plane cluster status.

    Returns:
        Dictionary with cluster status including resource usage,
        engine counts, and scheduling metrics.
    """
    manager = _require_control_plane_manager()

    try:
        return manager.get_cluster_status()
    except Exception as exc:
        logger.error("Failed to collect cluster status: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@control_plane_router.get("/backends")
async def list_backends() -> dict[str, Any]:
    """List all registered backends for dynamic discovery.

    Returns categorized lists of available LLM and Embedding backends
    with their health status. This endpoint enables clients to discover
    available services dynamically.

    Returns:
        Dictionary with llm_backends and embedding_backends lists.
    """
    manager = _require_control_plane_manager()

    try:
        return manager.get_registered_backends()
    except Exception as exc:
        logger.error("Failed to list registered backends: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@control_plane_router.get("/gpu")
async def gpu_resources() -> dict[str, Any]:
    """Get GPU resource information.

    Returns:
        Dictionary with GPU resource allocation and availability.
    """
    manager = _require_control_plane_manager()

    try:
        # Get GPU info from resource manager if available
        if hasattr(manager, "get_gpu_info"):
            return manager.get_gpu_info()  # type: ignore[attr-defined]
        else:
            # Fallback: collect basic GPU info
            return {
                "gpus": [],
                "message": "GPU info not available through Control Plane",
            }
    except Exception as exc:
        logger.error("Failed to get GPU resources: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
