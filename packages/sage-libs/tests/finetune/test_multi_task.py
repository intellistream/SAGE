# Copyright (c) 2025 IntelliStream. All rights reserved.
# Licensed under the Apache License, Version 2.0

"""Unit tests for AgentTuning multi-task training components."""

from __future__ import annotations

import pytest

from sage.libs.finetune.agent.multi_task import (
    AgentCapabilityEvaluator,
    AgentTuningConfig,
    CapabilityReport,
    CapabilityScore,
    MixerConfig,
    MultiTaskMixer,
    TaskSample,
)


class TestTaskSample:
    """Test TaskSample dataclass."""

    def test_create_task_sample(self) -> None:
        """Test creating a TaskSample."""
        sample = TaskSample(
            sample_id="test_001",
            task_type="tool_selection",
            instruction="Select the appropriate tool",
            input_text="I need to search for documents",
            output_text="search_tool",
        )

        assert sample.sample_id == "test_001"
        assert sample.task_type == "tool_selection"
        assert sample.instruction == "Select the appropriate tool"
        assert sample.input_text == "I need to search for documents"
        assert sample.output_text == "search_tool"
        assert sample.metadata == {}

    def test_task_sample_to_dict(self) -> None:
        """Test TaskSample to_dict conversion."""
        sample = TaskSample(
            sample_id="test_002",
            task_type="planning",
            instruction="Create a plan",
            input_text="Build an app",
            output_text="Step 1: Design",
            metadata={"difficulty": "hard"},
        )

        d = sample.to_dict()
        assert d["sample_id"] == "test_002"
        assert d["task_type"] == "planning"
        assert d["metadata"]["difficulty"] == "hard"

    def test_task_sample_from_dict(self) -> None:
        """Test TaskSample from_dict creation."""
        data = {
            "sample_id": "test_003",
            "task_type": "timing",
            "instruction": "Decide when to call",
            "input": "User asked about weather",
            "output": "call_now",
        }

        sample = TaskSample.from_dict(data)
        assert sample.sample_id == "test_003"
        assert sample.task_type == "timing"
        assert sample.input_text == "User asked about weather"


class TestMixerConfig:
    """Test MixerConfig dataclass."""

    def test_default_config(self) -> None:
        """Test default MixerConfig values."""
        config = MixerConfig()

        assert config.strategy == "weighted"
        assert config.shuffle is True
        assert config.seed == 42
        assert config.min_samples_per_task == 10

        # Check default weights
        assert "tool_selection" in config.task_weights
        assert "planning" in config.task_weights
        assert "timing" in config.task_weights
        assert "general" in config.task_weights

    def test_custom_config(self) -> None:
        """Test custom MixerConfig values."""
        config = MixerConfig(
            task_weights={"task_a": 0.6, "task_b": 0.4},
            strategy="balanced",
            shuffle=False,
            seed=123,
        )

        assert config.strategy == "balanced"
        assert config.shuffle is False
        assert config.seed == 123

    def test_weight_normalization(self) -> None:
        """Test that weights are normalized."""
        config = MixerConfig(task_weights={"a": 2.0, "b": 3.0, "c": 5.0})

        # Weights should be normalized to sum to 1
        total = sum(config.task_weights.values())
        assert abs(total - 1.0) < 0.001


