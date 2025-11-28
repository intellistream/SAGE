"""
注意力头分析模块 - 简化版

用于识别 RAG 系统中对检索最重要的注意力头。
整合了模型加载、Hook 注册、MNR 计算和结果可视化。
"""

from sage.benchmark.benchmark_refiner.analysis.head_analysis import (
    AttentionHookExtractor,
    HeadwiseEvaluator,
    MetricsAggregator,
    mean_normalized_rank,
)
from sage.benchmark.benchmark_refiner.analysis.visualization import plot_mnr_curve

__all__ = [
    # 核心类
    "AttentionHookExtractor",
    "HeadwiseEvaluator",
    "MetricsAggregator",
    # 指标
    "mean_normalized_rank",
    # 可视化
    "plot_mnr_curve",
]
