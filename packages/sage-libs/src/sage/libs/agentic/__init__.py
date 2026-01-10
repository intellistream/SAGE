"""Unified Agentic interfaces.

Status: implementations have been externalized to the `isage-agentic` package. This module now
exposes only the registry/interfaces. Install the external package to obtain concrete agents:

    pip install isage-agentic
    # or
    pip install -e packages/sage-libs[agentic]

The external package will automatically register its implementations with the factory.
"""

from __future__ import annotations

import warnings

from sage.libs.agentic.interface import (
    Agent,
    AgenticRegistryError,
    Planner,
    ToolSelector,
    WorkflowEngine,
    create_agent,
    create_planner,
    create_tool_selector,
    create_workflow_engine,
    list_agents,
    list_planners,
    list_tool_selectors,
    list_workflow_engines,
    register_agent,
    register_planner,
    register_tool_selector,
    register_workflow_engine,
)

# Try to auto-import external package if available
try:
    import isage_agentic  # noqa: F401

    _EXTERNAL_AVAILABLE = True
except ImportError:
    _EXTERNAL_AVAILABLE = False
    warnings.warn(
        "Agentic implementations not available. Install 'isage-agentic' package:\n"
        "  pip install isage-agentic\n"
        "or: pip install isage-libs[agentic]",
        ImportWarning,
        stacklevel=2,
    )

__all__ = [
    # Base classes
    "Agent",
    "Planner",
    "ToolSelector",
    "WorkflowEngine",
    # Registry
    "AgenticRegistryError",
    "register_agent",
    "register_planner",
    "register_tool_selector",
    "register_workflow_engine",
    # Factory
    "create_agent",
    "create_planner",
    "create_tool_selector",
    "create_workflow_engine",
    # Discovery
    "list_agents",
    "list_planners",
    "list_tool_selectors",
    "list_workflow_engines",
]
