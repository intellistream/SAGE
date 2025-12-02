#!/usr/bin/env python3
"""
Section 5.2.3: Tool Selection Experiment (RQ3)

研究问题: 现有方法从大规模工具库中选择正确工具的能力如何?

测试方法:
- selector.keyword    : BM25 关键词匹配
- selector.embedding  : Dense Retrieval 语义匹配
- selector.hybrid     : 40% BM25 + 60% Dense 融合
- selector.gorilla    : Embedding 检索 + LLM 重排序
- selector.dfsdt      : LLM 逐个评分 (ToolLLM 方法)

目标指标:
- Primary: Top-K Accuracy ≥ 95% (K=5)
- Secondary: MRR, Recall@K, Precision@K
- Tertiary: Latency (ms)

Usage:
    python exp_main_selection.py
    python exp_main_selection.py --max-samples 100 --top-k 5
    python exp_main_selection.py --skip-llm
"""

from __future__ import annotations

import argparse
import time

from .exp_utils import (
    ExperimentResult,
    ExperimentSummary,
    create_progress_bar,
    load_benchmark_data,
    print_metrics_detail,
    print_result_row,
    print_section_header,
    print_subsection_header,
    save_results,
    setup_experiment_env,
)


def compute_mrr(predictions: list[list[str]], references: list[list[str]]) -> float:
    """计算 Mean Reciprocal Rank。"""
    rr_sum = 0.0
    for pred, ref in zip(predictions, references):
        ref_set = set(ref)
        for i, p in enumerate(pred):
            if p in ref_set:
                rr_sum += 1.0 / (i + 1)
                break
    return rr_sum / len(predictions) if predictions else 0.0


def compute_top_k_accuracy(
    predictions: list[list[str]], references: list[list[str]], k: int
) -> float:
    """计算 Top-K Accuracy。"""
    hits = 0
    for pred, ref in zip(predictions, references):
        pred_top_k = set(pred[:k])
        ref_set = set(ref)
        if pred_top_k & ref_set:
            hits += 1
    return hits / len(predictions) if predictions else 0.0


def compute_recall_at_k(predictions: list[list[str]], references: list[list[str]], k: int) -> float:
    """计算 Recall@K。"""
    recalls = []
    for pred, ref in zip(predictions, references):
        pred_top_k = set(pred[:k])
        ref_set = set(ref)
        if ref_set:
            recalls.append(len(pred_top_k & ref_set) / len(ref_set))
        else:
            recalls.append(0.0)
    return sum(recalls) / len(recalls) if recalls else 0.0


def compute_precision_at_k(
    predictions: list[list[str]], references: list[list[str]], k: int
) -> float:
    """计算 Precision@K。"""
    precisions = []
    for pred, ref in zip(predictions, references):
        pred_top_k = set(pred[:k])
        ref_set = set(ref)
        if pred_top_k:
            precisions.append(len(pred_top_k & ref_set) / len(pred_top_k))
        else:
            precisions.append(0.0)
    return sum(precisions) / len(precisions) if precisions else 0.0


def normalize_ground_truth(ground_truth: object) -> list[str]:
    """将地面真实标签统一为字符串列表。"""

    if ground_truth is None:
        return []

    if isinstance(ground_truth, str):
        return [ground_truth]

    if isinstance(ground_truth, list):
        return [str(item) for item in ground_truth]

    if isinstance(ground_truth, dict):
        for key in ("top_k", "tool_ids", "tools", "ids"):
            value = ground_truth.get(key)
            if isinstance(value, list):
                return [str(item) for item in value]
            if isinstance(value, str):
                return [value]
        # fall back to any string-like values
        values = [str(value) for value in ground_truth.values() if value]
        if values:
            return values

    return [str(ground_truth)]


