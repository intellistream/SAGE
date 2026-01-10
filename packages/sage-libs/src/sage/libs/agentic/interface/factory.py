"""Factory and registry for agentic components.

This module provides dynamic registration and creation of agent implementations.
"""

from __future__ import annotations

from typing import Any, Callable

from sage.libs.agentic.interface.base import Agent, Planner, ToolSelector, WorkflowEngine

# Registry for agent implementations
_AGENT_REGISTRY: dict[str, Callable[..., Agent]] = {}
_PLANNER_REGISTRY: dict[str, Callable[..., Planner]] = {}
_TOOL_SELECTOR_REGISTRY: dict[str, Callable[..., ToolSelector]] = {}
_WORKFLOW_REGISTRY: dict[str, Callable[..., WorkflowEngine]] = {}


class AgenticRegistryError(Exception):
    """Error raised when registry operations fail."""

    pass


def register_agent(name: str, factory: Callable[..., Agent]) -> None:
    """Register an agent implementation.

    Args:
        name: Agent name (e.g., "react", "reflexion")
        factory: Factory function that creates agent instances
    """
    _AGENT_REGISTRY[name] = factory


def register_planner(name: str, factory: Callable[..., Planner]) -> None:
    """Register a planner implementation."""
    _PLANNER_REGISTRY[name] = factory


def register_tool_selector(name: str, factory: Callable[..., ToolSelector]) -> None:
    """Register a tool selector implementation."""
    _TOOL_SELECTOR_REGISTRY[name] = factory


def register_workflow_engine(name: str, factory: Callable[..., WorkflowEngine]) -> None:
    """Register a workflow engine implementation."""
    _WORKFLOW_REGISTRY[name] = factory


def create_agent(name: str, **kwargs: Any) -> Agent:
    """Create an agent instance by name.

    Args:
        name: Registered agent name
        **kwargs: Agent-specific configuration

    Returns:
        Agent instance

    Raises:
        AgenticRegistryError: If agent name not registered

    Example:
        >>> agent = create_agent("react", llm="gpt-4")
        >>> result = agent.run("What is the weather today?")
    """
    if name not in _AGENT_REGISTRY:
        available = list(_AGENT_REGISTRY.keys())
        raise AgenticRegistryError(
            f"Agent '{name}' not registered. Available: {available}. "
            f"Install 'isage-agentic' package for implementations."
        )
    return _AGENT_REGISTRY[name](**kwargs)


def create_planner(name: str, **kwargs: Any) -> Planner:
    """Create a planner instance by name."""
    if name not in _PLANNER_REGISTRY:
        available = list(_PLANNER_REGISTRY.keys())
        raise AgenticRegistryError(
            f"Planner '{name}' not registered. Available: {available}. "
            f"Install 'isage-agentic' package for implementations."
        )
    return _PLANNER_REGISTRY[name](**kwargs)


def create_tool_selector(name: str, **kwargs: Any) -> ToolSelector:
    """Create a tool selector instance by name."""
    if name not in _TOOL_SELECTOR_REGISTRY:
        available = list(_TOOL_SELECTOR_REGISTRY.keys())
        raise AgenticRegistryError(
            f"ToolSelector '{name}' not registered. Available: {available}. "
            f"Install 'isage-agentic' package for implementations."
        )
    return _TOOL_SELECTOR_REGISTRY[name](**kwargs)


def create_workflow_engine(name: str, **kwargs: Any) -> WorkflowEngine:
    """Create a workflow engine instance by name."""
    if name not in _WORKFLOW_REGISTRY:
        available = list(_WORKFLOW_REGISTRY.keys())
        raise AgenticRegistryError(
            f"WorkflowEngine '{name}' not registered. Available: {available}. "
            f"Install 'isage-agentic' package for implementations."
        )
    return _WORKFLOW_REGISTRY[name](**kwargs)


def list_agents() -> list[str]:
    """List all registered agent names."""
    return list(_AGENT_REGISTRY.keys())


def list_planners() -> list[str]:
    """List all registered planner names."""
    return list(_PLANNER_REGISTRY.keys())


def list_tool_selectors() -> list[str]:
    """List all registered tool selector names."""
    return list(_TOOL_SELECTOR_REGISTRY.keys())


def list_workflow_engines() -> list[str]:
    """List all registered workflow engine names."""
    return list(_WORKFLOW_REGISTRY.keys())


__all__ = [
    "AgenticRegistryError",
    "register_agent",
    "register_planner",
    "register_tool_selector",
    "register_workflow_engine",
    "create_agent",
    "create_planner",
    "create_tool_selector",
    "create_workflow_engine",
    "list_agents",
    "list_planners",
    "list_tool_selectors",
    "list_workflow_engines",
]
