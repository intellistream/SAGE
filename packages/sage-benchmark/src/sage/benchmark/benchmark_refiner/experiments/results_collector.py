"""
Results Collector for Refiner Benchmark
========================================

提供结果收集机制，让评测 Operators 的结果可以被程序化收集。
线程安全实现，支持 Pipeline 并行运行。

注意：ResultsCollector 已迁移到 sage-common 包。
此文件保留以保持向后兼容性。

使用示例:
    from sage.benchmark.benchmark_refiner.experiments.results_collector import ResultsCollector

    collector = ResultsCollector()
    collector.reset()

    # Pipeline 运行后
    results = collector.get_results()
    # [{"sample_id": 0, "f1": 0.35, "compression_rate": 2.5, ...}, ...]

    aggregated = collector.get_aggregated()
    # {"avg_f1": 0.35, "std_f1": 0.02, "avg_compression_rate": 2.5, ...}
"""

# Re-export from sage-common for backward compatibility
from sage.common.utils.results_collector import ResultsCollector, get_collector

__all__ = ["ResultsCollector", "get_collector"]
