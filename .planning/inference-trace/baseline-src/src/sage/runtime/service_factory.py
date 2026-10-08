from __future__ import annotations

import logging
from typing import Any

from .context_injection import create_service_with_context


class ServiceFactory:
    """Runtime-local service factory compatible with the kernel service task layer."""

    def __init__(
        self,
        service_name: str,
        service_class: type,
        service_args: tuple[Any, ...] = (),
        service_kwargs: dict[str, Any] | None = None,
    ):
        if not service_name:
            raise ValueError("service_name cannot be empty")
        if service_class is None:
            raise ValueError("service_class cannot be None")

        self.service_name = service_name or service_class.__name__
        self.service_class = service_class
        self.service_args = service_args
        self.service_kwargs = service_kwargs or {}

    def create_service(self, ctx: Any | None = None) -> Any:
        if self.service_class is None:
            raise ValueError(
                f"ServiceFactory for '{self.service_name}': service_class is None. "
                "This may be due to serialization issues in distributed environments."
            )

        return create_service_with_context(
            self.service_class,
            ctx,
            *self.service_args,
            **self.service_kwargs,
        )

    def __repr__(self) -> str:
        service_class_name = (
            self.service_class.__name__
            if getattr(self, "service_class", None) is not None
            else "Unknown"
        )
        return f"<ServiceFactory {getattr(self, 'service_name', 'Unknown')}: {service_class_name}>"

    def __getstate__(self):
        return {
            "service_name": getattr(self, "service_name", None),
            "service_class": getattr(self, "service_class", None),
            "service_args": getattr(self, "service_args", ()),
            "service_kwargs": getattr(self, "service_kwargs", {}),
        }

    def __setstate__(self, state):
        self.service_name = state.get("service_name") or "Unknown"
        self.service_class = state.get("service_class")
        self.service_args = state.get("service_args", ())
        self.service_kwargs = state.get("service_kwargs", {})

        if self.service_class is None:
            logging.warning("ServiceFactory: service_class is None after deserialization")
