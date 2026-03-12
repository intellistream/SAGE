"""Service primitives exposed from the consolidated SAGE runtime."""

from __future__ import annotations

import logging
from abc import ABC
from typing import Any


class BaseService(ABC):  # noqa: B024
    """Base class for runtime services registered into an environment."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        if not hasattr(self, "ctx"):
            self.ctx: Any | None = None
        self._logger: Any | None = None

    @property
    def logger(self) -> Any:
        if self._logger is None:
            if self.ctx is None:
                self._logger = logging.getLogger(self.__class__.__name__)
            else:
                self._logger = self.ctx.logger
        return self._logger

    @property
    def name(self) -> str:
        if self.ctx is not None:
            return self.ctx.name
        return self.__class__.__name__

    def call_service(
        self,
        service_name: str,
        *args: Any,
        timeout: float | None = None,
        method: str | None = None,
        **kwargs: Any,
    ) -> Any:
        if self.ctx is None:
            raise RuntimeError("Service context not initialized. Cannot access services.")
        return self.ctx.call_service(service_name, *args, timeout=timeout, method=method, **kwargs)

    def call_service_async(
        self,
        service_name: str,
        *args: Any,
        timeout: float | None = None,
        method: str | None = None,
        **kwargs: Any,
    ) -> Any:
        if self.ctx is None:
            raise RuntimeError("Service context not initialized. Cannot access services.")
        return self.ctx.call_service_async(
            service_name,
            *args,
            timeout=timeout,
            method=method,
            **kwargs,
        )

    def setup(self) -> None:
        pass

    def cleanup(self) -> None:
        pass

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass
