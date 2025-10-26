"""Service proxy manager for runtime contexts.

This layer wraps the lower-level ``ServiceManager`` to provide
cached service discovery and a streamlined API that works across
synchronous and asynchronous workflows.
"""

from __future__ import annotations

import logging
import threading
from typing import Any


class ProxyManager:
    """Unified proxy for service invocation.

    The proxy manager is responsible for resolving service metadata,
    delegating calls to :class:`ServiceManager`, and caching queue
    descriptors so repeated calls avoid hitting the control plane.
    """

    _DEFAULT_TIMEOUT: float = 10.0
    _DEFAULT_ASYNC_TIMEOUT: float = 30.0

    def __init__(self, context: Any, logger: logging.Logger | None = None) -> None:
        self._context = context
        self._logger = logger or logging.getLogger(__name__)
        self._service_manager = None
        self._lock = threading.RLock()
        self._service_queue_cache: dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _get_service_manager(self):
        with self._lock:
            if self._service_manager is None:
                from sage.kernel.runtime.service.service_caller import ServiceManager

                self._service_manager = ServiceManager(self._context, logger=self._logger)
            return self._service_manager

    def _resolve_service_descriptor(self, service_name: str) -> Any | None:
        """Return a cached queue descriptor for the requested service."""
        with self._lock:
            if service_name in self._service_queue_cache:
                return self._service_queue_cache[service_name]

            descriptor = None
            context = self._context
            if hasattr(context, "service_qds") and context.service_qds:
                descriptor = context.service_qds.get(service_name)
                if descriptor is not None:
                    self._service_queue_cache[service_name] = descriptor
            return descriptor

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def call_sync(
        self,
        service_name: str,
        *args: Any,
        timeout: float | None = None,
        method: str | None = None,
        **kwargs: Any,
    ) -> Any:
        """Perform a synchronous service invocation.

        Args:
            service_name: Logical name of the service to invoke.
            *args: Positional payload forwarded to the service method.
            timeout: Optional timeout override for the call.
            method: Optional explicit method name. Defaults to ``"process"``
                when omitted, enabling pipeline-as-service semantics.
            **kwargs: Additional keyword arguments forwarded to the service.
        """

        manager = self._get_service_manager()
        descriptor = self._resolve_service_descriptor(service_name)
        if descriptor is not None:
            manager.cache_service_descriptor(service_name, descriptor)

        return manager.call_sync(
            service_name,
            *args,
            timeout=(timeout if timeout is not None else self._DEFAULT_TIMEOUT),
            method=method,
            **kwargs,
        )

    def call_async(
        self,
        service_name: str,
        *args: Any,
        timeout: float | None = None,
        method: str | None = None,
        **kwargs: Any,
    ):
        """Perform an asynchronous service invocation returning a Future."""

        manager = self._get_service_manager()
        descriptor = self._resolve_service_descriptor(service_name)
        if descriptor is not None:
            manager.cache_service_descriptor(service_name, descriptor)

        return manager.call_async(
            service_name,
            *args,
            timeout=(timeout if timeout is not None else self._DEFAULT_ASYNC_TIMEOUT),
            method=method,
            **kwargs,
        )

    def shutdown(self) -> None:
        """Release any underlying resources held by the proxy manager."""
        with self._lock:
            if self._service_manager is not None:
                try:
                    self._service_manager.shutdown()
                finally:
                    self._service_manager = None
                    self._service_queue_cache.clear()

    # ------------------------------------------------------------------
    # Introspection helpers
    # ------------------------------------------------------------------
    @property
    def service_manager(self):
        """Expose the underlying :class:`ServiceManager` instance."""
        return self._get_service_manager()
