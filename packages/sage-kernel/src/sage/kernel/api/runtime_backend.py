"""Shared runtime backend access helpers for sage-kernel API tiers.

This module centralizes runtime-backend acquisition so both:

- `sage.kernel.facade` (default tier)
- `sage.kernel.api.FlownetEnvironment` (advanced tier)

route through the same protocol-adapter entry point.
"""

from __future__ import annotations

from typing import Any


def get_flownet_runtime_backend() -> Any:
    """Return the process-global Flownet runtime adapter.

    Returns:
        RuntimeBackendProtocol-compatible adapter instance.

    Raises:
        ImportError: If runtime adapter module is unavailable.
    """
    from sage.platform.runtime.adapters.flownet_adapter import get_flownet_adapter

    return get_flownet_adapter()
