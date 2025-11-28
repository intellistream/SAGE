"""
SAGE-Bench Internal Modules

这些模块是 sage-bench CLI 的内部实现，不应直接调用。
请使用 sage-bench CLI 作为统一入口。

Usage:
    sage-bench eval --dataset all
    sage-bench run --quick
    sage-bench llm status
"""

from .all_experiments import run_all_experiments
from .interactive import run_interactive_mode
from .training_comparison import run_training_comparison
from .unified_eval import run_evaluation

__all__ = [
    "run_evaluation",
    "run_all_experiments",
    "run_training_comparison",
    "run_interactive_mode",
]
