"""
注意力头分析模块 - 简化版

用于识别 RAG 系统中对检索最重要的注意力头。
整合了模型加载、Hook 注册、MNR 计算和结果可视化。

模块组成:
- head_analysis: 注意力头分析
- visualization: 可视化工具
- statistical: 统计显著性检验
"""

from sage.benchmark.benchmark_refiner.analysis.head_analysis import (
    AttentionHookExtractor,
    HeadwiseEvaluator,
    MetricsAggregator,
    mean_normalized_rank,
)
from sage.benchmark.benchmark_refiner.analysis.statistical import (
    SignificanceResult,
    TTestResult,
    bonferroni_correction,
    bootstrap_confidence_interval,
    cohens_d,
    compute_all_statistics,
    generate_significance_report,
    holm_bonferroni_correction,
    paired_t_test,
    wilcoxon_test,
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
    # 统计检验
    "TTestResult",
    "SignificanceResult",
    "paired_t_test",
    "bootstrap_confidence_interval",
    "cohens_d",
    "bonferroni_correction",
    "holm_bonferroni_correction",
    "generate_significance_report",
    "compute_all_statistics",
    "wilcoxon_test",
]
