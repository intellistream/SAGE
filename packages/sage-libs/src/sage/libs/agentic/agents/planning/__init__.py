"""
Planning Module

Provides hierarchical planning and timing judgment capabilities for agents.

Components:
- HierarchicalPlanner: Multi-step task decomposition with dependency management
- TimingDeciders: Rule-based, LLM-based, and hybrid timing judgment
- DependencyGraph: Dependency validation and topological sorting
- Utilities: Plan repair, validation, and improvement suggestions

Usage:
    >>> from sage.libs.agentic.agents.planning import (
    ...     HierarchicalPlanner,
    ...     RuleBasedTimingDecider,
    ...     PlanRequest,
    ...     TimingMessage,
    ...     PlannerConfig,
    ...     TimingConfig
    ... )
    >>>
    >>> # Create planner
    >>> config = PlannerConfig(min_steps=5, max_steps=10)
    >>> planner = HierarchicalPlanner.from_config(
    ...     config=config,
    ...     llm_client=your_llm_client,
    ...     tool_selector=your_tool_selector
    ... )
    >>>
    >>> # Generate plan
    >>> request = PlanRequest(
    ...     goal="Deploy application to production",
    ...     tools=[...],
    ...     constraints=["No downtime", "Rollback capability"]
    ... )
    >>> result = planner.plan(request)
    >>>
    >>> # Make timing decision
    >>> timing_config = TimingConfig(decision_threshold=0.8)
    >>> decider = RuleBasedTimingDecider(timing_config)
    >>> message = TimingMessage(user_message="What's the weather?")
    >>> decision = decider.decide(message)
"""

# Schemas and Data Structures
# Base Classes and Protocols
from .base import (
    BasePlanner,
    BaseTimingDecider,
    PlannerProtocol,
    TimingDeciderProtocol,
)
from .dependency_graph import DependencyGraph

# Core Implementations
from .hierarchical_planner import HierarchicalPlanner
from .react_planner import ReActConfig, ReActPlanner, ReActStep, ReActTrace
from .schemas import (
    PlannerConfig,
    PlanRequest,
    PlanResult,
    PlanStep,
    TimingConfig,
    TimingDecision,
    TimingMessage,
    ToolMetadata,
)
from .simple_llm_planner import SimpleLLMPlanner
from .timing_decider import (
    HybridTimingDecider,
    LLMBasedTimingDecider,
    RuleBasedTimingDecider,
)
from .tot_planner import (
    SearchMethod,
    ThoughtNode,
    ToTConfig,
    TreeOfThoughtsPlanner,
)

# Utilities
from .utils.repair import (
    create_fallback_plan,
    extract_and_repair_plan,
    extract_json_array,
    normalize_plan_steps,
    repair_json,
)
from .utils.validators import (
    check_plan_constraints,
    suggest_plan_improvements,
    validate_plan_result,
    validate_step_count,
    validate_step_dependencies,
    validate_tool_availability,
)

__all__ = [
    # Schemas
    "PlanStep",
    "PlanRequest",
    "PlanResult",
    "PlannerConfig",
    "TimingMessage",
    "TimingDecision",
    "TimingConfig",
    "ToolMetadata",
    # Base Classes
    "PlannerProtocol",
    "BasePlanner",
    "TimingDeciderProtocol",
    "BaseTimingDecider",
    # Planners
    "HierarchicalPlanner",
    "SimpleLLMPlanner",
    "ReActPlanner",
    "ReActConfig",
    "ReActStep",
    "ReActTrace",
    "TreeOfThoughtsPlanner",
    "ToTConfig",
    "ThoughtNode",
    "SearchMethod",
    # Timing Deciders
    "RuleBasedTimingDecider",
    "LLMBasedTimingDecider",
    "HybridTimingDecider",
    # Utilities
    "DependencyGraph",
    "extract_and_repair_plan",
    "extract_json_array",
    "repair_json",
    "normalize_plan_steps",
    "create_fallback_plan",
    "validate_plan_result",
    "validate_step_dependencies",
    "validate_tool_availability",
    "validate_step_count",
    "check_plan_constraints",
    "suggest_plan_improvements",
]
