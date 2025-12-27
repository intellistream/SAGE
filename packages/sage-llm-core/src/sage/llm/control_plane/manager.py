# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""Control Plane Manager - orchestrates scheduling, routing, and execution."""

from __future__ import annotations

import asyncio
import json
import logging
import threading
from collections import deque
from datetime import datetime
from typing import TYPE_CHECKING, Any, Literal

from sage.common.config.ports import SagePorts
from sage.common.config.user_paths import get_user_paths

if TYPE_CHECKING:  # pragma: no cover - type checking only
    from .engine_lifecycle import EngineLifecycleManager, EngineRuntime
    from .gpu_manager import GPUResourceManager

try:  # pragma: no cover - optional dependency wiring
    from .engine_lifecycle import (
        EngineLifecycleManager as RuntimeEngineLifecycleManager,
    )
    from .engine_lifecycle import (
        EngineRuntime,
    )
except ImportError:  # pragma: no cover - handled gracefully
    RuntimeEngineLifecycleManager = None
    EngineRuntime = None  # type: ignore[assignment]

try:  # pragma: no cover - optional dependency wiring
    from .gpu_manager import GPUResourceManager as RuntimeGPUResourceManager
except ImportError:  # pragma: no cover - handled gracefully
    RuntimeGPUResourceManager = None

from .autoscaler import Autoscaler, AutoscalerConfig
from .executors import (
    ExecutionCoordinatorBase,
    HttpExecutionCoordinator,
    LocalAsyncExecutionCoordinator,
)
from .metrics_collector import MetricsCollector as AutoscalerMetricsCollector
from .monitoring import MetricsCollector
from .parallelism import ParallelismOptimizer
from .pd_routing import PDRoutingStrategy
from .router import LoadBalancer, RequestRouter
from .strategies import (
    AdaptivePolicy,
    AegaeonPolicy,
    CostOptimizedPolicy,
    FIFOPolicy,
    PriorityPolicy,
    SchedulingPolicy,
    SLOAwarePolicy,
)
from .types import (
    EngineInfo,
    EngineState,
    ExecutionInstance,
    ExecutionInstanceType,
    InstanceMetrics,
    PDSeparationConfig,
    PerformanceMetrics,
    RequestMetadata,
    RequestStatus,
    RequestType,
    SchedulingDecision,
    SchedulingMetrics,
)

logger = logging.getLogger(__name__)


