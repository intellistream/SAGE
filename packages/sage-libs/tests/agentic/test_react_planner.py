"""
Tests for ReAct Planner

Tests cover:
- ReActPlanner: Basic planning functionality
- ReActStep: Step data structure
- ReActTrace: Trace collection and formatting
- Parsing: LLM response parsing
- Fallback: Heuristic-based planning when LLM unavailable
"""

from unittest.mock import Mock

import pytest


@pytest.mark.unit
class TestReActStep:
    """Test ReActStep data structure."""

    def test_init(self):
        """Test ReActStep initialization."""
        from sage.libs.agentic.agents.planning.react_planner import ReActStep

        step = ReActStep(
            step_id=0,
            thought="I need to read the file first",
            action="file_read",
            action_input={"path": "/tmp/test.txt"},
            observation="File content: hello world",
            confidence=0.9,
        )

        assert step.step_id == 0
        assert step.thought == "I need to read the file first"
        assert step.action == "file_read"
        assert step.action_input == {"path": "/tmp/test.txt"}
        assert step.observation == "File content: hello world"
        assert step.confidence == 0.9

    def test_to_plan_step(self):
        """Test conversion to standard PlanStep."""
        from sage.libs.agentic.agents.planning.react_planner import ReActStep

        step = ReActStep(
            step_id=1,
            thought="Process the data",
            action="data_process",
            action_input={"format": "json"},
        )

        plan_step = step.to_plan_step()

        assert plan_step.id == 1
        assert plan_step.action == "data_process"
        assert plan_step.tool_id == "data_process"
        assert plan_step.description == "Process the data"
        assert plan_step.inputs == {"format": "json"}
        assert plan_step.depends_on == [0]  # Depends on previous step


@pytest.mark.unit
class TestReActTrace:
    """Test ReActTrace data structure."""

    def test_empty_trace(self):
        """Test empty trace."""
        from sage.libs.agentic.agents.planning.react_planner import ReActTrace

        trace = ReActTrace()

        assert trace.steps == []
        assert trace.final_thought == ""
        assert trace.success is True
        assert trace.tool_sequence == []
        assert trace.reasoning_trace == ""

    def test_trace_with_steps(self):
        """Test trace with multiple steps."""
        from sage.libs.agentic.agents.planning.react_planner import ReActStep, ReActTrace

        steps = [
            ReActStep(
                step_id=0,
                thought="Read config file",
                action="file_read",
            ),
            ReActStep(
                step_id=1,
                thought="Parse the JSON",
                action="data_parse_json",
            ),
            ReActStep(
                step_id=2,
                thought="Send notification",
                action="notification_send",
            ),
        ]

        trace = ReActTrace(
            steps=steps,
            final_thought="Task completed successfully",
            success=True,
        )

        assert len(trace.steps) == 3
        assert trace.tool_sequence == ["file_read", "data_parse_json", "notification_send"]
        assert "Thought 1: Read config file" in trace.reasoning_trace
        assert "Action 1: file_read" in trace.reasoning_trace
        assert "Final Thought: Task completed successfully" in trace.reasoning_trace

    def test_trace_excludes_finish(self):
        """Test that 'finish' action is excluded from tool_sequence."""
        from sage.libs.agentic.agents.planning.react_planner import ReActStep, ReActTrace

        steps = [
            ReActStep(step_id=0, thought="Do something", action="tool_a"),
            ReActStep(step_id=1, thought="Done", action="finish"),
        ]

        trace = ReActTrace(steps=steps)

        assert trace.tool_sequence == ["tool_a"]


