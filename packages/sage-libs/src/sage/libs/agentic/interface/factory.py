"""Factory and registry for agentic implementations.

Provides separate registries for:
- Agents
- Planners
- Tool Selectors
- Orchestrators
- Intent Recognizers (merged from intent/)
- Intent Classifiers (merged from intent/)
- Reasoning Strategies (merged from reasoning/)
"""

from typing import Any

from .base import (
    BaseAgent,
    BaseOrchestrator,
    BasePlanner,
    BaseReasoningStrategy,
    BaseToolSelector,
    IntentClassifier,
    IntentRecognizer,
)

# ==================== Registries ====================

_AGENT_REGISTRY: dict[str, type[BaseAgent]] = {}
_PLANNER_REGISTRY: dict[str, type[BasePlanner]] = {}
_TOOL_SELECTOR_REGISTRY: dict[str, type[BaseToolSelector]] = {}
_ORCHESTRATOR_REGISTRY: dict[str, type[BaseOrchestrator]] = {}
_INTENT_RECOGNIZER_REGISTRY: dict[str, type[IntentRecognizer]] = {}
_INTENT_CLASSIFIER_REGISTRY: dict[str, type[IntentClassifier]] = {}
_REASONING_REGISTRY: dict[str, type[BaseReasoningStrategy]] = {}

# ==================== Agent Registry ====================


def register_agent(name: str, cls: type[BaseAgent]) -> None:
    """Register an agent implementation."""
    if name in _AGENT_REGISTRY:
        raise ValueError(f"Agent '{name}' already registered")
    if not issubclass(cls, BaseAgent):
        raise TypeError("Class must inherit from BaseAgent")
    _AGENT_REGISTRY[name] = cls


def create_agent(name: str, **kwargs: Any) -> BaseAgent:
    """Create an agent instance."""
    if name not in _AGENT_REGISTRY:
        available = ", ".join(_AGENT_REGISTRY.keys()) or "none"
        raise KeyError(
            f"Agent '{name}' not found. Available: {available}. Did you install 'isage-agentic'?"
        )
    return _AGENT_REGISTRY[name](**kwargs)


def list_agents() -> list[str]:
    """List registered agents."""
    return list(_AGENT_REGISTRY.keys())


# ==================== Planner Registry ====================


def register_planner(name: str, cls: type[BasePlanner]) -> None:
    """Register a planner implementation."""
    if name in _PLANNER_REGISTRY:
        raise ValueError(f"Planner '{name}' already registered")
    if not issubclass(cls, BasePlanner):
        raise TypeError("Class must inherit from BasePlanner")
    _PLANNER_REGISTRY[name] = cls


def create_planner(name: str, **kwargs: Any) -> BasePlanner:
    """Create a planner instance."""
    if name not in _PLANNER_REGISTRY:
        available = ", ".join(_PLANNER_REGISTRY.keys()) or "none"
        raise KeyError(f"Planner '{name}' not found. Available: {available}")
    return _PLANNER_REGISTRY[name](**kwargs)


def list_planners() -> list[str]:
    """List registered planners."""
    return list(_PLANNER_REGISTRY.keys())


# ==================== Tool Selector Registry ====================


def register_tool_selector(name: str, cls: type[BaseToolSelector]) -> None:
    """Register a tool selector implementation."""
    if name in _TOOL_SELECTOR_REGISTRY:
        raise ValueError(f"Tool selector '{name}' already registered")
    if not issubclass(cls, BaseToolSelector):
        raise TypeError("Class must inherit from BaseToolSelector")
    _TOOL_SELECTOR_REGISTRY[name] = cls


def create_tool_selector(name: str, **kwargs: Any) -> BaseToolSelector:
    """Create a tool selector instance."""
    if name not in _TOOL_SELECTOR_REGISTRY:
        available = ", ".join(_TOOL_SELECTOR_REGISTRY.keys()) or "none"
        raise KeyError(f"Tool selector '{name}' not found. Available: {available}")
    return _TOOL_SELECTOR_REGISTRY[name](**kwargs)


def list_tool_selectors() -> list[str]:
    """List registered tool selectors."""
    return list(_TOOL_SELECTOR_REGISTRY.keys())


# ==================== Orchestrator Registry ====================


def register_orchestrator(name: str, cls: type[BaseOrchestrator]) -> None:
    """Register an orchestrator implementation."""
    if name in _ORCHESTRATOR_REGISTRY:
        raise ValueError(f"Orchestrator '{name}' already registered")
    if not issubclass(cls, BaseOrchestrator):
        raise TypeError("Class must inherit from BaseOrchestrator")
    _ORCHESTRATOR_REGISTRY[name] = cls


