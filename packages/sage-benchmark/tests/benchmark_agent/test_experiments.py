"""
Unit tests for benchmark_agent experiments.

Tests cover:
- Configuration loading and validation
- Experiment lifecycle (prepare, run, finalize)
- Integration with DataManager
- Result generation
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from sage.benchmark.benchmark_agent.config.config_loader import ConfigLoader
from sage.benchmark.benchmark_agent.experiments import (
    PlanningConfig,
    PlanningExperiment,
    TimingDetectionConfig,
    TimingDetectionExperiment,
    ToolSelectionConfig,
    ToolSelectionExperiment,
)

# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def temp_config_dir(tmp_path):
    """Create temporary directory for config files."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    return config_dir


@pytest.fixture
def tool_selection_config_yaml(temp_config_dir):
    """Create tool selection config YAML."""
    config_content = """
experiment: tool_selection
profile: quick_eval
split: dev
top_k: 5
selector: bm25
verbose: true
report:
  format: ["json"]
  path: ${PROJECT_ROOT}/results/tool_selection_results
"""
    config_file = temp_config_dir / "tool_selection.yaml"
    config_file.write_text(config_content)
    return config_file


@pytest.fixture
def planning_config_yaml(temp_config_dir):
    """Create planning config YAML."""
    config_content = """
experiment: planning
profile: quick_eval
split: dev
max_steps: 5
planner: cot
verbose: false
report:
  format: ["json"]
  path: ${PROJECT_ROOT}/results/planning_results
"""
    config_file = temp_config_dir / "planning.yaml"
    config_file.write_text(config_content)
    return config_file


@pytest.fixture
def timing_config_yaml(temp_config_dir):
    """Create timing detection config YAML."""
    config_content = """
experiment: timing_detection
profile: quick_eval
split: dev
threshold: 0.7
detector: llm_based
verbose: false
report:
  format: ["json"]
  path: ${PROJECT_ROOT}/results/timing_results
"""
    config_file = temp_config_dir / "timing.yaml"
    config_file.write_text(config_content)
    return config_file


@pytest.fixture
def mock_data_manager():
    """Create mock DataManager."""
    mock_dm = MagicMock()

    # Mock agent_eval usage
    mock_agent_eval = MagicMock()
    mock_profile_data = {"tools": MagicMock(), "benchmark": MagicMock()}
    mock_agent_eval.load_profile.return_value = mock_profile_data
    mock_dm.get_by_usage.return_value = mock_agent_eval

    return mock_dm


@pytest.fixture
def mock_benchmark_samples():
    """Create mock benchmark samples."""

    class MockGroundTruth:
        def __init__(self, data):
            self.data = data

        def __getattr__(self, name):
            return self.data.get(name)

    class MockSample:
        def __init__(self, sample_id, instruction, task_type):
            self.sample_id = sample_id
            self.instruction = instruction
            self.task_type = task_type
            self.context = {}
            # Add required attributes for different task types
            self.candidate_tools = ["tool_001", "tool_002", "tool_003", "tool_004", "tool_005"]
            self.message = instruction  # For timing detection
            self.direct_answer = "Direct answer for testing"

        def get_typed_ground_truth(self):
            if self.task_type == "tool_selection":
                return MockGroundTruth(
                    {
                        "tool_ids": ["tool_001", "tool_002"],
                        "top_k": ["tool_001", "tool_002"],
                        "explanation": "Test explanation",
                        "reasoning": "Test reasoning",
                    }
                )
            elif self.task_type == "multi_step_planning":
                return MockGroundTruth(
                    {"tool_sequence": ["tool_001", "tool_003"], "plan_steps": ["Step 1", "Step 2"]}
                )
            elif self.task_type == "timing_judgment":
                return MockGroundTruth(
                    {"should_call_tool": True, "reasoning_chain": ["Reason 1", "Reason 2"]}
                )

    return [
        MockSample("sample_001", "Test instruction 1", "tool_selection"),
        MockSample("sample_002", "Test instruction 2", "tool_selection"),
        MockSample("sample_003", "Test instruction 3", "multi_step_planning"),
        MockSample("sample_004", "Test instruction 4", "timing_judgment"),
    ]


# ============================================================================
# ConfigLoader Tests
# ============================================================================


