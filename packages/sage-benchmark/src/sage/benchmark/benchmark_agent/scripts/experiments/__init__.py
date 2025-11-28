"""
SAGE-Bench Paper 1 Experiments Package

按论文 Experiment Section 组织的实验脚本集合:

- Section 5.2 (Main Results):
    - exp_main_timing.py      # RQ1: Timing Detection
    - exp_main_planning.py    # RQ2: Task Planning
    - exp_main_selection.py   # RQ3: Tool Selection

- Section 5.3 (Analysis):
    - exp_analysis_error.py       # 5.3.1 Error Analysis
    - exp_analysis_scaling.py     # 5.3.2 Scaling Analysis
    - exp_analysis_robustness.py  # 5.3.3 Robustness Analysis
    - exp_analysis_ablation.py    # 5.3.4 Ablation Studies

- Section 5.4 (Generalization):
    - exp_cross_dataset.py    # Cross-dataset evaluation

Usage:
    sage-bench paper1 run                    # 运行所有实验
    sage-bench paper1 run --section 5.2      # 仅主实验
    sage-bench paper1 timing                 # 单个实验
"""

from .exp_utils import (
    get_embedding_client,
    get_llm_client,
    load_benchmark_data,
    save_results,
    setup_experiment_env,
)

__all__ = [
    "setup_experiment_env",
    "load_benchmark_data",
    "save_results",
    "get_llm_client",
    "get_embedding_client",
]
