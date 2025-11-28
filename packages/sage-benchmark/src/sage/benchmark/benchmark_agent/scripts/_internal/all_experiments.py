"""
SAGE-Bench Internal Module: All Experiments Runner

WARNING: This is an internal module. Do not call directly.
Please use: sage-bench run [--challenge <challenge>] [--quick]
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def run_all_experiments(
    challenge: Optional[str] = None,
    quick: bool = False,
    skip_llm: bool = False,
    max_samples: Optional[int] = None,
    dataset: str = "sage",
    output_dir: Optional[str] = None,
) -> int:
    """
    运行完整 Benchmark 评测 (三个 Challenge)。

    Args:
        challenge: 指定单个 Challenge ('timing', 'planning', 'tool_selection')
        quick: 快速模式 (fewer samples)
        skip_llm: 跳过 LLM 方法
        max_samples: 最大样本数
        dataset: 数据集
        output_dir: 输出目录

    Returns:
        0 表示成功，1 表示失败
    """
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
        # 导入原模块中的 ExperimentRunner
        from sage.benchmark.benchmark_agent.scripts.run_all_experiments import (
            DEFAULT_DATA_DIR,
            ExperimentRunner,
            setup_environment,
        )

        setup_environment()

        # 确定样本数
        if quick:
            max_timing = 50
            max_planning = 30
            max_tool = 50
        elif max_samples:
            max_timing = max_planning = max_tool = max_samples
        else:
            max_timing = 150
            max_planning = 100
            max_tool = 100

        # 打印配置
        mode_str = "quick" if quick else "eval-only"
        print("=" * 70)
        print("🚀 SAGE AGENT BENCHMARK - Complete Experiment Runner")
        print("=" * 70)
        print(f"  Output directory: {out_path}")
        print(f"  Data directory:   {DEFAULT_DATA_DIR}")
        print(f"  Mode: {mode_str}")
        print(f"  Sample sizes: timing={max_timing}, planning={max_planning}, tool={max_tool}")
        if skip_llm:
            print("  ⚠️  LLM strategies: SKIPPED (--skip-llm)")
        print("=" * 70)

        runner = ExperimentRunner(out_path, verbose=False, skip_llm=skip_llm)

        # 确定运行哪些 Challenge
        run_timing = challenge is None or challenge == "timing"
        run_planning = challenge is None or challenge == "planning"
        run_tool_selection = challenge is None or challenge == "tool_selection"

        if run_timing:
            runner.run_timing_evaluation(max_samples=max_timing)
        if run_planning:
            runner.run_planning_evaluation(max_samples=max_planning)
        if run_tool_selection:
            # 支持跨数据集
            if dataset != "sage":
                from sage.benchmark.benchmark_agent.scripts._internal.unified_eval import (
                    run_evaluation,
                )

                run_evaluation(
                    dataset=dataset,
                    methods=["keyword", "embedding", "hybrid"]
                    if skip_llm
                    else ["keyword", "embedding", "hybrid", "gorilla", "dfsdt"],
                    max_samples=max_tool,
                    output_dir=str(out_path),
                )
            else:
                runner.run_tool_selection_evaluation(max_samples=max_tool, top_k=5)

        runner.generate_paper_materials()
        runner._generate_summary()
        runner.save_results()

        print("\n✅ All experiments completed")
        return 0

    except Exception as e:
        logger.error(f"Experiments failed: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    print("=" * 70)
    print("WARNING: This is an internal module.")
    print("Please use the CLI instead:")
    print()
    print("    sage-bench run [--challenge <challenge>] [--quick]")
    print()
    print("Examples:")
    print("    sage-bench run --quick")
    print("    sage-bench run --challenge tool_selection")
    print("    sage-bench run --dataset all")
    print("=" * 70)
    sys.exit(1)
