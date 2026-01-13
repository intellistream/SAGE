"""
Tests for planning module initialization and exports.
"""

import pytest


def test_planning_module_imports():
    """Test that all key components can be imported."""
    from sage_libs.sage_agentic.agents.planning import (
        BasePlanner,
        BaseTimingDecider,
        DependencyGraph,
        # Implementations
        HierarchicalPlanner,
        HybridTimingDecider,
        LLMBasedTimingDecider,
        PlannerConfig,
        # Base classes
        PlannerProtocol,
        PlanRequest,
        PlanResult,
        # Schemas
        PlanStep,
        RuleBasedTimingDecider,
        TimingConfig,
        TimingDeciderProtocol,
        TimingDecision,
        TimingMessage,
        ToolMetadata,
    )

    # Check that classes are properly defined
    assert PlanStep is not None
    assert HierarchicalPlanner is not None
    assert RuleBasedTimingDecider is not None


def test_plan_step_creation():
    """Test creating PlanStep instances."""
    from sage_libs.sage_agentic.agents.planning import PlanStep

    step = PlanStep(
        id=1,
        action="Search for information",
        tool_id="search_tool",
        inputs={"query": "test"},
        depends_on=[],
        expected_outputs=["results"],
        description="Test step",
    )

    assert step.id == 1
    assert step.action == "Search for information"
    assert step.tool_id == "search_tool"
    assert step.depends_on == []


def test_plan_request_creation():
    """Test creating PlanRequest instances."""
    from sage_libs.sage_agentic.agents.planning import PlanRequest, ToolMetadata

    tool = ToolMetadata(
        tool_id="tool_1",
        name="Test Tool",
        description="A test tool",
        category="testing",
        capabilities=["test"],
    )

    request = PlanRequest(goal="Test goal", tools=[tool], constraints=["constraint1"], max_steps=10)

    assert request.goal == "Test goal"
    assert len(request.tools) == 1
    assert request.max_steps == 10


def test_timing_message_creation():
    """Test creating TimingMessage instances."""
    from sage_libs.sage_agentic.agents.planning import TimingMessage

    message = TimingMessage(
        user_message="What's the weather?",
        conversation_history=[
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ],
        context={},
    )

    assert message.user_message == "What's the weather?"
    assert len(message.conversation_history) == 2


def test_planner_config_defaults():
    """Test PlannerConfig default values."""
    from sage_libs.sage_agentic.agents.planning import PlannerConfig

    config = PlannerConfig()

    assert config.min_steps == 5
    assert config.max_steps == 10
    assert config.enable_repair is True
    assert config.enable_dependency_check is True
    assert config.llm_temperature == 0.7
    assert config.max_retries == 2


def test_timing_config_defaults():
    """Test TimingConfig default values."""
    from sage_libs.sage_agentic.agents.planning import TimingConfig

    config = TimingConfig()

    assert config.decision_threshold == 0.5
    assert config.use_rule_based is True
    assert config.use_learning_based is False
    assert config.history_window == 5
