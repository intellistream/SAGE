from unittest.mock import Mock

import pytest

from sage.libs.agentic.agents.action.mcp_registry import MCPRegistry
from sage.libs.agentic.agents.profile.profile import BaseProfile
from sage.middleware.operators.agent.runtime import AgentRuntime


@pytest.fixture
def mock_profile():
    profile = Mock(spec=BaseProfile)
    profile.render_system_prompt.return_value = "System Prompt"
    profile.merged.return_value = profile
    return profile


@pytest.fixture
def mock_planner():
    # Don't use spec to avoid getting plan_stream attribute
    # This forces the runtime to use the fallback non-streaming path
    planner = Mock()
    # Remove plan_stream so runtime uses planner.plan() instead
    del planner.plan_stream
    return planner


@pytest.fixture
def mock_tools():
    tools = Mock(spec=MCPRegistry)
    tools.describe.return_value = {
        "test_tool": {
            "description": "A test tool",
            "input_schema": {
                "type": "object",
                "properties": {"arg1": {"type": "string"}},
                "required": ["arg1"],
            },
        }
    }
    return tools


@pytest.fixture
def agent_runtime(mock_profile, mock_planner, mock_tools):
    return AgentRuntime(profile=mock_profile, planner=mock_planner, tools=mock_tools, max_steps=5)


def test_step_success(agent_runtime, mock_planner, mock_tools):
    """Test successful execution of a plan."""
    # Mock plan
    mock_planner.plan.return_value = [
        {"type": "tool", "name": "test_tool", "arguments": {"arg1": "value1"}},
        {"type": "reply", "text": "Done"},
    ]

    # Mock tool execution
    mock_tools.call.return_value = "Tool Result"

    result = agent_runtime.step("Do something")

    assert result["reply"] == "Done"
    assert len(result["observations"]) == 1
    assert result["observations"][0]["tool"] == "test_tool"
    assert result["observations"][0]["ok"] is True
    assert result["observations"][0]["result"] == "Tool Result"

    mock_tools.call.assert_called_with("test_tool", {"arg1": "value1"})


def test_step_tool_validation_error(agent_runtime, mock_planner, mock_tools):
    """Test tool validation failure (missing required argument)."""
    mock_planner.plan.return_value = [
        {"type": "tool", "name": "test_tool", "arguments": {}},  # Missing arg1
        {"type": "reply", "text": "Done"},
    ]

    result = agent_runtime.step("Do something")

    assert len(result["observations"]) == 1
    assert result["observations"][0]["ok"] is False
    assert "Missing required fields" in result["observations"][0]["error"]

    # Tool should NOT be called
    mock_tools.call.assert_not_called()


def test_step_tool_execution_error(agent_runtime, mock_planner, mock_tools):
    """Test tool execution failure."""
    mock_planner.plan.return_value = [
        {"type": "tool", "name": "test_tool", "arguments": {"arg1": "value1"}},
        {"type": "reply", "text": "Done"},
    ]

    mock_tools.call.side_effect = Exception("Tool Failed")

    result = agent_runtime.step("Do something")

    assert len(result["observations"]) == 1
    assert result["observations"][0]["ok"] is False
    assert "Tool Failed" in result["observations"][0]["error"]


def test_execute_str(agent_runtime, mock_planner, mock_tools):
    """Test execute with string input."""
    mock_planner.plan.return_value = [{"type": "reply", "text": "Hello"}]

    result = agent_runtime.execute("Hi")

    assert isinstance(result, dict)
    assert result["reply"] == "Hello"


def test_execute_dict(agent_runtime, mock_planner, mock_tools):
    """Test execute with dict input."""
    mock_planner.plan.return_value = [{"type": "reply", "text": "Hello"}]

    result = agent_runtime.execute({"query": "Hi", "max_steps": 3})

    assert isinstance(result, dict)
    assert result["reply"] == "Hello"
    assert agent_runtime.max_steps == 5  # Should be restored


def test_planning_failure(agent_runtime, mock_planner):
    """Test handling of planning failure."""
    mock_planner.plan.side_effect = Exception("Planning Error")

    result = agent_runtime.step("Hi")

    # When planning fails, the result has empty reply and observations
    # The error is yielded as an event in step_stream, not returned in the result
    assert result["reply"] == ""
    assert result["observations"] == []
    assert result["plan"] == []
