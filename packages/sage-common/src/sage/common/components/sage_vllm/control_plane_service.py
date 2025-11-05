"""Control Plane-based vLLM service integration for SAGE.

Layer: L1 (Foundation - Common Components)

This module provides an advanced vLLM service using sageLLM's Control Plane for:
- Intelligent request scheduling (FIFO, Priority, SLO-Aware, Cost-Optimized, Adaptive)
- Multi-instance management and load balancing
- Prefilling/Decoding separation optimization
- Dynamic parallelism strategy selection
- Topology-aware routing (NVLINK, NUMA)
- Performance monitoring and metrics

Dependencies:
    - sage.common.service (L1 - BaseService interface)
    - sage.common.components.sage_vllm.sageLLM.control_plane (L1 - Control Plane)

Note:
    This service runs Control Plane in a background thread/task and provides
    a synchronous interface for SAGE compatibility.
"""

from __future__ import annotations

import asyncio
import threading
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from sage.common.service import BaseService

if TYPE_CHECKING:
    from sage.common.components.sage_vllm.sageLLM.control_plane import (
        ControlPlaneManager,
        ExecutionInstance,
        ExecutionInstanceType,
        RequestMetadata,
        RequestPriority,
    )

try:
    from sage.common.components.sage_vllm.sageLLM.control_plane import (
        ControlPlaneManager,
        ExecutionInstance,
        ExecutionInstanceType,
        RequestMetadata,
        RequestPriority,
    )

    CONTROL_PLANE_AVAILABLE = True
except ImportError:
    CONTROL_PLANE_AVAILABLE = False


@dataclass
class ControlPlaneVLLMServiceConfig:
    """Configuration for Control Plane-based vLLM service."""

    # Control Plane settings
    scheduling_policy: str = "adaptive"  # adaptive, slo_aware, priority, fifo, cost_optimized
    enable_pd_separation: bool = True  # Enable Prefilling/Decoding separation
    routing_strategy: str = "load_balanced"  # load_balanced, affinity, locality, topology_aware

    # Instance configurations
    instances: list[dict[str, Any]] = field(default_factory=list)

    # Default request settings
    default_priority: str = "NORMAL"
    default_slo_deadline_ms: int | None = None
    default_max_tokens: int = 512
    default_temperature: float = 0.7
    default_top_p: float = 0.95

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ControlPlaneVLLMServiceConfig:
        """Create config from dictionary."""
        return cls(
            scheduling_policy=data.get("scheduling_policy", "adaptive"),
            enable_pd_separation=data.get("enable_pd_separation", True),
            routing_strategy=data.get("routing_strategy", "load_balanced"),
            instances=data.get("instances", []),
            default_priority=data.get("default_priority", "NORMAL"),
            default_slo_deadline_ms=data.get("default_slo_deadline_ms"),
            default_max_tokens=data.get("default_max_tokens", 512),
            default_temperature=data.get("default_temperature", 0.7),
            default_top_p=data.get("default_top_p", 0.95),
        )


