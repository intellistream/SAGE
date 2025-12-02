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
- DatasetResult: 单数据集结果
- MultiDatasetExperimentResult: 多数据集实验结果
"""

from sage.benchmark.benchmark_refiner.experiments.base_experiment import (
    AVAILABLE_DATASETS,
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
    DatasetResult,
    LatencyExperiment,
    MultiDatasetExperimentResult,
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
    # Constants
    "AVAILABLE_DATASETS",
    # Enums
    "RefinerAlgorithm",
    "DatasetType",
    # Config and results
    "RefinerExperimentConfig",
    "AlgorithmMetrics",
    "ExperimentResult",
    "DatasetResult",
    "MultiDatasetExperimentResult",
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
