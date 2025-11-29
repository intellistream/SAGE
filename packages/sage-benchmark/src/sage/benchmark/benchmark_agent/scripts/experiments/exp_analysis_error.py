#!/usr/bin/env python3
"""
Section 5.3.1: Error Analysis

深入分析各方法的失败模式，找出改进方向。

分析内容:
1. Error Type Breakdown - 按 Challenge 分解错误类型
2. Failure Cascading Analysis - 早期错误导致的级联失败

输出:
- figures/fig4_analysis_error_breakdown.pdf
- tables/table_error_breakdown.tex

Usage:
    python exp_analysis_error.py
    python exp_analysis_error.py --challenge timing
    python exp_analysis_error.py --challenge all
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from typing import Any

from .exp_utils import (
    get_figures_dir,
    print_section_header,
    print_subsection_header,
    save_results,
    setup_experiment_env,
)

# =============================================================================
# Error Analysis Functions
# =============================================================================


def analyze_timing_errors(results: list[dict]) -> dict[str, Any]:
    """
    分析 Timing 错误类型。

    错误类型:
    - false_positive: 不该调用却调用 (调用频率过高)
    - false_negative: 该调用却没调用 (错过关键时机)
    - confidence_miscalibration: 高置信度但错误
    """
    error_counts = defaultdict(lambda: defaultdict(int))
    confidence_errors = defaultdict(list)

    for r in results:
        strategy = r.get("strategy", "unknown")
        predictions = r.get("predictions", [])
        references = r.get("references", [])
        confidences = r.get("confidences", [])

        for i, (pred, ref) in enumerate(zip(predictions, references)):
            if pred != ref:
                if pred and not ref:
                    error_counts[strategy]["false_positive"] += 1
                elif not pred and ref:
                    error_counts[strategy]["false_negative"] += 1

                # 置信度校准分析
                if confidences and i < len(confidences):
                    conf = confidences[i]
                    if conf > 0.8:  # 高置信但错误
                        error_counts[strategy]["high_conf_error"] += 1
                        confidence_errors[strategy].append(conf)

    return {
        "error_counts": {k: dict(v) for k, v in error_counts.items()},
        "confidence_errors": {
            k: {"count": len(v), "avg_conf": sum(v) / len(v) if v else 0}
            for k, v in confidence_errors.items()
        },
    }


def analyze_planning_errors(results: list[dict]) -> dict[str, Any]:
    """
    分析 Planning 错误类型。

    错误类型:
    - step_missing: 缺失关键步骤
    - wrong_order: 步骤顺序错误
    - invalid_step: 步骤不合理/幻觉
    - extra_steps: 多余步骤
    """
    error_counts = defaultdict(lambda: defaultdict(int))
    first_error_indices = defaultdict(list)

    for r in results:
        strategy = r.get("strategy", "unknown")
        predictions = r.get("predictions", [])
        references = r.get("references", [])

        for pred_plan, ref_plan in zip(predictions, references):
            pred_steps = pred_plan if isinstance(pred_plan, list) else []
            ref_steps = ref_plan if isinstance(ref_plan, list) else []

            if not ref_steps:
                continue

            # 分类错误
            pred_set = set(pred_steps)
            ref_set = set(ref_steps)

            # 缺失步骤
            missing = ref_set - pred_set
            if missing:
                error_counts[strategy]["step_missing"] += len(missing)

            # 多余步骤 (可能是幻觉)
            extra = pred_set - ref_set
            if extra:
                error_counts[strategy]["extra_steps"] += len(extra)

            # 顺序错误 (工具集合相同但顺序不同)
            if pred_set == ref_set and pred_steps != ref_steps:
                error_counts[strategy]["wrong_order"] += 1

            # 首次错误位置
            for i, (p, r) in enumerate(zip(pred_steps, ref_steps)):
                if p != r:
                    first_error_indices[strategy].append(i)
                    break

    # 计算首次错误分布
    first_error_dist = {}
    for strategy, indices in first_error_indices.items():
        if indices:
            dist = Counter(indices)
            first_error_dist[strategy] = {
                "distribution": dict(dist),
                "mean_index": sum(indices) / len(indices),
                "total_errors": len(indices),
            }

    return {
        "error_counts": {k: dict(v) for k, v in error_counts.items()},
        "first_error_distribution": first_error_dist,
    }


def analyze_selection_errors(results: list[dict], k: int = 5) -> dict[str, Any]:
    """
    分析 Selection 错误类型。

    错误类型:
    - top1_miss: 第一个选择就错
    - topk_miss: Top-K 内全错
    - rank_volatility: 正确答案排名不稳定
    - category_confusion: 跨类别混淆
    """
    error_counts = defaultdict(lambda: defaultdict(int))
    rank_positions = defaultdict(list)

    for r in results:
        strategy = r.get("strategy", "unknown")
        predictions = r.get("predictions", [])
        references = r.get("references", [])

        for pred_list, ref_list in zip(predictions, references):
            ref_set = set(ref_list) if isinstance(ref_list, list) else {ref_list}
            pred_top_k = pred_list[:k] if isinstance(pred_list, list) else [pred_list]

            # Top-1 错误
            if pred_top_k and pred_top_k[0] not in ref_set:
                error_counts[strategy]["top1_miss"] += 1

            # Top-K 全错
            if not (set(pred_top_k) & ref_set):
                error_counts[strategy]["topk_miss"] += 1

            # 记录正确答案的排名位置
            for i, p in enumerate(pred_list if isinstance(pred_list, list) else [pred_list]):
                if p in ref_set:
                    rank_positions[strategy].append(i + 1)
                    break

            # 类别混淆分析
            if pred_top_k:
                pred_categories = {_extract_category(p) for p in pred_top_k}
                ref_categories = {_extract_category(r) for r in ref_set}
                if pred_categories and ref_categories and not (pred_categories & ref_categories):
                    error_counts[strategy]["category_confusion"] += 1

    # 计算排名稳定性
    rank_analysis = {}
    for strategy, positions in rank_positions.items():
        if positions:
            rank_analysis[strategy] = {
                "mean_rank": sum(positions) / len(positions),
                "std_rank": (
                    sum((p - sum(positions) / len(positions)) ** 2 for p in positions)
                    / len(positions)
                )
                ** 0.5,
                "rank_1_count": sum(1 for p in positions if p == 1),
                "total": len(positions),
            }

    return {
        "error_counts": {k: dict(v) for k, v in error_counts.items()},
        "rank_analysis": rank_analysis,
    }


def _extract_category(tool_id: str) -> str:
    """从工具 ID 提取类别。"""
    parts = tool_id.split("_")
    return parts[0] if parts else "unknown"


# =============================================================================
# Cascading Failure Analysis
# =============================================================================


def analyze_cascading_failures(results: list[dict]) -> dict[str, Any]:
    """
    分析级联失败模式。

    检查早期错误是否导致后续步骤全部失败。
    """
    cascade_stats = defaultdict(lambda: {"cascading": 0, "non_cascading": 0, "recovery": 0})

    for r in results:
        strategy = r.get("strategy", "unknown")
        predictions = r.get("predictions", [])
        references = r.get("references", [])

        for pred_plan, ref_plan in zip(predictions, references):
            if not isinstance(pred_plan, list) or not isinstance(ref_plan, list):
                continue

            if len(pred_plan) < 2 or len(ref_plan) < 2:
                continue

            # 找到首次错误位置
            first_error_idx = None
            for i, (p, r) in enumerate(zip(pred_plan, ref_plan)):
                if p != r:
                    first_error_idx = i
                    break

            if first_error_idx is None:
                continue  # 全对

            # 检查首次错误后的情况
            remaining_pred = pred_plan[first_error_idx + 1 :]
            remaining_ref = ref_plan[first_error_idx + 1 :]

            if not remaining_ref:
                continue

            # 计算剩余步骤的正确率
            remaining_correct = sum(1 for p, r in zip(remaining_pred, remaining_ref) if p == r)
            remaining_acc = remaining_correct / len(remaining_ref) if remaining_ref else 0

            if remaining_acc < 0.2:  # 级联失败：后续几乎全错
                cascade_stats[strategy]["cascading"] += 1
            elif remaining_acc > 0.5:  # 恢复：后续大部分正确
                cascade_stats[strategy]["recovery"] += 1
            else:  # 部分影响
                cascade_stats[strategy]["non_cascading"] += 1

    return {
        "cascade_statistics": {k: dict(v) for k, v in cascade_stats.items()},
        "insight": "High cascading rate indicates fragile design without rollback/recovery mechanism.",
    }


# =============================================================================
# Main Experiment
# =============================================================================


def run_error_analysis(challenge: str = "all", verbose: bool = True) -> dict[str, Any]:
    """
    运行错误分析实验。

    Args:
        challenge: 要分析的挑战 ("timing", "planning", "selection", "all")
        verbose: 是否打印详细信息

    Returns:
        错误分析结果字典
    """
    setup_experiment_env(verbose=verbose)

    print_section_header("Section 5.3.1: Error Analysis")

    all_results = {}

    # 加载之前实验的结果
    # TODO: 实际应该从保存的结果文件加载
    # 这里用示例数据结构

    challenges_to_analyze = []
    if challenge == "all":
        challenges_to_analyze = ["timing", "planning", "selection"]
    else:
        challenges_to_analyze = [challenge]

    for ch in challenges_to_analyze:
        print_subsection_header(f"Analyzing: {ch.title()}")

        # 模拟加载结果 (实际应从文件加载)
        results = _load_experiment_results(ch)

        if ch == "timing":
            analysis = analyze_timing_errors(results)
        elif ch == "planning":
            analysis = analyze_planning_errors(results)
            # 添加级联分析
            analysis["cascading"] = analyze_cascading_failures(results)
        elif ch == "selection":
            analysis = analyze_selection_errors(results)

        all_results[ch] = analysis

        # 打印摘要
        if "error_counts" in analysis:
            print("    Error counts by strategy:")
            for strategy, counts in analysis["error_counts"].items():
                print(f"      {strategy}: {dict(counts)}")

    # 保存结果
    output_file = save_results(all_results, "5_3_analysis", "error_analysis")
    print(f"\n  Results saved to: {output_file}")

    # 生成图表
    _generate_error_figures(all_results)

    return all_results


def _load_experiment_results(challenge: str) -> list[dict]:
    """
    加载实验结果。

    TODO: 实际实现应从 section_5_2_main/{challenge}_results.json 加载
    """
    # 示例数据结构
    return [
        {
            "strategy": f"{challenge}_strategy_1",
            "predictions": [],
            "references": [],
            "confidences": [],
        }
    ]


def _generate_error_figures(results: dict) -> None:
    """生成错误分析图表。"""
    try:
        from figure_generator import plot_error_breakdown

        figures_dir = get_figures_dir()

        for challenge, analysis in results.items():
            if "error_counts" in analysis and analysis["error_counts"]:
                plot_error_breakdown(
                    analysis["error_counts"],
                    challenge=challenge,
                    output_path=figures_dir / f"fig4_analysis_error_{challenge}.pdf",
                )
                print(f"  Figure saved: fig4_analysis_error_{challenge}.pdf")

    except Exception as e:
        print(f"  Warning: Could not generate figures: {e}")


def main():
    parser = argparse.ArgumentParser(description="Section 5.3.1: Error Analysis")
    parser.add_argument(
        "--challenge",
        type=str,
        default="all",
        choices=["timing", "planning", "selection", "all"],
        help="Challenge to analyze",
    )
    parser.add_argument("--verbose", action="store_true", default=True, help="Verbose output")
    args = parser.parse_args()

    run_error_analysis(challenge=args.challenge, verbose=args.verbose)

    print("\n" + "=" * 70)
    print("📊 Error Analysis Complete")
    print("=" * 70)


if __name__ == "__main__":
    main()