@pytest.mark.unit
class TestReActConfig:
    """Test ReActConfig configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        from sage.libs.agentic.agents.planning.react_planner import ReActConfig

        config = ReActConfig()

        assert config.max_iterations == 10
        assert config.temperature == 0.2
        assert config.stop_on_finish is True
        assert config.include_observations is True

    def test_custom_config(self):
        """Test custom configuration."""
        from sage.libs.agentic.agents.planning.react_planner import ReActConfig

        config = ReActConfig(
            min_steps=3,
            max_steps=15,
            max_iterations=20,
            temperature=0.5,
        )

        assert config.min_steps == 3
        assert config.max_steps == 15
        assert config.max_iterations == 20
        assert config.temperature == 0.5


@pytest.mark.unit
class TestReActPlanner:
    """Test ReActPlanner implementation."""

    def test_init_without_llm(self):
        """Test initialization without LLM client."""
        from sage.libs.agentic.agents.planning.react_planner import (
            ReActConfig,
            ReActPlanner,
        )

        config = ReActConfig()
        planner = ReActPlanner(config)

        assert planner.llm_client is None
        assert planner.name == "react_planner"
        assert planner._total_plans == 0

    def test_init_with_llm(self):
        """Test initialization with LLM client."""
        from sage.libs.agentic.agents.planning.react_planner import (
            ReActConfig,
            ReActPlanner,
        )

        mock_llm = Mock()
        config = ReActConfig()
        planner = ReActPlanner(config, llm_client=mock_llm)

        assert planner.llm_client == mock_llm

    def test_from_config(self):
        """Test factory method."""
        from sage.libs.agentic.agents.planning.react_planner import (
            ReActConfig,
            ReActPlanner,
        )

        config = ReActConfig(max_iterations=5)
        planner = ReActPlanner.from_config(config)

        assert planner.react_config.max_iterations == 5

    def test_fallback_plan_generation(self):
        """Test fallback plan when no LLM available."""
        from sage.libs.agentic.agents.planning import (
            PlanRequest,
            ToolMetadata,
        )
        from sage.libs.agentic.agents.planning.react_planner import (
            ReActConfig,
            ReActPlanner,
        )

        config = ReActConfig()
        planner = ReActPlanner(config)  # No LLM

        tools = [
            ToolMetadata(
                tool_id="file_read",
                name="file_read",
                description="Read a file",
                category="io",
            ),
            ToolMetadata(
                tool_id="data_process",
                name="data_process",
                description="Process data",
                category="compute",
            ),
            ToolMetadata(
                tool_id="email_send",
                name="email_send",
                description="Send email",
                category="communication",
            ),
        ]

        request = PlanRequest(
            goal="Read file and process data then send email",
            tools=tools,
            min_steps=2,
            max_steps=5,
        )

        result = planner.plan(request)

        assert result.success
        assert len(result.steps) >= 2
        assert "reasoning_trace" in result.metadata

    def test_plan_with_empty_tools(self):
        """Test planning with no available tools."""
        from sage.libs.agentic.agents.planning import PlanRequest
        from sage.libs.agentic.agents.planning.react_planner import (
            ReActConfig,
            ReActPlanner,
        )

        config = ReActConfig()
        planner = ReActPlanner(config)

        request = PlanRequest(
            goal="Do something",
            tools=[],
            min_steps=1,
            max_steps=5,
        )

        result = planner.plan(request)

        assert not result.success
        assert len(result.steps) == 0

    def test_parse_react_step_basic(self):
        """Test parsing basic ReAct response."""
        from sage.libs.agentic.agents.planning.react_planner import (
            ReActConfig,
            ReActPlanner,
        )

        config = ReActConfig()
        planner = ReActPlanner(config)

        response = """Thought: I need to read the configuration file first.
Action: file_read
Action Input: {"path": "/config.json"}
Observation: Configuration loaded successfully."""

        step = planner._parse_react_step(
            response,
            step_id=0,
            available_tools=["file_read", "data_process", "email_send"],
        )

        assert step is not None
        assert step.thought == "I need to read the configuration file first."
        assert step.action == "file_read"
        assert step.action_input == {"path": "/config.json"}
        assert step.observation == "Configuration loaded successfully."

    def test_parse_react_step_fuzzy_match(self):
        """Test parsing with fuzzy tool matching."""
        from sage.libs.agentic.agents.planning.react_planner import (
            ReActConfig,
            ReActPlanner,
        )

        config = ReActConfig()
        planner = ReActPlanner(config)

        response = """Thought: Send a notification.
