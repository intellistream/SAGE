# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""
Base Experiment Module
======================

Provides the abstract base class for all predefined experiments.

This module defines:
- ExperimentResult: Data class for experiment results
- BaseExperiment: Abstract base class with lifecycle methods
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ExperimentResult:
    """Result of an experiment run.

    Attributes:
        experiment_name: Name of the experiment
        experiment_type: Type of experiment (throughput, latency, slo, mixed_ratio)
        start_time: Experiment start timestamp
        end_time: Experiment end timestamp
        parameters: Experiment parameters used
        results: Raw results from benchmark runs
        summary: Summary statistics
        charts: Paths to generated charts
        success: Whether experiment completed successfully
        error: Error message if experiment failed
    """

    experiment_name: str
    experiment_type: str
    start_time: datetime = field(default_factory=datetime.now)
    end_time: datetime | None = None
    parameters: dict[str, Any] = field(default_factory=dict)
    results: list[dict[str, Any]] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)
    charts: list[Path] = field(default_factory=list)
    success: bool = False
    error: str | None = None

    @property
    def duration_seconds(self) -> float:
        """Get experiment duration in seconds."""
        if self.end_time is None:
            return 0.0
        return (self.end_time - self.start_time).total_seconds()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "experiment_name": self.experiment_name,
            "experiment_type": self.experiment_type,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": self.duration_seconds,
            "parameters": self.parameters,
            "results": self.results,
            "summary": self.summary,
            "charts": [str(p) for p in self.charts],
            "success": self.success,
            "error": self.error,
        }

    def save(self, path: Path | str) -> None:
        """Save experiment result to JSON file.

        Args:
            path: Output file path
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)
        logger.info(f"Saved experiment result to {path}")


class BaseExperiment(ABC):
    """Abstract base class for predefined experiments.

    Experiments follow a lifecycle:
    1. prepare() - Set up resources and validate configuration
    2. run() - Execute the experiment
    3. finalize() - Clean up and compute final results
    4. visualize() - Generate charts and reports

    Subclasses must implement:
    - _execute(): Core experiment logic
    - _compute_summary(): Generate summary statistics

    Example:
        class MyExperiment(BaseExperiment):
            def _execute(self) -> list[dict[str, Any]]:
                # Run benchmark variations
                return results

            def _compute_summary(self, results: list[dict[str, Any]]) -> dict[str, Any]:
                # Compute summary statistics
                return summary

        exp = MyExperiment(name="my_exp", output_dir="./results")
        result = await exp.run_full()
    """

    def __init__(
        self,
        name: str,
        output_dir: str | Path = "./.benchmarks",
        verbose: bool = True,
    ):
        """Initialize experiment.

        Args:
            name: Experiment name
            output_dir: Directory for output files
            verbose: Whether to print progress messages
        """
        self.name = name
        self.output_dir = Path(output_dir)
        self.verbose = verbose
        self._result: ExperimentResult | None = None
        self._prepared = False

    @property
    @abstractmethod
    def experiment_type(self) -> str:
        """Return experiment type identifier."""
        pass

    def _log(self, message: str) -> None:
        """Log a message if verbose mode is enabled."""
        if self.verbose:
            print(message)

    def prepare(self) -> None:
        """Prepare experiment resources and validate configuration.

        This method is called before run() to set up any required resources
        and validate that the experiment can be executed.

        Raises:
            ValueError: If configuration is invalid
        """
        self._log(f"\n🔧 Preparing experiment: {self.name}")

        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize result
        self._result = ExperimentResult(
            experiment_name=self.name,
            experiment_type=self.experiment_type,
            parameters=self._get_parameters(),
        )

        # Subclass-specific preparation
        self._prepare_impl()

        self._prepared = True
        self._log("   Preparation complete")

    def _prepare_impl(self) -> None:
        """Subclass-specific preparation logic.

        Override this method to add custom preparation steps.
        """
        pass

    @abstractmethod
    def _get_parameters(self) -> dict[str, Any]:
        """Get experiment parameters for logging.

        Returns:
            Dictionary of experiment parameters
        """
        pass

    @abstractmethod
    async def _execute(self) -> list[dict[str, Any]]:
        """Execute the core experiment logic.

        Returns:
            List of results from benchmark runs
        """
        pass

    @abstractmethod
    def _compute_summary(self, results: list[dict[str, Any]]) -> dict[str, Any]:
        """Compute summary statistics from results.

        Args:
            results: Raw results from _execute()

        Returns:
            Summary statistics dictionary
        """
        pass

    async def run(self) -> ExperimentResult:
        """Run the experiment.

        Returns:
            ExperimentResult with raw results and summary

        Raises:
            RuntimeError: If prepare() was not called
        """
        if not self._prepared:
            self.prepare()

        if self._result is None:
            raise RuntimeError("Experiment result not initialized")

        self._log(f"\n🚀 Running experiment: {self.name}")

        try:
            # Execute experiment
            results = await self._execute()
            self._result.results = results

            # Compute summary
            self._result.summary = self._compute_summary(results)
            self._result.success = True

        except Exception as e:
            self._result.success = False
            self._result.error = str(e)
            logger.exception(f"Experiment failed: {e}")
            raise

        finally:
            self._result.end_time = datetime.now()

        return self._result

    def finalize(self) -> ExperimentResult:
        """Finalize experiment and clean up resources.

        Returns:
            Final ExperimentResult

        Raises:
            RuntimeError: If run() was not called
        """
        if self._result is None:
            raise RuntimeError("Experiment not run yet")

        self._log(f"\n✅ Finalizing experiment: {self.name}")

        # Save result
        result_path = self.output_dir / f"{self.name}_result.json"
        self._result.save(result_path)

        # Subclass-specific finalization
        self._finalize_impl()

        self._log(f"   Results saved to {result_path}")

        return self._result

    def _finalize_impl(self) -> None:
        """Subclass-specific finalization logic.

        Override this method to add custom cleanup steps.
        """
        pass

    def visualize(self) -> list[Path]:
        """Generate visualizations for experiment results.

        Returns:
            List of paths to generated charts

        Raises:
            RuntimeError: If run() was not called
        """
        if self._result is None:
            raise RuntimeError("Experiment not run yet")

        self._log(f"\n📊 Generating visualizations for: {self.name}")

        charts = self._visualize_impl()
        self._result.charts = charts

        self._log(f"   Generated {len(charts)} charts")

        return charts

    def _visualize_impl(self) -> list[Path]:
        """Generate experiment-specific visualizations.

        Override this method to add custom visualizations.

        Returns:
            List of paths to generated charts
        """
        return []

    async def run_full(self) -> ExperimentResult:
        """Run complete experiment lifecycle.

        Convenience method that calls prepare(), run(), finalize(),
        and visualize() in sequence.

        Returns:
            Final ExperimentResult
        """
        self.prepare()
        await self.run()
        self.visualize()
        return self.finalize()


# Re-export
__all__ = [
    "BaseExperiment",
    "ExperimentResult",
]
