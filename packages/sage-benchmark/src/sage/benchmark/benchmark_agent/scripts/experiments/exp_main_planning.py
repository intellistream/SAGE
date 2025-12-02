#!/usr/bin/env python3
"""
Section 5.2.2: Task Planning Experiment (RQ2)

研究问题: 现有方法将复杂任务分解为执行步骤的能力如何?

测试方法:
- planner.simple       : 简单贪心匹配
- planner.hierarchical : 层次化分解 (HuggingGPT)
- planner.llm_based    : LLM 生成计划 (CoT Prompting)
- planner.react        : 交错执行 (ReAct)

目标指标:
- Primary: Plan Success Rate ≥ 90%
- Secondary: Step Accuracy, Tool Coverage
- Tertiary: Average Plan Length

Usage:
    python exp_main_planning.py
    python exp_main_planning.py --max-samples 100
    python exp_main_planning.py --skip-llm
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


def compute_step_accuracy(predicted_steps: list[str], reference_steps: list[str]) -> float:
    """计算步骤级别的准确率。"""
    if not reference_steps:
        return 1.0 if not predicted_steps else 0.0

    correct = sum(1 for p, r in zip(predicted_steps, reference_steps) if p == r)
    return correct / len(reference_steps)


def compute_tool_coverage(predicted_steps: list[str], reference_steps: list[str]) -> float:
    """计算工具覆盖率。"""
    if not reference_steps:
        return 1.0

    ref_set = set(reference_steps)
    pred_set = set(predicted_steps)
    return len(pred_set & ref_set) / len(ref_set)


def is_plan_success(
    predicted_steps: list[str], reference_steps: list[str], threshold: float = 0.8
) -> bool:
    """判断计划是否成功 (步骤准确率 >= threshold)。"""
    if not reference_steps:
        return not predicted_steps

    step_acc = compute_step_accuracy(predicted_steps, reference_steps)
    return step_acc >= threshold


def run_planning_experiment(
    max_samples: int = 100,
    skip_llm: bool = False,
    verbose: bool = True,
) -> ExperimentSummary:
    """
    运行 Task Planning 实验。

    Args:
        max_samples: 最大测试样本数
        skip_llm: 是否跳过 LLM-based 方法
        verbose: 是否打印详细信息

    Returns:
        ExperimentSummary 对象
    """
    setup_experiment_env(verbose=verbose)

    print_section_header("Section 5.2.2: Task Planning (RQ2)")
    print("   Target: Plan Success Rate ≥ 90%")
    print(f"   Max samples: {max_samples}")

    # 加载数据
    samples = load_benchmark_data("planning", split="test", max_samples=max_samples)
    if not samples:
        print("  ❌ No planning data available")
        return ExperimentSummary(section="5_2_main", challenge="planning")

    print(f"   Loaded {len(samples)} samples")

    # 获取策略注册表
    try:
        from sage.benchmark.benchmark_agent import get_adapter_registry

        registry = get_adapter_registry()
    except ImportError as e:
        print(f"  ❌ Failed to import adapter registry: {e}")
        return ExperimentSummary(section="5_2_main", challenge="planning")

    # 定义测试策略
    strategies = [
        ("planner.simple", "Simple"),
        ("planner.hierarchical", "Hierarchical"),
        ("planner.llm_based", "LLM-based"),
    ]

    # 跳过 LLM 策略
    LLM_STRATEGIES = {"planner.llm_based", "planner.react"}
    if skip_llm:
        strategies = [(name, display) for name, display in strategies if name not in LLM_STRATEGIES]
        print("  ⚠️  Skipping LLM-based strategies")

    results = []
    target = 0.90

    for strategy_name, display_name in strategies:
        print_subsection_header(f"Testing: {display_name}")

        try:
            planner = registry.get(strategy_name)
        except Exception as e:
            print(f"    ⚠️  Failed to create planner: {e}")
            continue

        # 运行评测
        start_time = time.time()
        success_count = 0
        step_accuracies = []
        tool_coverages = []
        plan_lengths = []

        with create_progress_bar(len(samples), desc=f"  {display_name}") as pbar:
            for sample in samples:
                try:
                    task_description = sample.get("task", sample.get("instruction", ""))
                    available_tools = sample.get("available_tools", sample.get("tools", []))
                    reference_plan = sample.get("ground_truth", sample.get("expected_plan", []))

                    # 标准化 reference
                    if isinstance(reference_plan, list) and reference_plan:
                        if isinstance(reference_plan[0], dict):
                            ref_steps = [
                                s.get("tool_id", s.get("tool", "")) for s in reference_plan
                            ]
                        else:
                            ref_steps = reference_plan
                    else:
                        ref_steps = []

                    # 调用规划器
                    plan_result = planner.plan(task_description, available_tools=available_tools)

                    # 提取预测步骤
                    if hasattr(plan_result, "tool_sequence"):
                        pred_steps = plan_result.tool_sequence
                    elif hasattr(plan_result, "steps"):
                        pred_steps = [
                            s.tool_id if hasattr(s, "tool_id") else str(s)
                            for s in plan_result.steps
                        ]
                    elif isinstance(plan_result, list):
                        pred_steps = [
                            s.get("tool_id", str(s)) if isinstance(s, dict) else str(s)
                            for s in plan_result
                        ]
                    else:
                        pred_steps = []

                    # 计算指标
                    if is_plan_success(pred_steps, ref_steps):
                        success_count += 1

                    step_acc = compute_step_accuracy(pred_steps, ref_steps)
                    tool_cov = compute_tool_coverage(pred_steps, ref_steps)

                    step_accuracies.append(step_acc)
                    tool_coverages.append(tool_cov)
                    plan_lengths.append(len(pred_steps))

                except Exception as e:
                    if verbose:
                        print(f"    Error: {e}")
                    step_accuracies.append(0.0)
                    tool_coverages.append(0.0)
                    plan_lengths.append(0)

                pbar.update(1)

        elapsed = time.time() - start_time

        # 计算汇总指标
        n = len(samples)
        success_rate = success_count / n if n > 0 else 0
        avg_step_acc = sum(step_accuracies) / n if n > 0 else 0
        avg_tool_cov = sum(tool_coverages) / n if n > 0 else 0
        avg_plan_len = sum(plan_lengths) / n if n > 0 else 0

        exp_result = ExperimentResult(
            challenge="planning",
            strategy=strategy_name,
            metrics={
                "plan_success_rate": success_rate,
                "step_accuracy": avg_step_acc,
                "tool_coverage": avg_tool_cov,
            },
            metadata={
                "total_samples": n,
                "success_count": success_count,
                "avg_plan_length": avg_plan_len,
                "latency_ms": elapsed * 1000 / n if n > 0 else 0,
            },
            passed=success_rate >= target,
            target=target,
        )
        results.append(exp_result)

        # 打印结果
        print_result_row(
            display_name, {"plan_success_rate": success_rate}, exp_result.passed, target
        )
        if verbose:
            print_metrics_detail(exp_result.metrics)

    # 找出最佳策略
    best_result = max(results, key=lambda r: r.metrics["plan_success_rate"]) if results else None

    summary = ExperimentSummary(
        section="5_2_main",
        challenge="planning",
        results=results,
        best_strategy=best_result.strategy if best_result else None,
        best_metric=best_result.metrics["plan_success_rate"] if best_result else None,
        target_met=any(r.passed for r in results),
    )

    # 保存结果
    output_file = save_results(summary.to_dict(), "5_2_main", "planning")
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
            challenge="planning",
            metrics=["plan_success_rate", "step_accuracy", "tool_coverage"],
            target=target,
            output_path=figures_dir / "fig2_main_planning_comparison.pdf",
            title="Task Planning: Strategy Comparison",
        )

        # 生成表格
        generate_detailed_table(
            [{"strategy": r.strategy.split(".")[-1], "metrics": r.metrics} for r in results],
            challenge="planning",
            metrics=["plan_success_rate", "step_accuracy", "tool_coverage"],
            output_path=tables_dir / "table_planning_detailed.tex",
        )

        print(f"  Figure saved to: {figures_dir / 'fig2_main_planning_comparison.pdf'}")

    return summary


def main():
    parser = argparse.ArgumentParser(description="Section 5.2.2: Task Planning Experiment")
    parser.add_argument("--max-samples", type=int, default=100, help="Maximum samples to test")
    parser.add_argument("--skip-llm", action="store_true", help="Skip LLM-based methods")
    parser.add_argument("--verbose", action="store_true", default=True, help="Verbose output")
    args = parser.parse_args()

    summary = run_planning_experiment(
        max_samples=args.max_samples,
        skip_llm=args.skip_llm,
        verbose=args.verbose,
    )

    # 打印总结
    print("\n" + "=" * 70)
    print("📊 Summary")
    print("=" * 70)
    print(f"  Best strategy: {summary.best_strategy}")
    print(
        f"  Best success rate: {summary.best_metric * 100:.1f}%" if summary.best_metric else "  N/A"
    )
    print(f"  Target met: {'✅ YES' if summary.target_met else '❌ NO'}")


if __name__ == "__main__":
    main()
