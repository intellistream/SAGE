"""
SAGE-Bench Internal Module: Training Method Comparison

WARNING: This is an internal module. Do not call directly.
Please use: sage-bench train [--methods <methods>] [--quick]
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def run_training_comparison(
    methods: list[str] = None,
    base_model: str = "Qwen/Qwen2.5-1.5B-Instruct",
    quick: bool = False,
    dry_run: bool = False,
    output_dir: Optional[str] = None,
) -> int:
    """
    运行训练方法对比实验 (Paper 2)。

    Args:
        methods: 训练方法列表
        base_model: 基础模型
        quick: 快速模式
        dry_run: 模拟运行 (不实际训练)
        output_dir: 输出目录

    Returns:
        0 表示成功，1 表示失败
    """
    if methods is None:
        methods = ["A_baseline", "D_combined"]

    # 添加路径
    script_dir = Path(__file__).parent.parent
    sys.path.insert(0, str(script_dir.parent.parent.parent.parent))

    # 确定输出目录
    if output_dir:
        out_path = Path(output_dir)
    else:
        out_path = Path.home() / ".sage" / "benchmark" / "results"
    out_path.mkdir(parents=True, exist_ok=True)

    try:
        # 导入原模块
        from sage.benchmark.benchmark_agent.scripts.run_all_experiments import (
            ExperimentRunner,
            setup_environment,
        )

        setup_environment()

        print("=" * 70)
        print("🚀 SAGE Training Method Comparison")
        print("=" * 70)
        print(f"  Methods: {', '.join(methods)}")
        print(f"  Base model: {base_model}")
        print(f"  Quick mode: {quick}")
        print(f"  Dry run: {dry_run}")
        print(f"  Output: {out_path}")
        print("=" * 70)

        runner = ExperimentRunner(out_path, verbose=False)

        runner.run_training_comparison(
            methods=methods,
            base_model=base_model,
            dry_run=dry_run,
        )

        runner.save_results()

        print("\n✅ Training comparison completed")
        return 0

    except Exception as e:
        logger.error(f"Training comparison failed: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    print("=" * 70)
    print("WARNING: This is an internal module.")
    print("Please use the CLI instead:")
    print()
    print("    sage-bench train [--methods <methods>] [--quick]")
    print()
    print("Examples:")
    print("    sage-bench train --quick")
    print("    sage-bench train --methods A_baseline,D_combined")
    print("    sage-bench train --dry-run")
    print("=" * 70)
    sys.exit(1)
