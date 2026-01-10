"""Base interfaces for Agentic components.

This module defines the abstract interfaces for agent systems.
Implementations are provided by the external package 'isage-agentic'.

Key Interfaces:
- Agent: Core agent execution
- Planner: Task planning and decomposition
- ToolSelector: Tool selection for subtasks
- WorkflowOrchestrator: Multi-agent coordination
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Iterator


@dataclass
class AgentResponse:
    """Response from agent execution."""

    result: Any
    reasoning: str = ""
    tool_calls: list[dict[str, Any]] = None
    metadata: dict[str, Any] = None

    def __post_init__(self):
        if self.tool_calls is None:
            self.tool_calls = []
        if self.metadata is None:
            self.metadata = {}


class Agent(ABC):
    """Abstract base class for all agents.

    Examples of implementations:
    - ReAct: Reasoning + Acting loop
    - ReWOO: Reasoning Without Observation
    - Reflexion: Self-reflection agent
    """

    @abstractmethod
    def run(self, task: str, **kwargs: Any) -> AgentResponse:
        """Execute the agent with the given task.

        Args:
            task: Task description or user query
            **kwargs: Additional task-specific parameters

        Returns:
            AgentResponse containing result and metadata
        """
        pass

    @abstractmethod
    def reset(self) -> None:
        """Reset agent state (e.g., clear conversation history)."""
        pass

    def stream(self, task: str, **kwargs: Any) -> Iterator[AgentResponse]:
        """Stream execution results (optional).

        Default implementation yields final result.
        Streaming agents should override this.
        """
        yield self.run(task, **kwargs)


class Planner(ABC):
    """Abstract base class for planning components.

    Examples of implementations:
    - Sequential Planner: Linear step-by-step plans
    - Hierarchical Planner: Tree-structured plans
    - Dynamic Planner: Adaptive replanning
    """

    @abstractmethod
    def plan(self, goal: str, context: dict[str, Any]) -> list[dict[str, Any]]:
        """Generate a plan for achieving the goal.

        Args:
            goal: High-level goal description
            context: Planning context (constraints, resources, etc.)

        Returns:
            List of plan steps, each step is a dict with:
              - action: Action to take
              - params: Action parameters
              - dependencies: List of step indices this depends on
        """
        pass

    def replan(
        self,
        original_plan: list[dict[str, Any]],
        feedback: str,
        context: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Revise a plan based on execution feedback.

        Args:
            original_plan: Previously generated plan
            feedback: Feedback from execution (errors, partial results)
            context: Updated context

        Returns:
            Revised plan

        Note:
            Default implementation regenerates from scratch.
            Implementations can override for smarter replanning.
        """
        return self.plan(goal=feedback, context=context)


class ToolSelector(ABC):
    """Abstract base class for tool selection components.

    Tool selectors choose appropriate tools for subtasks.

    Examples of implementations:
    - Embedding-based: Use semantic similarity
    - LLM-based: Use LLM for selection
    - Rule-based: Use predefined rules
    """

    @abstractmethod
    def select(self, task: str, available_tools: list[dict[str, Any]], top_k: int = 5) -> list[str]:
        """Select appropriate tools for the task.

        Args:
            task: Task description
            available_tools: List of tool definitions, each dict contains:
              - name: Tool name
              - description: Tool description
              - parameters: Tool parameters schema (optional)
            top_k: Maximum number of tools to select

        Returns:
            Selected tool names in priority order
        """
        pass

    def rank(self, task: str, tool_names: list[str]) -> list[tuple[str, float]]:
        """Rank tools by relevance (optional).

        Args:
            task: Task description
            tool_names: List of tool names

        Returns:
            List of (tool_name, score) tuples, sorted by score descending
        """
        # Default: return unscored list
        return [(name, 0.0) for name in tool_names]


class WorkflowEngine(ABC):
    """Abstract base class for workflow execution engines.

    Workflow engines execute multi-step workflows with agents.

    Examples of implementations:
    - Sequential: Execute steps in order
    - DAG: Execute steps based on dependency graph
    - Dynamic: Adaptive workflow execution
    """

    @abstractmethod
    def execute(self, workflow: dict[str, Any], context: dict[str, Any] = None) -> dict[str, Any]:
        """Execute a workflow definition.

        Args:
            workflow: Workflow definition containing:
              - steps: List of workflow steps
              - graph: Dependency graph (optional)
              - entry_point: Starting step (optional)
            context: Initial execution context

        Returns:
            Workflow execution results containing:
              - output: Final workflow output
              - trace: Execution trace (optional)
              - metrics: Performance metrics (optional)
        """
        pass

    def add_step(self, name: str, agent: Agent, dependencies: list[str] = None) -> None:
        """Add a step to the workflow (optional).

        Args:
            name: Step identifier
            agent: Agent to execute for this step
            dependencies: List of step names this step depends on
        """
        pass


__all__ = [
    "AgentResponse",
    "Agent",
    "Planner",
    "ToolSelector",
    "WorkflowEngine",
]