class TestMultiTaskMixer:
    """Test MultiTaskMixer class."""

    @pytest.fixture
    def sample_datasets(self) -> dict[str, list[TaskSample]]:
        """Create sample datasets for testing."""
        return {
            "tool_selection": [
                TaskSample(
                    sample_id=f"ts_{i}",
                    task_type="tool_selection",
                    instruction="Select tool",
                    input_text=f"Query {i}",
                    output_text=f"tool_{i}",
                )
                for i in range(50)
            ],
            "planning": [
                TaskSample(
                    sample_id=f"plan_{i}",
                    task_type="planning",
                    instruction="Create plan",
                    input_text=f"Task {i}",
                    output_text=f"Plan {i}",
                )
                for i in range(40)
            ],
            "timing": [
                TaskSample(
                    sample_id=f"timing_{i}",
                    task_type="timing",
                    instruction="Decide timing",
                    input_text=f"Context {i}",
                    output_text="yes" if i % 2 == 0 else "no",
                )
                for i in range(30)
            ],
            "general": [
                TaskSample(
                    sample_id=f"gen_{i}",
                    task_type="general",
                    instruction="General task",
                    input_text=f"Input {i}",
                    output_text=f"Output {i}",
                )
                for i in range(20)
            ],
        }

    def test_mixer_creation(self) -> None:
        """Test creating a MultiTaskMixer."""
        mixer = MultiTaskMixer()
        assert mixer is not None
        assert mixer.task_weights is not None

    def test_mixer_with_config(self) -> None:
        """Test creating mixer with custom config."""
        config = MixerConfig(
            task_weights={"a": 0.5, "b": 0.5},
            strategy="balanced",
        )
        mixer = MultiTaskMixer(config)

        assert mixer.config.strategy == "balanced"

    def test_set_weights(self) -> None:
        """Test updating task weights."""
        mixer = MultiTaskMixer()
        mixer.set_weights({"task_a": 0.7, "task_b": 0.3})

        weights = mixer.task_weights
        assert abs(weights["task_a"] - 0.7) < 0.001
        assert abs(weights["task_b"] - 0.3) < 0.001

    def test_mix_weighted(self, sample_datasets: dict[str, list[TaskSample]]) -> None:
        """Test weighted mixing strategy."""
        config = MixerConfig(
            task_weights={
                "tool_selection": 0.4,
                "planning": 0.3,
                "timing": 0.2,
                "general": 0.1,
            },
            strategy="weighted",
        )
        mixer = MultiTaskMixer(config)

        mixed = mixer.mix(sample_datasets, total_size=100)

        assert len(mixed) > 0
        assert len(mixed) <= 140  # Total available samples

        # Check stats
        stats = mixer.get_stats()
        assert "tool_selection" in stats
        assert "planning" in stats

    def test_mix_balanced(self, sample_datasets: dict[str, list[TaskSample]]) -> None:
        """Test balanced mixing strategy."""
        config = MixerConfig(strategy="balanced")
        mixer = MultiTaskMixer(config)

        mixed = mixer.mix(sample_datasets, total_size=80)

        assert len(mixed) > 0

        # In balanced mode, each task should have similar counts
        stats = mixer.get_stats()
        counts = list(stats.values())
        if len(counts) > 1:
            # Check that counts are relatively balanced
            max_diff = max(counts) - min(counts)
            # Allow some variance due to min_samples_per_task
            assert max_diff <= max(counts) * 0.5 or max_diff <= 10

    def test_mix_curriculum(self, sample_datasets: dict[str, list[TaskSample]]) -> None:
        """Test curriculum mixing strategy."""
        config = MixerConfig(strategy="curriculum")
        mixer = MultiTaskMixer(config)

        mixed = mixer.mix(sample_datasets, total_size=90)

        assert len(mixed) > 0
        # Curriculum should produce samples in stages

    def test_mix_empty_dataset(self) -> None:
        """Test mixing with empty datasets."""
        mixer = MultiTaskMixer()

        mixed = mixer.mix({"task_a": []}, total_size=100)
        assert mixed == []

    def test_mix_single_task(self) -> None:
        """Test mixing with single task."""
        samples = [
            TaskSample(
                sample_id=f"s_{i}",
                task_type="single",
                instruction="Task",
                input_text=f"In {i}",
                output_text=f"Out {i}",
            )
            for i in range(20)
        ]

        config = MixerConfig(task_weights={"single": 1.0})
        mixer = MultiTaskMixer(config)

        mixed = mixer.mix({"single": samples}, total_size=15)

        assert len(mixed) <= 20
        assert all(s.task_type == "single" for s in mixed)

    def test_iter_batches(self, sample_datasets: dict[str, list[TaskSample]]) -> None:
        """Test iterating over batches."""
        mixer = MultiTaskMixer()

        batches = list(mixer.iter_batches(sample_datasets, batch_size=10, total_size=50))

        total_samples = sum(len(b) for b in batches)
        assert total_samples > 0

        # Each batch should have at most batch_size samples
        for batch in batches[:-1]:  # All but last
            assert len(batch) == 10
        # Last batch may be smaller
        assert len(batches[-1]) <= 10


class TestCapabilityScore:
    """Test CapabilityScore dataclass."""

    def test_create_score(self) -> None:
        """Test creating a CapabilityScore."""
        score = CapabilityScore(
            capability="tool_use",
            score=0.85,
            num_samples=100,
            details={"correct": 85, "total": 100},
        )

        assert score.capability == "tool_use"
        assert score.score == 0.85
        assert score.num_samples == 100
        assert score.details["correct"] == 85


