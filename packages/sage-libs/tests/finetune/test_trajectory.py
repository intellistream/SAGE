"""Unit tests for FireAct trajectory collection and processing."""

import json
import tempfile
from pathlib import Path

import pytest

from sage.libs.finetune.agent.trajectory import (
    AgentTrajectory,
    CollectorConfig,
    SFTConversionConfig,
    TrajectoryCollector,
    TrajectoryFilter,
    TrajectoryStep,
    TrajectoryToSFTConverter,
    load_trajectories,
)


class TestTrajectoryStep:
    """Tests for TrajectoryStep dataclass."""

    def test_create_step_basic(self):
        """Test creating a basic trajectory step."""
        step = TrajectoryStep(
            step_id=0,
            thought="I need to search for information",
            action="search",
            action_input={"query": "Python programming"},
            observation="Found 10 results about Python...",
        )
        assert step.step_id == 0
        assert step.thought == "I need to search for information"
        assert step.action == "search"
        assert step.action_input == {"query": "Python programming"}
        assert step.observation == "Found 10 results about Python..."
        assert step.reward == 0.0  # default

    def test_create_step_with_reward(self):
        """Test creating a step with explicit reward."""
        step = TrajectoryStep(
            step_id=1,
            thought="Final answer",
            action="finish",
            action_input={"answer": "The answer is 42"},
            observation="Task completed",
            reward=1.0,
        )
        assert step.reward == 1.0
        assert step.step_id == 1

    def test_step_to_dict(self):
        """Test converting step to dictionary."""
        step = TrajectoryStep(
            step_id=2,
            thought="Thinking...",
            action="calculate",
            action_input={"expression": "2 + 2"},
            observation="4",
            reward=0.5,
        )
        d = step.to_dict()
        assert d["step_id"] == 2
        assert d["thought"] == "Thinking..."
        assert d["action"] == "calculate"
        assert d["action_input"] == {"expression": "2 + 2"}
        assert d["observation"] == "4"
        assert d["reward"] == 0.5

    def test_step_from_dict(self):
        """Test creating step from dictionary."""
        data = {
            "step_id": 3,
            "thought": "Let me check",
            "action": "lookup",
            "action_input": {"key": "API docs"},
            "observation": "Found documentation",
            "reward": 0.8,
        }
        step = TrajectoryStep.from_dict(data)
        assert step.step_id == 3
        assert step.thought == "Let me check"
        assert step.action == "lookup"
        assert step.reward == 0.8


