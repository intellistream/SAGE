"""
AgentTuning: Multi-Task Agent Capability Training

Implements the AgentTuning approach from:
"AgentTuning: Enabling Generalized Agent Abilities for LLMs" (Zeng et al., 2023)

Core idea: Multi-task mixed training to improve generalized agent capabilities
across tool selection, planning, timing judgment, and general instruction following.

Features:
- MultiTaskMixer: Weighted mixing of different task types
- AgentCapabilityEvaluator: Multi-dimensional capability assessment
- Task-specific data formatters
"""

from __future__ import annotations

import logging
import random
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Iterator, Literal, Optional

logger = logging.getLogger(__name__)


@dataclass
class TaskSample:
    """Single sample from a task dataset."""

    sample_id: str
    task_type: str  # tool_selection, planning, timing, general
    instruction: str
    input_text: str
    output_text: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary format."""
        return {
            "sample_id": self.sample_id,
            "task_type": self.task_type,
            "instruction": self.instruction,
            "input": self.input_text,
            "output": self.output_text,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> TaskSample:
        """Create from dictionary."""
        return cls(
            sample_id=data.get("sample_id", ""),
            task_type=data.get("task_type", "general"),
            instruction=data.get("instruction", ""),
            input_text=data.get("input", ""),
            output_text=data.get("output", ""),
            metadata=data.get("metadata", {}),
        )


@dataclass
class MixerConfig:
    """Configuration for MultiTaskMixer."""

    # Task weights for sampling
    task_weights: dict[str, float] = field(
        default_factory=lambda: {
            "tool_selection": 0.35,
            "planning": 0.30,
            "timing": 0.20,
            "general": 0.15,
        }
    )

    # Mixing strategy
    strategy: Literal["weighted", "balanced", "curriculum"] = "weighted"

    # Curriculum learning settings (if strategy == "curriculum")
    curriculum_stages: list[dict[str, float]] = field(default_factory=list)

    # Sampling settings
    shuffle: bool = True
    seed: int = 42

    # Size limits
    max_total_samples: Optional[int] = None
    min_samples_per_task: int = 10

    def __post_init__(self):
        """Validate configuration."""
        # Normalize weights
        total = sum(self.task_weights.values())
        if total > 0:
            self.task_weights = {k: v / total for k, v in self.task_weights.items()}


class MultiTaskMixer:
    """
    Multi-task data mixer for AgentTuning.

    Mixes samples from different agent tasks according to specified weights,
    enabling generalized agent capability training.

    Example:
        >>> mixer = MultiTaskMixer(config)
        >>> mixed_data = mixer.mix({
        ...     "tool_selection": tool_selection_data,
        ...     "planning": planning_data,
        ...     "timing": timing_data,
        ...     "general": general_data,
        ... })
    """

    def __init__(self, config: Optional[MixerConfig] = None):
        """
        Initialize MultiTaskMixer.

        Args:
            config: Mixer configuration. Uses defaults if not provided.
        """
        self.config = config or MixerConfig()
        self._rng = random.Random(self.config.seed)
        self._stats: dict[str, int] = defaultdict(int)

    @property
    def task_weights(self) -> dict[str, float]:
        """Get current task weights."""
        return self.config.task_weights.copy()

    def set_weights(self, weights: dict[str, float]) -> None:
        """
        Update task weights.

        Args:
            weights: New task weights (will be normalized)
        """
        total = sum(weights.values())
        if total > 0:
            self.config.task_weights = {k: v / total for k, v in weights.items()}
        logger.info(f"Updated task weights: {self.config.task_weights}")

    def mix(
        self,
        task_datasets: dict[str, list[TaskSample]],
        total_size: Optional[int] = None,
    ) -> list[TaskSample]:
        """
        Mix multiple task datasets according to weights.

        Args:
            task_datasets: Dictionary mapping task type to list of samples
            total_size: Target total size (uses max_total_samples if not provided)

        Returns:
            Mixed list of samples from all tasks
        """
        if self.config.strategy == "weighted":
            return self._mix_weighted(task_datasets, total_size)
        elif self.config.strategy == "balanced":
            return self._mix_balanced(task_datasets, total_size)
        elif self.config.strategy == "curriculum":
            return self._mix_curriculum(task_datasets, total_size)
        else:
            return self._mix_weighted(task_datasets, total_size)

    def _mix_weighted(
        self,
        task_datasets: dict[str, list[TaskSample]],
        total_size: Optional[int] = None,
    ) -> list[TaskSample]:
        """
        Mix datasets using weighted sampling.

        Samples from each task proportionally to its weight.
        """
        mixed: list[TaskSample] = []
        self._stats.clear()

        # Calculate target sizes for each task
        total = total_size or self.config.max_total_samples
        if total is None:
            total = sum(len(d) for d in task_datasets.values())

        # Sample from each task according to weight
        for task_type, samples in task_datasets.items():
            if not samples:
                continue

            weight = self.config.task_weights.get(task_type, 0.1)
            target_count = max(
                self.config.min_samples_per_task,
                int(total * weight),
            )

            # Don't exceed available samples
            actual_count = min(target_count, len(samples))

            # Sample without replacement if possible
            if actual_count >= len(samples):
                selected = samples.copy()
            else:
                selected = self._rng.sample(samples, actual_count)

            mixed.extend(selected)
            self._stats[task_type] = len(selected)

        # Shuffle the mixed dataset
        if self.config.shuffle:
            self._rng.shuffle(mixed)

        logger.info(f"Mixed {len(mixed)} samples: {dict(self._stats)}")
        return mixed

    def _mix_balanced(
        self,
        task_datasets: dict[str, list[TaskSample]],
        total_size: Optional[int] = None,
    ) -> list[TaskSample]:
        """
        Mix datasets with balanced sampling (equal samples per task).
        """
        mixed: list[TaskSample] = []
        self._stats.clear()

        # Find minimum size across tasks
        min_size = min(len(d) for d in task_datasets.values() if d)
        if total_size:
            per_task = total_size // len(task_datasets)
            min_size = min(min_size, per_task)

        # Sample equal amounts from each task
        for task_type, samples in task_datasets.items():
            if not samples:
                continue

            actual_count = min(min_size, len(samples))
            selected = (
                self._rng.sample(samples, actual_count) if actual_count < len(samples) else samples
            )

            mixed.extend(selected)
            self._stats[task_type] = len(selected)

        if self.config.shuffle:
            self._rng.shuffle(mixed)

        logger.info(f"Balanced mixed {len(mixed)} samples: {dict(self._stats)}")
        return mixed

    def _mix_curriculum(
        self,
        task_datasets: dict[str, list[TaskSample]],
        total_size: Optional[int] = None,
    ) -> list[TaskSample]:
        """
        Mix datasets using curriculum learning stages.

        Progressively introduces more complex tasks.
        """
        mixed: list[TaskSample] = []
        self._stats.clear()

        stages = self.config.curriculum_stages or [
            # Stage 1: Focus on basic tool selection
            {"tool_selection": 0.6, "general": 0.4},
            # Stage 2: Add planning
            {"tool_selection": 0.4, "planning": 0.4, "general": 0.2},
            # Stage 3: Full mix
            {"tool_selection": 0.35, "planning": 0.30, "timing": 0.20, "general": 0.15},
        ]

        total = (
            total_size
            or self.config.max_total_samples
            or sum(len(d) for d in task_datasets.values())
        )
        per_stage = total // len(stages)

        for stage_idx, stage_weights in enumerate(stages):
            # Normalize stage weights
            stage_total = sum(stage_weights.values())
            stage_weights = {k: v / stage_total for k, v in stage_weights.items()}

            stage_samples: list[TaskSample] = []

            for task_type, samples in task_datasets.items():
                if not samples:
                    continue

                weight = stage_weights.get(task_type, 0)
                if weight <= 0:
                    continue

                target_count = max(
                    self.config.min_samples_per_task,
                    int(per_stage * weight),
                )
                actual_count = min(target_count, len(samples))

                selected = (
                    self._rng.sample(samples, actual_count)
                    if actual_count < len(samples)
                    else samples[:actual_count]
                )
                stage_samples.extend(selected)
                self._stats[f"{task_type}_stage{stage_idx}"] = len(selected)

            if self.config.shuffle:
                self._rng.shuffle(stage_samples)

            mixed.extend(stage_samples)

        logger.info(f"Curriculum mixed {len(mixed)} samples across {len(stages)} stages")
        return mixed

    def get_stats(self) -> dict[str, int]:
        """Get mixing statistics from last mix operation."""
        return dict(self._stats)

    def iter_batches(
        self,
        task_datasets: dict[str, list[TaskSample]],
        batch_size: int = 32,
        total_size: Optional[int] = None,
    ) -> Iterator[list[TaskSample]]:
        """
        Iterate over mixed data in batches.

        Args:
            task_datasets: Task datasets to mix
            batch_size: Size of each batch
            total_size: Total samples to generate

        Yields:
            Batches of mixed samples
        """
        mixed = self.mix(task_datasets, total_size)

        for i in range(0, len(mixed), batch_size):
            yield mixed[i : i + batch_size]


@dataclass
class CapabilityScore:
    """Score for a single capability dimension."""

    capability: str
    score: float  # 0.0 - 1.0
    num_samples: int
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class CapabilityReport:
    """Complete capability evaluation report."""

    scores: dict[str, CapabilityScore]
    overall_score: float
    num_total_samples: int
    evaluation_time_seconds: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary format."""
        return {
            "scores": {
                k: {"score": v.score, "num_samples": v.num_samples, "details": v.details}
                for k, v in self.scores.items()
            },
            "overall_score": self.overall_score,
            "num_total_samples": self.num_total_samples,
            "evaluation_time_seconds": self.evaluation_time_seconds,
            "metadata": self.metadata,
        }

    def summary(self) -> str:
        """Generate human-readable summary."""
        lines = ["=" * 50, "Agent Capability Evaluation Report", "=" * 50]
        for cap, score in self.scores.items():
            lines.append(f"  {cap}: {score.score:.2%} ({score.num_samples} samples)")
        lines.append("-" * 50)
        lines.append(f"  Overall: {self.overall_score:.2%}")
        lines.append(f"  Total samples: {self.num_total_samples}")
        lines.append(f"  Evaluation time: {self.evaluation_time_seconds:.1f}s")
        return "\n".join(lines)


