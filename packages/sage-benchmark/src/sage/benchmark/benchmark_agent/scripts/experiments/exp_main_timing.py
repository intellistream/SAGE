#!/usr/bin/env python3
"""
Section 5.2.1: Timing Detection Experiment (RQ1)

研究问题: 现有方法在判断"是否需要调用工具"上的表现如何?

测试方法:
- timing.rule_based   : 关键词 + 正则规则
- timing.embedding    : 语义相似度判断
- timing.llm_based    : 直接 LLM 推理
- timing.hybrid       : Rule 初筛 + LLM 精判

目标指标:
- Primary: Accuracy ≥ 95%
- Secondary: Precision, Recall, F1
- Tertiary: Latency (ms)

Usage:
    python exp_main_timing.py
    python exp_main_timing.py --max-samples 100
    python exp_main_timing.py --skip-llm
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
from .figure_generator import generate_detailed_table, plot_challenge_comparison


def run_timing_experiment(
    max_samples: int = 150,
    skip_llm: bool = False,
    verbose: bool = True,
) -> ExperimentSummary:
    """
    运行 Timing Detection 实验。

    Args:
        max_samples: 最大测试样本数
        skip_llm: 是否跳过 LLM-based 方法
        verbose: 是否打印详细信息

    Returns:
        ExperimentSummary 对象
    """
    setup_experiment_env(verbose=verbose)

    print_section_header("Section 5.2.1: Timing Detection (RQ1)")
    print("   Target: Accuracy ≥ 95%")
    print(f"   Max samples: {max_samples}")

    # 加载数据
    samples = load_benchmark_data("timing", split="test", max_samples=max_samples)
    if not samples:
        print("  ❌ No timing data available")
        return ExperimentSummary(section="5_2_main", challenge="timing")

    print(f"   Loaded {len(samples)} samples")

    # 获取策略注册表
    try:
        from sage.benchmark.benchmark_agent import get_adapter_registry

        registry = get_adapter_registry()
    except ImportError as e:
        print(f"  ❌ Failed to import adapter registry: {e}")
        return ExperimentSummary(section="5_2_main", challenge="timing")

    # 定义测试策略
    strategies = [
        ("timing.rule_based", "Rule-based"),
        ("timing.embedding", "Embedding"),
        ("timing.llm_based", "LLM-based"),
        ("timing.hybrid", "Hybrid"),
    ]

    # 跳过 LLM 策略
    LLM_STRATEGIES = {"timing.llm_based", "timing.hybrid"}
    if skip_llm:
        strategies = [(name, display) for name, display in strategies if name not in LLM_STRATEGIES]
        print("  ⚠️  Skipping LLM-based strategies")

    results = []
    target = 0.95

    for strategy_name, display_name in strategies:
        print_subsection_header(f"Testing: {display_name}")

        try:
            detector = registry.get(strategy_name)
        except Exception as e:
            print(f"    ⚠️  Failed to create detector: {e}")
            continue

        # 运行评测
        start_time = time.time()
        correct = 0
        true_positives = 0
        false_positives = 0
        false_negatives = 0
        true_negatives = 0

        with create_progress_bar(len(samples), desc=f"  {display_name}") as pbar:
            for sample in samples:
                try:
                    # 创建消息对象
                    from sage.benchmark.benchmark_agent.experiments.timing_detection_exp import (
                        TimingMessage,
                    )

                    message = TimingMessage(
                        sample_id=sample.get("sample_id", ""),
                        message=sample.get("message", ""),
                        context=sample.get("context", {}),
                    )

                    result = detector.decide(message)
                    predicted = result.should_call_tool
                    expected = sample.get("should_call_tool", False)

                    if predicted == expected:
                        correct += 1

                    # 混淆矩阵
                    if predicted and expected:
                        true_positives += 1
                    elif predicted and not expected:
                        false_positives += 1
                    elif not predicted and expected:
                        false_negatives += 1
                    else:
                        true_negatives += 1

                except Exception as e:
                    if verbose:
                        print(f"    Error: {e}")

                pbar.update(1)

        elapsed = time.time() - start_time

        # 计算指标
        n = len(samples)
        accuracy = correct / n if n > 0 else 0
        precision = (
            true_positives / (true_positives + false_positives)
            if (true_positives + false_positives) > 0
            else 0
        )
        recall = (
            true_positives / (true_positives + false_negatives)
            if (true_positives + false_negatives) > 0
            else 0
        )
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

        exp_result = ExperimentResult(
            challenge="timing",
            strategy=strategy_name,
            metrics={
                "accuracy": accuracy,
                "precision": precision,
                "recall": recall,
                "f1": f1,
            },
            metadata={
                "total_samples": n,
                "correct": correct,
                "latency_ms": elapsed * 1000 / n if n > 0 else 0,
                "confusion_matrix": {
                    "tp": true_positives,
                    "fp": false_positives,
                    "fn": false_negatives,
                    "tn": true_negatives,
                },
            },
            passed=accuracy >= target,
            target=target,
        )
        results.append(exp_result)

        # 打印结果
        print_result_row(display_name, exp_result.metrics, exp_result.passed, target)
        if verbose:
            print_metrics_detail(exp_result.metrics)

    # 找出最佳策略
    best_result = max(results, key=lambda r: r.metrics["accuracy"]) if results else None

    summary = ExperimentSummary(
        section="5_2_main",
        challenge="timing",
        results=results,
        best_strategy=best_result.strategy if best_result else None,
        best_metric=best_result.metrics["accuracy"] if best_result else None,
        target_met=any(r.passed for r in results),
    )

    # 保存结果
    output_file = save_results(summary.to_dict(), "5_2_main", "timing")
    print(f"\n  Results saved to: {output_file}")

    # 生成图表
    if results:
        from figure_generator import get_figures_dir, get_tables_dir

        figures_dir = get_figures_dir()
        tables_dir = get_tables_dir()

        # 生成对比图
        plot_challenge_comparison(
            [{"strategy": r.strategy.split(".")[-1], "metrics": r.metrics} for r in results],
            challenge="timing",
            metrics=["accuracy", "precision", "recall", "f1"],
            target=target,
            output_path=figures_dir / "fig1_main_timing_comparison.pdf",
            title="Timing Detection: Strategy Comparison",
        )

        # 生成表格
        generate_detailed_table(
            [{"strategy": r.strategy.split(".")[-1], "metrics": r.metrics} for r in results],
            challenge="timing",
            metrics=["accuracy", "precision", "recall", "f1"],
            output_path=tables_dir / "table_timing_detailed.tex",
        )

        print(f"  Figure saved to: {figures_dir / 'fig1_main_timing_comparison.pdf'}")

    return summary


def main():
    parser = argparse.ArgumentParser(description="Section 5.2.1: Timing Detection Experiment")
    parser.add_argument("--max-samples", type=int, default=150, help="Maximum samples to test")
    parser.add_argument("--skip-llm", action="store_true", help="Skip LLM-based methods")
    parser.add_argument("--verbose", action="store_true", default=True, help="Verbose output")
    args = parser.parse_args()

    summary = run_timing_experiment(
        max_samples=args.max_samples,
        skip_llm=args.skip_llm,
        verbose=args.verbose,
    )

    # 打印总结
    print("\n" + "=" * 70)
    print("📊 Summary")
    print("=" * 70)
    print(f"  Best strategy: {summary.best_strategy}")
    print(f"  Best accuracy: {summary.best_metric * 100:.1f}%" if summary.best_metric else "  N/A")
    print(f"  Target met: {'✅ YES' if summary.target_met else '❌ NO'}")


if __name__ == "__main__":
    main()
