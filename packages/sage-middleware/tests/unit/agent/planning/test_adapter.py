from unittest.mock import MagicMock

import pytest
from sage_libs.sage_agentic.agents.planning.schemas import PlanResult, PlanStep

from sage.middleware.operators.agent.planning.planner_adapter import SageLibsPlannerAdapter


@pytest.fixture
def mock_planner_cls():
    return MagicMock()


@pytest.fixture
def adapter(mock_planner_cls):
    config = MagicMock()
    llm_client = MagicMock()
    return SageLibsPlannerAdapter(mock_planner_cls, config, llm_client)


def test_plan_success(adapter):
    # Mock the inner planner returning a PlanResult
    mock_result = PlanResult(
        steps=[
            PlanStep(id=1, action="tool1", inputs={"arg": 1}),
            PlanStep(id=2, action="finish", inputs={}),
        ],
        final_thought="Done",
    )
    adapter.planner.plan.return_value = mock_result

    tools = {"tool1": {"description": "desc", "category": "general"}}

    result = adapter.plan("sys", "query", tools)

    # Should convert tool1 to tool step
    assert len(result) == 1
    assert result[0]["type"] == "tool"
    assert result[0]["name"] == "tool1"
    assert result[0]["arguments"] == {"arg": 1}


def test_plan_failure(adapter):
    adapter.planner.plan.side_effect = Exception("Planning error")

    result = adapter.plan("sys", "query", {})

    assert len(result) == 1
    assert result[0]["type"] == "reply"
    assert "Planning failed" in result[0]["text"]


def test_plan_no_steps(adapter):
    """Test that when planner returns no steps, adapter returns 'No plan generated.'"""
    mock_result = PlanResult(steps=[], final_thought="Just a thought")
    adapter.planner.plan.return_value = mock_result

    result = adapter.plan("sys", "query", {})

    # Implementation returns "No plan generated." when steps is empty
    assert len(result) == 1
    assert result[0]["type"] == "reply"
    assert result[0]["text"] == "No plan generated."


def test_plan_context_passed(adapter):
    """Test that context is passed to planner correctly."""
    mock_result = PlanResult(steps=[], final_thought="Done")
    adapter.planner.plan.return_value = mock_result

    adapter.plan("sys", "query", {})

    # Check if context was passed in request
    call_args = adapter.planner.plan.call_args
    assert call_args is not None
    request = call_args[0][0]
    assert "system_prompt" in request.context
    assert request.context["system_prompt"] == "sys"


def test_plan_unknown_action(adapter):
    # Step with action not in tools
    mock_result = PlanResult(
        steps=[PlanStep(id=1, action="unknown_action", inputs={})], final_thought="Fallback thought"
    )
    adapter.planner.plan.return_value = mock_result

    tools = {"tool1": {"category": "general"}}

    result = adapter.plan("sys", "query", tools)

    # Should ignore unknown action and fallback to reply with final_thought
    assert len(result) == 1
    assert result[0]["type"] == "reply"
    assert result[0]["text"] == "Fallback thought"