class AgentCapabilityEvaluator:
    """
    Multi-dimensional agent capability evaluator.

    Evaluates agent models across multiple capability dimensions:
    - tool_use: Tool selection and invocation accuracy
    - planning: Multi-step task planning quality
    - reasoning: Chain-of-thought reasoning ability
    - instruction_following: Ability to follow complex instructions

    Example:
        >>> evaluator = AgentCapabilityEvaluator()
        >>> report = evaluator.evaluate(model, test_sets)
        >>> print(report.summary())
    """

    CAPABILITIES = ["tool_use", "planning", "reasoning", "instruction_following"]

    def __init__(
        self,
        capabilities: Optional[list[str]] = None,
        capability_weights: Optional[dict[str, float]] = None,
    ):
        """
        Initialize evaluator.

        Args:
            capabilities: List of capabilities to evaluate (uses all if not specified)
            capability_weights: Weights for computing overall score
        """
        self.capabilities = capabilities or self.CAPABILITIES.copy()
        self.capability_weights = capability_weights or dict.fromkeys(self.capabilities, 1.0)

        # Normalize weights
        total = sum(self.capability_weights.get(c, 1.0) for c in self.capabilities)
        self.capability_weights = {
            c: self.capability_weights.get(c, 1.0) / total for c in self.capabilities
        }

        # Evaluation functions for each capability
        self._evaluators: dict[str, Callable] = {
            "tool_use": self._eval_tool_use,
            "planning": self._eval_planning,
            "reasoning": self._eval_reasoning,
            "instruction_following": self._eval_instruction_following,
        }

    def evaluate(
        self,
        model: Any,
        test_sets: dict[str, list[TaskSample]],
        generate_fn: Optional[Callable] = None,
        max_samples_per_capability: Optional[int] = None,
    ) -> CapabilityReport:
        """
        Evaluate model capabilities.

        Args:
            model: Model to evaluate
            test_sets: Test samples for each capability
            generate_fn: Custom generation function (model, prompt) -> response
            max_samples_per_capability: Limit samples per capability

        Returns:
            CapabilityReport with scores for each capability
        """
        import time

        start_time = time.time()
        scores: dict[str, CapabilityScore] = {}
        total_samples = 0

        for capability in self.capabilities:
            if capability not in test_sets or not test_sets[capability]:
                logger.warning(f"No test data for capability: {capability}")
                continue

            samples = test_sets[capability]
            if max_samples_per_capability:
                samples = samples[:max_samples_per_capability]

            evaluator_fn = self._evaluators.get(capability)
            if evaluator_fn is None:
                logger.warning(f"No evaluator for capability: {capability}")
                continue

            score = evaluator_fn(model, samples, generate_fn)
            scores[capability] = score
            total_samples += score.num_samples

        # Compute overall score
        overall = 0.0
        for cap, weight in self.capability_weights.items():
            if cap in scores:
                overall += weight * scores[cap].score

        eval_time = time.time() - start_time

        return CapabilityReport(
            scores=scores,
            overall_score=overall,
            num_total_samples=total_samples,
            evaluation_time_seconds=eval_time,
        )

    def evaluate_single_capability(
        self,
        model: Any,
        capability: str,
        test_samples: list[TaskSample],
        generate_fn: Optional[Callable] = None,
    ) -> CapabilityScore:
        """
        Evaluate a single capability.

        Args:
            model: Model to evaluate
            capability: Capability to evaluate
            test_samples: Test samples
            generate_fn: Custom generation function

        Returns:
            CapabilityScore for the capability
        """
        evaluator_fn = self._evaluators.get(capability)
        if evaluator_fn is None:
            raise ValueError(f"Unknown capability: {capability}")

        return evaluator_fn(model, test_samples, generate_fn)

    def _eval_tool_use(
        self,
        model: Any,
        samples: list[TaskSample],
        generate_fn: Optional[Callable] = None,
    ) -> CapabilityScore:
        """
        Evaluate tool use capability.

        Metrics:
        - Tool selection accuracy
        - Parameter extraction accuracy
        - Tool invocation format correctness
        """
        correct = 0
        total = len(samples)

        for sample in samples:
            try:
                # Generate response
                prompt = self._format_tool_use_prompt(sample)
                if generate_fn:
                    response = generate_fn(model, prompt)
                else:
                    response = self._default_generate(model, prompt)

                # Check correctness
                if self._check_tool_use_correctness(response, sample):
                    correct += 1
            except Exception as e:
                logger.debug(f"Tool use evaluation error: {e}")

        score = correct / total if total > 0 else 0.0

        return CapabilityScore(
            capability="tool_use",
            score=score,
            num_samples=total,
            details={"correct": correct, "total": total},
        )

    def _eval_planning(
        self,
        model: Any,
        samples: list[TaskSample],
        generate_fn: Optional[Callable] = None,
    ) -> CapabilityScore:
        """
        Evaluate planning capability.

        Metrics:
        - Plan completeness
        - Step ordering correctness
        - Tool sequence accuracy
        """
        total_score = 0.0
        total = len(samples)

        for sample in samples:
            try:
                prompt = self._format_planning_prompt(sample)
                if generate_fn:
                    response = generate_fn(model, prompt)
                else:
                    response = self._default_generate(model, prompt)

                sample_score = self._score_planning_response(response, sample)
                total_score += sample_score
            except Exception as e:
                logger.debug(f"Planning evaluation error: {e}")

        score = total_score / total if total > 0 else 0.0

        return CapabilityScore(
            capability="planning",
            score=score,
            num_samples=total,
            details={"average_score": score},
        )

    def _eval_reasoning(
        self,
        model: Any,
        samples: list[TaskSample],
        generate_fn: Optional[Callable] = None,
    ) -> CapabilityScore:
        """
        Evaluate reasoning capability.

        Metrics:
        - Logical consistency
        - Step-by-step reasoning quality
        - Final answer correctness
        """
        total_score = 0.0
        total = len(samples)

        for sample in samples:
            try:
                prompt = self._format_reasoning_prompt(sample)
                if generate_fn:
                    response = generate_fn(model, prompt)
                else:
                    response = self._default_generate(model, prompt)

                sample_score = self._score_reasoning_response(response, sample)
                total_score += sample_score
            except Exception as e:
                logger.debug(f"Reasoning evaluation error: {e}")

        score = total_score / total if total > 0 else 0.0

        return CapabilityScore(
            capability="reasoning",
            score=score,
            num_samples=total,
            details={"average_score": score},
        )

    def _eval_instruction_following(
        self,
        model: Any,
        samples: list[TaskSample],
        generate_fn: Optional[Callable] = None,
    ) -> CapabilityScore:
        """
        Evaluate instruction following capability.

        Metrics:
        - Format adherence
        - Constraint satisfaction
        - Output completeness
        """
        total_score = 0.0
        total = len(samples)

        for sample in samples:
            try:
                prompt = self._format_instruction_prompt(sample)
                if generate_fn:
                    response = generate_fn(model, prompt)
                else:
                    response = self._default_generate(model, prompt)

                sample_score = self._score_instruction_response(response, sample)
                total_score += sample_score
            except Exception as e:
                logger.debug(f"Instruction following evaluation error: {e}")

        score = total_score / total if total > 0 else 0.0

        return CapabilityScore(
            capability="instruction_following",
            score=score,
            num_samples=total,
            details={"average_score": score},
        )

    # ===== Prompt formatting helpers =====

    def _format_tool_use_prompt(self, sample: TaskSample) -> str:
        """Format prompt for tool use evaluation."""
        return f"{sample.instruction}\n\nInput: {sample.input_text}"

    def _format_planning_prompt(self, sample: TaskSample) -> str:
        """Format prompt for planning evaluation."""
        return f"{sample.instruction}\n\nTask: {sample.input_text}\n\nGenerate a step-by-step plan:"

    def _format_reasoning_prompt(self, sample: TaskSample) -> str:
        """Format prompt for reasoning evaluation."""
        return f"{sample.instruction}\n\nProblem: {sample.input_text}\n\nThink step by step:"

    def _format_instruction_prompt(self, sample: TaskSample) -> str:
        """Format prompt for instruction following evaluation."""
        return f"{sample.instruction}\n\nInput: {sample.input_text}"

    # ===== Response checking helpers =====

    def _default_generate(self, model: Any, prompt: str) -> str:
        """Default generation function."""
        if hasattr(model, "generate"):
            return model.generate(prompt)
        elif hasattr(model, "chat"):
            return model.chat([{"role": "user", "content": prompt}])
        else:
            raise ValueError("Model must have generate() or chat() method")

    def _check_tool_use_correctness(self, response: str, sample: TaskSample) -> bool:
        """Check if tool use response is correct."""
        expected = sample.output_text.strip().lower()
        actual = response.strip().lower()

        # Extract tool name from response
        if "tool:" in actual or "function:" in actual:
            # Check if expected tool appears in response
            return expected in actual or any(word in actual for word in expected.split())

        return expected in actual

    def _score_planning_response(self, response: str, sample: TaskSample) -> float:
        """Score a planning response (0.0 - 1.0)."""
        expected = sample.output_text.strip().lower()
        actual = response.strip().lower()

        # Check for step-by-step structure
        has_steps = any(marker in actual for marker in ["step 1", "1.", "first", "- "])

        # Check for expected tools/actions
        expected_words = set(expected.split())
        actual_words = set(actual.split())
        overlap = len(expected_words & actual_words) / max(len(expected_words), 1)

        # Combine scores
        structure_score = 0.3 if has_steps else 0.0
        content_score = min(overlap * 0.7, 0.7)

        return structure_score + content_score

    def _score_reasoning_response(self, response: str, sample: TaskSample) -> float:
        """Score a reasoning response (0.0 - 1.0)."""
        expected = sample.output_text.strip().lower()
        actual = response.strip().lower()

        # Check for reasoning markers
        has_reasoning = any(
            marker in actual for marker in ["because", "therefore", "thus", "so", "since"]
        )

        # Check for expected content
        expected_words = set(expected.split())
        actual_words = set(actual.split())
        overlap = len(expected_words & actual_words) / max(len(expected_words), 1)

        # Combine scores
        reasoning_score = 0.3 if has_reasoning else 0.0
        content_score = min(overlap * 0.7, 0.7)

        return reasoning_score + content_score

    def _score_instruction_response(self, response: str, sample: TaskSample) -> float:
        """Score an instruction following response (0.0 - 1.0)."""
        expected = sample.output_text.strip().lower()
        actual = response.strip().lower()

        # Check format constraints from metadata
        format_score = 1.0
        if "format" in sample.metadata:
            expected_format = sample.metadata["format"]
            if expected_format == "json" and not (actual.startswith("{") or actual.startswith("[")):
                format_score = 0.5
            elif expected_format == "list" and not any(
                marker in actual for marker in ["- ", "* ", "1."]
            ):
                format_score = 0.5

        # Check content overlap
        expected_words = set(expected.split())
        actual_words = set(actual.split())
        content_score = len(expected_words & actual_words) / max(len(expected_words), 1)

        return format_score * 0.3 + content_score * 0.7


