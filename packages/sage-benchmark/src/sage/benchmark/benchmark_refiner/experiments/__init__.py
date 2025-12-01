"""
Refiner Experiments Module
==========================

提供 Refiner 算法评测的统一实验管理框架。

包含:
- BaseRefinerExperiment: 实验基类
- ComparisonExperiment: 多算法对比实验
- QualityExperiment: 答案质量评测实验
- LatencyExperiment: 延迟评测实验
- CompressionExperiment: 压缩率评测实验
- RefinerExperimentRunner: 实验运行器
- ResultsCollector: 结果收集器
"""

from sage.benchmark.benchmark_refiner.experiments.base_experiment import (
    AlgorithmMetrics,
    BaseRefinerExperiment,
    DatasetType,
    ExperimentResult,
    RefinerAlgorithm,
    RefinerExperimentConfig,
)
from sage.benchmark.benchmark_refiner.experiments.comparison_experiment import (
    ComparisonExperiment,
    CompressionExperiment,
    LatencyExperiment,
    QualityExperiment,
)
from sage.benchmark.benchmark_refiner.experiments.results_collector import (
    ResultsCollector,
    get_collector,
)
from sage.benchmark.benchmark_refiner.experiments.runner import (
    RefinerExperimentRunner,
)

__all__ = [
    # Enums
    "RefinerAlgorithm",
    "DatasetType",
    # Config and results
    "RefinerExperimentConfig",
    "AlgorithmMetrics",
    "ExperimentResult",
    # Experiment classes
    "BaseRefinerExperiment",
    "ComparisonExperiment",
    "QualityExperiment",
    "LatencyExperiment",
    "CompressionExperiment",
    # Runner
    "RefinerExperimentRunner",
    # Results collector
    "ResultsCollector",
    "get_collector",
]