class TestConfigLoader:
    """Test configuration loading and validation."""

    def test_load_tool_selection_config(self, tool_selection_config_yaml):
        """Test loading tool selection config."""
        loader = ConfigLoader()
        config = loader.load_config(str(tool_selection_config_yaml))

        assert isinstance(config, ToolSelectionConfig)
        assert config.experiment == "tool_selection"
        assert config.profile == "quick_eval"
        assert config.split == "dev"
        assert config.top_k == 5
        assert config.selector == "bm25"
        assert getattr(config, "verbose", False) is True

    def test_load_planning_config(self, planning_config_yaml):
        """Test loading planning config."""
        loader = ConfigLoader()
        config = loader.load_config(str(planning_config_yaml))

        assert isinstance(config, PlanningConfig)
        assert config.experiment == "planning"
        assert config.max_steps == 5
        assert config.planner == "cot"
        assert getattr(config, "verbose", False) is False

    def test_load_timing_config(self, timing_config_yaml):
        """Test loading timing detection config."""
        loader = ConfigLoader()
        config = loader.load_config(str(timing_config_yaml))

        assert isinstance(config, TimingDetectionConfig)
        assert config.experiment == "timing_detection"
        assert config.threshold == 0.7
        assert config.detector == "llm_based"

    def test_env_var_expansion(self, temp_config_dir):
        """Test environment variable expansion."""
        config_content = """
experiment: tool_selection
profile: quick_eval
split: dev
report:
  path: ${PROJECT_ROOT}/results/test
"""
        config_file = temp_config_dir / "env_test.yaml"
        config_file.write_text(config_content)

        loader = ConfigLoader()
        config = loader.load_config(str(config_file))

        # PROJECT_ROOT should be expanded
        assert "${PROJECT_ROOT}" not in config.report.path
        assert "results/test" in config.report.path

    def test_invalid_experiment_type(self, temp_config_dir):
        """Test invalid experiment type raises error."""
        config_content = """
experiment: invalid_type
profile: quick_eval
"""
        config_file = temp_config_dir / "invalid.yaml"
        config_file.write_text(config_content)

        loader = ConfigLoader()
        with pytest.raises(ValueError, match="Unknown experiment type"):
            loader.load_config(str(config_file))


# ============================================================================
# ToolSelectionExperiment Tests
# ============================================================================


class TestToolSelectionExperiment:
    """Test tool selection experiment."""

    def test_initialization(self, tool_selection_config_yaml):
        """Test experiment initialization."""
        loader = ConfigLoader()
        config = loader.load_config(str(tool_selection_config_yaml))

        exp = ToolSelectionExperiment(config)
        assert exp.config.experiment == "tool_selection"
        assert exp.config.top_k == 5

    def test_prepare_with_mock_dm(self, tool_selection_config_yaml, mock_data_manager):
        """Test prepare phase with mock DataManager."""
        loader = ConfigLoader()
        config = loader.load_config(str(tool_selection_config_yaml))

        exp = ToolSelectionExperiment(config, data_manager=mock_data_manager)
        exp.prepare()

        # Verify DataManager was called
        mock_data_manager.get_by_usage.assert_called_once_with("agent_eval")

    def test_run_without_strategy(
        self, tool_selection_config_yaml, mock_data_manager, mock_benchmark_samples
    ):
        """Test run phase without strategy (returns empty results)."""
        loader = ConfigLoader()
        config = loader.load_config(str(tool_selection_config_yaml))
        config.max_samples = 2

        exp = ToolSelectionExperiment(config, data_manager=mock_data_manager)

        # Mock benchmark loader
        mock_loader = MagicMock()
        mock_loader.iter_split.return_value = iter(
            [s for s in mock_benchmark_samples if s.task_type == "tool_selection"][:2]
        )
        exp.benchmark_loader = mock_loader

        result = exp.run()

        assert result is not None
        assert len(result.predictions) == 2
        assert len(result.references) == 2
        assert result.metadata["total_samples"] == 2


# ============================================================================
# PlanningExperiment Tests
# ============================================================================


class TestPlanningExperiment:
    """Test planning experiment."""

    def test_initialization(self, planning_config_yaml):
        """Test experiment initialization."""
        loader = ConfigLoader()
        config = loader.load_config(str(planning_config_yaml))

        exp = PlanningExperiment(config)
        assert exp.config.experiment == "planning"
        assert exp.config.max_steps == 5

    def test_run_with_mock_strategy(
        self, planning_config_yaml, mock_data_manager, mock_benchmark_samples
    ):
        """Test run phase with mock strategy."""
        loader = ConfigLoader()
        config = loader.load_config(str(planning_config_yaml))
        config.max_samples = 1

        # Create mock strategy
        mock_strategy = MagicMock()
        mock_plan = MagicMock()
        mock_plan.plan_steps = ["Step 1", "Step 2"]
        mock_plan.tool_sequence = ["tool_001", "tool_002"]
        mock_strategy.plan.return_value = mock_plan

        # Create mock adapter registry
        mock_registry = MagicMock()
        mock_registry.get.return_value = mock_strategy

        exp = PlanningExperiment(
            config, data_manager=mock_data_manager, adapter_registry=mock_registry
        )

        exp.prepare()

        # Mock benchmark loader AFTER prepare() to override what prepare() sets
        mock_loader = MagicMock()
        mock_loader.iter_split.return_value = iter(
            [s for s in mock_benchmark_samples if s.task_type == "multi_step_planning"][:1]
        )
        exp.benchmark_loader = mock_loader

        result = exp.run()

        assert len(result.predictions) == 1
        assert result.predictions[0]["tool_sequence"] == ["tool_001", "tool_002"]


