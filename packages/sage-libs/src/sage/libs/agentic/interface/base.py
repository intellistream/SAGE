"""Base interfaces for Agentic components.

This module defines the abstract interfaces for agent systems.
Implementations are provided by the external package 'isage-agentic'.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Agent(ABC):
    """Abstract base class for all agents."""

    @abstractmethod
    def run(self, task: str, **kwargs: Any) -> str:
        """Execute the agent with the given task.

        Args:
            task: Task description or user query
            **kwargs: Additional task-specific parameters

        Returns:
            Agent execution result
        """
        pass

    @abstractmethod
    def reset(self) -> None:
        """Reset agent state."""
        pass


class Planner(ABC):
    """Abstract base class for planning components."""

    @abstractmethod
    def plan(self, goal: str, context: dict[str, Any]) -> list[dict[str, Any]]:
        """Generate a plan for achieving the goal.

        Args:
            goal: High-level goal description
            context: Planning context (constraints, resources, etc.)

        Returns:
            List of plan steps
        """
        pass


class ToolSelector(ABC):
    """Abstract base class for tool selection components."""

    @abstractmethod
    def select(self, task: str, available_tools: list[str]) -> list[str]:
        """Select appropriate tools for the task.

        Args:
            task: Task description
            available_tools: List of available tool names

        Returns:
            Selected tool names in priority order
        """
        pass


class WorkflowEngine(ABC):
    """Abstract base class for workflow execution engines."""

    @abstractmethod
    def execute(self, workflow: dict[str, Any]) -> dict[str, Any]:
        """Execute a workflow definition.

        Args:
            workflow: Workflow definition (DAG, steps, etc.)

        Returns:
            Workflow execution results
        """
        pass


__all__ = [
    "Agent",
    "Planner",
    "ToolSelector",
    "WorkflowEngine",
]