def run_selection_experiment(
    max_samples: int = 100,
    top_k: int = 5,
    skip_llm: bool = False,
    verbose: bool = True,
) -> ExperimentSummary:
    """
    运行 Tool Selection 实验。

    Args:
        max_samples: 最大测试样本数
        top_k: Top-K 参数
        skip_llm: 是否跳过 LLM-based 方法
        verbose: 是否打印详细信息

    Returns:
        ExperimentSummary 对象
    """
    setup_experiment_env(verbose=verbose)

    print_section_header("Section 5.2.3: Tool Selection (RQ3)")
    print(f"   Target: Top-{top_k} Accuracy ≥ 95%")
    print(f"   Max samples: {max_samples}")

    # 加载数据
    samples = load_benchmark_data("selection", split="test", max_samples=max_samples)
    if not samples:
        print("  ❌ No selection data available")
        return ExperimentSummary(section="5_2_main", challenge="selection")

    print(f"   Loaded {len(samples)} samples")

    # 获取策略注册表
    try:
        from sage.benchmark.benchmark_agent import get_adapter_registry

        registry = get_adapter_registry()
    except ImportError as e:
        print(f"  ❌ Failed to import adapter registry: {e}")
        return ExperimentSummary(section="5_2_main", challenge="selection")

    # 定义测试策略
    strategies = [
        ("selector.keyword", "Keyword (BM25)"),
        ("selector.embedding", "Embedding"),
        ("selector.hybrid", "Hybrid"),
        ("selector.gorilla", "Gorilla"),
        ("selector.dfsdt", "DFSDT"),
    ]

    # 跳过 LLM 策略
    LLM_STRATEGIES = {"selector.gorilla", "selector.dfsdt"}
    if skip_llm:
        strategies = [(name, display) for name, display in strategies if name not in LLM_STRATEGIES]
        print("  ⚠️  Skipping LLM-based strategies")

    results = []
    target = 0.95

    for strategy_name, display_name in strategies:
        print_subsection_header(f"Testing: {display_name}")

        try:
            selector = registry.get(strategy_name)
        except Exception as e:
            print(f"    ⚠️  Failed to create selector: {e}")
            continue

        # 运行评测
        start_time = time.time()
        all_predictions = []
        all_references = []

        with create_progress_bar(len(samples), desc=f"  {display_name}") as pbar:
            for sample in samples:
                try:
                    query = sample.get("instruction", sample.get("query", ""))
                    candidate_tools = sample.get("candidate_tools", [])
                    ground_truth = sample.get("ground_truth", sample.get("expected_tools", []))

                    # 调用选择器
                    predictions = selector.select(
                        query, candidate_tools=candidate_tools, top_k=top_k
                    )

                    # 提取工具 ID
                    if predictions and hasattr(predictions[0], "tool_id"):
                        pred_ids = [p.tool_id for p in predictions]
                    elif predictions and isinstance(predictions[0], dict):
                        pred_ids = [p.get("tool_id", p.get("id", str(p))) for p in predictions]
                    else:
                        pred_ids = [str(p) for p in predictions] if predictions else []

                    # 标准化 ground truth
                    ref_ids = normalize_ground_truth(ground_truth)

                    all_predictions.append(pred_ids)
                    all_references.append(ref_ids)

                except Exception as e:
                    if verbose:
                        print(f"    Error: {e}")
                    all_predictions.append([])
                    all_references.append(sample.get("ground_truth", []))

                pbar.update(1)

        elapsed = time.time() - start_time

        # 计算指标
        n = len(samples)
        top_k_acc = compute_top_k_accuracy(all_predictions, all_references, top_k)
        mrr = compute_mrr(all_predictions, all_references)
        recall_k = compute_recall_at_k(all_predictions, all_references, top_k)
        precision_k = compute_precision_at_k(all_predictions, all_references, top_k)

        exp_result = ExperimentResult(
            challenge="selection",
            strategy=strategy_name,
            metrics={
                "top_k_accuracy": top_k_acc,
                "mrr": mrr,
                f"recall@{top_k}": recall_k,
                f"precision@{top_k}": precision_k,
            },
            metadata={
                "total_samples": n,
                "top_k": top_k,
                "latency_ms": elapsed * 1000 / n if n > 0 else 0,
            },
            passed=top_k_acc >= target,
            target=target,
        )
        results.append(exp_result)

        # 打印结果
        print_result_row(display_name, {"top_k_accuracy": top_k_acc}, exp_result.passed, target)
        if verbose:
            print_metrics_detail(exp_result.metrics)

    # 找出最佳策略
    best_result = max(results, key=lambda r: r.metrics["top_k_accuracy"]) if results else None

    summary = ExperimentSummary(
        section="5_2_main",
        challenge="selection",
        results=results,
        best_strategy=best_result.strategy if best_result else None,
        best_metric=best_result.metrics["top_k_accuracy"] if best_result else None,
        target_met=any(r.passed for r in results),
    )

    # 保存结果
    output_file = save_results(summary.to_dict(), "5_2_main", "selection")
    print(f"\n  Results saved to: {output_file}")

    # 生成图表
    if results:
        from figure_generator import (
            generate_detailed_table,
            get_figures_dir,
            get_tables_dir,
            plot_challenge_comparison,
        )

        figures_dir = get_figures_dir()
        tables_dir = get_tables_dir()

        # 生成对比图
        plot_challenge_comparison(
            [{"strategy": r.strategy.split(".")[-1], "metrics": r.metrics} for r in results],
            challenge="selection",
            metrics=["top_k_accuracy", "mrr"],
            target=target,
            output_path=figures_dir / "fig3_main_selection_comparison.pdf",
            title=f"Tool Selection: Strategy Comparison (Top-{top_k})",
        )

        # 生成表格
        generate_detailed_table(
            [{"strategy": r.strategy.split(".")[-1], "metrics": r.metrics} for r in results],
            challenge="selection",
            metrics=["top_k_accuracy", "mrr", f"recall@{top_k}", f"precision@{top_k}"],
            output_path=tables_dir / "table_selection_detailed.tex",
        )

        print(f"  Figure saved to: {figures_dir / 'fig3_main_selection_comparison.pdf'}")

    return summary


def main():
    parser = argparse.ArgumentParser(description="Section 5.2.3: Tool Selection Experiment")
    parser.add_argument("--max-samples", type=int, default=100, help="Maximum samples to test")
    parser.add_argument("--top-k", type=int, default=5, help="Top-K parameter")
    parser.add_argument("--skip-llm", action="store_true", help="Skip LLM-based methods")
    parser.add_argument("--verbose", action="store_true", default=True, help="Verbose output")
    args = parser.parse_args()

    summary = run_selection_experiment(
        max_samples=args.max_samples,
        top_k=args.top_k,
        skip_llm=args.skip_llm,
        verbose=args.verbose,
    )

    # 打印总结
    print("\n" + "=" * 70)
    print("📊 Summary")
    print("=" * 70)
    print(f"  Best strategy: {summary.best_strategy}")
    print(
        f"  Best Top-K accuracy: {summary.best_metric * 100:.1f}%"
        if summary.best_metric
        else "  N/A"
    )
    print(f"  Target met: {'✅ YES' if summary.target_met else '❌ NO'}")


if __name__ == "__main__":
    main()
