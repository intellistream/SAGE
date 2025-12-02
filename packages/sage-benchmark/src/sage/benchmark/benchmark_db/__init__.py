"""
Benchmark ANNS - Streaming Index Benchmark Framework

精简的流式索引基准测试框架
"""

__version__ = "1.0.0"

from .bench import (
    BaseANN,
    BaseStreamingANN,
    BenchmarkMetrics,
    BenchmarkRunner,
    MaintenancePolicy,
    MaintenanceState,
    get_algorithm,
    register_algorithm,
)
from .datasets import DATASETS, Dataset, load_dataset, prepare_dataset

__all__ = [
    "Dataset",
    "DATASETS",
    "load_dataset",
    "prepare_dataset",
    "BaseANN",
    "BaseStreamingANN",
    "get_algorithm",
    "register_algorithm",
    "BenchmarkRunner",
    "BenchmarkMetrics",
    "MaintenanceState",
    "MaintenancePolicy",
]