class TestAgentTrajectory:
    """Tests for AgentTrajectory dataclass."""

    def test_create_empty_trajectory(self):
        """Test creating an empty trajectory."""
        traj = AgentTrajectory(
            trajectory_id="traj_001",
            task_id="task_001",
            instruction="What is the weather?",
            steps=[],
        )
        assert traj.trajectory_id == "traj_001"
        assert traj.instruction == "What is the weather?"
        assert len(traj.steps) == 0
        assert traj.success is False  # default
        assert traj.total_reward == 0.0  # default
        assert traj.num_steps == 0

    def test_create_trajectory_with_steps(self):
        """Test creating trajectory with multiple steps."""
        steps = [
            TrajectoryStep(0, "Think 1", "action1", {"a": 1}, "obs1", 0.3),
            TrajectoryStep(1, "Think 2", "action2", {"b": 2}, "obs2", 0.5),
            TrajectoryStep(2, "Think 3", "finish", {"answer": "done"}, "done", 1.0),
        ]
        traj = AgentTrajectory(
            trajectory_id="traj_002",
            task_id="task_002",
            instruction="Complex question",
            steps=steps,
            success=True,
            total_reward=1.8,
        )
        assert len(traj.steps) == 3
        assert traj.success is True
        assert traj.total_reward == 1.8
        assert traj.num_steps == 3

    def test_trajectory_tools_used(self):
        """Test tools_used property."""
        steps = [
            TrajectoryStep(0, "T1", "search", {}, "o1"),
            TrajectoryStep(1, "T2", "calculate", {}, "o2"),
            TrajectoryStep(2, "T3", "finish", {}, "o3"),
        ]
        traj = AgentTrajectory(
            trajectory_id="traj_003",
            task_id="task_003",
            instruction="Test",
            steps=steps,
        )
        tools = traj.tools_used
        assert "search" in tools
        assert "calculate" in tools
        assert "finish" not in tools  # finish is excluded

    def test_trajectory_to_dict(self):
        """Test converting trajectory to dictionary."""
        steps = [TrajectoryStep(0, "Think", "act", {"x": 1}, "obs", 0.5)]
        traj = AgentTrajectory(
            trajectory_id="traj_004",
            task_id="task_004",
            instruction="Test query",
            steps=steps,
            success=True,
            total_reward=0.5,
        )
        d = traj.to_dict()
        assert d["trajectory_id"] == "traj_004"
        assert d["instruction"] == "Test query"
        assert len(d["steps"]) == 1
        assert d["success"] is True
        assert d["total_reward"] == 0.5

    def test_trajectory_from_dict(self):
        """Test creating trajectory from dictionary."""
        data = {
            "trajectory_id": "traj_005",
            "task_id": "task_005",
            "instruction": "Another query",
            "steps": [
                {
                    "step_id": 0,
                    "thought": "Thinking",
                    "action": "search",
                    "action_input": {"q": "test"},
                    "observation": "results",
                    "reward": 0.7,
                }
            ],
            "success": True,
            "total_reward": 0.7,
        }
        traj = AgentTrajectory.from_dict(data)
        assert traj.trajectory_id == "traj_005"
        assert traj.instruction == "Another query"
        assert len(traj.steps) == 1
        assert traj.steps[0].thought == "Thinking"
        assert traj.success is True

    def test_trajectory_add_step(self):
        """Test adding steps to a trajectory."""
        traj = AgentTrajectory(
            trajectory_id="traj_006",
            task_id="task_006",
            instruction="Test",
        )
        step = TrajectoryStep(0, "Think", "act", {}, "obs", 0.5)
        traj.add_step(step)
        assert traj.num_steps == 1
        assert traj.total_reward == 0.5


class TestTrajectoryCollector:
    """Tests for TrajectoryCollector class."""

    def test_default_config(self):
        """Test collector with default configuration."""

        # Create a mock agent
        class MockAgent:
            def run_step(self, context):
                return {
                    "thought": "I should finish",
                    "action": "finish",
                    "action_input": {},
                }

        collector = TrajectoryCollector(agent=MockAgent())
        assert collector.config.max_steps == 10
        assert collector.config.reward_success == 5.0
        assert collector.config.penalty_error == -1.0

    def test_custom_config(self):
        """Test collector with custom configuration."""

        class MockAgent:
            def run_step(self, context):
                return {"thought": "Done", "action": "finish", "action_input": {}}

        config = CollectorConfig(
            max_steps=5,
            reward_success=10.0,
            penalty_error=-2.0,
            timeout_seconds=30.0,
        )
        collector = TrajectoryCollector(agent=MockAgent(), config=config)
        assert collector.config.max_steps == 5
        assert collector.config.reward_success == 10.0

    def test_collect_single_task(self):
        """Test collecting trajectory for a single task."""

        class SimpleAgent:
            def __init__(self):
                self.step_count = 0

            def run_step(self, context):
                self.step_count += 1
                if self.step_count >= 2:
                    return {"thought": "Done", "action": "finish", "action_input": {}}
                return {
                    "thought": "Working",
                    "action": "search",
                    "action_input": {"q": "test"},
                }

        agent = SimpleAgent()
        collector = TrajectoryCollector(agent=agent)
        tasks = [
            {
                "task_id": "task_001",
                "instruction": "Search for something",
                "available_tools": ["search", "finish"],
            }
        ]
        trajectories = collector.collect(tasks)
        assert len(trajectories) == 1
        assert trajectories[0].task_id == "task_001"
        assert len(trajectories[0].steps) >= 1


