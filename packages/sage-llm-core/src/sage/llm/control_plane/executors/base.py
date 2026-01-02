"""Abstract base executor for control plane execution coordinators.

Duplicate of `control_plane.executor.base` living under `executors` to
support both import paths during refactor.
"""

from __future__ import annotations

import abc
from typing import Any

from ..types import (
    ExecutionInstance,
    PerformanceMetrics,
    RequestMetadata,
    SchedulingDecision,
)


class ExecutionCoordinatorBase(abc.ABC):
    def __init__(self):
        self.instances: dict[str, ExecutionInstance] = {}
        self.active_requests: dict[str, RequestMetadata] = {}
        self.request_to_instance: dict[str, str] = {}
        self.metrics: PerformanceMetrics = PerformanceMetrics()

    @abc.abstractmethod
    async def cleanup(self) -> None:
        raise NotImplementedError

    def register_instance(self, instance: ExecutionInstance) -> None:
        self.instances[instance.instance_id] = instance

    def unregister_instance(self, instance_id: str) -> None:
        if instance_id in self.instances:
            del self.instances[instance_id]

    def get_instance(self, instance_id: str) -> ExecutionInstance | None:
        return self.instances.get(instance_id)

    def get_available_instances(self) -> list[ExecutionInstance]:
        return [inst for inst in self.instances.values() if inst.can_accept_request]

    def get_all_instances(self) -> list[ExecutionInstance]:
        return list(self.instances.values())

    async def add_instance(self, instance: ExecutionInstance) -> None:
        """
        Dynamically add a new instance to the pool.

        Args:
            instance: New ExecutionInstance to add
        """
        self.register_instance(instance)

    @abc.abstractmethod
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
        raise NotImplementedError

    @abc.abstractmethod
    async def execute_request(
        self, request: RequestMetadata, instance: ExecutionInstance, decision: SchedulingDecision
    ) -> dict[str, Any]:
        raise NotImplementedError

    @abc.abstractmethod
    async def health_check(self, instance: ExecutionInstance) -> bool:
        raise NotImplementedError

    @abc.abstractmethod
    async def health_check_all(self) -> dict[str, bool]:
        raise NotImplementedError

    def get_metrics(self) -> PerformanceMetrics:
        return self.metrics

    def set_manager_callback(self, manager: Any) -> None:  # noqa: B027
        """Set the manager callback for coordination.

        Args:
            manager: The ControlPlaneManager instance

        Note:
            Subclasses can override this if they need manager callbacks.
            Default implementation does nothing.
        """

    @abc.abstractmethod
    async def get_instance_info(self, instance: ExecutionInstance) -> dict[str, Any] | None:
        raise NotImplementedError

    @abc.abstractmethod
    def get_instance_metrics(self, instance_id: str) -> dict[str, Any] | None:
        raise NotImplementedError

    @abc.abstractmethod
    async def shutdown_all(self) -> None:
        raise NotImplementedError