class ControlPlaneManager:
    """
    Main Control Plane Manager for sageLLM.

    Coordinates request scheduling, routing, and execution across multiple
    vLLM instances with intelligent parallelism strategies.
    """

    def __init__(
        self,
        scheduling_policy: str = "adaptive",
        routing_strategy: str = "load_balanced",
        enable_auto_scaling: bool = False,
        enable_monitoring: bool = True,
        enable_pd_separation: bool = True,
        pd_config: PDSeparationConfig | None = None,
        autoscaler_config: AutoscalerConfig | None = None,
        mode: Literal["http", "local"] = "http",
        auto_restart: bool = True,
        max_restart_attempts: int = 3,
        health_check_interval: float = 10.0,
        health_check_timeout: float = 5.0,
        restart_backoff_base: float = 1.0,
        consecutive_failures_threshold: int = 2,
    ):
        """
        Initialize Control Plane Manager.

        Args:
            scheduling_policy: Scheduling policy to use
                - "fifo": First-In-First-Out
                - "priority": Priority-based
                - "slo_aware": SLO-aware scheduling
                - "cost_optimized": Cost-optimized
                - "adaptive": Adaptive policy selection
            routing_strategy: Request routing strategy
            enable_auto_scaling: Enable automatic instance scaling
            enable_monitoring: Enable performance monitoring
            enable_pd_separation: Enable Prefilling/Decoding separation
            pd_config: PD separation configuration
            autoscaler_config: Autoscaler configuration
            auto_restart: Enable automatic engine restart on failure
            max_restart_attempts: Maximum number of restart attempts per engine
            health_check_interval: Interval between health checks in seconds
            health_check_timeout: Timeout for each health check request
            restart_backoff_base: Base time in seconds for exponential backoff
            consecutive_failures_threshold: Number of consecutive failures before restart
        """

        # Core components
        # Choose executor implementation based on mode ('http' or 'local')
        self.mode = mode
        executor: ExecutionCoordinatorBase
        if mode == "http":
            executor = HttpExecutionCoordinator()
        elif mode == "local":
            executor = LocalAsyncExecutionCoordinator()
        else:
            logger.warning(
                "Unknown mode '%s' for ControlPlaneManager, defaulting to 'http'",
                mode,
            )
            executor = HttpExecutionCoordinator()
        self.executor = executor
        self.router = RequestRouter(routing_strategy)
        self.load_balancer = LoadBalancer()
        self.parallelism_optimizer = ParallelismOptimizer()
        self.gpu_manager: GPUResourceManager | None = self._init_gpu_manager()
        self.lifecycle_manager: EngineLifecycleManager | None = (
            self._init_engine_lifecycle_manager()
        )
        self._engine_registry: dict[str, dict[str, Any]] = {}
        self._engine_registry_lock = threading.Lock()
        self._reserved_ports: set[int] = set()

        # Set executor callback for failure handling
        self.executor.set_manager_callback(self)

        # PD Separation routing
        self.enable_pd_separation = enable_pd_separation
        self.pd_config = pd_config or PDSeparationConfig()
        self.pd_router: PDRoutingStrategy | None = (
            PDRoutingStrategy(self.pd_config) if enable_pd_separation else None
        )

        # Scheduling policy
        self.scheduling_policy = self._create_policy(scheduling_policy)

        # Request queues
        self.pending_queue: deque[RequestMetadata] = deque()
        self.running_requests: dict[str, RequestMetadata] = {}

        # Configuration
        self.enable_auto_scaling = enable_auto_scaling
        self.enable_monitoring = enable_monitoring

        # Monitoring (from original code for scheduling metrics)
        self.metrics_collector = MetricsCollector()

        # Autoscaler (SLA-based dynamic scaling)
        self.autoscaler: Autoscaler | None = None
        self.autoscaler_metrics_collector: AutoscalerMetricsCollector | None = None
        if enable_auto_scaling:
            self.autoscaler_metrics_collector = AutoscalerMetricsCollector(
                executor_coordinator=self.executor
            )
            self.autoscaler = Autoscaler(
                config=autoscaler_config or AutoscalerConfig(),
                metrics_collector=self.autoscaler_metrics_collector,
                executor_callback=self._handle_scaling_decision,
            )
            logger.info("Autoscaler enabled")

        # Auto-restart configuration
        self.auto_restart = auto_restart
        self.max_restart_attempts = max_restart_attempts
        self.health_check_interval = health_check_interval
        self.health_check_timeout = health_check_timeout
        self.restart_backoff_base = restart_backoff_base
        self.consecutive_failures_threshold = consecutive_failures_threshold

        # Auto-restart state tracking
        # engine_id -> {"consecutive_failures": int, "restart_count": int, "last_restart_time": float}
        self._engine_health_state: dict[str, dict[str, Any]] = {}
        self._engine_health_state_lock = threading.Lock()

        # Persistence for engine registry
        self.paths = get_user_paths()
        self.registry_file = self.paths.state_dir / "control_plane_registry.json"
        self.registry_file.parent.mkdir(parents=True, exist_ok=True)
        # Engine registration tracking (for Task 1A: Engine registration and lifecycle)
        # Maps engine_id to EngineInfo for state tracking and heartbeat management
        self._registered_engines: dict[str, EngineInfo] = {}
        self._registered_engines_lock = threading.Lock()

        # Background tasks
        self.background_tasks: list[asyncio.Task] = []
        self._running = False

        logger.info(
            "Control Plane initialized with policy=%s, routing=%s, pd_separation=%s, "
            "autoscaling=%s, auto_restart=%s",
            scheduling_policy,
            routing_strategy,
            enable_pd_separation,
            enable_auto_scaling,
            auto_restart,
        )

    def _save_registry(self) -> None:
        """Persist the registered engines to disk."""
        try:
            with self._registered_engines_lock:
                data = {"engines": [e.to_dict() for e in self._registered_engines.values()]}
            with open(self.registry_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as exc:  # pragma: no cover - defensive persistence
            logger.error("Failed to save registry: %s", exc)

    def _load_registry(self) -> None:
        """Load registered engines from disk."""
        if not self.registry_file.exists():
            return

        try:
            logger.info("Loading registry from %s", self.registry_file)
            with open(self.registry_file) as f:
                data = json.load(f)

            for engine_data in data.get("engines", []):
                engine_id = engine_data["engine_id"]
                with self._registered_engines_lock:
                    if engine_id in self._registered_engines:
                        continue

                try:
                    # Use register_engine for side effects (instances, ports)
                    self.register_engine(
                        engine_id=engine_id,
                        model_id=engine_data["model_id"],
                        host=engine_data["host"],
                        port=engine_data["port"],
                        engine_kind=engine_data.get("engine_kind", "llm"),
                        metadata=engine_data.get("metadata", {}),
                        _skip_save=True,
                    )
                    logger.info("Restored engine %s from registry", engine_id)
                except Exception as exc:  # pragma: no cover - defensive persistence
                    logger.error("Failed to restore engine %s: %s", engine_id, exc)

        except Exception as exc:  # pragma: no cover - defensive persistence
            logger.error("Failed to load registry: %s", exc)

    def _create_policy(self, policy_name: str) -> SchedulingPolicy:
        """Create scheduling policy instance."""

        policies = {
            "fifo": FIFOPolicy(),
            "priority": PriorityPolicy(),
            "slo_aware": SLOAwarePolicy(),
            "cost_optimized": CostOptimizedPolicy(),
            "adaptive": AdaptivePolicy(),
            "aegaeon": AegaeonPolicy(),
        }

        return policies.get(policy_name, AdaptivePolicy())

    async def start(self):
        """Start the control plane background tasks."""
        if self._running:
            logger.warning("Control plane already running")
            return

        self._running = True
        logger.info("Starting Control Plane...")
        # Load persisted registry and discover running engines if available
        self._load_registry()

        if self.lifecycle_manager:
            try:
                logger.info("Discovering existing engines...")
                discovered = self.lifecycle_manager.discover_running_engines()
                logger.info("Discovered %d existing engines", len(discovered))
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.warning("Failed to discover existing engines: %s", exc)
        # Start scheduling loop
        task = asyncio.create_task(self._scheduling_loop())
        self.background_tasks.append(task)

        # Start health check loop (for execution instances)
        task = asyncio.create_task(self._health_check_loop())
        self.background_tasks.append(task)

        # Start engine health check and auto-restart loop if enabled
        if self.auto_restart and self.lifecycle_manager:
            task = asyncio.create_task(self._engine_health_and_restart_loop())
            self.background_tasks.append(task)
            logger.info("Engine auto-restart enabled")

        # Start autoscaler if enabled
        if self.autoscaler:
            await self.autoscaler.start()
            logger.info("Autoscaler started")

        # Start monitoring loop if enabled
        if self.enable_monitoring:
            task = asyncio.create_task(self._monitoring_loop())
            self.background_tasks.append(task)

        logger.info("Control Plane started successfully")

    async def stop(self):
        """Stop the control plane."""
        if not self._running:
            return

        logger.info("Stopping Control Plane...")
        self._running = False

        # Stop autoscaler
        if self.autoscaler:
            await self.autoscaler.stop()

        # Cancel background tasks
        for task in self.background_tasks:
            task.cancel()

        await asyncio.gather(*self.background_tasks, return_exceptions=True)
        self.background_tasks.clear()

        logger.info("Control Plane stopped")

    def register_instance(self, instance: ExecutionInstance):
        """Register a new vLLM execution instance."""
        self.executor.register_instance(instance)

    def unregister_instance(self, instance_id: str):
        """Unregister an execution instance."""
        self.executor.unregister_instance(instance_id)

    # ------------------------------------------------------------------
    # Engine Registration and State Management (Task 1A)
    # ------------------------------------------------------------------

    def register_engine(
        self,
        engine_id: str,
        model_id: str,
        host: str,
        port: int,
        engine_kind: str = "llm",
        metadata: dict[str, Any] | None = None,
        _skip_save: bool = False,
    ) -> EngineInfo:
        """Register a new engine with the Control Plane.

        This method should be called after an engine process has been spawned
        and is starting up. It creates an ExecutionInstance and registers it
        with the executor for request routing.

        Args:
            engine_id: Unique identifier for the engine.
            model_id: The model loaded on this engine.
            host: Hostname or IP address of the engine.
            port: Port number the engine is listening on.
            engine_kind: Type of engine ('llm' or 'embedding').
            metadata: Optional additional metadata.
            _skip_save: Internal flag to skip saving registry (used during load).

        Returns:
            EngineInfo object representing the registered engine.

        Raises:
            ValueError: If an engine with the same ID is already registered.
        """
        with self._registered_engines_lock:
            if engine_id in self._registered_engines:
                raise ValueError(f"Engine {engine_id} is already registered")

            engine_info = EngineInfo(
                engine_id=engine_id,
                model_id=model_id,
                host=host,
                port=port,
                state=EngineState.STARTING,
                engine_kind=engine_kind,
                metadata=dict(metadata) if metadata else {},
            )
            self._registered_engines[engine_id] = engine_info

        # Create and register ExecutionInstance for request routing
        instance_metadata = dict(metadata or {})
        instance_metadata.setdefault("engine_kind", engine_kind)

        # Determine instance type
        if engine_kind == "embedding":
            instance_type = ExecutionInstanceType.EMBEDDING
        else:
            instance_type = ExecutionInstanceType.GENERAL

        instance = ExecutionInstance(
            instance_id=engine_id,
            host=host if host != "0.0.0.0" else "localhost",
            port=port,
            model_name=model_id,
            instance_type=instance_type,
            metadata=instance_metadata,
            supported_request_types=(
                [RequestType.EMBEDDING] if engine_kind == "embedding" else None
            ),
            embedding_model_loaded=model_id if engine_kind == "embedding" else None,
        )
        self.register_instance(instance)

        # Reserve the port
        self._reserved_ports.add(port)

        if not _skip_save:
            self._save_registry()
        logger.info(
            "Engine %s registered (model=%s, host=%s:%d, kind=%s)",
            engine_id,
            model_id,
            host,
            port,
            engine_kind,
        )
        return engine_info

    def unregister_engine(self, engine_id: str) -> EngineInfo | None:
        """Unregister an engine from the Control Plane.

        This removes the engine from the registration tracking. The engine
        should be stopped before calling this method.

        Args:
            engine_id: The ID of the engine to unregister.

        Returns:
            The EngineInfo that was removed, or None if not found.
        """
        with self._registered_engines_lock:
            engine_info = self._registered_engines.pop(engine_id, None)

        if engine_info:
            logger.info("Engine %s unregistered", engine_id)
            self._save_registry()
        else:
            logger.warning("Attempted to unregister unknown engine %s", engine_id)

        return engine_info

    def get_engine_info(self, engine_id: str) -> EngineInfo | None:
        """Get information about a registered engine.

        Args:
            engine_id: The ID of the engine.

        Returns:
            EngineInfo if found, None otherwise.
        """
        with self._registered_engines_lock:
            return self._registered_engines.get(engine_id)

    def get_engine_state(self, engine_id: str) -> EngineState | None:
        """Get the current state of a registered engine.

        Args:
            engine_id: The ID of the engine.

        Returns:
            EngineState if found, None otherwise.
        """
        engine_info = self.get_engine_info(engine_id)
        return engine_info.state if engine_info else None

    def list_registered_engines(
        self,
        state_filter: EngineState | None = None,
    ) -> list[EngineInfo]:
        """List all registered engines, optionally filtered by state.

        Args:
            state_filter: If provided, only return engines in this state.

        Returns:
            List of EngineInfo objects.
        """
        with self._registered_engines_lock:
            engines = list(self._registered_engines.values())

        if state_filter is not None:
            engines = [e for e in engines if e.state == state_filter]

        return engines

    def update_engine_state(
        self,
        engine_id: str,
        new_state: EngineState,
        *,
        reset_failures: bool = False,
    ) -> bool:
        """Update the state of a registered engine.

        This method handles state transitions and validates them according
        to the EngineState state machine.

        Args:
            engine_id: The ID of the engine.
            new_state: The new state to transition to.
            reset_failures: If True, reset the consecutive_failures counter.

        Returns:
            True if the state was updated, False if engine not found.
        """
        with self._registered_engines_lock:
            engine_info = self._registered_engines.get(engine_id)
            if not engine_info:
                logger.warning("Cannot update state for unknown engine %s", engine_id)
                return False

            old_state = engine_info.state
            engine_info.state = new_state

            if reset_failures:
                engine_info.consecutive_failures = 0

            logger.info(
                "Engine %s state changed: %s -> %s",
                engine_id,
                old_state.value,
                new_state.value,
            )

        return True

    def record_engine_heartbeat(self, engine_id: str) -> bool:
        """Record a successful heartbeat for an engine.

        This method should be called when an engine health check succeeds.
        It updates the last_heartbeat timestamp and resets failure counters.
        If the engine is in STARTING state, it transitions to READY.

        Args:
            engine_id: The ID of the engine.

        Returns:
            True if heartbeat was recorded, False if engine not found.
        """
        with self._registered_engines_lock:
            engine_info = self._registered_engines.get(engine_id)
            if not engine_info:
                return False

            engine_info.last_heartbeat = datetime.now()
            engine_info.consecutive_failures = 0

            # Transition from STARTING to READY on first successful heartbeat
            if engine_info.state == EngineState.STARTING:
                engine_info.state = EngineState.READY
                logger.info("Engine %s is now READY", engine_id)

        return True

    def record_engine_failure(self, engine_id: str) -> int:
        """Record a health check failure for an engine.

        This method increments the consecutive failure counter. If the
        counter reaches the threshold (default 3), the engine transitions
        to ERROR state.

        Args:
            engine_id: The ID of the engine.

        Returns:
            The new consecutive failure count, or -1 if engine not found.
        """
        with self._registered_engines_lock:
            engine_info = self._registered_engines.get(engine_id)
            if not engine_info:
                return -1

            engine_info.consecutive_failures += 1
            failure_count = engine_info.consecutive_failures

            # Transition to ERROR after consecutive failures threshold
            if failure_count >= self.consecutive_failures_threshold and engine_info.state not in (
                EngineState.STOPPED,
                EngineState.ERROR,
            ):
                engine_info.state = EngineState.ERROR
                logger.warning(
                    "Engine %s entered ERROR state after %d consecutive failures",
                    engine_id,
                    failure_count,
                )

        return failure_count

    def start_engine_drain(self, engine_id: str) -> bool:
        """Start draining an engine for graceful shutdown.

        This transitions the engine to DRAINING state, which means it will
        stop accepting new requests but continue processing existing ones.

        Args:
            engine_id: The ID of the engine.

        Returns:
            True if drain was started, False if engine not found or
            already in terminal state.
        """
        with self._registered_engines_lock:
            engine_info = self._registered_engines.get(engine_id)
            if not engine_info:
                logger.warning("Cannot drain unknown engine %s", engine_id)
                return False

            if engine_info.is_terminal:
                logger.warning(
                    "Cannot drain engine %s in terminal state %s",
                    engine_id,
                    engine_info.state.value,
                )
                return False

            engine_info.state = EngineState.DRAINING
            logger.info("Engine %s is now DRAINING", engine_id)

        return True

    def check_engine_drain_complete(self, engine_id: str) -> bool:
        """Check if an engine has finished draining.

        An engine is considered drained when it has no active requests.

        Args:
            engine_id: The ID of the engine.

        Returns:
            True if engine is drained (no active requests), False otherwise.
        """
        with self._registered_engines_lock:
            engine_info = self._registered_engines.get(engine_id)
            if not engine_info:
                return True  # Non-existent engine is considered drained

            if engine_info.state != EngineState.DRAINING:
                return False

            return engine_info.active_requests == 0

    def update_engine_active_requests(
        self,
        engine_id: str,
        active_requests: int,
    ) -> bool:
        """Update the active request count for an engine.

        Args:
            engine_id: The ID of the engine.
            active_requests: The current number of active requests.

        Returns:
            True if updated, False if engine not found.
        """
        with self._registered_engines_lock:
            engine_info = self._registered_engines.get(engine_id)
            if not engine_info:
                return False

            engine_info.active_requests = active_requests

        return True

    async def stop_engine_gracefully(
        self,
        engine_id: str,
        timeout: float = 30.0,
    ) -> bool:
        """Stop an engine gracefully with draining.

        This method:
        1. Transitions the engine to DRAINING state
        2. Waits for active requests to complete (up to timeout)
        3. Stops the engine process
        4. Transitions to STOPPED state

        Args:
            engine_id: The ID of the engine to stop.
            timeout: Maximum time to wait for draining in seconds.

        Returns:
            True if engine was stopped gracefully, False otherwise.
        """
        # Start draining
        if not self.start_engine_drain(engine_id):
            return False

        # Wait for drain to complete
        start_time = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start_time < timeout:
            if self.check_engine_drain_complete(engine_id):
                logger.info("Engine %s drain complete", engine_id)
                break
            await asyncio.sleep(0.5)
        else:
            logger.warning(
                "Engine %s drain timeout after %.1f seconds, forcing stop",
                engine_id,
                timeout,
            )

        # Stop the engine process
        if self.lifecycle_manager:
            self.lifecycle_manager.stop_engine(engine_id)

        # Release resources (port, GPU, instance registration)
        engine_entry = self._pop_engine_metadata(engine_id)
        if engine_entry:
            gpu_ids = engine_entry.get("gpu_ids", [])
            memory_per_gpu_gb = engine_entry.get("memory_per_gpu_gb", 0.0)
            port = engine_entry.get("port")
            instance_id = engine_entry.get("instance_id")

            if gpu_ids and memory_per_gpu_gb and self.gpu_manager:
                self.gpu_manager.release_resources(gpu_ids, memory_per_gpu_gb)
            if port:
                self._release_port(port)
            if instance_id:
                self.unregister_instance(instance_id)

        # Clean up health state tracking
        with self._engine_health_state_lock:
            self._engine_health_state.pop(engine_id, None)

        # Update state to STOPPED
        self.update_engine_state(engine_id, EngineState.STOPPED)

        logger.info("Engine %s stopped gracefully and resources released", engine_id)
        return True

    async def submit_request(
        self,
        request: RequestMetadata,
    ) -> str:
        """
        Submit a new inference request.

        Args:
            request: Request metadata

        Returns:
            Request ID
        """

        # Add to pending queue
        request.queue_time = datetime.now()
        self.pending_queue.append(request)

        logger.info(
            "Request %s submitted (priority=%s, queue_size=%d)",
            request.request_id,
            request.priority.name,
            len(self.pending_queue),
        )

        return request.request_id

    async def get_request_status(self, request_id: str) -> RequestStatus | None:
        """Get status of a request."""

        # Check if running
        if request_id in self.running_requests:
            return RequestStatus.RUNNING

        # Check if in queue
        for req in self.pending_queue:
            if req.request_id == request_id:
                return RequestStatus.QUEUED

        return None

    async def cancel_request(self, request_id: str) -> bool:
        """Cancel a pending request."""

        # Remove from pending queue
        for _i, req in enumerate(self.pending_queue):
            if req.request_id == request_id:
                self.pending_queue.remove(req)
                logger.info("Request %s cancelled", request_id)
                return True

        logger.warning("Request %s not found or already running", request_id)
        return False

    async def on_instance_failure(
        self,
        instance_id: str,
        failed_requests: list[tuple[str, RequestMetadata]],
    ):
        """
        Handle instance failure by rescheduling affected requests.

        Args:
            instance_id: ID of the failed instance
            failed_requests: List of (request_id, request) tuples that were running
        """
        logger.warning(
            "Handling instance failure for %s, rescheduling %d requests",
            instance_id,
            len(failed_requests),
        )

        # Record failure in metrics
        self.metrics_collector.record_instance_failure(instance_id)

        # Reschedule each failed request
        for req_id, request in failed_requests:
            # Track retry count
            request.tags["retry_count"] = request.tags.get("retry_count", 0) + 1

            # Check retry limit (max 3 retries)
            if request.tags["retry_count"] > 3:
                logger.error("Request %s exceeded retry limit, marking as failed", req_id)
                self.running_requests.pop(req_id, None)
                continue

            # Re-add to pending queue (at the front for priority)
            request.queue_time = datetime.now()
            self.pending_queue.appendleft(request)

            # Remove from running requests
            self.running_requests.pop(req_id, None)

            logger.info(
                "Request %s rescheduled (retry: %d/%d)",
                req_id,
                request.tags["retry_count"],
                3,
            )

        logger.info(
            "Instance %s failure handled, %d requests rescheduled",
            instance_id,
            len(failed_requests),
        )

    async def _scheduling_loop(self):
        """Main scheduling loop."""

        while self._running:
            try:
                # Record queue length for metrics
                self.metrics_collector.record_queue_length(len(self.pending_queue))

                await self._schedule_pending_requests()
                await asyncio.sleep(0.1)  # Schedule every 100ms
            except Exception as e:
                logger.error("Scheduling loop error: %s", e)

    async def _schedule_pending_requests(self):
        """Schedule pending requests to instances."""

        if not self.pending_queue:
            return

        # Get available instances
        instances = self.executor.get_available_instances()
        if not instances:
            return

        # Get requests to schedule (up to available capacity)
        requests_to_schedule = []
        max_schedule = sum(max(0, i.max_concurrent_requests - i.active_requests) for i in instances)

        for _ in range(min(len(self.pending_queue), max_schedule)):
            if self.pending_queue:
                requests_to_schedule.append(self.pending_queue.popleft())

        if not requests_to_schedule:
            return

        # Apply scheduling policy
        decisions = self.scheduling_policy.schedule(
            requests_to_schedule,
            instances,
        )

        # Execute scheduled requests
        for decision, request in zip(decisions, requests_to_schedule, strict=False):
            await self._execute_scheduled_request(request, decision)

    async def _execute_scheduled_request(
        self,
        request: RequestMetadata,
        decision: SchedulingDecision,
    ):
        """Execute a scheduled request with PD-aware routing if enabled."""

        # Get target instance (may be adjusted by PD router)
        instance = self.executor.get_instance(decision.target_instance_id)
        if not instance or not instance.can_accept_request:
            # Re-queue if instance not available
            self.pending_queue.appendleft(request)
            return

        # PD-aware routing: determine request phase and route to appropriate instance
        if self.enable_pd_separation and self.pd_router:
            pd_router = self.pd_router  # Local reference for type checker
            target_phase = pd_router.determine_request_phase(request)

            if target_phase:  # Only proceed if phase was determined
                logger.debug(
                    "PD routing: request %s routed to phase %s",
                    request.request_id,
                    target_phase.name,
                )

                # Filter instances by target phase
                compatible_instances = pd_router.filter_instances_by_type(
                    self.executor.get_all_instances(),
                    target_phase,
                )

                if compatible_instances:
                    # Select best instance based on PD specialization
                    best_instance = max(
                        compatible_instances,
                        key=lambda inst: pd_router.get_instance_specialization(inst).get(
                            target_phase.name, 0
                        ),
                    )
                    instance = best_instance
                    logger.debug(
                        "Selected PD-specialized instance %s for request %s",
                        instance.instance_id,
                        request.request_id,
                    )

        # Recommend parallelism config based on instance type
        if self.enable_pd_separation and self.pd_router:
            parallelism_config = self.pd_router.recommend_parallelism_config(instance, request)
            if parallelism_config:
                decision.tensor_parallel_size = parallelism_config["tensor_parallel_size"]
                decision.pipeline_parallel_size = parallelism_config["pipeline_parallel_size"]

        # Otherwise optimize parallelism strategy
        else:
            strategy, config = self.parallelism_optimizer.select_strategy(
                request,
                instance,
                instance.gpu_count,
            )

            # Update decision with optimized config
            decision.tensor_parallel_size = config.tensor_parallel_size
            decision.pipeline_parallel_size = config.pipeline_parallel_size
            decision.parallelism_strategy = strategy.strategy_type

        # Mark as running
        request.schedule_time = datetime.now()
        self.running_requests[request.request_id] = request

        logger.info(
            "Scheduling request %s to instance %s (TP=%d, PP=%d, type=%s)",
            request.request_id,
            instance.instance_id,
            decision.tensor_parallel_size,
            decision.pipeline_parallel_size,
            instance.instance_type.name if hasattr(instance, "instance_type") else "unknown",
        )

        # Execute asynchronously
        asyncio.create_task(self._execute_and_cleanup(request, instance, decision))

    async def _execute_and_cleanup(
        self,
        request: RequestMetadata,
        instance: ExecutionInstance,
        decision: SchedulingDecision,
    ):
        """Execute request and cleanup."""

        try:
            await self.executor.execute_request(request, instance, decision)

            logger.info(
                "Request %s completed (latency=%.2fms)",
                request.request_id,
                request.latency_ms,
            )

            # Record metrics
            if request.latency_ms:
                self.metrics_collector.record_request_completion(
                    request, decision, request.latency_ms, success=True
                )

        except Exception as e:
            logger.error("Request %s failed: %s", request.request_id, e)

            # Record failure
            if request.latency_ms:
                self.metrics_collector.record_request_completion(
                    request, decision, request.latency_ms, success=False
                )

        finally:
            # Cleanup
            self.running_requests.pop(request.request_id, None)

            # Update instance metrics
            self.metrics_collector.update_instance_metrics(instance)

    async def _health_check_loop(self):
        """Periodic health check of instances."""

        while self._running:
            try:
                await self.executor.health_check_all()
                await asyncio.sleep(10)  # Check every 10 seconds
            except Exception as e:
                logger.error("Health check loop error: %s", e)

    async def _engine_health_and_restart_loop(self):
        """Periodic health check of managed engines with automatic restart.

        This loop checks the health of all engines managed by the lifecycle manager
        and attempts to restart failed engines with exponential backoff.
        """
        while self._running:
            try:
                if not self.lifecycle_manager:
                    await asyncio.sleep(self.health_check_interval)
                    continue

                # Get health status of all managed engines
                health_results = await self.lifecycle_manager.health_check_all()

                for engine_id, is_healthy in health_results.items():
                    await self._handle_engine_health_result(engine_id, is_healthy)

                await asyncio.sleep(self.health_check_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Engine health check loop error: %s", e)
                await asyncio.sleep(self.health_check_interval)

    async def _handle_engine_health_result(
        self,
        engine_id: str,
        is_healthy: bool,
    ) -> None:
        """Handle health check result for a single engine.

        Args:
            engine_id: The engine identifier
            is_healthy: Whether the engine health check passed
        """
        with self._engine_health_state_lock:
            if engine_id not in self._engine_health_state:
                self._engine_health_state[engine_id] = {
                    "consecutive_failures": 0,
                    "restart_count": 0,
                    "last_restart_time": 0.0,
                }
            state = self._engine_health_state[engine_id]

        if is_healthy:
            # Reset consecutive failures on success
            with self._engine_health_state_lock:
                state["consecutive_failures"] = 0
            return

        # Increment consecutive failures
        with self._engine_health_state_lock:
            state["consecutive_failures"] += 1
            consecutive_failures = state["consecutive_failures"]
            restart_count = state["restart_count"]

        logger.warning(
            "Engine %s health check failed (consecutive=%d, restarts=%d/%d)",
            engine_id,
            consecutive_failures,
            restart_count,
            self.max_restart_attempts,
        )

        # Check if we should attempt restart
        if consecutive_failures < self.consecutive_failures_threshold:
            logger.debug(
                "Engine %s: waiting for more failures before restart (current=%d, threshold=%d)",
                engine_id,
                consecutive_failures,
                self.consecutive_failures_threshold,
            )
            return

        if restart_count >= self.max_restart_attempts:
            logger.error(
                "Engine %s exceeded max restart attempts (%d), marking as FAILED",
                engine_id,
                self.max_restart_attempts,
            )
            # Mark engine as permanently failed
            await self._mark_engine_failed(engine_id)
            return

        # Calculate backoff delay
        backoff_delay = self.restart_backoff_base * (2**restart_count)
        last_restart = state.get("last_restart_time", 0.0)
        time_since_last_restart = asyncio.get_event_loop().time() - last_restart

        if time_since_last_restart < backoff_delay:
            logger.debug(
                "Engine %s: in backoff period (%.1fs remaining)",
                engine_id,
                backoff_delay - time_since_last_restart,
            )
            return

        # Attempt restart
        await self._attempt_engine_restart(engine_id)

    async def _attempt_engine_restart(self, engine_id: str) -> bool:
        """Attempt to restart a failed engine.

        Args:
            engine_id: The engine identifier to restart

        Returns:
            True if restart was successful, False otherwise
        """
        if not self.lifecycle_manager:
            return False

        # Get engine metadata from registry
        with self._engine_registry_lock:
            engine_meta = self._engine_registry.get(engine_id)
            if not engine_meta:
                logger.warning("Cannot restart engine %s: not found in registry", engine_id)
                return False
            # Copy metadata to avoid mutation during restart
            engine_meta = dict(engine_meta)

        model_id = engine_meta.get("model_id", "")
        engine_kind = engine_meta.get("engine_kind", "llm")

        # Check if there's already a healthy engine for the same model
        # This prevents restart loops when another engine is already running
        existing_healthy = self._find_healthy_engine_for_model(model_id, engine_kind)
        if existing_healthy and existing_healthy != engine_id:
            logger.info(
                "Skipping restart of engine %s: healthy engine %s already serves model %s",
                engine_id,
                existing_healthy,
                model_id,
            )
            # Clean up the old engine instead of restarting
            self.lifecycle_manager.stop_engine(engine_id, timeout=5.0)
            with self._engine_registry_lock:
                self._engine_registry.pop(engine_id, None)
            with self._engine_health_state_lock:
                self._engine_health_state.pop(engine_id, None)
            return False

        logger.info("Attempting to restart engine %s", engine_id)

        # Update restart tracking
        with self._engine_health_state_lock:
            state = self._engine_health_state.get(engine_id, {})
            state["restart_count"] = state.get("restart_count", 0) + 1
            state["last_restart_time"] = asyncio.get_event_loop().time()
            state["consecutive_failures"] = 0
            self._engine_health_state[engine_id] = state
            current_restart = state["restart_count"]

        try:
            # Stop the old engine first
            logger.info("Stopping failed engine %s", engine_id)
            self.lifecycle_manager.stop_engine(engine_id, timeout=10.0)

            # Release resources before restart
            if self.gpu_manager:
                gpu_ids = engine_meta.get("gpu_ids", [])
                memory_per_gpu_gb = engine_meta.get("memory_per_gpu_gb", 0.0)
                if gpu_ids and memory_per_gpu_gb:
                    self.gpu_manager.release_resources(gpu_ids, memory_per_gpu_gb)

            port = engine_meta.get("port")
            if port:
                self._release_port(port)

            # Unregister old instance
            instance_id = engine_meta.get("instance_id")
            if instance_id:
                self.unregister_instance(instance_id)

            # Remove old engine from registry
            with self._engine_registry_lock:
                self._engine_registry.pop(engine_id, None)

            # Wait a bit before restart
            await asyncio.sleep(1.0)

            # Restart with same configuration
            new_engine_info = self.request_engine_startup(
                model_id=model_id,
                tensor_parallel_size=engine_meta.get("tensor_parallel_size", 1),
                pipeline_parallel_size=engine_meta.get("pipeline_parallel_size", 1),
                port=None,  # Let the system assign a new port
                instance_host=engine_meta.get("metadata", {}).get("host", "localhost"),
                instance_type=self._get_instance_type_from_meta(engine_meta),
                max_concurrent_requests=engine_meta.get("metadata", {}).get(
                    "max_concurrent_requests", 256
                ),
                engine_label=engine_meta.get("engine_label"),
                metadata=engine_meta.get("metadata"),
                engine_kind=engine_kind,
            )

            new_engine_id = new_engine_info.get("engine_id", "")
            logger.info(
                "Engine restart successful: %s -> %s (attempt %d/%d)",
                engine_id,
                new_engine_id,
                current_restart,
                self.max_restart_attempts,
            )

            # Transfer health state to new engine ID
            with self._engine_health_state_lock:
                if engine_id in self._engine_health_state:
                    old_state = self._engine_health_state.pop(engine_id)
                    self._engine_health_state[new_engine_id] = old_state

            return True

        except Exception as e:
            logger.error(
                "Failed to restart engine %s (attempt %d/%d): %s",
                engine_id,
                current_restart,
                self.max_restart_attempts,
                e,
            )
            return False

    def _find_healthy_engine_for_model(
        self,
        model_id: str,
        engine_kind: str = "llm",
    ) -> str | None:
        """Find a healthy engine serving the given model.

        Args:
            model_id: The model identifier to look for
            engine_kind: Type of engine ('llm' or 'embedding')

        Returns:
            Engine ID if found, None otherwise
        """
        if not self.lifecycle_manager:
            return None

        try:
            engines = self.lifecycle_manager.list_engines()
            for engine in engines:
                if engine.get("model_id") != model_id:
                    continue
                # Check engine kind
                runtime = engine.get("runtime", "llm")
                if runtime != engine_kind:
                    continue
                # Only consider healthy engines (RUNNING or STARTING)
                status = engine.get("status", "").upper()
                if status in ("RUNNING", "STARTING"):
                    return engine.get("engine_id")
        except Exception as e:
            logger.debug("Error finding healthy engine for model %s: %s", model_id, e)

        return None

    def _get_instance_type_from_meta(self, engine_meta: dict[str, Any]) -> ExecutionInstanceType:
        """Get ExecutionInstanceType from engine metadata."""
        meta = engine_meta.get("metadata", {})
        type_str = meta.get("instance_type")
        if type_str:
            try:
                return ExecutionInstanceType[type_str.upper()]
            except (KeyError, AttributeError):
                pass
        engine_kind = engine_meta.get("engine_kind", "llm")
        if engine_kind == "embedding":
            return ExecutionInstanceType.EMBEDDING
        return ExecutionInstanceType.GENERAL

    async def _mark_engine_failed(self, engine_id: str) -> None:
        """Mark an engine as permanently failed after exhausting restart attempts."""
        if not self.lifecycle_manager:
            return

        logger.error(
            "Engine %s marked as FAILED after %d restart attempts",
            engine_id,
            self.max_restart_attempts,
        )

        # Update engine status in lifecycle manager
        try:
            status = self.lifecycle_manager.get_engine_status(engine_id)
            if status:
                logger.info(
                    "Engine %s final status: %s (pid=%s)",
                    engine_id,
                    status.get("status"),
                    status.get("pid"),
                )
        except Exception as e:
            logger.debug("Could not get final status for engine %s: %s", engine_id, e)

        # Unregister from execution pool to prevent routing requests to it
        with self._engine_registry_lock:
            engine_meta = self._engine_registry.get(engine_id)
            if engine_meta:
                instance_id = engine_meta.get("instance_id")
                if instance_id:
                    self.unregister_instance(instance_id)

        # Clean up health state
        with self._engine_health_state_lock:
            self._engine_health_state.pop(engine_id, None)

    async def _monitoring_loop(self):
        """Periodic monitoring and metrics collection."""

        while self._running:
            try:
                metrics = self.executor.get_metrics()

                # Log metrics
                logger.info(
                    "Metrics: active=%d, queued=%d, completed=%d, failed=%d, "
                    "avg_latency=%.2fms, slo_compliance=%.2f%%",
                    metrics.active_requests,
                    len(self.pending_queue),
                    metrics.completed_requests,
                    metrics.failed_requests,
                    metrics.avg_latency_ms,
                    metrics.slo_compliance_rate * 100,
                )

                await asyncio.sleep(5)  # Monitor every 5 seconds
            except Exception as e:
                logger.error("Monitoring loop error: %s", e)

    async def _handle_scaling_decision(self, decision):
        """
        Handle autoscaling decision from Autoscaler.

        This callback is invoked by the Autoscaler when it determines
        that instances need to be scaled up or down.

        Args:
            decision: ScalingDecision with target instance counts
        """
        from .types import ExecutionInstanceType

        # Get current instance counts
        instances = self.executor.get_all_instances()
        current_prefill = sum(
            1 for i in instances if i.instance_type == ExecutionInstanceType.PREFILLING
        )
        current_decode = sum(
            1 for i in instances if i.instance_type == ExecutionInstanceType.DECODING
        )

        # Calculate deltas
        prefill_delta = decision.num_prefill_instances - current_prefill
        decode_delta = decision.num_decode_instances - current_decode

        logger.info(
            f"Autoscaling decision: prefill {current_prefill} -> "
            f"{decision.num_prefill_instances} (delta={prefill_delta}), "
            f"decode {current_decode} -> {decision.num_decode_instances} "
            f"(delta={decode_delta})"
        )

        # Apply scaling changes
        try:
            # Scale prefill instances
            if prefill_delta > 0:
                await self._scale_up_prefill(prefill_delta)
            elif prefill_delta < 0:
                await self._scale_down_prefill(abs(prefill_delta))

            # Scale decode instances
            if decode_delta > 0:
                await self._scale_up_decode(decode_delta)
            elif decode_delta < 0:
                await self._scale_down_decode(abs(decode_delta))

            logger.info("Autoscaling completed successfully")

        except Exception as e:
            logger.error(f"Failed to apply autoscaling decision: {e}", exc_info=True)

    async def _scale_up_prefill(self, count: int):
        """
        Scale up prefill instances.

        Args:
            count: Number of instances to add

        Note: This is a placeholder. Actual implementation depends on
        deployment environment (Kubernetes, cloud APIs, etc.)
        """
        logger.info(f"Scaling up {count} prefill instances")
        # TODO: Implement instance creation
        # - For Kubernetes: create new pods
        # - For cloud: launch new VMs/containers
        # - For local: start new processes
        #
        # Example Kubernetes approach:
        # await kubernetes_client.scale_deployment(
        #     deployment_name="prefill-worker",
        #     replicas=current + count
        # )

    async def _scale_down_prefill(self, count: int):
        """
        Scale down prefill instances.

        Args:
            count: Number of instances to remove

        Note: Should gracefully drain instances before removal.
        """
        logger.info(f"Scaling down {count} prefill instances")
        # TODO: Implement graceful instance removal
        # 1. Select instances to remove (prefer least loaded)
        # 2. Mark as unavailable (stop accepting new requests)
        # 3. Wait for active requests to complete
        # 4. Shutdown and remove
        from .types import ExecutionInstanceType

        instances = [
            i
            for i in self.executor.get_all_instances()
            if i.instance_type == ExecutionInstanceType.PREFILLING
        ]

        # Sort by load (ascending) to remove least loaded first
        instances.sort(key=lambda x: x.active_requests)

        for i in range(min(count, len(instances))):
            instance = instances[i]
            logger.info(f"Removing prefill instance {instance.instance_id}")
            await self.executor.remove_instance_gracefully(instance.instance_id)

    async def _scale_up_decode(self, count: int):
        """
        Scale up decode instances.

        Args:
            count: Number of instances to add
        """
        logger.info(f"Scaling up {count} decode instances")
        # TODO: Implement instance creation (similar to prefill)

    async def _scale_down_decode(self, count: int):
        """
        Scale down decode instances.

        Args:
            count: Number of instances to remove
        """
        logger.info(f"Scaling down {count} decode instances")
        from .types import ExecutionInstanceType

        instances = [
            i
            for i in self.executor.get_all_instances()
            if i.instance_type == ExecutionInstanceType.DECODING
        ]

        instances.sort(key=lambda x: x.active_requests)

        for i in range(min(count, len(instances))):
            instance = instances[i]
            logger.info(f"Removing decode instance {instance.instance_id}")
            await self.executor.remove_instance_gracefully(instance.instance_id)

    def get_autoscaler_status(self) -> dict:
        """Get autoscaler status."""
        if not self.autoscaler:
            return {"enabled": False}

        return {
            "enabled": True,
            **self.autoscaler.get_status(),
        }

    def get_metrics(self) -> PerformanceMetrics:
        """Get current performance metrics."""
        metrics = self.executor.get_metrics()
        metrics.queued_requests = len(self.pending_queue)
        return metrics

    def get_scheduling_metrics(self) -> SchedulingMetrics:
        """
        Get scheduling-specific metrics.

        Returns:
            SchedulingMetrics with policy performance data
        """
        return self.metrics_collector.get_scheduling_metrics(self.scheduling_policy.name)

    def get_instance_metrics_detailed(self, instance_id: str) -> InstanceMetrics | None:
        """
        Get detailed metrics for a specific instance.

        Args:
            instance_id: Instance identifier

        Returns:
            InstanceMetrics or None if not found
        """
        return self.metrics_collector.get_instance_metrics(instance_id)

    def get_all_instance_metrics(self) -> dict[str, InstanceMetrics]:
        """
        Get detailed metrics for all instances.

        Returns:
            Dictionary mapping instance_id to InstanceMetrics
        """
        return self.metrics_collector.get_all_instance_metrics()

    def get_instances(self) -> list[ExecutionInstance]:
        """Get all registered instances."""
        return self.executor.get_all_instances()

    def get_instance_metrics(self, instance_id: str) -> dict[str, Any] | None:
        """Get metrics for a specific instance."""
        return self.executor.get_instance_metrics(instance_id)

    def update_policy(self, policy_name: str):
        """Update scheduling policy."""
        self.scheduling_policy = self._create_policy(policy_name)
        logger.info("Scheduling policy updated to: %s", policy_name)

    def get_status(self) -> dict[str, Any]:
        """Get Control Plane status."""

        return {
            "running": self._running,
            "scheduling_policy": self.scheduling_policy.name,
            "routing_strategy": self.router.routing_strategy,
            "pending_requests": len(self.pending_queue),
            "running_requests": len(self.running_requests),
            "registered_instances": len(self.executor.instances),
            "available_instances": len(self.executor.get_available_instances()),
            "metrics": self.get_metrics(),
        }

    # ------------------------------------------------------------------
    # Dynamic engine lifecycle management
    # ------------------------------------------------------------------
    def request_engine_startup(
        self,
        model_id: str,
        *,
        tensor_parallel_size: int = 1,
        pipeline_parallel_size: int = 1,
        port: int | None = None,
        instance_host: str = "localhost",
        instance_type: ExecutionInstanceType = ExecutionInstanceType.GENERAL,
        max_concurrent_requests: int = 256,
        extra_spawn_args: list[str] | None = None,
        required_memory_gb: float | None = None,
        engine_label: str | None = None,
        metadata: dict[str, Any] | None = None,
        engine_kind: str = "llm",
        use_gpu: bool | None = None,
    ) -> dict[str, Any]:
        """Provision a new vLLM/vLLM-compatible engine and register it.

        This method coordinates GPU reservations, process lifecycle, and
        Control Plane registration so that new engines become immediately
        available for scheduling.
        """

        lifecycle_manager, gpu_manager = self._require_engine_managers()
        runtime_kind = self._normalize_engine_kind(engine_kind)
        if tensor_parallel_size <= 0:
            raise ValueError("tensor_parallel_size must be >= 1")
        if pipeline_parallel_size <= 0:
            raise ValueError("pipeline_parallel_size must be >= 1")
        if (
            runtime_kind is not None
            and runtime_kind.value == "embedding"
            and instance_type == ExecutionInstanceType.GENERAL
        ):
            instance_type = ExecutionInstanceType.EMBEDDING

        logger.info(
            "Requesting engine startup for model=%s tp=%d port=%s use_gpu=%s",
            model_id,
            tensor_parallel_size,
            port or "auto",
            use_gpu,
        )

        # Determine GPU requirement:
        # - use_gpu=True: Force GPU usage
        # - use_gpu=False: Force no GPU
        # - use_gpu=None (default): LLM uses GPU, Embedding does not
        if use_gpu is not None:
            needs_gpu = use_gpu
        else:
            needs_gpu = runtime_kind is None or runtime_kind.value != "embedding"
        per_gpu_memory_gb = 0.0
        gpu_ids: list[int] = []
        if needs_gpu:
            per_gpu_memory_gb = self._resolve_required_memory(
                model_id=model_id,
                tensor_parallel_size=tensor_parallel_size,
                provided_value=required_memory_gb,
                gpu_manager=gpu_manager,
            )
            gpu_ids = gpu_manager.allocate_resources(per_gpu_memory_gb, tensor_parallel_size)
            if not gpu_ids or len(gpu_ids) < tensor_parallel_size:
                raise RuntimeError(
                    "Unable to allocate sufficient GPU resources for requested engine"
                )

        try:
            allocated_port = self._reserve_port(port)
        except Exception:
            if needs_gpu and gpu_ids:
                gpu_manager.release_resources(gpu_ids, per_gpu_memory_gb)
            raise

        try:
            engine_id = lifecycle_manager.spawn_engine(
                model_id=model_id,
                gpu_ids=gpu_ids,
                port=allocated_port,
                tensor_parallel_size=tensor_parallel_size,
                pipeline_parallel_size=pipeline_parallel_size,
                extra_args=extra_spawn_args,
                engine_kind=(runtime_kind or EngineRuntime.LLM) if EngineRuntime else None,  # type: ignore
            )
        except Exception:
            self._release_port(allocated_port)
            if needs_gpu and gpu_ids:
                gpu_manager.release_resources(gpu_ids, per_gpu_memory_gb)
            logger.exception("Failed to spawn engine for model %s", model_id)
            raise

        instance_metadata = dict(metadata or {})
        if runtime_kind is not None:
            instance_metadata.setdefault("engine_kind", runtime_kind.value)
        if engine_label:
            instance_metadata["label"] = engine_label
            instance_metadata.setdefault("engine_label", engine_label)
        label = instance_metadata.get("engine_label") or instance_metadata.get("label")

        instance = ExecutionInstance(
            instance_id=engine_id,
            host=instance_host,
            port=allocated_port,
            model_name=model_id,
            tensor_parallel_size=tensor_parallel_size,
            pipeline_parallel_size=pipeline_parallel_size,
            gpu_count=len(gpu_ids),
            gpu_memory_gb=per_gpu_memory_gb * max(1, len(gpu_ids)),
            instance_type=instance_type,
            max_concurrent_requests=max_concurrent_requests,
            metadata=instance_metadata,
            supported_request_types=(
                [RequestType.EMBEDDING]
                if runtime_kind is not None and runtime_kind.value == "embedding"
                else None
            ),
            embedding_model_loaded=(
                model_id if runtime_kind is not None and runtime_kind.value == "embedding" else None
            ),
        )
        self.register_instance(instance)
        self._record_engine_metadata(
            engine_id=engine_id,
            instance_id=instance.instance_id,
            model_id=model_id,
            port=allocated_port,
            gpu_ids=gpu_ids,
            memory_per_gpu_gb=per_gpu_memory_gb,
            tensor_parallel_size=tensor_parallel_size,
            pipeline_parallel_size=pipeline_parallel_size,
            engine_label=label,
            metadata=instance_metadata,
            engine_kind=(runtime_kind or EngineRuntime.LLM).value if EngineRuntime else "llm",
        )

        logger.info(
            "Engine %s spawned on port %d with GPUs %s",
            engine_id,
            allocated_port,
            gpu_ids,
        )

        engine_info = {
            "engine_id": engine_id,
            "instance_id": instance.instance_id,
            "model_id": model_id,
            "host": instance_host,
            "port": allocated_port,
            "gpu_ids": gpu_ids,
            "tensor_parallel_size": tensor_parallel_size,
            "pipeline_parallel_size": pipeline_parallel_size,
            "memory_per_gpu_gb": per_gpu_memory_gb,
            "engine_label": label,
            "engine_kind": (runtime_kind or EngineRuntime.LLM).value if EngineRuntime else "llm",
        }

        # Initialize health state tracking for auto-restart
        if self.auto_restart:
            with self._engine_health_state_lock:
                self._engine_health_state[engine_id] = {
                    "consecutive_failures": 0,
                    "restart_count": 0,
                    "last_restart_time": 0.0,
                }

        status_snapshot = self._safe_get_engine_status(engine_id)
        if status_snapshot:
            engine_info.update(
                {
                    "status": status_snapshot.get("status"),
                    "pid": status_snapshot.get("pid"),
                    "uptime_seconds": status_snapshot.get("uptime_seconds"),
                }
            )

        return engine_info

    def request_engine_shutdown(self, engine_id: str) -> dict[str, Any]:
        """Stop a managed engine and release its resources."""

        lifecycle_manager, gpu_manager = self._require_engine_managers()
        logger.info("Requesting engine shutdown for %s", engine_id)

        success = lifecycle_manager.stop_engine(engine_id)
        if not success:
            logger.warning("Failed to stop engine %s", engine_id)
            return {"engine_id": engine_id, "stopped": False, "status": "FAILED"}

        engine_entry = self._pop_engine_metadata(engine_id)
        if engine_entry:
            gpu_ids = engine_entry.get("gpu_ids", [])
            memory_per_gpu_gb = engine_entry.get("memory_per_gpu_gb", 0.0)
            port = engine_entry.get("port")
            instance_id = engine_entry.get("instance_id")

            if gpu_ids and memory_per_gpu_gb:
                gpu_manager.release_resources(gpu_ids, memory_per_gpu_gb)
            if port:
                self._release_port(port)
            if instance_id:
                self.unregister_instance(instance_id)

        # Clean up health state tracking
        with self._engine_health_state_lock:
            self._engine_health_state.pop(engine_id, None)

        logger.info("Engine %s stopped and resources released", engine_id)
        return {"engine_id": engine_id, "stopped": True, "status": "STOPPED"}

    def prune_stopped_engines(self) -> int:
        """Remove all STOPPED/FAILED engine records and release their resources.

        This is useful for cleaning up stale engine records that accumulate
        over time. Running engines are not affected.

        Returns:
            Number of engine records pruned.
        """
        if not self.lifecycle_manager:
            return 0

        # First, release resources for all stopped/failed engines
        engines_to_prune = []
        for engine_info in self.lifecycle_manager.list_engines():
            status = engine_info.get("status", "")
            engine_id = engine_info.get("engine_id", "")
            if status in {"STOPPED", "FAILED"} and engine_id:
                engines_to_prune.append(engine_id)

        for engine_id in engines_to_prune:
            # Release port and GPU resources if we have metadata
            engine_entry = self._pop_engine_metadata(engine_id)
            if engine_entry:
                gpu_ids = engine_entry.get("gpu_ids", [])
                memory_per_gpu_gb = engine_entry.get("memory_per_gpu_gb", 0.0)
                port = engine_entry.get("port")
                instance_id = engine_entry.get("instance_id")

                if gpu_ids and memory_per_gpu_gb and self.gpu_manager:
                    self.gpu_manager.release_resources(gpu_ids, memory_per_gpu_gb)
                if port:
                    self._release_port(port)
                if instance_id:
                    self.unregister_instance(instance_id)

            # Clean up health state tracking
            with self._engine_health_state_lock:
                self._engine_health_state.pop(engine_id, None)

        # Now prune the engine records from lifecycle manager
        pruned = self.lifecycle_manager.prune_stopped_engines()
        if pruned > 0:
            logger.info("Pruned %d stopped/failed engines and released resources", pruned)
        return pruned

    def get_cluster_status(self) -> dict[str, Any]:
        """Return consolidated GPU, engine, and instance status."""

        gpu_status: list[dict[str, Any]] = []
        if self.gpu_manager:
            try:
                gpu_status = self.gpu_manager.get_system_status()  # type: ignore
            except Exception:  # pragma: no cover - defensive logging
                logger.exception("Failed to fetch GPU status")

        engine_status: list[dict[str, Any]] = []
        if self.lifecycle_manager:
            try:
                engine_status = self.lifecycle_manager.list_engines()
            except Exception:  # pragma: no cover - defensive logging
                logger.exception("Failed to list managed engines")

        instances = [
            {
                "instance_id": inst.instance_id,
                "model_name": inst.model_name,
                "host": inst.host,
                "port": inst.port,
                "instance_type": inst.instance_type.name
                if isinstance(inst.instance_type, ExecutionInstanceType)
                else str(inst.instance_type),
                "active_requests": inst.active_requests,
                "max_concurrent_requests": inst.max_concurrent_requests,
                "is_available": inst.is_available,
                "is_healthy": inst.is_healthy,
                "metadata": inst.metadata,
            }
            for inst in self.executor.get_all_instances()
        ]

        return {
            "control_plane": self.get_status(),
            "gpu": gpu_status,
            "engines": engine_status,
            "managed_instances": instances,
            "resource_reservations": self._get_engine_registry_snapshot(),
        }

    def get_registered_backends(self) -> dict[str, Any]:
        """Get all registered backend instances for dynamic discovery.

        Returns a categorized list of all registered LLM and Embedding backends
        that are currently available for routing. This endpoint is used by
        UnifiedInferenceClient to dynamically discover available services.

        Returns:
            Dictionary containing:
                - llm_backends: List of LLM backend info (host, port, model, healthy)
                - embedding_backends: List of Embedding backend info
                - timestamp: ISO format timestamp of when this snapshot was taken
        """
        llm_backends: list[dict[str, Any]] = []
        embedding_backends: list[dict[str, Any]] = []

        for inst in self.executor.get_all_instances():
            backend_info = {
                "instance_id": inst.instance_id,
                "host": inst.host,
                "port": inst.port,
                "model_name": inst.model_name,
                "base_url": f"http://{inst.host}:{inst.port}/v1",
                "is_healthy": inst.is_healthy,
                "is_available": inst.is_available,
                "active_requests": inst.active_requests,
                "max_concurrent_requests": inst.max_concurrent_requests,
                "metadata": inst.metadata,
            }

            # Categorize by instance type
            instance_type = (
                inst.instance_type.name
                if isinstance(inst.instance_type, ExecutionInstanceType)
                else str(inst.instance_type)
            )

            # Check if this is an embedding instance
            if instance_type in ("EMBEDDING",):
                embedding_backends.append(backend_info)
            elif instance_type in ("LLM_EMBEDDING",):
                # Mixed instance: add to both lists
                llm_backends.append(backend_info)
                embedding_backends.append(backend_info)
            else:
                # GENERAL, PREFILLING, DECODING, HYBRID are all LLM types
                llm_backends.append(backend_info)

        return {
            "llm_backends": llm_backends,
            "embedding_backends": embedding_backends,
            "total_llm_backends": len(llm_backends),
            "total_embedding_backends": len(embedding_backends),
            "healthy_llm_backends": sum(1 for b in llm_backends if b["is_healthy"]),
            "healthy_embedding_backends": sum(1 for b in embedding_backends if b["is_healthy"]),
            "timestamp": datetime.now().isoformat(),
        }

    def get_engine_health_status(self) -> dict[str, Any]:
        """Get health status and restart tracking for all managed engines.

        Returns:
            Dictionary with auto_restart config and per-engine health state
        """
        with self._engine_health_state_lock:
            engine_states = {
                engine_id: {
                    "consecutive_failures": state.get("consecutive_failures", 0),
                    "restart_count": state.get("restart_count", 0),
                    "last_restart_time": state.get("last_restart_time", 0.0),
                    "can_restart": state.get("restart_count", 0) < self.max_restart_attempts,
                }
                for engine_id, state in self._engine_health_state.items()
            }

        return {
            "auto_restart_enabled": self.auto_restart,
            "max_restart_attempts": self.max_restart_attempts,
            "health_check_interval": self.health_check_interval,
            "consecutive_failures_threshold": self.consecutive_failures_threshold,
            "engines": engine_states,
        }

    # ------------------------------------------------------------------
    # Internal helpers for engine lifecycle management
    # ------------------------------------------------------------------
    def _init_gpu_manager(self) -> GPUResourceManager | None:
        if RuntimeGPUResourceManager is None:
            logger.debug("GPUResourceManager not available; GPU tracking disabled")
            return None
        try:
            return RuntimeGPUResourceManager()
        except Exception:  # pragma: no cover - dependency wiring
            logger.exception("Unable to initialize GPUResourceManager")
            return None

    def _init_engine_lifecycle_manager(self) -> EngineLifecycleManager | None:
        if RuntimeEngineLifecycleManager is None:
            logger.debug("EngineLifecycleManager not available; dynamic lifecycle control disabled")
            return None
        try:
            # Pass self as control_plane so discovered engines can register
            return RuntimeEngineLifecycleManager(control_plane=self)
        except Exception:  # pragma: no cover - dependency wiring
            logger.exception("Unable to initialize EngineLifecycleManager")
            return None

    def _require_engine_managers(self) -> tuple[EngineLifecycleManager, GPUResourceManager]:
        if not self.lifecycle_manager or not self.gpu_manager:
            raise RuntimeError(
                "Engine lifecycle management requires GPUResourceManager and EngineLifecycleManager"
            )
        return self.lifecycle_manager, self.gpu_manager

    def _normalize_engine_kind(self, engine_kind: str | None) -> EngineRuntime | None:  # type: ignore
        if EngineRuntime is None:
            return None
        if not engine_kind:
            return EngineRuntime.LLM
        normalized = engine_kind.strip().lower()
        for kind in EngineRuntime:
            if kind.value == normalized:
                return kind
        raise ValueError(
            f"Unsupported engine_kind '{engine_kind}'. Expected one of {[k.value for k in EngineRuntime]}"
        )

    def _resolve_required_memory(
        self,
        *,
        model_id: str,
        tensor_parallel_size: int,
        provided_value: float | None,
        gpu_manager: GPUResourceManager,
    ) -> float:
        if provided_value is not None:
            if provided_value <= 0:
                raise ValueError("required_memory_gb must be positive when provided")
            return float(provided_value)

        estimated = float(gpu_manager.estimate_model_memory(model_id, tensor_parallel_size))
        if estimated <= 0:
            raise RuntimeError("GPUResourceManager returned invalid memory estimate")
        return estimated

    def _safe_get_engine_status(self, engine_id: str) -> dict[str, Any] | None:
        if not self.lifecycle_manager:
            return None
        try:
            return self.lifecycle_manager.get_engine_status(engine_id)
        except Exception:  # pragma: no cover - best-effort logging
            logger.debug("Failed to get engine status for %s", engine_id, exc_info=True)
            return None

    def _get_all_reserved_ports(self) -> set[int]:
        """Get all reserved ports from both manager and lifecycle manager.

        This ensures we don't allocate a port that's already reserved
        by the lifecycle manager (which tracks ports for spawned engines).
        """
        reserved = set(self._reserved_ports)
        if self.lifecycle_manager:
            reserved.update(self.lifecycle_manager.reserved_ports)
        return reserved

    def _reserve_port(self, requested_port: int | None = None) -> int:
        all_reserved = self._get_all_reserved_ports()

        if requested_port is not None:
            if not SagePorts.is_available(requested_port):
                raise RuntimeError(f"Requested port {requested_port} is already in use")
            with self._engine_registry_lock:
                if requested_port in all_reserved:
                    raise RuntimeError(f"Requested port {requested_port} is reserved")
                self._reserved_ports.add(requested_port)
            return requested_port

        for candidate in SagePorts.get_llm_ports():
            with self._engine_registry_lock:
                # Re-check all reserved ports inside lock to avoid race conditions
                all_reserved = self._get_all_reserved_ports()
                if candidate in all_reserved:
                    continue
            if SagePorts.is_available(candidate):
                with self._engine_registry_lock:
                    self._reserved_ports.add(candidate)
                return candidate

        fallback = SagePorts.find_available_port()
        if fallback is None:
            raise RuntimeError("Unable to find an available port for a new engine")
        with self._engine_registry_lock:
            self._reserved_ports.add(fallback)
        return fallback

    def _release_port(self, port: int | None) -> None:
        if not port:
            return
        with self._engine_registry_lock:
            self._reserved_ports.discard(port)

    def _record_engine_metadata(
        self,
        *,
        engine_id: str,
        instance_id: str,
        model_id: str,
        port: int,
        gpu_ids: list[int],
        memory_per_gpu_gb: float,
        tensor_parallel_size: int,
        pipeline_parallel_size: int,
        engine_label: str | None,
        metadata: dict[str, Any] | None = None,
        engine_kind: str,
    ) -> None:
        with self._engine_registry_lock:
            self._engine_registry[engine_id] = {
                "instance_id": instance_id,
                "model_id": model_id,
                "port": port,
                "gpu_ids": gpu_ids,
                "memory_per_gpu_gb": memory_per_gpu_gb,
                "tensor_parallel_size": tensor_parallel_size,
                "pipeline_parallel_size": pipeline_parallel_size,
                "engine_label": engine_label,
                "metadata": dict(metadata or {}),
                "engine_kind": engine_kind,
            }

    def _pop_engine_metadata(self, engine_id: str) -> dict[str, Any] | None:
        with self._engine_registry_lock:
            entry = self._engine_registry.pop(engine_id, None)
        return entry

    def _get_engine_registry_snapshot(self) -> list[dict[str, Any]]:
        with self._engine_registry_lock:
            return [
                {
                    "engine_id": engine_id,
                    "model_id": meta.get("model_id"),
                    "port": meta.get("port"),
                    "gpu_ids": meta.get("gpu_ids"),
                    "tensor_parallel_size": meta.get("tensor_parallel_size"),
                    "engine_label": meta.get("engine_label"),
                    "memory_per_gpu_gb": meta.get("memory_per_gpu_gb"),
                    "metadata": dict(meta.get("metadata", {})),
                    "engine_kind": meta.get(
                        "engine_kind",
                        EngineRuntime.LLM.value if EngineRuntime else "llm",
                    ),
                }
                for engine_id, meta in self._engine_registry.items()
            ]
