"""
Agent Benchmark Scripts

Executable scripts for running agent training experiments:
- run_method_comparison.py: Compare different training methods (A-D)
- run_full_training_comparison.py: Full training on A100 GPUs
- agent_sft_training_example.py: SFT training demonstration

Usage:
    # From command line
    python -m sage.benchmark.benchmark_agent.scripts.run_method_comparison --demo

    # Or directly
    cd packages/sage-benchmark/src/sage/benchmark/benchmark_agent/scripts
    python run_method_comparison.py --quick
"""

__all__ = [
    "run_method_comparison",
    "run_full_training_comparison",
    "agent_sft_training_example",
]
