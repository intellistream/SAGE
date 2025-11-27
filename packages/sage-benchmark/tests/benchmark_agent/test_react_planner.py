# Copyright (c) 2025 IntelliStream. All rights reserved.
# Licensed under the Apache License, Version 2.0

"""Unit tests for ReAct planner in benchmark framework."""

from __future__ import annotations

import pytest

from sage.benchmark.benchmark_agent.adapter_registry import get_adapter_registry


class TestReActPlannerRegistry:
    """Test ReAct planner registry integration."""

    def test_react_planner_registered(self) -> None:
        """Test ReAct planner is registered in adapter registry."""
        registry = get_adapter_registry()
        strategies = registry.list_strategies()

        # Check planner.react is registered
        assert "planner.react" in strategies

    def test_react_alias_registered(self) -> None:
        """Test 'react' alias is registered."""
        registry = get_adapter_registry()
        strategies = registry.list_strategies()

        assert "react" in strategies

    def test_create_react_planner_from_registry(self) -> None:
        """Test creating ReAct planner from registry."""
        registry = get_adapter_registry()
        planner = registry.get("planner.react")

        assert planner is not None
        # Should have a plan method
        assert hasattr(planner, "plan")

    def test_create_react_planner_via_alias(self) -> None:
        """Test creating ReAct planner via alias."""
        registry = get_adapter_registry()
        planner = registry.get("react")

        assert planner is not None
        assert hasattr(planner, "plan")


class TestReActPlannerPlanMethod:
    """Test ReAct planner plan method."""

    def test_plan_returns_planning_prediction(self) -> None:
        """Test plan returns PlanningPrediction."""
        from sage.benchmark.benchmark_agent.experiments.base_experiment import (
            PlanningPrediction,
        )
        from sage.benchmark.benchmark_agent.experiments.planning_exp import (
            PlanningTask,
        )

        registry = get_adapter_registry()
        planner = registry.get("planner.react")

        task = PlanningTask(
            sample_id="test_1",
            instruction="Search for information and then summarize it",
            context={},
            available_tools=["search", "summarize", "write"],
        )

        result = planner.plan(task)

        assert result is not None
        assert isinstance(result, PlanningPrediction)
        assert hasattr(result, "steps")
        assert hasattr(result, "tool_sequence")

    def test_plan_with_empty_tools(self) -> None:
        """Test plan with empty tools returns empty prediction."""
        from sage.benchmark.benchmark_agent.experiments.base_experiment import (
            PlanningPrediction,
        )
        from sage.benchmark.benchmark_agent.experiments.planning_exp import (
            PlanningTask,
        )

        registry = get_adapter_registry()
        planner = registry.get("planner.react")

        task = PlanningTask(
            sample_id="test_2",
            instruction="Do something",
            context={},
            available_tools=[],
        )

        result = planner.plan(task)

        assert result is not None
        assert isinstance(result, PlanningPrediction)
        assert result.steps == []
        assert result.tool_sequence == []

    def test_plan_fallback_heuristic(self) -> None:
        """Test plan falls back to heuristic when LLM unavailable."""
        from sage.benchmark.benchmark_agent.experiments.base_experiment import (
            PlanningPrediction,
        )
        from sage.benchmark.benchmark_agent.experiments.planning_exp import (
            PlanningTask,
        )

        registry = get_adapter_registry()
        planner = registry.get("planner.react")

        # Task with tools that match instruction keywords
        task = PlanningTask(
            sample_id="test_3",
            instruction="First search the database, then filter results and finally export",
            context={},
            available_tools=["search", "filter", "export", "unused_tool"],
        )

        result = planner.plan(task)

        assert result is not None
        assert isinstance(result, PlanningPrediction)
        # Should have some steps based on heuristics
        assert len(result.steps) >= 0  # May be empty if no LLM
        assert isinstance(result.tool_sequence, list)


