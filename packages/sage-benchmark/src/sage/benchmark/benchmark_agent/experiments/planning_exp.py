"""
Planning Experiment

Experiment runner for evaluating agent task planning capabilities.
Tests ability to generate multi-step plans with tool sequences.
"""

import json
from pathlib import Path
from typing import Any

from sage.benchmark.benchmark_agent.experiments.base_experiment import (
    BaseExperiment,
    ExperimentResult,
    PlanningConfig,
)


class PlanningTask:
    """Task for planning."""

    def __init__(
        self, sample_id: str, instruction: str, context: dict[str, Any], available_tools: list[str]
    ):
        self.sample_id = sample_id
        self.instruction = instruction
        self.context = context
        self.available_tools = available_tools


class PlanningSample:
    """Sample for planning evaluation."""

    def __init__(self, data: dict[str, Any]):
        self.sample_id = data.get("sample_id", "")
        self.instruction = data.get("instruction", "")
        self.context = data.get("context", {})
        self.available_tools = data.get("available_tools", [])
        self.ground_truth_steps = data.get("ground_truth_steps", [])
        self.tool_sequence = data.get("tool_sequence", [])


class LocalPlanningDataLoader:
    """Load planning data from local JSONL files."""

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir

    def iter_split(self, task_type: str = "task_planning", split: str = "test"):
        """Iterate over samples in the specified split."""
        split_file = self.data_dir / f"{split}.jsonl"
        if not split_file.exists():
            raise FileNotFoundError(f"Split file not found: {split_file}")

        with open(split_file, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    yield PlanningSample(data)


class PlanningExperiment(BaseExperiment):
    """
    Experiment for task planning evaluation.

    Workflow:
    1. Load planning benchmark samples
    2. For each task, call planner strategy to generate plan
    3. Collect plan predictions and ground truth sequences
    4. Return ExperimentResult for evaluation
    """

    def __init__(
        self, config: PlanningConfig, data_manager: Any = None, adapter_registry: Any = None
    ):
        """
        Initialize planning experiment.

        Args:
            config: Planning configuration
            data_manager: DataManager for data loading
            adapter_registry: Registry containing planner strategies
        """
        super().__init__(config, data_manager, adapter_registry)
        self.config: PlanningConfig = config
        self._local_data_dir: Path | None = None

    def set_local_data_dir(self, data_dir: str | Path) -> None:
        """Set local data directory for loading data."""
        self._local_data_dir = Path(data_dir)

    def prepare(self):
        """Prepare experiment: load data and initialize planner."""
        # Don't call super().prepare() to avoid DataManager requirement
        verbose = getattr(self.config, "verbose", False)

        if verbose:
            print(f"\n{'=' * 60}")
            print(f"Planning Experiment: {self.experiment_id}")
            print(f"{'=' * 60}")
            print(f"Profile: {self.config.profile}")
            print(f"Split: {self.config.split}")
            print(f"Planner: {self.config.planner}")
            print(f"Max steps: {self.config.max_steps}")

        # Try local data first
        if self._local_data_dir is not None:
            self.benchmark_loader = LocalPlanningDataLoader(self._local_data_dir)
            if verbose:
                print(f"✓ Loaded local data from: {self._local_data_dir}")
        elif self.dm is not None:
            # Load data through DataManager
            try:
                agent_eval = self.dm.get_by_usage("agent_eval")
                profile_data = agent_eval.load_profile(self.config.profile)

                self.benchmark_loader = profile_data.get("benchmark")
                self.tools_loader = profile_data.get("tools")

                if verbose:
                    print("✓ Loaded benchmark data via DataManager")

            except Exception as e:
                print(f"Warning: Could not load data via DataManager: {e}")
                # Try default local path
                default_path = (
                    Path(__file__).parent.parent.parent.parent.parent.parent
                    / "data"
                    / "task_planning"
                )
                if default_path.exists():
                    self.benchmark_loader = LocalPlanningDataLoader(default_path)
                    if verbose:
                        print(f"✓ Loaded local data from default path: {default_path}")
        else:
            # Try default local path
            default_path = (
                Path(__file__).parent.parent.parent.parent.parent.parent / "data" / "task_planning"
            )
            if default_path.exists():
                self.benchmark_loader = LocalPlanningDataLoader(default_path)
                if verbose:
                    print(f"✓ Loaded local data from default path: {default_path}")

        # Initialize planner strategy
        if self.adapter_registry is not None:
            try:
                self.strategy = self.adapter_registry.get(self.config.planner)
                if verbose:
                    print(f"✓ Initialized planner: {self.config.planner}")
            except Exception as e:
                print(f"Warning: Could not load planner: {e}")
                self.strategy = None
        else:
            self.strategy = None

    def run(self) -> ExperimentResult:
        """
        Run planning experiment.

        Returns:
            ExperimentResult with plan predictions and references
        """
        verbose = getattr(self.config, "verbose", False)

        if verbose:
            print("\nRunning experiment...")

        predictions = []
        references = []
        metadata = {"total_samples": 0, "failed_samples": 0, "avg_plan_length": 0}

        if self.benchmark_loader is None:
            print("Error: No data loader available")
            return self._create_result(
                predictions=predictions, references=references, metadata=metadata
            )

        try:
            samples = self.benchmark_loader.iter_split(
                task_type="task_planning", split=self.config.split
            )

            total_plan_length = 0

            for idx, sample in enumerate(samples):
                if self.config.max_samples and idx >= self.config.max_samples:
                    break

                metadata["total_samples"] += 1

                try:
                    # Create planning task
                    task = PlanningTask(
                        sample_id=sample.sample_id,
                        instruction=sample.instruction,
                        context=sample.context if hasattr(sample, "context") else {},
                        available_tools=sample.available_tools
                        if hasattr(sample, "available_tools")
                        else [],
                    )

                    # Get prediction from strategy
                    if self.strategy is not None:
                        plan = self.strategy.plan(task)

                        pred_dict = {
                            "sample_id": sample.sample_id,
                            "plan_steps": [
                                {
                                    "step_id": step.step_id,
                                    "description": step.description,
                                    "tool_id": step.tool_id,
                                    "confidence": step.confidence,
                                }
                                for step in plan.steps
                            ],
                            "tool_sequence": plan.tool_sequence,
                        }
                        total_plan_length += len(plan.steps)
                    else:
                        pred_dict = {
                            "sample_id": sample.sample_id,
                            "plan_steps": [],
                            "tool_sequence": [],
                        }

                    predictions.append(pred_dict)

                    # Get ground truth from sample data
                    ref_dict = {
                        "sample_id": sample.sample_id,
                        "plan_steps": sample.ground_truth_steps,
                        "tool_sequence": sample.tool_sequence,
                    }
                    references.append(ref_dict)

                    if verbose and (idx + 1) % 10 == 0:
                        print(f"  Processed {idx + 1} samples...")

                except Exception as e:
                    metadata["failed_samples"] += 1
                    if verbose:
                        print(f"  Error processing sample {idx}: {e}")
                    continue

            # Calculate average plan length
            if metadata["total_samples"] > 0:
                metadata["avg_plan_length"] = total_plan_length / metadata["total_samples"]

        except Exception as e:
            print(f"Error iterating samples: {e}")

        if verbose:
            print("\nCompleted:")
            print(f"  Total samples: {metadata['total_samples']}")
            print(f"  Failed samples: {metadata['failed_samples']}")
            print(f"  Avg plan length: {metadata['avg_plan_length']:.1f}")

        return self._create_result(
            predictions=predictions, references=references, metadata=metadata
        )
