"""
Agent Capability Benchmark Module

This module provides infrastructure for evaluating agent capabilities including:
- Tool selection
- Task planning
- Timing detection

Architecture:
    config/         Configuration files and loaders
    experiments/    Experiment runners and base classes
    adapter_registry.py  Strategy adapter registry

Usage:
    # Via CLI
    python -m sage.benchmark.benchmark_agent --config config/tool_selection_exp.yaml

    # Programmatic
    from sage.benchmark.benchmark_agent import ToolSelectionExperiment
    from sage.benchmark.benchmark_agent.config import ConfigLoader
    from sage.benchmark.benchmark_agent.adapter_registry import get_adapter_registry
    from sage.data import DataManager

    loader = ConfigLoader()
    config = loader.load_config("config/tool_selection_exp.yaml")

    dm = DataManager.get_instance()
    registry = get_adapter_registry()

    exp = ToolSelectionExperiment(config, data_manager=dm, adapter_registry=registry)
    exp.prepare()
    result = exp.run()
    exp.finalize()
"""

from sage.benchmark.benchmark_agent.adapter_registry import (
    AdapterRegistry,
    PlannerAdapter,
    SelectorAdapter,
    TimingAdapter,
    get_adapter_registry,
    register_strategy,
)

# Data paths management
from sage.benchmark.benchmark_agent.data_paths import (
    DataPathsConfig,
    RuntimePaths,
    SourcePaths,
    ensure_runtime_dirs,
    get_data_paths_config,
    get_runtime_paths,
    get_source_paths,
)
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
from sage.benchmark.benchmark_agent.experiments.method_comparison import (
    ExperimentResult as ComparisonResult,
)
from sage.benchmark.benchmark_agent.experiments.method_comparison import (
    MethodComparisonExperiment,
    MethodConfig,
    MethodRegistry,
    run_full_comparison,
    run_quick_comparison,
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
    # Adapter Registry
    "AdapterRegistry",
    "SelectorAdapter",
    "PlannerAdapter",
    "TimingAdapter",
    "get_adapter_registry",
    "register_strategy",
    # Data Paths
    "get_source_paths",
    "get_runtime_paths",
    "get_data_paths_config",
    "ensure_runtime_dirs",
    "SourcePaths",
    "RuntimePaths",
    "DataPathsConfig",
    # ACEBench
    "load_acebench_samples",
    "save_acebench_to_jsonl",
]


# Lazy imports for ACEBench
def load_acebench_samples(*args, **kwargs):
    """Load ToolACE samples in SAGE benchmark format."""
    from sage.benchmark.benchmark_agent.acebench_loader import load_acebench_samples as _load

    return _load(*args, **kwargs)


def save_acebench_to_jsonl(*args, **kwargs):
    """Save ToolACE samples to JSONL file."""
    from sage.benchmark.benchmark_agent.acebench_loader import save_acebench_to_jsonl as _save

    return _save(*args, **kwargs)
