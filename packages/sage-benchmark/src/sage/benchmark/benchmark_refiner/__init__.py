"""
Benchmark Refiner - Refiner算法评测套件
======================================

Layer: L5 (Applications - Benchmarking)
Dependencies: sage.middleware (L4), sage.libs (L3)

提供多种上下文压缩算法的评测框架，包括：
- 评测 Pipeline (baseline, longrefiner, reform, provence)
- 注意力头分析工具 (MNR指标)
- 统一实验管理框架
- CLI 命令行工具

核心评测指标 (来自 sage.middleware.operators.rag.evaluate):
- F1Evaluate: Token级别F1分数
- TokenCountEvaluate: Token计数
- LatencyEvaluate: 延迟评测 (Retrieve/Refine/Generate)
- CompressionRateEvaluate: 压缩率
- RougeLEvaluate: ROUGE-L F1分数
- RecallEvaluate / BertRecallEvaluate: 召回率

已实现的算法:
- LongRefiner: 三阶段压缩 (Query Analysis → Doc Structuring → Global Selection)
- REFORM: 基于注意力头的token级压缩
- Provence: 句子级上下文剪枝 (DeBERTa-v3)
- Simple/Baseline: 无压缩基线

CLI 使用:
    # 快速对比多算法
    sage-refiner-bench compare --algorithms baseline,longrefiner,reform --samples 100

    # 从配置文件运行实验
    sage-refiner-bench run --config experiment.yaml

    # Budget 扫描
    sage-refiner-bench sweep --algorithm longrefiner --budgets 512,1024,2048

Python 使用:
    from sage.benchmark.benchmark_refiner.experiments import (
        RefinerExperimentRunner,
        RefinerExperimentConfig,
    )

    # 快速对比
    runner = RefinerExperimentRunner()
    result = runner.quick_compare(
        algorithms=["baseline", "longrefiner", "reform"],
        max_samples=100,
    )

目录结构:
    benchmark_refiner/
    ├── analysis/           # 注意力头分析工具
    ├── config/             # 配置文件
    ├── experiments/        # 统一实验管理
    │   ├── base_experiment.py
    │   ├── comparison_experiment.py
    │   └── runner.py
    ├── implementations/    # Pipeline实现
    │   └── pipelines/
    └── cli.py              # CLI入口
"""

__layer__ = "L5"

# Analysis tools
from sage.benchmark.benchmark_refiner.analysis import (
    AttentionHookExtractor,
    HeadwiseEvaluator,
    MetricsAggregator,
    mean_normalized_rank,
    plot_mnr_curve,
)

# Experiment framework
from sage.benchmark.benchmark_refiner.experiments import (
    AlgorithmMetrics,
    BaseRefinerExperiment,
    ComparisonExperiment,
    CompressionExperiment,
    DatasetType,
    ExperimentResult,
    LatencyExperiment,
    QualityExperiment,
    RefinerAlgorithm,
    RefinerExperimentConfig,
    RefinerExperimentRunner,
)

__all__ = [
    # Analysis
    "AttentionHookExtractor",
    "HeadwiseEvaluator",
    "MetricsAggregator",
    "mean_normalized_rank",
    "plot_mnr_curve",
    # Experiment framework - Enums
    "RefinerAlgorithm",
    "DatasetType",
    # Experiment framework - Config and results
    "RefinerExperimentConfig",
    "AlgorithmMetrics",
    "ExperimentResult",
    # Experiment framework - Experiment classes
    "BaseRefinerExperiment",
    "ComparisonExperiment",
    "QualityExperiment",
    "LatencyExperiment",
    "CompressionExperiment",
    # Experiment framework - Runner
    "RefinerExperimentRunner",
]
