"""
SAGE-Bench Internal Module: Unified Tool Selection Evaluation

WARNING: This is an internal module. Do not call directly.
Please use: sage-bench eval --dataset <dataset> --methods <methods>
"""

from __future__ import annotations

import logging
import sys
import warnings
from pathlib import Path

logger = logging.getLogger(__name__)

# 懒加载，避免循环导入
_unified_eval_module = None


def _get_module():
    """延迟导入原有模块"""
    global _unified_eval_module
    if _unified_eval_module is None:
        # 添加路径
        script_dir = Path(__file__).parent.parent
        sys.path.insert(0, str(script_dir.parent.parent.parent.parent))

        # 动态导入原模块中的函数
        from sage.benchmark.benchmark_agent.scripts.run_unified_eval import (
            EXTERNAL_BENCHMARKS,
        )
        from sage.benchmark.benchmark_agent.scripts.run_unified_eval import (
            print_comparison_table as _print_table,
        )
        from sage.benchmark.benchmark_agent.scripts.run_unified_eval import (
            run_evaluation as _run_eval,
        )
        from sage.benchmark.benchmark_agent.scripts.run_unified_eval import (
            save_results as _save_results,
        )

        _unified_eval_module = {
            "run_evaluation": _run_eval,
            "save_results": _save_results,
            "print_comparison_table": _print_table,
            "EXTERNAL_BENCHMARKS": EXTERNAL_BENCHMARKS,
        }
    return _unified_eval_module


def run_evaluation(
    dataset: str = "sage",
    methods: list[str] = None,
    max_samples: int = 100,
    top_k: int = 5,
    use_embedded: bool = False,
    model_id: str = None,
    output_dir: str = None,
) -> int:
    """
    运行统一工具选择评测。

    Args:
        dataset: 数据集名称 ('sage', 'acebench', 'apibank', 'all', etc.)
        methods: 评测方法列表
        max_samples: 最大样本数
        top_k: Top-K 评测值
        use_embedded: 是否使用内嵌 LLM
        model_id: LLM 模型 ID
        output_dir: 输出目录

    Returns:
        0 表示成功，1 表示失败
    """
    if methods is None:
        methods = ["keyword", "embedding", "hybrid"]

    # 确定输出目录
    if output_dir:
        out_path = Path(output_dir)
    else:
        out_path = Path.home() / ".sage" / "benchmark" / "results"
    out_path.mkdir(parents=True, exist_ok=True)

    # 打印配置
    print("\n" + "=" * 70)
    print("Unified Tool Selection Evaluation")
    print("=" * 70)
    print(f"Dataset(s): {dataset}")
    print(f"Methods: {', '.join(methods)}")
    print(f"Max samples: {max_samples}")
    print(f"Top-K: {top_k}")
    print(f"Use embedded LLM: {use_embedded}")
    print("=" * 70)

    try:
        mod = _get_module()

        # 调用原有评测函数
        results = mod["run_evaluation"](
            dataset=dataset,
            methods=methods,
            max_samples=max_samples,
            use_embedded=use_embedded,
            model_id=model_id,
            output_dir=out_path,
            top_k=top_k,
        )

        if results:
            mod["print_comparison_table"](results)
            mod["save_results"](results, out_path)
            return 0
        else:
            logger.error("No results generated")
            return 1

    except Exception as e:
        logger.error(f"Evaluation failed: {e}")
        import traceback

        traceback.print_exc()
        return 1


def _warn_direct_call():
    """警告用户不要直接调用此模块"""
    warnings.warn(
        "This is an internal module. Please use 'sage-bench eval' instead.",
        DeprecationWarning,
        stacklevel=3,
    )


if __name__ == "__main__":
    print("=" * 70)
    print("WARNING: This is an internal module.")
    print("Please use the CLI instead:")
    print()
    print("    sage-bench eval --dataset <dataset> --methods <methods>")
    print()
    print("Examples:")
    print("    sage-bench eval --dataset sage --samples 100")
    print("    sage-bench eval --dataset all --methods keyword,embedding,gorilla")
    print("=" * 70)
    sys.exit(1)