class TestTrajectoryFilter:
    """Tests for TrajectoryFilter class."""

    @pytest.fixture
    def sample_trajectories(self) -> list[AgentTrajectory]:
        """Create sample trajectories for testing."""
        return [
            AgentTrajectory(
                trajectory_id="traj_001",
                task_id="task_001",
                instruction="Q1",
                steps=[TrajectoryStep(0, "T", "search", {}, "o", 0.8)],
                success=True,
                total_reward=0.8,
            ),
            AgentTrajectory(
                trajectory_id="traj_002",
                task_id="task_002",
                instruction="Q2",
                steps=[
                    TrajectoryStep(0, "T1", "search", {}, "o1", 0.3),
                    TrajectoryStep(1, "T2", "calculate", {}, "o2", 0.3),
                ],
                success=True,
                total_reward=0.6,
            ),
            AgentTrajectory(
                trajectory_id="traj_003",
                task_id="task_003",
                instruction="Q3",
                steps=[TrajectoryStep(0, "T", "lookup", {}, "o", 0.2)],
                success=False,
                total_reward=0.2,
            ),
            AgentTrajectory(
                trajectory_id="traj_004",
                task_id="task_004",
                instruction="Q4",
                steps=[],
                success=False,
                total_reward=0.0,
            ),
        ]

    def test_filter_by_min_reward(self, sample_trajectories):
        """Test filtering by minimum reward."""
        filter_ = TrajectoryFilter(min_reward=0.5, require_success=False, min_tool_usage=0)
        filtered = filter_.filter(sample_trajectories)
        assert len(filtered) == 2
        assert all(t.total_reward >= 0.5 for t in filtered)

    def test_filter_by_success(self, sample_trajectories):
        """Test filtering by success requirement."""
        filter_ = TrajectoryFilter(require_success=True, min_tool_usage=0)
        filtered = filter_.filter(sample_trajectories)
        assert all(t.success for t in filtered)
        assert len(filtered) == 2

    def test_filter_by_min_steps(self, sample_trajectories):
        """Test filtering by minimum steps."""
        filter_ = TrajectoryFilter(min_steps=2, require_success=False, min_tool_usage=0)
        filtered = filter_.filter(sample_trajectories)
        assert len(filtered) == 1
        assert filtered[0].instruction == "Q2"

    def test_filter_by_max_steps(self, sample_trajectories):
        """Test filtering by maximum steps."""
        filter_ = TrajectoryFilter(
            max_steps=1, require_success=False, min_tool_usage=0, min_steps=0
        )
        filtered = filter_.filter(sample_trajectories)
        # Q1, Q3 have 1 step each, Q4 has 0 steps - all pass max_steps=1
        # Q2 has 2 steps - excluded
        assert len(filtered) == 3

    def test_combined_filters(self, sample_trajectories):
        """Test combining multiple filter criteria."""
        filter_ = TrajectoryFilter(
            min_reward=0.5,
            require_success=True,
            min_steps=1,
            min_tool_usage=0,
        )
        filtered = filter_.filter(sample_trajectories)
        assert len(filtered) == 2  # Q1 and Q2


