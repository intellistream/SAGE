"""Interface definitions for agentic.

This module defines the abstract interfaces and registries for agentic components.
Concrete implementations are provided by the external package 'isage-agentic'.

Merged modules:
- Intent recognition (from sage.libs.intent)
- Reasoning strategies (from sage.libs.reasoning)
- SIAS (will be in isage-agentic[sias])

Architecture:
- Interface layer (here): Abstract base classes, factory pattern
- Implementation layer (isage-agentic): Concrete implementations

Usage:
    # Import interfaces
    from sage.libs.agentic.interface import BaseAgent, create_agent

    # In isage-agentic, register implementations
    from sage.libs.agentic.interface import register_agent
    register_agent("react", ReactAgent)
"""

from .base import *  # noqa: F401, F403
from .factory import *  # noqa: F401, F403

__all__ = [
    # Base classes
    "AgentAction",
    "AgentResult",
    "Intent",
    "BaseAgent",
    "BasePlanner",
    "BaseToolSelector",
    "BaseOrchestrator",
    "IntentRecognizer",
    "IntentClassifier",
    "BaseReasoningStrategy",
    # Factory functions
    "register_agent",
    "create_agent",
    "list_agents",
    "register_planner",
    "create_planner",
    "list_planners",
    "register_tool_selector",
    "create_tool_selector",
    "list_tool_selectors",
    "register_orchestrator",
    "create_orchestrator",
    "list_orchestrators",
    "register_intent_recognizer",
    "create_intent_recognizer",
    "list_intent_recognizers",
    "register_intent_classifier",
    "create_intent_classifier",
    "list_intent_classifiers",
    "register_reasoning_strategy",
    "create_reasoning_strategy",
    "list_reasoning_strategies",
]