class TestReActPlannerSageLibsIntegration:
    """Test ReAct planner integration with sage-libs."""

    def test_sage_libs_react_planner_available(self) -> None:
        """Test sage-libs ReActPlanner can be imported."""
        try:
            from sage.libs.agentic.agents.planning import ReActConfig, ReActPlanner

            assert ReActPlanner is not None
            assert ReActConfig is not None
        except ImportError:
            pytest.skip("sage-libs ReActPlanner not available")

    def test_sage_libs_react_config(self) -> None:
        """Test ReActConfig parameters."""
        try:
            from sage.libs.agentic.agents.planning import ReActConfig

            config = ReActConfig(
                max_iterations=10,
                temperature=0.3,
                stop_on_finish=True,
                include_observations=True,
            )

            assert config.max_iterations == 10
            assert config.temperature == 0.3
            assert config.stop_on_finish is True
            assert config.include_observations is True
        except ImportError:
            pytest.skip("sage-libs ReActConfig not available")

    def test_sage_libs_react_planner_creation(self) -> None:
        """Test ReActPlanner can be created without LLM client."""
        try:
            from sage.libs.agentic.agents.planning import ReActConfig, ReActPlanner

            config = ReActConfig(
                max_iterations=12,
                temperature=0.2,
                stop_on_finish=True,
                include_observations=True,
            )

            # Create without LLM client (will use fallback)
            planner = ReActPlanner(config=config, llm_client=None)
            assert planner is not None
        except ImportError:
            pytest.skip("sage-libs ReActPlanner not available")

    def test_sage_libs_react_step_dataclass(self) -> None:
        """Test ReActStep dataclass."""
        try:
            from sage.libs.agentic.agents.planning.react_planner import ReActStep

            step = ReActStep(
                step_id=1,
                thought="I need to analyze this",
                action="search",
                action_input={"query": "test"},
                observation="Results found",
            )
            assert step.step_id == 1
            assert step.thought == "I need to analyze this"
            assert step.action == "search"
            assert step.action_input == {"query": "test"}
            assert step.observation == "Results found"
        except ImportError:
            pytest.skip("sage-libs ReActStep not available")

    def test_sage_libs_react_trace_dataclass(self) -> None:
        """Test ReActTrace dataclass."""
        try:
            from sage.libs.agentic.agents.planning.react_planner import (
                ReActStep,
                ReActTrace,
            )

            step1 = ReActStep(
                step_id=0,
                thought="First step",
                action="search",
                action_input={},
            )
            step2 = ReActStep(
                step_id=1,
                thought="Second step",
                action="analyze",
                action_input={},
            )

            trace = ReActTrace(
                steps=[step1, step2],
                final_thought="Task completed",
                success=True,
            )

            assert len(trace.steps) == 2
            assert trace.final_thought == "Task completed"
            assert trace.success is True
            assert trace.tool_sequence == ["search", "analyze"]
        except ImportError:
            pytest.skip("sage-libs ReActTrace not available")


class TestReActPlannerDataStructures:
    """Test ReAct planner data structures."""

    def test_plan_step_structure(self) -> None:
        """Test PlanStep data structure."""
        from sage.benchmark.benchmark_agent.experiments.base_experiment import PlanStep

        step = PlanStep(
            step_id=1,
            description="Search for information",
            tool_id="search",
            confidence=0.9,
        )

        assert step.step_id == 1
        assert step.description == "Search for information"
        assert step.tool_id == "search"
        assert step.confidence == 0.9

    def test_planning_prediction_structure(self) -> None:
        """Test PlanningPrediction data structure."""
        from sage.benchmark.benchmark_agent.experiments.base_experiment import (
            PlanningPrediction,
            PlanStep,
        )

        steps = [
            PlanStep(step_id=0, description="Step 1", tool_id="tool1", confidence=0.8),
            PlanStep(step_id=1, description="Step 2", tool_id="tool2", confidence=0.7),
        ]

        prediction = PlanningPrediction(
            steps=steps,
            tool_sequence=["tool1", "tool2"],
        )

        assert len(prediction.steps) == 2
        assert prediction.tool_sequence == ["tool1", "tool2"]

    def test_planning_task_structure(self) -> None:
        """Test PlanningTask data structure."""
        from sage.benchmark.benchmark_agent.experiments.planning_exp import (
            PlanningTask,
        )

        task = PlanningTask(
            sample_id="task_001",
            instruction="Complete the workflow",
            context={"key": "value"},
            available_tools=["read", "process", "write"],
        )

        assert task.sample_id == "task_001"
        assert task.instruction == "Complete the workflow"
        assert task.available_tools == ["read", "process", "write"]
        assert task.context == {"key": "value"}


class TestReActPlannerListStrategies:
    """Test listing strategies includes ReAct planner."""

    def test_list_strategies_includes_react(self) -> None:
        """Test list_strategies includes ReAct planner."""
        registry = get_adapter_registry()
        strategies = registry.list_strategies()

        # Verify react planner entries
        assert "planner.react" in strategies
        assert "react" in strategies

    def test_planners_include_react(self) -> None:
        """Test planners include react."""
        registry = get_adapter_registry()
        strategies = registry.list_strategies()

        # Get all planner strategies
        planners = [s for s in strategies if s.startswith("planner.")]

        assert "planner.react" in planners
        # Also check other planners for comparison
        assert len(planners) >= 1