class ControlPlaneVLLMService(BaseService):
    """Advanced vLLM service using sageLLM Control Plane for intelligent scheduling and routing.

    This service provides a synchronous interface while running Control Plane asynchronously
    in the background. It manages the lifecycle of the Control Plane and translates between
    SAGE's synchronous service interface and Control Plane's async API.
    """

    def __init__(self, config: dict[str, Any]):
        super().__init__()
        if not CONTROL_PLANE_AVAILABLE:
            raise RuntimeError(
                "sageLLM Control Plane is not available. "
                "Please ensure the control_plane module is properly installed."
            )

        self.config = ControlPlaneVLLMServiceConfig.from_dict(config)
        self.control_plane: ControlPlaneManager
        self._loop: asyncio.AbstractEventLoop | None = None
        self._loop_thread: threading.Thread | None = None
        self._ready = threading.Event()

    # ------------------------------------------------------------------
    # SAGE lifecycle hooks
    # ------------------------------------------------------------------
    def setup(self) -> None:
        """Initialize Control Plane and start background event loop."""
        self.logger.info("ControlPlaneVLLMService setup starting")

        # Create and start event loop in background thread
        self._loop = asyncio.new_event_loop()
        self._loop_thread = threading.Thread(target=self._run_event_loop, daemon=True)
        self._loop_thread.start()

        # Wait for Control Plane to be ready
        self._ready.wait(timeout=30.0)

        self.logger.info(
            f"ControlPlaneVLLMService setup complete - "
            f"{len(self.config.instances)} instances registered"
        )

    def cleanup(self) -> None:
        """Shutdown Control Plane and stop event loop."""
        self.logger.info("ControlPlaneVLLMService cleanup starting")

        if self._loop and self._loop.is_running():
            # Schedule cleanup in the event loop
            future = asyncio.run_coroutine_threadsafe(self.control_plane.stop(), self._loop)
            try:
                future.result(timeout=10.0)
            except Exception as e:
                self.logger.error(f"Error during Control Plane shutdown: {e}")

            # Stop the event loop
            self._loop.call_soon_threadsafe(self._loop.stop)

        if self._loop_thread:
            self._loop_thread.join(timeout=5.0)

        self.logger.info("ControlPlaneVLLMService cleanup complete")

    # ------------------------------------------------------------------
    # Public service API
    # ------------------------------------------------------------------
    def process(self, payload: dict[str, Any]) -> Any:
        """Process requests through Control Plane.

        Args:
            payload: Request payload with task, inputs, and options

        Returns:
            Result based on task type
        """
        task = (payload or {}).get("task", "generate")
        inputs = (payload or {}).get("inputs")
        options = (payload or {}).get("options", {})

        if task == "generate":
            if inputs is None:
                raise ValueError("'generate' task requires 'inputs'")
            return self._sync_call(self._generate(inputs, options))

        if task == "show_instances":
            return self.show_instances()

        if task == "health_check":
            return self._sync_call(self.health_check_all())

        if task == "get_metrics":
            return self.get_metrics()

        raise ValueError(f"Unknown task: {task}")

    def generate(self, prompt: str, **options: Any) -> str:
        """Generate text using intelligent scheduling.

        Args:
            prompt: Input prompt
            **options: Generation options (priority, slo_deadline_ms, max_tokens, etc.)

        Returns:
            Generated text
        """
        return self._sync_call(self._generate(prompt, options))

    # ------------------------------------------------------------------
    # Information and monitoring methods
    # ------------------------------------------------------------------
    def show_instances(self) -> list[dict[str, Any]]:
        """Get information about all registered instances."""
        instances = self.control_plane.get_instances()
        return [
            {
                "instance_id": inst.instance_id,
                "host": inst.host,
                "port": inst.port,
                "model_name": inst.model_name,
                "instance_type": inst.instance_type.name,
                "gpu_count": inst.gpu_count,
                "is_available": inst.is_available,
                "is_healthy": inst.is_healthy,
                "current_load": inst.current_load,
                "active_requests": inst.active_requests,
            }
            for inst in instances
        ]

    def get_metrics(self) -> dict[str, Any]:
        """Get performance metrics from Control Plane."""
        metrics = self.control_plane.get_metrics()
        return {
            "total_requests": metrics.total_requests,
            "completed_requests": metrics.completed_requests,
            "failed_requests": metrics.failed_requests,
            "active_requests": metrics.active_requests,
            "avg_latency_ms": metrics.avg_latency_ms,
            "p50_latency_ms": metrics.p50_latency_ms,
            "p95_latency_ms": metrics.p95_latency_ms,
            "p99_latency_ms": metrics.p99_latency_ms,
            "slo_compliance_rate": metrics.slo_compliance_rate,
            "requests_per_second": metrics.requests_per_second,
        }

    # ------------------------------------------------------------------
    # Internal async methods
    # ------------------------------------------------------------------
    def _run_event_loop(self) -> None:
        """Run event loop in background thread."""
        asyncio.set_event_loop(self._loop)
        if self._loop is None:
            raise RuntimeError(
                "Event loop is not initialized (self._loop is None) in _run_event_loop."
            )

        try:
            # Initialize Control Plane
            self.control_plane = ControlPlaneManager(
                scheduling_policy=self.config.scheduling_policy,
                routing_strategy=self.config.routing_strategy,
                mode="http",
                enable_pd_separation=self.config.enable_pd_separation,
            )

            # Register instances
            for instance_config in self.config.instances:
                instance = self._create_instance(instance_config)
                self.control_plane.register_instance(instance)
                self.logger.info(
                    f"Registered instance {instance.instance_id} at {instance.host}:{instance.port}"
                )

            # Start Control Plane
            self._loop.run_until_complete(self.control_plane.start())
            self._ready.set()

            # Run event loop
            self._loop.run_forever()

        except Exception as e:
            self.logger.error(f"Event loop error: {e}")
            raise
        finally:
            self._loop.close()

    async def _generate(self, prompt: str, options: dict[str, Any]) -> str:
        """Generate text asynchronously.

        Args:
            prompt: Input prompt
            options: Generation options

        Returns:
            Generated text
        """
        # Create request metadata
        request = self._create_request(prompt, options)

        # Submit to Control Plane
        request_id = await self.control_plane.submit_request(request)

        # Wait for completion (simplified - in production should use callbacks/futures)
        from sage.common.components.sage_vllm.sageLLM.control_plane import RequestStatus

        # Default timeout: 300 seconds (5 minutes)
        timeout = options.get("timeout", 300.0)
        start_time = asyncio.get_event_loop().time()

        while True:
            # Check timeout
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > timeout:
                raise TimeoutError(f"Request {request_id} timed out after {timeout} seconds")

            status = await self.control_plane.get_request_status(request_id)
            if status == RequestStatus.COMPLETED:
                # In a real implementation, we'd get the actual result
                # For now, return a placeholder
                return f"[Generated response for: {prompt[:50]}...]"
            elif status == RequestStatus.FAILED:
                raise RuntimeError(f"Request {request_id} failed")
            await asyncio.sleep(0.1)

    async def health_check_all(self) -> dict[str, bool]:
        """Check health of all instances.

        Returns:
            Dictionary mapping instance_id to health status
        """
        return await self.control_plane.executor.health_check_all()

    def _create_instance(self, config: dict[str, Any]) -> ExecutionInstance:
        """Create ExecutionInstance from configuration."""
        instance_type = ExecutionInstanceType.GENERAL
        if "instance_type" in config:
            instance_type = ExecutionInstanceType[config["instance_type"]]

        return ExecutionInstance(
            instance_id=config["instance_id"],
            host=config["host"],
            port=config["port"],
            model_name=config["model_name"],
            instance_type=instance_type,
            tensor_parallel_size=config.get("tensor_parallel_size", 1),
            pipeline_parallel_size=config.get("pipeline_parallel_size", 1),
            gpu_count=config.get("gpu_count", 1),
            gpu_memory_gb=config.get("gpu_memory_gb", 80.0),
            max_concurrent_requests=config.get("max_concurrent_requests", 256),
        )

    def _create_request(self, prompt: str, options: dict[str, Any]) -> RequestMetadata:
        """Create RequestMetadata from prompt and options."""
        request_id = options.get("request_id", str(uuid.uuid4()))

        # Parse priority
        priority_str = options.get("priority", self.config.default_priority)
        priority = RequestPriority[priority_str]

        return RequestMetadata(
            request_id=request_id,
            prompt=prompt,
            priority=priority,
            slo_deadline_ms=options.get("slo_deadline_ms", self.config.default_slo_deadline_ms),
            max_tokens=options.get("max_tokens", self.config.default_max_tokens),
            temperature=options.get("temperature", self.config.default_temperature),
            top_p=options.get("top_p", self.config.default_top_p),
        )

    def _sync_call(self, coro: Any) -> Any:
        """Execute async coroutine synchronously.

        Args:
            coro: Coroutine to execute

        Returns:
            Result of coroutine
        """
        if not self._loop:
            raise RuntimeError("Event loop not initialized")

        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout=30.0)
