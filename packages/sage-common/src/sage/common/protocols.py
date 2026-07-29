"""Runtime context protocols shared by SAGE foundation packages.

The concrete context implementations live in ``sage-kernel``.  Keeping these
structural interfaces in ``sage-common`` prevents the foundation layer from
importing the runtime layer solely for annotations.
"""

from __future__ import annotations

from concurrent.futures import Future
from logging import Logger
from typing import Any, Protocol


class _ServiceCallerProtocol(Protocol):
    """Operations shared by task and service runtime contexts."""

    name: str

    @property
    def logger(self) -> Logger:
        """Return the context logger."""

    def call_service(
        self,
        service_name: str,
        *args: Any,
        timeout: float | None = None,
        method: str | None = None,
        **kwargs: Any,
    ) -> Any:
        """Call a registered service synchronously."""

    def call_service_async(
        self,
        service_name: str,
        *args: Any,
        timeout: float | None = None,
        method: str | None = None,
        **kwargs: Any,
    ) -> Future[Any]:
        """Call a registered service asynchronously."""


class TaskContextProtocol(_ServiceCallerProtocol, Protocol):
    """Structural interface injected into operator functions."""


class ServiceContextProtocol(_ServiceCallerProtocol, Protocol):
    """Structural interface injected into services."""
