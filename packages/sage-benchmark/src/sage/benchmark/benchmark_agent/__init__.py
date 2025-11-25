"""
Agent Capability Benchmark Module

This module provides infrastructure for evaluating agent capabilities including:
- Tool selection
- Task planning
- Timing detection

Architecture:
    config/         Configuration files and loaders
    experiments/    Experiment runners and base classes

Usage:
    # Via CLI
    python -m sage.benchmark.benchmark_agent --config config/tool_selection_exp.yaml

    # Programmatic
    from sage.benchmark.benchmark_agent import ToolSelectionExperiment
    from sage.benchmark.benchmark_agent.config import ConfigLoader

    loader = ConfigLoader()
    config = loader.load_config("config/tool_selection_exp.yaml")
    exp = ToolSelectionExperiment(config)
    exp.prepare()
    result = exp.run()
    exp.finalize()
"""

from sage.benchmark.benchmark_agent.experiments import (
    # Base classes
    BaseExperiment,
    ExperimentConfig,
    ExperimentResult,
    PlanningConfig,
    PlanningExperiment,
    TimingDetectionConfig,
    TimingDetectionExperiment,
    # Configs
    ToolSelectionConfig,
    # Experiments
    ToolSelectionExperiment,
)

__version__ = "0.1.0"

__all__ = [
    "__version__",
    # Experiments
    "ToolSelectionExperiment",
    "PlanningExperiment",
    "TimingDetectionExperiment",
    # Base
    "BaseExperiment",
    "ExperimentConfig",
    "ExperimentResult",
    # Configs
    "ToolSelectionConfig",
    "PlanningConfig",
    "TimingDetectionConfig",
]
