from __future__ import annotations

import logging
from typing import Any, TypeVar

T = TypeVar("T")


def create_with_context(
    target_class: type[T],
    context: Any,
    context_attr_name: str = "ctx",
    *args,
    **kwargs,
) -> T:
    """Create an instance with context injected before ``__init__`` runs."""
    if context is None:
        return target_class(*args, **kwargs)

    instance = target_class.__new__(target_class)

    try:
        setattr(instance, context_attr_name, context)
    except (AttributeError, TypeError) as exc:
        logging.warning("Failed to inject context into %s: %s", target_class.__name__, exc)
        instance = target_class(*args, **kwargs)
        try:
            setattr(instance, context_attr_name, context)
        except (AttributeError, TypeError):
            logging.warning(
                "Failed to inject context after construction for %s",
                target_class.__name__,
            )
        return instance

    instance.__init__(*args, **kwargs)  # type: ignore[misc]
    return instance


def create_service_with_context(
    service_class: type[T], service_context: Any | None, *args, **kwargs
) -> T:
    """Create a service instance with ``ctx`` injected."""
    return create_with_context(service_class, service_context, "ctx", *args, **kwargs)
