"""
SAGE-Bench Scripts

统一的 Benchmark 实验脚本入口。

所有实验功能位于 experiments/ 子包:
- run_paper1_experiments.py: 论文 1 实验统一入口
- exp_main_*.py: Section 5.2 主实验
- exp_analysis_*.py: Section 5.3 分析实验
- exp_cross_dataset.py: Section 5.4 跨数据集泛化
- exp_training_comparison.py: Section 5.5 训练方法对比

Usage:
    # CLI 入口
    sage-bench run --quick
    sage-bench eval --dataset all
    sage-bench train --dry-run
    sage-bench llm status

    # 直接运行
    python -m sage.benchmark.benchmark_agent.scripts.experiments.run_paper1_experiments --quick
"""

__all__ = [
    "experiments",
]
