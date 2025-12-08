"""
注意力头分析模块 - 简化版

用于识别 RAG 系统中对检索最重要的注意力头。
整合了模型加载、Hook 注册、MNR 计算和结果可视化。

模块组成:
- head_analysis: 注意力头分析
- visualization: 可视化工具
- statistical: 统计显著性检验
- latex_export: LaTeX 表格导出
"""

from sage.benchmark.benchmark_refiner.analysis.head_analysis import (
    AttentionHookExtractor,
    HeadwiseEvaluator,
    MetricsAggregator,
    mean_normalized_rank,
)
from sage.benchmark.benchmark_refiner.analysis.latex_export import (
    TableConfig,
    export_all_tables,
    generate_ablation_table,
    generate_case_study_table,
    generate_latency_breakdown_table,
    generate_main_results_table,
    generate_significance_table,
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
from sage.benchmark.benchmark_refiner.analysis.visualization import (
    generate_visualization_report,
    plot_algorithm_comparison,
    plot_dataset_heatmap,
    plot_latency_breakdown,
    plot_mnr_curve,
    plot_pareto_frontier,
    plot_radar_chart,
)

__all__ = [
    # 核心类
    "AttentionHookExtractor",
    "HeadwiseEvaluator",
    "MetricsAggregator",
    # 指标
    "mean_normalized_rank",
    # 可视化 - 注意力头分析
    "plot_mnr_curve",
    # 可视化 - 算法对比
    "plot_algorithm_comparison",
    "plot_pareto_frontier",
    "plot_latency_breakdown",
    "plot_dataset_heatmap",
    "plot_radar_chart",
    "generate_visualization_report",
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
    # LaTeX 导出
    "TableConfig",
    "generate_main_results_table",
    "generate_ablation_table",
    "generate_significance_table",
    "generate_case_study_table",
    "generate_latency_breakdown_table",
    "export_all_tables",
]
