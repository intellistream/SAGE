"""
Tests for agentic operators.
"""

from sage.middleware.operators.agentic import (
    PlanningOperator,
    TimingOperator,
    ToolSelectionOperator,
)


class MockSelector:
    """Mock selector for testing."""

    def select(self, query, top_k=5):
        return [{"tool_id": f"tool_{i}"} for i in range(top_k)]


class MockPlanner:
    """Mock planner for testing."""

    def plan(self, request):
        return {"steps": [{"action": "do_something"}]}


class MockTimingDecider:
    """Mock timing decider for testing."""

    def decide(self, message):
        return {"decision": "call"}


class TestToolSelectionOperator:
    """Test tool selection operator."""

    def test_operator_initialization(self):
        """Test creating operator."""
        selector = MockSelector()
        operator = ToolSelectionOperator(selector=selector, config={"selector": {"top_k": 5}})

        assert operator.orchestrator is not None
        assert operator.adapter is not None

    def test_operator_call(self):
        """Test calling operator."""
        selector = MockSelector()
        operator = ToolSelectionOperator(selector=selector, config={"selector": {"top_k": 3}})

        result = operator("test query")

        assert len(result) == 3
        assert result[0]["tool_id"] == "tool_0"

    def test_operator_metrics(self):
        """Test getting metrics."""
        selector = MockSelector()
        operator = ToolSelectionOperator(selector=selector)

        operator("query1")
        operator("query2")

        metrics = operator.get_metrics()
        assert metrics["total_operations"] == 2


class TestPlanningOperator:
    """Test planning operator."""

    def test_operator_initialization(self):
        """Test creating operator."""
        planner = MockPlanner()
        operator = PlanningOperator(planner=planner, config={"planner": {"max_steps": 10}})

        assert operator.orchestrator is not None
        assert operator.adapter is not None

    def test_operator_call(self):
        """Test calling operator."""
        planner = MockPlanner()
        operator = PlanningOperator(planner=planner)

        result = operator("test request")

        assert "steps" in result
        assert len(result["steps"]) > 0

    def test_operator_metrics(self):
        """Test getting metrics."""
        planner = MockPlanner()
        operator = PlanningOperator(planner=planner)

        operator("request1")

        metrics = operator.get_metrics()
        assert metrics["total_operations"] == 1


class TestTimingOperator:
    """Test timing operator."""

    def test_operator_initialization(self):
        """Test creating operator."""
        timing_decider = MockTimingDecider()
        operator = TimingOperator(
            timing_decider=timing_decider, config={"timing": {"threshold": 0.7}}
        )

        assert operator.orchestrator is not None
        assert operator.adapter is not None

    def test_operator_call(self):
        """Test calling operator."""
        timing_decider = MockTimingDecider()
        operator = TimingOperator(timing_decider=timing_decider)

        result = operator("test message")

        assert result["decision"] == "call"

    def test_operator_metrics(self):
        """Test getting metrics."""
        timing_decider = MockTimingDecider()
        operator = TimingOperator(timing_decider=timing_decider)

        operator("message1")
        operator("message2")

        metrics = operator.get_metrics()
        assert metrics["total_operations"] == 2
