"""Base classes for agentic components.

This module defines the core abstractions for:
- Agents: Autonomous task executors
- Planners: Task planning and decomposition
- Tool Selectors: Dynamic tool selection
- Orchestrators: Multi-agent coordination
- Intent Recognizers: User intent understanding (merged from intent module)
- Reasoning Strategies: Search and optimization (merged from reasoning module)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional

# ==================== Data Classes ====================


@dataclass
class AgentAction:
    """Represents an action taken by an agent."""

    tool_name: str
    tool_input: dict[str, Any]
    thought: Optional[str] = None
    confidence: float = 1.0


@dataclass
class AgentResult:
    """Result of agent execution."""

    output: Any
    intermediate_steps: list[tuple[AgentAction, str]]
    metadata: dict[str, Any]


@dataclass
class Intent:
    """Recognized user intent."""

    name: str
    confidence: float
    slots: dict[str, Any]
    metadata: dict[str, Any]


# ==================== Agent Base Classes ====================


class BaseAgent(ABC):
    """Abstract base class for all agents."""

    @abstractmethod
    def plan(self, task: str, context: dict[str, Any]) -> list[AgentAction]:
        """Plan actions for a given task."""
        pass

    @abstractmethod
    def execute(self, task: str, **kwargs) -> AgentResult:
        """Execute the agent on a task."""
        pass

    @abstractmethod
    def reset(self) -> None:
        """Reset agent state."""
        pass


class BasePlanner(ABC):
    """Abstract base class for planning strategies."""

    @abstractmethod
    def plan(self, goal: str, available_tools: list[str], context: dict[str, Any]) -> list[str]:
        """Generate a plan as a sequence of tool calls."""
        pass


class BaseToolSelector(ABC):
    """Abstract base class for tool selection."""

    @abstractmethod
    def select_tools(
        self, query: str, available_tools: list[dict[str, Any]], top_k: int = 3
    ) -> list[str]:
        """Select top-k relevant tools for a query."""
        pass

    @abstractmethod
    def add_tool(self, tool_spec: dict[str, Any]) -> None:
        """Add a tool to the selector's knowledge."""
        pass


class BaseOrchestrator(ABC):
    """Abstract base class for multi-agent orchestration."""

    @abstractmethod
    def coordinate(self, task: str, agents: list[BaseAgent], **kwargs) -> AgentResult:
        """Coordinate multiple agents to complete a task."""
        pass


# ==================== Intent Base Classes (merged from intent/) ====================


class IntentRecognizer(ABC):
    """Abstract base class for intent recognition."""

    @abstractmethod
    def recognize(self, text: str, context: Optional[dict[str, Any]] = None) -> Intent:
        """Recognize intent from text."""
        pass


class IntentClassifier(ABC):
    """Abstract base class for intent classification."""

    @abstractmethod
    def classify(self, text: str) -> list[Intent]:
        """Classify text into multiple intents."""
        pass


# ==================== Reasoning Base Classes (merged from reasoning/) ====================


class BaseReasoningStrategy(ABC):
    """Abstract base class for reasoning strategies."""

    @abstractmethod
    def search(
        self, initial_state: Any, goal_check: callable, expand: callable, **kwargs
    ) -> list[Any]:
        """Perform search/reasoning to reach goal."""
        pass


__all__ = [
    # Data classes
    "AgentAction",
    "AgentResult",
    "Intent",
    # Agent classes
    "BaseAgent",
    "BasePlanner",
    "BaseToolSelector",
    "BaseOrchestrator",
    # Intent classes (merged)
    "IntentRecognizer",
    "IntentClassifier",
    # Reasoning classes (merged)
    "BaseReasoningStrategy",
]