# ===== Configuration for AgentTuning method =====


@dataclass
class AgentTuningConfig:
    """Configuration for AgentTuning training method."""

    # Multi-task mixing
    task_weights: dict[str, float] = field(
        default_factory=lambda: {
            "tool_selection": 0.35,
            "planning": 0.30,
            "timing": 0.20,
            "general": 0.15,
        }
    )
    mixing_strategy: Literal["weighted", "balanced", "curriculum"] = "weighted"

    # Training settings
    num_epochs: int = 2
    learning_rate: float = 2e-5
    max_train_samples: Optional[int] = None

    # Evaluation settings
    eval_capabilities: list[str] = field(
        default_factory=lambda: ["tool_use", "planning", "reasoning", "instruction_following"]
    )
    capability_weights: dict[str, float] = field(
        default_factory=lambda: {
            "tool_use": 0.35,
            "planning": 0.30,
            "reasoning": 0.20,
            "instruction_following": 0.15,
        }
    )

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "task_weights": self.task_weights,
            "mixing_strategy": self.mixing_strategy,
            "num_epochs": self.num_epochs,
            "learning_rate": self.learning_rate,
            "max_train_samples": self.max_train_samples,
            "eval_capabilities": self.eval_capabilities,
            "capability_weights": self.capability_weights,
        }
