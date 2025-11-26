"""
Timing Detection Experiment

Experiment runner for evaluating agent timing judgment capabilities.
Tests ability to decide when to invoke tools versus answering directly.
"""

from typing import Any

from sage.benchmark.benchmark_agent.experiments.base_experiment import (
    BaseExperiment,
    ExperimentResult,
    TimingDetectionConfig,
)


class TimingMessage:
    """Message for timing judgment."""

    def __init__(
        self, sample_id: str, message: str, context: dict[str, Any], direct_answer: str = None
    ):
        self.sample_id = sample_id
        self.message = message
        self.context = context
        self.direct_answer = direct_answer


class TimingDetectionExperiment(BaseExperiment):
    """
    Experiment for timing judgment evaluation.

    Workflow:
    1. Load timing judgment benchmark samples
    2. For each message, call detector to decide whether to call tool
    3. Collect decisions and ground truth
    4. Return ExperimentResult for evaluation
    """

    def __init__(
        self, config: TimingDetectionConfig, data_manager: Any = None, adapter_registry: Any = None
    ):
        """
        Initialize timing detection experiment.

        Args:
            config: Timing detection configuration
            data_manager: DataManager for data loading
            adapter_registry: Registry containing detector strategies
        """
        super().__init__(config, data_manager, adapter_registry)
        self.config: TimingDetectionConfig = config

    def prepare(self):
        """Prepare experiment: load data and initialize detector."""
        super().prepare()

        verbose = getattr(self.config, "verbose", False)
        if verbose:
            print(f"\n{'=' * 60}")
            print(f"Timing Detection Experiment: {self.experiment_id}")
            print(f"{'=' * 60}")
            print(f"Profile: {self.config.profile}")
            print(f"Split: {self.config.split}")
            print(f"Detector: {self.config.detector}")
            print(f"Threshold: {self.config.threshold}")

        # Load data through DataManager
        try:
            agent_eval = self.dm.get_by_usage("agent_eval")
            profile_data = agent_eval.load_profile(self.config.profile)

            self.benchmark_loader = profile_data.get("benchmark")

            if verbose:
                print("✓ Loaded benchmark data")

        except Exception as e:
            print(f"Warning: Could not load data: {e}")

        # Initialize detector strategy
        if self.adapter_registry is not None:
            try:
                self.strategy = self.adapter_registry.get(self.config.detector)
                if verbose:
                    print(f"✓ Initialized detector: {self.config.detector}")
            except Exception as e:
                print(f"Warning: Could not load detector: {e}")
                self.strategy = None
        else:
            self.strategy = None

    def run(self) -> ExperimentResult:
        """
        Run timing detection experiment.

        Returns:
            ExperimentResult with timing decisions and references
        """
        verbose = getattr(self.config, "verbose", False)
        if verbose:
            print("\nRunning experiment...")

        predictions = []
        references = []
        metadata = {
            "total_samples": 0,
            "failed_samples": 0,
            "positive_predictions": 0,
            "negative_predictions": 0,
        }

        try:
            samples = self.benchmark_loader.iter_split(
                task_type="timing_judgment", split=self.config.split
            )

            for idx, sample in enumerate(samples):
                if self.config.max_samples and idx >= self.config.max_samples:
                    break

                metadata["total_samples"] += 1

                try:
                    # Create timing message
                    message = TimingMessage(
                        sample_id=sample.sample_id,
                        message=sample.instruction,
                        context=sample.context if hasattr(sample, "context") else {},
                        direct_answer=sample.direct_answer
                        if hasattr(sample, "direct_answer")
                        else None,
                    )

                    # Get prediction from strategy
                    if self.strategy is not None:
                        decision = self.strategy.decide(message)

                        pred_dict = {
                            "sample_id": sample.sample_id,
                            "should_call_tool": decision.should_call_tool,
                            "confidence": decision.confidence,
                            "reasoning": decision.reasoning,
                        }

                        if decision.should_call_tool:
                            metadata["positive_predictions"] += 1
                        else:
                            metadata["negative_predictions"] += 1
                    else:
                        pred_dict = {
                            "sample_id": sample.sample_id,
                            "should_call_tool": False,
                            "confidence": 0.5,
                            "reasoning": None,
                        }
                        metadata["negative_predictions"] += 1

                    predictions.append(pred_dict)

                    # Get ground truth
                    gt = sample.get_typed_ground_truth()
                    ref_dict = {
                        "sample_id": sample.sample_id,
                        "should_call_tool": gt.should_call_tool,
                        "reasoning_chain": gt.reasoning_chain
                        if hasattr(gt, "reasoning_chain")
                        else None,
                        "direct_answer": gt.direct_answer if hasattr(gt, "direct_answer") else None,
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
            print(f"  Positive predictions: {metadata['positive_predictions']}")
            print(f"  Negative predictions: {metadata['negative_predictions']}")

        return self._create_result(
            predictions=predictions, references=references, metadata=metadata
        )