Action: send_notification
Action Input: {}"""

        step = planner._parse_react_step(
            response,
            step_id=0,
            available_tools=["file_read", "notification_send", "email_send"],
        )

        assert step is not None
        # Should fuzzy match to notification_send
        assert step.action == "notification_send"

    def test_parse_react_step_finish(self):
        """Test parsing finish action."""
        from sage.libs.agentic.agents.planning.react_planner import (
            ReActConfig,
            ReActPlanner,
        )

        config = ReActConfig()
        planner = ReActPlanner(config)

        response = """Thought: All tasks completed.
Action: finish
Action Input: {}"""

        step = planner._parse_react_step(
            response,
            step_id=5,
            available_tools=["tool_a", "tool_b"],
        )

        assert step is not None
        assert step.action == "finish"

    def test_parse_react_step_invalid(self):
        """Test parsing invalid response."""
        from sage.libs.agentic.agents.planning.react_planner import (
            ReActConfig,
            ReActPlanner,
        )

        config = ReActConfig()
        planner = ReActPlanner(config)

        response = "This is not a valid ReAct response"

        step = planner._parse_react_step(
            response,
            step_id=0,
            available_tools=["tool_a"],
        )

        # Should return None for completely invalid response
        assert step is None


@pytest.mark.unit
class TestReActPlannerWithMockLLM:
    """Test ReActPlanner with mocked LLM."""

    def test_plan_with_llm(self):
        """Test planning with mocked LLM responses."""
        from sage.libs.agentic.agents.planning import (
            PlanRequest,
            ToolMetadata,
        )
        from sage.libs.agentic.agents.planning.react_planner import (
            ReActConfig,
            ReActPlanner,
        )

        # Setup mock LLM
        mock_llm = Mock()
        mock_llm.chat.side_effect = [
            """Thought: First, I need to read the input file.
Action: file_read
Action Input: {}
Observation: File content loaded.""",
            """Thought: Now process the data.
Action: data_process
Action Input: {}
Observation: Data processed.""",
            """Thought: Task complete.
Action: finish
Action Input: {}""",
        ]

        config = ReActConfig(max_iterations=5)
        planner = ReActPlanner(config, llm_client=mock_llm)

        tools = [
            ToolMetadata(
                tool_id="file_read",
                name="file_read",
                description="Read file",
                category="io",
            ),
            ToolMetadata(
                tool_id="data_process",
                name="data_process",
                description="Process data",
                category="compute",
            ),
        ]

        request = PlanRequest(
            goal="Read and process file",
            tools=tools,
            min_steps=1,
            max_steps=5,
        )

        result = planner.plan(request)

        assert result.success
        assert len(result.steps) == 2  # Should have 2 steps before finish
        assert result.tool_sequence == ["file_read", "data_process"]
        assert mock_llm.chat.call_count == 3


@pytest.mark.unit
class TestAdapterRegistryReActIntegration:
    """Test ReAct planner integration with AdapterRegistry."""

    def test_registry_has_react_planner(self):
        """Test that registry contains ReAct planner."""
        from sage.benchmark.benchmark_agent.adapter_registry import get_adapter_registry

        registry = get_adapter_registry()
        strategies = registry.list_strategies()

        assert "planner.react" in strategies
        assert "react" in strategies

    def test_create_react_planner_from_registry(self):
        """Test creating ReAct planner from registry."""
        from sage.benchmark.benchmark_agent.adapter_registry import get_adapter_registry

        registry = get_adapter_registry()
        planner = registry.get("planner.react")

        assert planner is not None
        assert hasattr(planner, "plan")

    def test_react_planner_plan_method(self):
        """Test ReAct planner's plan method through adapter."""
        from sage.benchmark.benchmark_agent.adapter_registry import get_adapter_registry
        from sage.benchmark.benchmark_agent.experiments.planning_exp import PlanningTask

        registry = get_adapter_registry()
        planner = registry.get("planner.react")

        task = PlanningTask(
            sample_id="test_001",
            instruction="Read config file and send notification",
            context={},
            available_tools=["file_read", "notification_send", "email_send"],
        )

        result = planner.plan(task)

        assert result is not None
        assert hasattr(result, "steps")
        assert hasattr(result, "tool_sequence")
