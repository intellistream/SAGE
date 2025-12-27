"""Backward-compatibility namespace for legacy ``sage.llm.sageLLM`` imports.

The legacy path is kept to avoid breaking older callers/tests while the
Control Plane modules live under ``sage.llm.control_plane``.
"""

from __future__ import annotations

import sys
from importlib import import_module

_control_plane = import_module("sage.llm.control_plane")

# Expose the control_plane package under the legacy namespace and mirror
# commonly used submodules so deep imports resolve correctly.
__path__ = _control_plane.__path__  # type: ignore[attr-defined]
sys.modules[f"{__name__}.control_plane"] = _control_plane

_alias_targets = {
    "control_plane": _control_plane,
    "control_plane.gpu_manager": import_module("sage.llm.control_plane.gpu_manager"),
    "control_plane.engine_lifecycle": import_module("sage.llm.control_plane.engine_lifecycle"),
    "control_plane.executors": import_module("sage.llm.control_plane.executors"),
    "control_plane.executors.embedding_executor": import_module(
        "sage.llm.control_plane.executors.embedding_executor"
    ),
    "control_plane.request_classifier": import_module(
        "sage.llm.control_plane.request_classifier"
    ),
    "control_plane.strategies": import_module("sage.llm.control_plane.strategies"),
    "control_plane.strategies.hybrid_policy": import_module(
        "sage.llm.control_plane.strategies.hybrid_policy"
    ),
    "control_plane.types": import_module("sage.llm.control_plane.types"),
}

for alias, module in _alias_targets.items():
    sys.modules[f"{__name__}.{alias}"] = module

__all__ = ["control_plane"]