class TestCapabilityReport:
    """Test CapabilityReport dataclass."""

    def test_create_report(self) -> None:
        """Test creating a CapabilityReport."""
        scores = {
            "tool_use": CapabilityScore("tool_use", 0.8, 50),
            "planning": CapabilityScore("planning", 0.7, 40),
        }

        report = CapabilityReport(
            scores=scores,
            overall_score=0.75,
            num_total_samples=90,
            evaluation_time_seconds=10.5,
        )

        assert report.overall_score == 0.75
        assert report.num_total_samples == 90
        assert "tool_use" in report.scores

    def test_report_to_dict(self) -> None:
        """Test CapabilityReport to_dict conversion."""
        scores = {
            "tool_use": CapabilityScore("tool_use", 0.8, 50),
        }

        report = CapabilityReport(
            scores=scores,
            overall_score=0.8,
            num_total_samples=50,
            evaluation_time_seconds=5.0,
        )

        d = report.to_dict()
        assert "scores" in d
        assert "overall_score" in d
        assert d["overall_score"] == 0.8

    def test_report_summary(self) -> None:
        """Test CapabilityReport summary generation."""
        scores = {
            "tool_use": CapabilityScore("tool_use", 0.8, 50),
            "planning": CapabilityScore("planning", 0.7, 40),
        }

        report = CapabilityReport(
            scores=scores,
            overall_score=0.75,
            num_total_samples=90,
            evaluation_time_seconds=10.5,
        )

        summary = report.summary()
        assert "Agent Capability Evaluation Report" in summary
        assert "tool_use" in summary
        assert "planning" in summary
        assert "Overall" in summary


class TestAgentCapabilityEvaluator:
    """Test AgentCapabilityEvaluator class."""

    def test_evaluator_creation(self) -> None:
        """Test creating an evaluator."""
        evaluator = AgentCapabilityEvaluator()

        assert evaluator is not None
        assert "tool_use" in evaluator.capabilities
        assert "planning" in evaluator.capabilities
        assert "reasoning" in evaluator.capabilities
        assert "instruction_following" in evaluator.capabilities

    def test_evaluator_with_custom_capabilities(self) -> None:
        """Test evaluator with custom capabilities."""
        evaluator = AgentCapabilityEvaluator(
            capabilities=["tool_use", "planning"],
            capability_weights={"tool_use": 0.6, "planning": 0.4},
        )

        assert len(evaluator.capabilities) == 2
        assert "tool_use" in evaluator.capabilities
        assert "reasoning" not in evaluator.capabilities

    def test_evaluate_single_capability(self) -> None:
        """Test evaluating a single capability with mock model."""

        class MockModel:
            def generate(self, prompt: str) -> str:
                return "search_tool"

        evaluator = AgentCapabilityEvaluator()
        samples = [
            TaskSample(
                sample_id="t1",
                task_type="tool_use",
                instruction="Select tool",
                input_text="Search for documents",
                output_text="search_tool",
            ),
            TaskSample(
                sample_id="t2",
                task_type="tool_use",
                instruction="Select tool",
                input_text="Write file",
                output_text="write_tool",
            ),
        ]

        score = evaluator.evaluate_single_capability(
            model=MockModel(),
            capability="tool_use",
            test_samples=samples,
        )

        assert score.capability == "tool_use"
        assert score.num_samples == 2
        assert 0.0 <= score.score <= 1.0


class TestAgentTuningConfig:
    """Test AgentTuningConfig dataclass."""

    def test_default_config(self) -> None:
        """Test default AgentTuningConfig values."""
        config = AgentTuningConfig()

        assert config.mixing_strategy == "weighted"
        assert config.num_epochs == 2
        assert "tool_selection" in config.task_weights
        assert "tool_use" in config.eval_capabilities

    def test_custom_config(self) -> None:
        """Test custom AgentTuningConfig values."""
        config = AgentTuningConfig(
            task_weights={"custom": 1.0},
            mixing_strategy="curriculum",
            num_epochs=5,
        )

        assert config.mixing_strategy == "curriculum"
        assert config.num_epochs == 5
        assert "custom" in config.task_weights

    def test_config_to_dict(self) -> None:
        """Test AgentTuningConfig to_dict conversion."""
        config = AgentTuningConfig()
        d = config.to_dict()

        assert "task_weights" in d
        assert "mixing_strategy" in d
        assert "num_epochs" in d
        assert "eval_capabilities" in d