def create_orchestrator(name: str, **kwargs: Any) -> BaseOrchestrator:
    """Create an orchestrator instance."""
    if name not in _ORCHESTRATOR_REGISTRY:
        available = ", ".join(_ORCHESTRATOR_REGISTRY.keys()) or "none"
        raise KeyError(f"Orchestrator '{name}' not found. Available: {available}")
    return _ORCHESTRATOR_REGISTRY[name](**kwargs)


def list_orchestrators() -> list[str]:
    """List registered orchestrators."""
    return list(_ORCHESTRATOR_REGISTRY.keys())


# ==================== Intent Recognizer Registry (merged from intent/) ====================


def register_intent_recognizer(name: str, cls: type[IntentRecognizer]) -> None:
    """Register an intent recognizer implementation."""
    if name in _INTENT_RECOGNIZER_REGISTRY:
        raise ValueError(f"Intent recognizer '{name}' already registered")
    if not issubclass(cls, IntentRecognizer):
        raise TypeError("Class must inherit from IntentRecognizer")
    _INTENT_RECOGNIZER_REGISTRY[name] = cls


def create_intent_recognizer(name: str, **kwargs: Any) -> IntentRecognizer:
    """Create an intent recognizer instance."""
    if name not in _INTENT_RECOGNIZER_REGISTRY:
        available = ", ".join(_INTENT_RECOGNIZER_REGISTRY.keys()) or "none"
        raise KeyError(f"Intent recognizer '{name}' not found. Available: {available}")
    return _INTENT_RECOGNIZER_REGISTRY[name](**kwargs)


def list_intent_recognizers() -> list[str]:
    """List registered intent recognizers."""
    return list(_INTENT_RECOGNIZER_REGISTRY.keys())


# ==================== Intent Classifier Registry (merged from intent/) ====================


def register_intent_classifier(name: str, cls: type[IntentClassifier]) -> None:
    """Register an intent classifier implementation."""
    if name in _INTENT_CLASSIFIER_REGISTRY:
        raise ValueError(f"Intent classifier '{name}' already registered")
    if not issubclass(cls, IntentClassifier):
        raise TypeError("Class must inherit from IntentClassifier")
    _INTENT_CLASSIFIER_REGISTRY[name] = cls


def create_intent_classifier(name: str, **kwargs: Any) -> IntentClassifier:
    """Create an intent classifier instance."""
    if name not in _INTENT_CLASSIFIER_REGISTRY:
        available = ", ".join(_INTENT_CLASSIFIER_REGISTRY.keys()) or "none"
        raise KeyError(f"Intent classifier '{name}' not found. Available: {available}")
    return _INTENT_CLASSIFIER_REGISTRY[name](**kwargs)


def list_intent_classifiers() -> list[str]:
    """List registered intent classifiers."""
    return list(_INTENT_CLASSIFIER_REGISTRY.keys())


# ==================== Reasoning Strategy Registry (merged from reasoning/) ====================


def register_reasoning_strategy(name: str, cls: type[BaseReasoningStrategy]) -> None:
    """Register a reasoning strategy implementation."""
    if name in _REASONING_REGISTRY:
        raise ValueError(f"Reasoning strategy '{name}' already registered")
    if not issubclass(cls, BaseReasoningStrategy):
        raise TypeError("Class must inherit from BaseReasoningStrategy")
    _REASONING_REGISTRY[name] = cls


def create_reasoning_strategy(name: str, **kwargs: Any) -> BaseReasoningStrategy:
    """Create a reasoning strategy instance."""
    if name not in _REASONING_REGISTRY:
        available = ", ".join(_REASONING_REGISTRY.keys()) or "none"
        raise KeyError(f"Reasoning strategy '{name}' not found. Available: {available}")
    return _REASONING_REGISTRY[name](**kwargs)


def list_reasoning_strategies() -> list[str]:
    """List registered reasoning strategies."""
    return list(_REASONING_REGISTRY.keys())


__all__ = [
    # Agent
    "register_agent",
    "create_agent",
    "list_agents",
    # Planner
    "register_planner",
    "create_planner",
    "list_planners",
    # Tool Selector
    "register_tool_selector",
    "create_tool_selector",
    "list_tool_selectors",
    # Orchestrator
    "register_orchestrator",
    "create_orchestrator",
    "list_orchestrators",
    # Intent (merged)
    "register_intent_recognizer",
    "create_intent_recognizer",
    "list_intent_recognizers",
    "register_intent_classifier",
    "create_intent_classifier",
    "list_intent_classifiers",
    # Reasoning (merged)
    "register_reasoning_strategy",
    "create_reasoning_strategy",
    "list_reasoning_strategies",
]