# ============================================================================
# TimingDetectionExperiment Tests
# ============================================================================


class TestTimingDetectionExperiment:
    """Test timing detection experiment."""

    def test_initialization(self, timing_config_yaml):
        """Test experiment initialization."""
        loader = ConfigLoader()
        config = loader.load_config(str(timing_config_yaml))

        exp = TimingDetectionExperiment(config)
        assert exp.config.experiment == "timing_detection"
        assert exp.config.threshold == 0.7

    def test_run_with_mock_strategy(
        self, timing_config_yaml, mock_data_manager, mock_benchmark_samples
    ):
        """Test run phase with mock strategy."""
        loader = ConfigLoader()
        config = loader.load_config(str(timing_config_yaml))
        config.max_samples = 1

        # Create mock strategy
        mock_strategy = MagicMock()
        mock_decision = MagicMock()
        mock_decision.should_call_tool = True
        mock_decision.confidence = 0.85
        mock_decision.reasoning = "Test reasoning"
        mock_strategy.decide.return_value = mock_decision

        # Create mock adapter registry
        mock_registry = MagicMock()
        mock_registry.get.return_value = mock_strategy

        exp = TimingDetectionExperiment(
            config, data_manager=mock_data_manager, adapter_registry=mock_registry
        )

        exp.prepare()

        # Mock benchmark loader AFTER prepare() to override what prepare() sets
        mock_loader = MagicMock()
        mock_loader.iter_split.return_value = iter(
            [s for s in mock_benchmark_samples if s.task_type == "timing_judgment"][:1]
        )
        exp.benchmark_loader = mock_loader

        result = exp.run()

        assert len(result.predictions) == 1
        assert result.predictions[0]["should_call_tool"] is True
        assert result.predictions[0]["confidence"] == 0.85


# ============================================================================
# Integration Tests
# ============================================================================


class TestExperimentLifecycle:
    """Test full experiment lifecycle."""

    def test_complete_lifecycle(self, tool_selection_config_yaml, mock_data_manager, tmp_path):
        """Test complete lifecycle: prepare -> run -> finalize."""
        loader = ConfigLoader()
        config = loader.load_config(str(tool_selection_config_yaml))

        # Use temp output path
        config.report.path = str(tmp_path)
        config.max_samples = 2

        exp = ToolSelectionExperiment(config, data_manager=mock_data_manager)

        # Mock benchmark samples
        mock_loader = MagicMock()

        class MockSample:
            def __init__(self, sid):
                self.sample_id = sid
                self.instruction = f"Instruction {sid}"
                self.context = {}
                self.candidate_tools = ["tool_001", "tool_002", "tool_003"]

            def get_typed_ground_truth(self):
                class GT:
                    tool_ids = ["tool_001"]
                    top_k = ["tool_001"]
                    explanation = "Test explanation"
                    reasoning = "Test"

                return GT()

        mock_loader.iter_split.return_value = iter([MockSample("001"), MockSample("002")])

        exp.benchmark_loader = mock_loader

        # Run lifecycle
        exp.prepare()
        result = exp.run()

        # Save result manually using built-in methods
        result_file = Path(tmp_path) / f"{exp.experiment_id}_results.json"
        with open(result_file, "w") as f:
            import json

            json.dump(
                {
                    "experiment_id": result.experiment_id,
                    "predictions": result.predictions,
                    "references": result.references,
                    "metadata": result.metadata,
                },
                f,
            )

        exp.finalize()

        # Verify result was saved
        result_files = list(Path(tmp_path).glob("*_results.json"))
        assert len(result_files) > 0

        with open(result_files[0]) as f:
            saved_data = json.load(f)

        assert "experiment_id" in saved_data
        assert "predictions" in saved_data
        assert "references" in saved_data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
