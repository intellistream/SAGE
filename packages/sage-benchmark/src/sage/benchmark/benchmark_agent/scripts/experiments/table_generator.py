"""
Table Generator - LaTeX 表格生成模块

为 Paper 1 所有实验生成 LaTeX 格式的表格:
- Main Results 表
- Benchmark Details 表
- Ablation Study 表
- Training Comparison 表
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from .exp_utils import get_tables_dir

# =============================================================================
# LaTeX 表格生成
# =============================================================================


def generate_main_results_table(
    timing_results: list[dict],
    planning_results: list[dict],
    selection_results: list[dict],
    output_path: Optional[Path] = None,
) -> str:
    """
    生成主结果表 (Table 1)。

    Args:
        timing_results: Timing 实验结果
        planning_results: Planning 实验结果
        selection_results: Selection 实验结果
        output_path: 输出路径

    Returns:
        LaTeX 表格字符串
    """

    # 找各 challenge 最佳结果
    def get_best(results, metric):
        if not results:
            return None
        return max(results, key=lambda r: r.get("metrics", {}).get(metric, 0))

    timing_best = get_best(timing_results, "accuracy")
    planning_best = get_best(planning_results, "plan_success_rate")
    selection_best = get_best(selection_results, "top_k_accuracy")

    lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\caption{Main results on SAGE-AgentBench. Best performing strategy for each challenge.}",
        r"\label{tab:main}",
        r"\begin{tabular}{lccc}",
        r"\toprule",
        r"\textbf{Challenge} & \textbf{Strategy} & \textbf{Primary Metric} & \textbf{Target Met} \\",
        r"\midrule",
    ]

    if timing_best:
        acc = timing_best.get("metrics", {}).get("accuracy", 0) * 100
        strategy = timing_best.get("strategy", "").replace("timing.", "").replace("_", " ").title()
        passed = acc >= 95
        status = r"\cmark" if passed else r"\xmark"
        lines.append(f"Timing Detection & {strategy} & {acc:.1f}\\% & {status} \\\\")

    if planning_best:
        rate = planning_best.get("metrics", {}).get("plan_success_rate", 0) * 100
        strategy = (
            planning_best.get("strategy", "").replace("planner.", "").replace("_", " ").title()
        )
        passed = rate >= 90
        status = r"\cmark" if passed else r"\xmark"
        lines.append(f"Task Planning & {strategy} & {rate:.1f}\\% & {status} \\\\")

    if selection_best:
        acc = selection_best.get("metrics", {}).get("top_k_accuracy", 0) * 100
        strategy = (
            selection_best.get("strategy", "").replace("selector.", "").replace("_", " ").title()
        )
        passed = acc >= 95
        status = r"\cmark" if passed else r"\xmark"
        lines.append(f"Tool Selection & {strategy} & {acc:.1f}\\% & {status} \\\\")

    lines.extend(
        [
            r"\bottomrule",
            r"\end{tabular}",
            r"\end{table}",
        ]
    )

    content = "\n".join(lines)

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content)

    return content


def generate_benchmark_details_table(
    timing_results: list[dict],
    planning_results: list[dict],
    selection_results: list[dict],
    output_path: Optional[Path] = None,
) -> str:
    """
    生成详细 Benchmark 结果表 (Table 2)。

    显示所有策略在所有指标上的表现。
    """
    lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\caption{Detailed benchmark results across all strategies.}",
        r"\label{tab:benchmark}",
        r"\small",
        r"\begin{tabular}{llcccc}",
        r"\toprule",
        r"\textbf{Challenge} & \textbf{Strategy} & \textbf{Metric 1} & \textbf{Metric 2} & \textbf{Metric 3} & \textbf{Pass} \\",
        r"\midrule",
    ]

    # Timing results
    for r in timing_results or []:
        name = r.get("strategy", "").replace("timing.", "").replace("_", " ").title()
        metrics = r.get("metrics", {})
        acc = metrics.get("accuracy", 0) * 100
        prec = metrics.get("precision", 0) * 100
        rec = metrics.get("recall", 0) * 100
        passed = acc >= 95
        status = r"\cmark" if passed else r"\xmark"
        lines.append(
            f"Timing & {name} & Acc: {acc:.1f}\\% & Prec: {prec:.1f}\\% & Rec: {rec:.1f}\\% & {status} \\\\"
        )

    if timing_results:
        lines.append(r"\midrule")

    # Planning results
    for r in planning_results or []:
        name = r.get("strategy", "").replace("planner.", "").replace("_", " ").title()
        metrics = r.get("metrics", {})
        success = metrics.get("plan_success_rate", 0) * 100
        step = metrics.get("step_accuracy", 0) * 100
        seq = metrics.get("sequence_match", 0) * 100
        passed = success >= 90
        status = r"\cmark" if passed else r"\xmark"
        lines.append(
            f"Planning & {name} & Succ: {success:.1f}\\% & Step: {step:.1f}\\% & Seq: {seq:.1f}\\% & {status} \\\\"
        )

    if planning_results:
        lines.append(r"\midrule")

    # Tool selection results
    for r in selection_results or []:
        name = r.get("strategy", "").replace("selector.", "").replace("_", " ").title()
        metrics = r.get("metrics", {})
        top_k = metrics.get("top_k_accuracy", 0) * 100
        mrr = metrics.get("mrr", 0) * 100
        recall = metrics.get("recall_at_k", 0) * 100
        passed = top_k >= 95
        status = r"\cmark" if passed else r"\xmark"
        lines.append(
            f"Selection & {name} & Top-K: {top_k:.1f}\\% & MRR: {mrr:.1f}\\% & R@K: {recall:.1f}\\% & {status} \\\\"
        )

    lines.extend(
        [
            r"\bottomrule",
            r"\end{tabular}",
            r"\end{table}",
        ]
    )

    content = "\n".join(lines)

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content)

    return content


def generate_training_comparison_table(
    training_results: list[dict],
    output_path: Optional[Path] = None,
) -> str:
    """
    生成训练方法对比表 (Table 3)。
    """
    lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\caption{Training method comparison. Performance after fine-tuning on SAGE-AgentBench.}",
        r"\label{tab:training}",
        r"\small",
        r"\begin{tabular}{lcccc}",
        r"\toprule",
        r"\textbf{Method} & \textbf{Timing} & \textbf{Planning} & \textbf{Selection} & \textbf{Overall} \\",
        r"\midrule",
    ]

    for r in training_results or []:
        name = r.get("method_name", "").replace("_", " ")
        timing = r.get("timing_accuracy", 0) * 100
        planning = r.get("planning_success_rate", 0) * 100
        selection = r.get("selection_top_k_accuracy", 0) * 100
        overall = (timing + planning + selection) / 3
        lines.append(
            f"{name} & {timing:.1f}\\% & {planning:.1f}\\% & {selection:.1f}\\% & {overall:.1f}\\% \\\\"
        )

    lines.extend(
        [
            r"\bottomrule",
            r"\end{tabular}",
            r"\end{table}",
        ]
    )

    content = "\n".join(lines)

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content)

    return content


def generate_ablation_table(
    ablation_results: dict[str, dict[str, float]],
    title: str = "Ablation study results",
    label: str = "tab:ablation",
    output_path: Optional[Path] = None,
) -> str:
    """
    生成消融实验表。

    Args:
        ablation_results: {"config_name": {"metric1": 0.9, ...}, ...}
        title: 表格标题
        label: LaTeX 标签
        output_path: 输出路径
    """
    if not ablation_results:
        return ""

    configs = list(ablation_results.keys())
    metrics = list(next(iter(ablation_results.values())).keys())

    # 构建表格
    col_spec = "l" + "c" * len(metrics)
    header = (
        r"\textbf{Config} & "
        + " & ".join([f"\\textbf{{{m.replace('_', ' ').title()}}}" for m in metrics])
        + r" \\"
    )

    lines = [
        r"\begin{table}[t]",
        r"\centering",
        f"\\caption{{{title}}}",
        f"\\label{{{label}}}",
        r"\small",
        f"\\begin{{tabular}}{{{col_spec}}}",
        r"\toprule",
        header,
        r"\midrule",
    ]

    for config in configs:
        values = ablation_results[config]
        row = config.replace("_", " ")
        for metric in metrics:
            val = values.get(metric, 0)
            if isinstance(val, float):
                row += f" & {val * 100:.1f}\\%"
            else:
                row += f" & {val}"
        row += r" \\"
        lines.append(row)

    lines.extend(
        [
            r"\bottomrule",
            r"\end{tabular}",
            r"\end{table}",
        ]
    )

    content = "\n".join(lines)

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content)

    return content


def generate_cross_dataset_table(
    cross_dataset_results: dict[str, dict[str, float]],
    output_path: Optional[Path] = None,
) -> str:
    """
    生成跨数据集对比表。

    Args:
        cross_dataset_results: {"method": {"sage": 0.9, "acebench": 0.85, ...}, ...}
    """
    if not cross_dataset_results:
        return ""

    methods = list(cross_dataset_results.keys())
    datasets = list(next(iter(cross_dataset_results.values())).keys())

    col_spec = "l" + "c" * len(datasets)
    header = (
        r"\textbf{Method} & " + " & ".join([f"\\textbf{{{d.upper()}}}" for d in datasets]) + r" \\"
    )

    lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\caption{Cross-dataset generalization. Top-5 accuracy on different benchmarks.}",
        r"\label{tab:crossdataset}",
        r"\small",
        f"\\begin{{tabular}}{{{col_spec}}}",
        r"\toprule",
        header,
        r"\midrule",
    ]

    for method in methods:
        row = method.replace("_", " ").title()
        for dataset in datasets:
            val = cross_dataset_results[method].get(dataset, 0) * 100
            row += f" & {val:.1f}\\%"
        row += r" \\"
        lines.append(row)

    lines.extend(
        [
            r"\bottomrule",
            r"\end{tabular}",
            r"\end{table}",
        ]
    )

    content = "\n".join(lines)

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content)

    return content


# =============================================================================
# 批量生成
# =============================================================================


def generate_all_tables(
    all_results: dict[str, Any],
    output_dir: Optional[Path] = None,
) -> dict[str, Path]:
    """
    生成所有论文表格。

    Args:
        all_results: 包含所有实验结果的字典
        output_dir: 输出目录

    Returns:
        生成的表格文件路径字典
    """
    tables_dir = output_dir or get_tables_dir()
    tables_dir.mkdir(parents=True, exist_ok=True)

    generated = {}

    # Table 1: Main Results
    timing = all_results.get("timing", [])
    planning = all_results.get("planning", [])
    selection = all_results.get("selection", [])

    if timing or planning or selection:
        path = tables_dir / "table1_main_results.tex"
        generate_main_results_table(timing, planning, selection, path)
        generated["main_results"] = path
        print(f"  Generated: {path}")

    # Table 2: Benchmark Details
    if timing or planning or selection:
        path = tables_dir / "table2_benchmark_details.tex"
        generate_benchmark_details_table(timing, planning, selection, path)
        generated["benchmark_details"] = path
        print(f"  Generated: {path}")

    # Table 3: Training Comparison
    training = all_results.get("training", [])
    if training:
        path = tables_dir / "table3_training_comparison.tex"
        generate_training_comparison_table(training, path)
        generated["training_comparison"] = path
        print(f"  Generated: {path}")

    # Table 4: Ablation
    ablation = all_results.get("ablation", {})
    if ablation:
        path = tables_dir / "table4_ablation.tex"
        generate_ablation_table(ablation, output_path=path)
        generated["ablation"] = path
        print(f"  Generated: {path}")

    # Table 5: Cross-Dataset
    cross_dataset = all_results.get("cross_dataset", {})
    if cross_dataset:
        path = tables_dir / "table5_cross_dataset.tex"
        generate_cross_dataset_table(cross_dataset, path)
        generated["cross_dataset"] = path
        print(f"  Generated: {path}")

    return generated
