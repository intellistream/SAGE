"""
Base Experiment Framework for Agent Benchmarking

This module provides the abstract base class and configuration models for
agent capability experiments (tool selection, planning, timing judgment).
"""

import os
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class ReportConfig(BaseModel):
    """Configuration for experiment report generation."""

    format: list[Literal["json", "markdown"]] = Field(default=["json", "markdown"])
    include_breakdowns: bool = Field(default=True)
    path: str = Field(default="${PROJECT_ROOT}/outputs/agent_benchmark")
    markdown_template: Optional[str] = Field(default=None)

    @field_validator("path")
    @classmethod
    def resolve_path(cls, v):
        """Resolve environment variables in path."""
        if "${PROJECT_ROOT}" in v:
            project_root = os.environ.get("PROJECT_ROOT", os.getcwd())
            v = v.replace("${PROJECT_ROOT}", project_root)
        return v


class ExperimentConfig(BaseModel):
    """Base configuration for all experiments."""

    experiment: Literal["tool_selection", "planning", "timing_detection"]
    profile: str = Field(default="quick_eval", description="DataManager usage profile")
    split: Literal["train", "dev", "test"] = Field(default="dev")
    metrics: list[str] = Field(default_factory=list)
    report: ReportConfig = Field(default_factory=ReportConfig)
    max_samples: Optional[int] = Field(default=None, description="Limit number of samples")
    seed: int = Field(default=42, description="Random seed for reproducibility")

    class Config:
        extra = "allow"  # Allow additional fields for experiment-specific configs


class ToolSelectionConfig(ExperimentConfig):
    """Configuration for tool selection experiments."""

    experiment: Literal["tool_selection"] = "tool_selection"
    selector: str = Field(default="baseline.keyword", description="Selector strategy name")
    top_k: int = Field(default=5, description="Number of tools to select")
    selector_params: dict[str, Any] = Field(default_factory=dict)


class PlanningConfig(ExperimentConfig):
    """Configuration for task planning experiments."""

    experiment: Literal["planning"] = "planning"
    planner: str = Field(default="baseline.template", description="Planning strategy name")
    min_steps: int = Field(default=5)
    max_steps: int = Field(default=10)
    planner_params: dict[str, Any] = Field(default_factory=dict)


class TimingDetectionConfig(ExperimentConfig):
    """Configuration for timing judgment experiments."""

    experiment: Literal["timing_detection"] = "timing_detection"
    detector: str = Field(default="baseline.threshold", description="Timing detector strategy")
    threshold: float = Field(default=0.5, description="Decision threshold")
    detector_params: dict[str, Any] = Field(default_factory=dict)


class ToolPrediction(BaseModel):
    """Prediction for tool selection."""

    tool_id: str
    score: float = Field(ge=0.0, le=1.0)


class PlanStep(BaseModel):
    """Single step in a planning prediction."""

    step_id: int
    description: str
    tool_id: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class PlanningPrediction(BaseModel):
    """Prediction for task planning."""

    steps: list[PlanStep]
    tool_sequence: list[str]

    @field_validator("tool_sequence")
    @classmethod
    def validate_sequence(cls, v, info):
        """Ensure tool_sequence matches steps."""
        if "steps" in info.data:
            step_tools = [step.tool_id for step in info.data["steps"]]
            if v != step_tools:
                raise ValueError("tool_sequence must match step tool_ids")
        return v


class TimingDecision(BaseModel):
    """Decision for timing judgment."""

    should_call_tool: bool
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: Optional[str] = Field(default=None)


class ExperimentResult(BaseModel):
    """Result of an experiment run."""

    task: Literal["tool_selection", "planning", "timing_detection"]
    experiment_id: str
    config: dict[str, Any]
    predictions: list[dict[str, Any]]
    references: list[dict[str, Any]]
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    class Config:
        extra = "allow"


class BaseExperiment(ABC):
    """
    Abstract base class for agent capability experiments.

    Defines the lifecycle and interface for running experiments:
    1. prepare() - Load data and initialize components
    2. run() - Execute experiment and collect results
    3. finalize() - Cleanup and save artifacts

    Subclasses must implement the run() method.
    """

    def __init__(
        self, config: ExperimentConfig, data_manager: Any = None, adapter_registry: Any = None
    ):
        """
        Initialize experiment.

        Args:
            config: Experiment configuration
            data_manager: DataManager instance for data loading
            adapter_registry: Registry for strategy adapters
        """
        self.config = config
        self.dm = data_manager
        self.adapter_registry = adapter_registry
        self.experiment_id = f"{config.experiment}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Will be populated by subclasses
        self.benchmark_loader = None
        self.tools_loader = None
        self.strategy = None

    def prepare(self):
        """
        Prepare experiment: load data, initialize strategy.

        This method loads the benchmark data and tool catalog from DataManager,
        and initializes the strategy adapter based on config.
        """
        if self.dm is None:
            raise ValueError("DataManager is required for data loading")

        # Load data sources through DataManager
        # This will be implemented by subclasses based on their needs
        pass

    @abstractmethod
    def run(self) -> ExperimentResult:
        """
        Run the experiment and return results.

        Returns:
            ExperimentResult containing predictions, references, and metadata
        """
        pass

    def finalize(self):
        """
        Finalize experiment: save artifacts, cleanup resources.

        Default implementation creates output directory.
        Subclasses can override to add custom cleanup logic.
        """
        output_dir = Path(self.config.report.path)
        output_dir.mkdir(parents=True, exist_ok=True)

    def run_iteration(self, sample: Any) -> Any:
        """
        Process a single sample (template method).

        Args:
            sample: A single benchmark sample

        Returns:
            Prediction for this sample
        """
        # To be implemented by subclasses if needed
        raise NotImplementedError("run_iteration not implemented")

    def _create_result(
        self,
        predictions: list[dict[str, Any]],
        references: list[dict[str, Any]],
        metadata: Optional[dict[str, Any]] = None,
    ) -> ExperimentResult:
        """
        Create ExperimentResult from predictions and references.

        Args:
            predictions: List of prediction dicts
            references: List of reference/ground truth dicts
            metadata: Optional metadata dict

        Returns:
            ExperimentResult object
        """
        return ExperimentResult(
            task=self.config.experiment,
            experiment_id=self.experiment_id,
            config=self.config.model_dump(),
            predictions=predictions,
            references=references,
            metadata=metadata or {},
        )


# Config type mapping for dynamic loading
CONFIG_TYPES = {
    "tool_selection": ToolSelectionConfig,
    "planning": PlanningConfig,
    "timing_detection": TimingDetectionConfig,
}


def create_config(config_dict: dict[str, Any]) -> ExperimentConfig:
    """
    Create appropriate config object from dictionary.

    Args:
        config_dict: Configuration dictionary (from YAML)

    Returns:
        Typed ExperimentConfig subclass instance
    """
    experiment_type = config_dict.get("experiment")
    if experiment_type not in CONFIG_TYPES:
        raise ValueError(f"Unknown experiment type: {experiment_type}")

    config_class = CONFIG_TYPES[experiment_type]
    return config_class(**config_dict)
