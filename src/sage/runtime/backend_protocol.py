"""Runtime backend protocol owned by the main SAGE repository."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class NodeInfoProtocol(ABC):
    @property
    @abstractmethod
    def node_id(self) -> str:
        pass

    @property
    @abstractmethod
    def address(self) -> str:
        pass

    @property
    @abstractmethod
    def is_schedulable(self) -> bool:
        pass

    @property
    @abstractmethod
    def resource_summary(self) -> dict[str, Any]:
        pass


class MethodCallFuture(ABC):
    @abstractmethod
    def result(self, timeout: float | None = None) -> Any:
        pass

    @abstractmethod
    def cancel(self) -> bool:
        pass

    @property
    @abstractmethod
    def done(self) -> bool:
        pass


class MethodRefProtocol(ABC):
    @abstractmethod
    def call(self, *args: Any, **kwargs: Any) -> Any:
        pass

    @abstractmethod
    def async_call(self, *args: Any, **kwargs: Any) -> MethodCallFuture:
        pass

    @abstractmethod
    def cancel(self) -> bool:
        pass


class ActorHandleProtocol(ABC):
    @abstractmethod
    def get_method(self, name: str) -> MethodRefProtocol:
        pass

    def cancel(self) -> bool:
        return False


class FlowRunHandleProtocol(ABC):
    @abstractmethod
    def call(self, *args: Any, **kwargs: Any) -> Any:
        pass

    @abstractmethod
    def cancel(self) -> None:
        pass


class RuntimeBackendProtocol(ABC):
    @abstractmethod
    def start(self, config: Any | None = None) -> None:
        pass

    @abstractmethod
    def stop(self) -> None:
        pass

    @abstractmethod
    def create(
        self,
        actor_class: type,
        /,
        *args: Any,
        actor_config: Any | None = None,
        **kwargs: Any,
    ) -> ActorHandleProtocol:
        pass

    @abstractmethod
    def submit(
        self,
        flow_obj: Any,
        *,
        ingress: Any | None = None,
        egress: Any | None = None,
        run_config: Any | None = None,
    ) -> FlowRunHandleProtocol:
        pass

    @abstractmethod
    def list_nodes(self) -> list[NodeInfoProtocol]:
        pass


__all__ = [
    "RuntimeBackendProtocol",
    "ActorHandleProtocol",
    "MethodRefProtocol",
    "MethodCallFuture",
    "FlowRunHandleProtocol",
    "NodeInfoProtocol",
]
