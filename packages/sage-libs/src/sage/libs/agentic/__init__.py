"""Agentic layer - Agent framework, planning, and workflow optimization.

**Status**: 🚧 Preparing for extraction to `isage-agentic` package (~1.1M, 65 files)

This module serves as the **interface/registry layer** for agentic components.
Heavy implementations will be moved to the external `isage-agentic` package.

Public API (stable interfaces):
- interfaces: Protocol definitions (Agent, Planner, ToolSelector, WorkflowOptimizer)
- registry: Factory and registration system

Current implementations (will move to isage-agentic):
- agents: Agent implementations, planners, tool selection, bots, runtime
- intent: Intent classification and routing
- workflow: Workflow generation and optimization
- workflows: Concrete workflow presets

Usage:
    # Interface layer (will remain in sage-libs)
    from sage.libs.agentic.interfaces import Planner, ToolSelector
    from sage.libs.agentic.registry import planner_registry, tool_selector_registry

    # Create instances via registry
    planner = planner_registry.create("react", llm=llm_client)
    selector = tool_selector_registry.create("hybrid", embedder=embedder)

    # Current implementations (will require isage-agentic package in future)
    from sage.libs.agentic.agents.planning import ReActPlanner  # Future: isage_agentic.planning

See: packages/sage-libs/docs/agentic/EXTERNALIZATION_PLAN.md
"""

# Core submodules (implementations that will move to external package)
# Legacy/backward compatibility exports
from . import (
    agents,  # Agent framework, planning, tool selection
    intent,  # Intent classification
    interfaces,
    reasoning,  # Search algorithms (beam, DFS, BFS, scoring)
    registry,
    sias,  # Streaming Importance-Aware System (tool selection reasoning)
    workflow,  # Workflow optimization
    workflows,
)
from . import eval as evaluation  # Rename to avoid shadowing built-in eval()

# New interface layer (stable API for external packages)
try:
    from .interface import (
        PlannerProtocol,
        PlannerRegistry,
        PlanRequest,
        PlanResult,
        SelectorRegistry,
        ToolSelectorProtocol,
    )

    _LEGACY_INTERFACE_AVAILABLE = True
except ImportError:
    _LEGACY_INTERFACE_AVAILABLE = False

__all__ = [
    # Interface layer (stable)
    "interfaces",
    "registry",
    # Current implementations (transitional)
    "agents",
    "intent",
    "workflow",
    "workflows",
    "reasoning",  # Search algorithms
    "sias",  # Tool selection reasoning
    "evaluation",  # Eval metrics (renamed from 'eval' to avoid built-in shadow)
]

# Add legacy exports if available
if _LEGACY_INTERFACE_AVAILABLE:
    __all__.extend(
        [
            "PlannerProtocol",
            "ToolSelectorProtocol",
            "PlannerRegistry",
            "SelectorRegistry",
            "PlanRequest",
            "PlanResult",
        ]
    )
