# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""Execution coordinator for managing vLLM instances via HTTP API."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any

import aiohttp

from ..types import (
    ExecutionInstance,
    PerformanceMetrics,
    RequestMetadata,
    SchedulingDecision,
)
from .base import ExecutionCoordinatorBase

logger = logging.getLogger(__name__)


class HttpExecutionCoordinator(ExecutionCoordinatorBase):
    """
    Coordinates execution across multiple vLLM instances via HTTP API.

    All vLLM instances are accessed uniformly through OpenAI-compatible API,
    regardless of whether they are local or remote. This enables location-
    transparent scheduling where the Control Plane focuses purely on
    scheduling policies without caring about instance deployment.

    Design Philosophy:
    - Unified abstraction: All vLLM instances are "remote resources"
    - Location transparent: localhost:8000 and 192.168.1.100:8000 are treated the same
    - Scheduling focused: Control Plane only implements scheduling strategies
    - Simple implementation: Single HTTP client path, no local/remote branches
    """

    def __init__(self, timeout: int = 300):
        super().__init__()
        self.http_session: aiohttp.ClientSession | None = None
        self.timeout = aiohttp.ClientTimeout(total=timeout)

        logger.info("ExecutionCoordinator initialized in HTTP client mode")

    async def initialize(self) -> None:
        if not self.http_session:
            self.http_session = aiohttp.ClientSession(timeout=self.timeout)
            logger.info("HTTP session initialized for vLLM communication")

    async def cleanup(self) -> None:
        if self.http_session:
            await self.http_session.close()
            self.http_session = None
            logger.info("HTTP session closed")

    def register_instance(self, instance: ExecutionInstance):
        """
        Register a vLLM execution instance.

        The instance must be a running vLLM server started with:
            python -m vllm.entrypoints.openai.api_server --model <model> --port <port>

        Args:
            instance: ExecutionInstance with host:port of a running vLLM server.
                     Can be localhost (e.g., localhost:8000) for local GPUs,
                     or remote IP (e.g., 192.168.1.100:8000) for remote machines.

        Example:
            # Local GPU 0
            instance = ExecutionInstance(
                instance_id="gpu-0",
                host="localhost",
                port=8000,
                model_name="meta-llama/Llama-2-7b",
                gpu_count=1,
            )
            coordinator.register_instance(instance)

            # Remote GPU on another machine
            instance = ExecutionInstance(
                instance_id="remote-gpu-0",
                host="192.168.1.100",
                port=8000,
                model_name="meta-llama/Llama-2-7b",
                gpu_count=1,
            )
            coordinator.register_instance(instance)
        """
        self.instances[instance.instance_id] = instance
        logger.info(
            "Registered vLLM instance: %s at %s:%d (model=%s, GPUs=%d)",
            instance.instance_id,
            instance.host,
            instance.port,
            instance.model_name,
            instance.gpu_count,
        )

    async def remove_instance_gracefully(self, instance_id: str, max_wait_sec: int = 300) -> None:
        """
        Gracefully remove an instance from the pool.

        This method:
        1. Marks the instance as unavailable (stops accepting new requests)
        2. Waits for active requests to complete (up to max_wait_sec)
        3. Removes the instance from the registry

        Args:
            instance_id: ID of instance to remove
            max_wait_sec: Maximum time to wait for requests to complete (seconds)
        """
        instance = self.get_instance(instance_id)
        if not instance:
            logger.warning("Instance %s not found for removal", instance_id)
            return

        logger.info("Gracefully removing instance %s", instance_id)

        # Step 1: Mark as unavailable
        instance.is_available = False
        logger.info("Instance %s marked unavailable", instance_id)

        # Step 2: Wait for active requests to complete
        wait_interval = 5  # seconds
        elapsed = 0

        while instance.active_requests > 0 and elapsed < max_wait_sec:
            logger.info(
                "Waiting for %d requests to complete on instance %s (%d/%ds)",
                instance.active_requests,
                instance_id,
                elapsed,
                max_wait_sec,
            )
            await asyncio.sleep(wait_interval)
            elapsed += wait_interval

        if instance.active_requests > 0:
            logger.warning(
                "Force removing instance %s with %d active requests after %ds timeout",
                instance_id,
                instance.active_requests,
                max_wait_sec,
            )
        else:
            logger.info("All requests completed on instance %s", instance_id)

        # Step 3: Remove from registry
        self.unregister_instance(instance_id)
        logger.info("Instance %s removed from registry", instance_id)

    async def execute_request(
        self,
        request: RequestMetadata,
        instance: ExecutionInstance,
        decision: SchedulingDecision,
    ) -> dict[str, Any]:
        """
        Execute a request on a vLLM instance via HTTP API.

        Args:
            request: Request metadata with prompt and parameters
            instance: Target vLLM instance (can be local or remote)
            decision: Scheduling decision

        Returns:
            Execution result from vLLM in OpenAI format

        Raises:
            RuntimeError: If HTTP request fails or vLLM returns error
        """
        # Ensure HTTP session exists
        if not self.http_session:
            await self.initialize()

        # Track request state
        self.active_requests[request.request_id] = request
        self.request_to_instance[request.request_id] = instance.instance_id

        # Update instance load
        instance.active_requests += 1
        instance.current_load = min(
            1.0, instance.active_requests / instance.max_concurrent_requests
        )

        request.start_time = datetime.now()

        try:
            # Execute via HTTP (unified path for all instances)
            result = await self._execute_via_http(request, instance, decision)
            request.end_time = datetime.now()
            self._update_metrics(request, instance, success=True)
            return result

        except Exception as e:
            logger.error(
                "Execution failed for request %s on %s:%d: %s",
                request.request_id,
                instance.host,
                instance.port,
                e,
            )
            request.end_time = datetime.now()
            self._update_metrics(request, instance, success=False)
            raise

        finally:
            # Cleanup
            instance.active_requests -= 1
            instance.current_load = max(
                0.0, instance.active_requests / instance.max_concurrent_requests
            )
            self.active_requests.pop(request.request_id, None)
            self.request_to_instance.pop(request.request_id, None)

    async def _execute_via_http(
        self,
        request: RequestMetadata,
        instance: ExecutionInstance,
        decision: SchedulingDecision,
    ) -> dict[str, Any]:
        """
        Execute request via vLLM's OpenAI-compatible HTTP API.

        This is the unified execution path for all instances (local and remote).
        vLLM exposes OpenAI-compatible endpoints:
        - POST /v1/completions - Text completion
        - POST /v1/chat/completions - Chat completion
        - GET /health - Health check
        - GET /v1/models - List models

        Args:
            request: Request metadata
            instance: Target instance
            decision: Scheduling decision

        Returns:
            vLLM response in OpenAI format
        """
        url = f"http://{instance.host}:{instance.port}/v1/completions"

        # Build OpenAI-compatible payload
        payload = {
            "model": instance.model_name,
            "prompt": request.prompt or "",
            "max_tokens": request.max_tokens or 512,
            "temperature": request.temperature,
            "top_p": request.top_p,
            "stream": False,
            "n": 1,
            "logprobs": None,
            "echo": False,
        }

        # Optional fields
        if request.user_id:
            payload["user"] = request.user_id

        logger.info(
            "Executing request %s on %s:%d (model=%s, max_tokens=%d)",
            request.request_id,
            instance.host,
            instance.port,
            instance.model_name,
            request.max_tokens or 512,
        )

        start_time = datetime.now()

        if not self.http_session:
            raise RuntimeError("HTTP session not initialized")

        try:
            async with self.http_session.post(
                url, json=payload, timeout=aiohttp.ClientTimeout(total=self.timeout.total)
            ) as response:
                elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000

                if response.status == 200:
                    result = await response.json()
                    logger.info(
                        "Request %s completed in %.2fms (tokens: %d)",
                        request.request_id,
                        elapsed_ms,
                        result.get("usage", {}).get("total_tokens", 0),
                    )
                    return result  # type: ignore[no-any-return]
                else:
                    error_text = await response.text()
                    raise RuntimeError(f"vLLM returned status {response.status}: {error_text}")

        except aiohttp.ClientError as e:
            raise RuntimeError(f"HTTP error calling {url}: {e}")
        except TimeoutError:
            raise RuntimeError(f"Request timeout calling {url} (timeout={self.timeout.total}s)")

    async def health_check(self, instance: ExecutionInstance) -> bool:
        """
        Check health of a vLLM instance via HTTP with consecutive failure tracking.

        Args:
            instance: Instance to check

        Returns:
            True if healthy (HTTP 200), False otherwise
        """
        if not self.http_session:
            await self.initialize()

        if not self.http_session:
            return False

        try:
            url = f"http://{instance.host}:{instance.port}/health"
            timeout = aiohttp.ClientTimeout(total=5)

            async with self.http_session.get(url, timeout=timeout) as response:
                is_healthy = response.status == 200

                # Update instance health status
                instance.is_healthy = is_healthy

                if is_healthy:
                    # Reset consecutive failures on success
                    instance.metadata["consecutive_failures"] = 0
                else:
                    # Increment consecutive failures
                    instance.metadata["consecutive_failures"] = (
                        instance.metadata.get("consecutive_failures", 0) + 1
                    )
                    logger.warning(
                        "Health check failed for %s at %s:%d (status=%d, failures=%d)",
                        instance.instance_id,
                        instance.host,
                        instance.port,
                        response.status,
                        instance.metadata["consecutive_failures"],
                    )

                # Trigger failure callback if threshold exceeded
                if instance.metadata.get("consecutive_failures", 0) >= 3:
                    await self._on_instance_failure(instance)

                return bool(is_healthy)

        except TimeoutError:
            logger.warning(
                "Health check timeout for %s at %s:%d",
                instance.instance_id,
                instance.host,
                instance.port,
            )
            instance.is_healthy = False
            instance.metadata["consecutive_failures"] = (
                instance.metadata.get("consecutive_failures", 0) + 1
            )
            if instance.metadata.get("consecutive_failures", 0) >= 3:
                await self._on_instance_failure(instance)
            return False

        except aiohttp.ClientError as e:
            logger.warning(
                "Health check error for %s at %s:%d: %s",
                instance.instance_id,
                instance.host,
                instance.port,
                e,
            )
            instance.is_healthy = False
            instance.metadata["consecutive_failures"] = (
                instance.metadata.get("consecutive_failures", 0) + 1
            )
            if instance.metadata.get("consecutive_failures", 0) >= 3:
                await self._on_instance_failure(instance)
            return False

    async def _on_instance_failure(self, instance: ExecutionInstance):
        """
        Handle instance failure after consecutive health check failures.

        Args:
            instance: Failed instance
        """
        logger.critical(
            "Instance %s marked as FAILED (consecutive failures: %d)",
            instance.instance_id,
            instance.metadata.get("consecutive_failures", 0),
        )

        # Mark instance as unavailable
        instance.is_available = False
        instance.is_healthy = False

        # Get requests running on this instance
        failed_request_ids = [
            req_id
            for req_id, inst_id in self.request_to_instance.items()
            if inst_id == instance.instance_id
        ]

        if failed_request_ids:
            logger.warning(
                "Instance %s failure affects %d running requests: %s",
                instance.instance_id,
                len(failed_request_ids),
                failed_request_ids,
            )

            # Collect request metadata if available
            failed_requests = []
            for req_id in failed_request_ids:
                if req_id in self.active_requests:
                    failed_requests.append((req_id, self.active_requests[req_id]))

            # Notify manager callback if set
            if hasattr(self, "_manager_callback") and self._manager_callback:
                try:
                    await self._manager_callback.on_instance_failure(
                        instance.instance_id, failed_requests
                    )
                except Exception as e:
                    logger.error("Error calling manager callback for instance failure: %s", e)

    def set_manager_callback(self, manager: Any):
        """
        Set manager callback for instance failure notifications.

        Args:
            manager: ControlPlaneManager instance
        """
        self._manager_callback = manager

    async def get_instance_info(self, instance: ExecutionInstance) -> dict[str, Any] | None:
        """
        Get instance information via HTTP (optional, if vLLM exposes it).

        Args:
            instance: Instance to query

        Returns:
            Instance info dict or None if not available
        """
        if not self.http_session:
            await self.initialize()

        if not self.http_session:
            return None

        try:
            url = f"http://{instance.host}:{instance.port}/v1/models"
            timeout = aiohttp.ClientTimeout(total=5)

            async with self.http_session.get(url, timeout=timeout) as response:
                if response.status == 200:
                    result: dict[str, Any] = await response.json()
                    return result
                else:
                    logger.debug("Instance info not available for %s", instance.instance_id)
                    return None

        except Exception as e:
            logger.debug(
                "Could not retrieve instance info for %s: %s",
                instance.instance_id,
                e,
            )
            return None

    def _update_metrics(
        self,
        request: RequestMetadata,
        instance: ExecutionInstance,
        success: bool,
    ):
        """Update performance metrics."""
        # Update total requests counter
        self.metrics.total_requests += 1

        if success:
            self.metrics.completed_requests += 1

            # Update latency metrics
            if request.latency_ms:
                # Update instance average latency (exponential moving average)
                if instance.avg_latency_ms == 0:
                    instance.avg_latency_ms = request.latency_ms
                else:
                    alpha = 0.1  # Smoothing factor
                    instance.avg_latency_ms = (
                        1 - alpha
                    ) * instance.avg_latency_ms + alpha * request.latency_ms

                # Update global average latency
                if self.metrics.avg_latency_ms == 0:
                    self.metrics.avg_latency_ms = request.latency_ms
                else:
                    total_completed = self.metrics.completed_requests
                    self.metrics.avg_latency_ms = (
                        (total_completed - 1) * self.metrics.avg_latency_ms + request.latency_ms
                    ) / total_completed
        else:
            self.metrics.failed_requests += 1

    def get_metrics(self) -> PerformanceMetrics:
        """Get aggregated performance metrics."""
        return self.metrics

    async def health_check_all(self) -> dict[str, bool]:
        """
        Check health of all registered instances.

        Updates the is_healthy status for each instance.
        Returns a dict mapping instance_id to health status.
        """
        if not self.instances:
            return {}

        # Check all instances in parallel
        tasks = [self.health_check(instance) for instance in self.instances.values()]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Update instance health status and collect results
        health_status: dict[str, bool] = {}
        for instance, result in zip(self.instances.values(), results, strict=False):
            if isinstance(result, Exception):
                logger.error("Health check exception for %s: %s", instance.instance_id, result)
                instance.is_healthy = False
                health_status[instance.instance_id] = False
            elif isinstance(result, bool):
                instance.is_healthy = result
                health_status[instance.instance_id] = result
            else:
                # Shouldn't happen, but handle it gracefully
                instance.is_healthy = False
                health_status[instance.instance_id] = False

        return health_status

    def get_instance_metrics(self, instance_id: str) -> dict[str, Any] | None:
        """
        Get metrics for a specific instance.

        Args:
            instance_id: ID of the instance

        Returns:
            Dictionary with instance metrics or None if not found
        """
        instance = self.instances.get(instance_id)
        if not instance:
            return None

        return {
            "instance_id": instance.instance_id,
            "host": instance.host,
            "port": instance.port,
            "model_name": instance.model_name,
            "is_healthy": instance.is_healthy,
            "is_available": instance.is_available,
            "current_load": instance.current_load,
            "active_requests": instance.active_requests,
            "max_concurrent_requests": instance.max_concurrent_requests,
            "avg_latency_ms": instance.avg_latency_ms,
            "throughput_tokens_per_sec": instance.throughput_tokens_per_sec,
            "gpu_count": instance.gpu_count,
            "gpu_utilization": instance.gpu_utilization,
            "gpu_memory_gb": instance.gpu_memory_gb,
            "instance_type": instance.instance_type.value,
        }

    async def shutdown_all(self):
        """Shutdown coordinator and cleanup resources."""
        await self.cleanup()
        logger.info("ExecutionCoordinator shutdown complete")