class TestTrajectoryToSFTConverter:
    """Tests for TrajectoryToSFTConverter class."""

    @pytest.fixture
    def sample_trajectory(self) -> AgentTrajectory:
        """Create a sample trajectory for testing."""
        return AgentTrajectory(
            trajectory_id="traj_001",
            task_id="task_001",
            instruction="What is the capital of France?",
            available_tools=["search", "finish"],
            steps=[
                TrajectoryStep(
                    step_id=0,
                    thought="I should search for this information",
                    action="search",
                    action_input={"query": "capital of France"},
                    observation="Paris is the capital of France",
                    reward=0.8,
                ),
                TrajectoryStep(
                    step_id=1,
                    thought="I now know the answer",
                    action="finish",
                    action_input={"answer": "Paris"},
                    observation="Task completed",
                    reward=1.0,
                ),
            ],
            success=True,
            total_reward=1.8,
        )

    def test_convert_to_alpaca(self, sample_trajectory):
        """Test conversion to Alpaca format."""
        config = SFTConversionConfig(output_format="alpaca")
        converter = TrajectoryToSFTConverter(config)
        examples = converter.convert([sample_trajectory])
        assert len(examples) >= 1
        # Alpaca format has instruction, input, output
        example = examples[0]
        assert "instruction" in example
        assert "output" in example

    def test_convert_to_sharegpt(self, sample_trajectory):
        """Test conversion to ShareGPT format."""
        config = SFTConversionConfig(output_format="sharegpt")
        converter = TrajectoryToSFTConverter(config)
        examples = converter.convert([sample_trajectory])
        assert len(examples) >= 1
        example = examples[0]
        assert "conversations" in example
        assert isinstance(example["conversations"], list)

    def test_convert_to_chatml(self, sample_trajectory):
        """Test conversion to ChatML format."""
        config = SFTConversionConfig(output_format="chatml")
        converter = TrajectoryToSFTConverter(config)
        examples = converter.convert([sample_trajectory])
        assert len(examples) >= 1
        example = examples[0]
        assert "messages" in example
        assert isinstance(example["messages"], list)

    def test_include_observations(self, sample_trajectory):
        """Test including observations in output."""
        config = SFTConversionConfig(
            output_format="alpaca",
            include_observation=True,
        )
        converter = TrajectoryToSFTConverter(config)
        examples = converter.convert([sample_trajectory])
        # Check that observation is somewhere in the output
        output_str = str(examples)
        assert "Paris is the capital of France" in output_str

    def test_exclude_observations(self, sample_trajectory):
        """Test excluding observations from output."""
        config = SFTConversionConfig(
            output_format="alpaca",
            include_observation=False,
        )
        converter = TrajectoryToSFTConverter(config)
        examples = converter.convert([sample_trajectory])
        # Output should not include observation content in main output
        for example in examples:
            if "output" in example:
                assert "Observation:" not in example["output"]


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_load_trajectories_from_jsonl(self):
        """Test loading trajectories from a JSONL file."""
        trajectories_data = [
            {
                "trajectory_id": "traj_001",
                "task_id": "task_001",
                "instruction": "Query 1",
                "steps": [],
                "success": True,
                "total_reward": 0.5,
            },
            {
                "trajectory_id": "traj_002",
                "task_id": "task_002",
                "instruction": "Query 2",
                "steps": [],
                "success": False,
                "total_reward": 0.0,
            },
        ]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            for t in trajectories_data:
                f.write(json.dumps(t) + "\n")
            temp_path = f.name

        try:
            loaded = list(load_trajectories(temp_path))
            assert len(loaded) == 2
            assert loaded[0].instruction == "Query 1"
            assert loaded[1].success is False
        finally:
            Path(temp_path).unlink()


class TestTrajectoryIntegration:
    """Integration tests for the trajectory module."""

    def test_full_pipeline(self):
        """Test the full trajectory collection to SFT conversion pipeline."""
        # Create sample trajectories directly (simulating collection)
        trajectories = []
        for i in range(3):
            steps = []
            for j in range(2):
                steps.append(
                    TrajectoryStep(
                        step_id=j,
                        thought=f"Thought {j}",
                        action=f"action_{j}" if j == 0 else "finish",
                        action_input={"step": j},
                        observation=f"observation_{j}",
                        reward=0.5,
                    )
                )
            traj = AgentTrajectory(
                trajectory_id=f"traj_{i:03d}",
                task_id=f"task_{i:03d}",
                instruction=f"Query {i}",
                steps=steps,
                success=(i % 2 == 0),
                total_reward=1.0,
            )
            trajectories.append(traj)

        assert len(trajectories) == 3

        # Step 2: Filter trajectories
        filter_ = TrajectoryFilter(require_success=True, min_tool_usage=0)
        filtered = filter_.filter(trajectories)
        assert len(filtered) == 2  # Only successful ones

        # Step 3: Convert to SFT format
        converter = TrajectoryToSFTConverter(
            SFTConversionConfig(
                output_format="alpaca",
                include_observation=True,
            )
        )
        sft_examples = converter.convert(filtered)
        assert len(sft_examples) > 0
        # All examples should have proper format
        for example in sft_examples:
            assert "instruction" in example

    def test_save_and_load_trajectories(self):
        """Test saving and loading trajectories."""
        # Create trajectories
        trajectories = [
            AgentTrajectory(
                trajectory_id="traj_001",
                task_id="task_001",
                instruction="Save test query",
                steps=[TrajectoryStep(0, "Think", "search", {"q": "test"}, "result", 0.5)],
                success=True,
                total_reward=0.5,
            )
        ]

        # Save to file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            for traj in trajectories:
                f.write(json.dumps(traj.to_dict()) + "\n")
            temp_path = f.name

        try:
            # Load from file
            loaded = list(load_trajectories(temp_path))
            assert len(loaded) == 1
            assert loaded[0].instruction == "Save test query"
            assert loaded[0].success is True
        finally:
            Path(temp_path).unlink()
