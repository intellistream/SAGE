"""
Tool Selection Experiment

Experiment runner for evaluating tool selection capabilities.
Tests ability to select relevant tools from a candidate set given a user instruction.
"""

from typing import Any

from sage.benchmark.benchmark_agent.experiments.base_experiment import (
    BaseExperiment,
    ExperimentResult,
    ToolSelectionConfig,
)


class ToolSelectionQuery:
    """Query for tool selection."""

    def __init__(
        self, sample_id: str, instruction: str, context: dict[str, Any], candidate_tools: list[str]
    ):
        self.sample_id = sample_id
        self.instruction = instruction
        self.context = context
        self.candidate_tools = candidate_tools


class ToolSelectionExperiment(BaseExperiment):
    """
    Experiment for tool selection evaluation.

    Workflow:
    1. Load benchmark samples from DataManager
    2. For each sample, call selector strategy to get predictions
    3. Collect predictions and ground truth
    4. Return ExperimentResult for evaluation
    """

    def __init__(
        self, config: ToolSelectionConfig, data_manager: Any = None, adapter_registry: Any = None
    ):
        """
        Initialize tool selection experiment.

        Args:
            config: Tool selection configuration
            data_manager: DataManager for data loading
            adapter_registry: Registry containing selector strategies
        """
        super().__init__(config, data_manager, adapter_registry)
        self.config: ToolSelectionConfig = config

    def prepare(self):
        """Prepare experiment: load data and initialize selector."""
        super().prepare()

        verbose = getattr(self.config, "verbose", False)
        if verbose:
            print(f"\n{'=' * 60}")
            print(f"Tool Selection Experiment: {self.experiment_id}")
            print(f"{'=' * 60}")
            print(f"Profile: {self.config.profile}")
            print(f"Split: {self.config.split}")
            print(f"Selector: {self.config.selector}")
            print(f"Top-k: {self.config.top_k}")

        # Load data through DataManager
        try:
            agent_eval = self.dm.get_by_usage("agent_eval")
            profile_data = agent_eval.load_profile(self.config.profile)

            self.benchmark_loader = profile_data.get("benchmark")
            self.tools_loader = profile_data.get("tools")

            if verbose:
                print("✓ Loaded benchmark data")

        except Exception as e:
            print(f"Warning: Could not load data: {e}")

        # Initialize selector strategy
        if self.adapter_registry is not None:
            try:
                self.strategy = self.adapter_registry.get(self.config.selector)
                if verbose:
                    print(f"✓ Initialized selector: {self.config.selector}")
            except Exception as e:
                print(f"Warning: Could not load selector: {e}")
                self.strategy = None
        else:
            self.strategy = None

    def run(self) -> ExperimentResult:
        """
        Run tool selection experiment.

        Returns:
            ExperimentResult with predictions and references
        """
        verbose = getattr(self.config, "verbose", False)
        if verbose:
            print("\nRunning experiment...")

        predictions = []
        references = []
        metadata = {"total_samples": 0, "failed_samples": 0}

        try:
            samples = self.benchmark_loader.iter_split(
                task_type="tool_selection", split=self.config.split
            )

            for idx, sample in enumerate(samples):
                if self.config.max_samples and idx >= self.config.max_samples:
                    break

                metadata["total_samples"] += 1

                try:
                    query = ToolSelectionQuery(
                        sample_id=sample.sample_id,
                        instruction=sample.instruction,
                        context=sample.context if hasattr(sample, "context") else {},
                        candidate_tools=sample.candidate_tools,
                    )

                    if self.strategy is not None:
                        pred_tools = self.strategy.predict(query, top_k=self.config.top_k)
                        pred_dict = {
                            "sample_id": sample.sample_id,
                            "predicted_tools": [
                                {"tool_id": p.tool_id, "score": p.score} for p in pred_tools
                            ],
                        }
                    else:
                        pred_dict = {"sample_id": sample.sample_id, "predicted_tools": []}

                    predictions.append(pred_dict)

                    gt = sample.get_typed_ground_truth()
                    ref_dict = {
                        "sample_id": sample.sample_id,
                        "ground_truth_tools": gt.top_k,
                        "explanation": gt.explanation if hasattr(gt, "explanation") else None,
                    }
                    references.append(ref_dict)

                    if verbose and (idx + 1) % 10 == 0:
                        print(f"  Processed {idx + 1} samples...")

                except Exception as e:
                    metadata["failed_samples"] += 1
                    if verbose:
                        print(f"  Error processing sample {idx}: {e}")
                    continue

        except Exception as e:
            print(f"Error iterating samples: {e}")

        if verbose:
            print("\nCompleted:")
            print(f"  Total samples: {metadata['total_samples']}")
            print(f"  Failed samples: {metadata['failed_samples']}")

        return self._create_result(
            predictions=predictions, references=references, metadata=metadata
        )
