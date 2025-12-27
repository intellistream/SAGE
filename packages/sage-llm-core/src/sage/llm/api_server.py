"""Compatibility shim for legacy ``sage.llm.api_server`` imports.

Exports helpers from ``sage.common.components.sage_llm.api_server`` to keep
downstream callers and tests working during the namespace transition.
"""

from sage.common.components.sage_llm.api_server import (
    _select_available_gpus,
    get_served_model_name,
)

__all__ = ["_select_available_gpus", "get_served_model_name"]
