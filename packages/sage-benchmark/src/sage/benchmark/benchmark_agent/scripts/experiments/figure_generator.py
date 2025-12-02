"""
Figure Generator - 统一图表生成模块

为 Paper 1 所有实验生成一致风格的图表:
- 使用学术论文标准样式
- 支持 PDF + PNG 双格式输出
- 颜色方案对色盲友好
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import numpy as np

# =============================================================================
# 图表样式配置
# =============================================================================

# Matplotlib 样式设置
FIGURE_STYLE = {
    "font.family": "serif",
    "font.serif": ["Times New Roman", "DejaVu Serif"],
    "font.size": 10,
    "axes.titlesize": 12,
    "axes.labelsize": 10,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "legend.fontsize": 9,
    "figure.figsize": (8, 6),
    "figure.dpi": 100,
    "savefig.dpi": 300,
    "savefig.format": "pdf",
    "savefig.bbox": "tight",
    "axes.grid": True,
    "grid.alpha": 0.3,
}

# 颜色方案 (colorblind-friendly, based on ColorBrewer)
COLORS = {
    # 主色调
    "primary": "#1f77b4",  # 蓝色
    "secondary": "#ff7f0e",  # 橙色
    "tertiary": "#2ca02c",  # 绿色
    "quaternary": "#d62728",  # 红色
    "quinary": "#9467bd",  # 紫色
    # 语义色
    "success": "#2ca02c",
    "warning": "#ff7f0e",
    "danger": "#d62728",
    "info": "#1f77b4",
    # 特殊用途
    "target_line": "#7f7f7f",  # 灰色目标线
    "baseline": "#bcbd22",  # 黄绿色 baseline
    "best": "#17becf",  # 青色最佳
}

# 策略颜色映射
STRATEGY_COLORS = {
    # Timing
    "rule_based": COLORS["primary"],
    "llm_based": COLORS["secondary"],
    "hybrid": COLORS["tertiary"],
    "embedding": COLORS["quaternary"],
    # Planning
    "simple": COLORS["primary"],
    "hierarchical": COLORS["secondary"],
    "react": COLORS["quaternary"],
    # Selection
    "keyword": COLORS["primary"],
    "gorilla": COLORS["quaternary"],
    "dfsdt": COLORS["quinary"],
}

# 图表尺寸预设
FIGURE_SIZES = {
    "single": (6, 4),  # 单列
    "double": (10, 4),  # 双列
    "wide": (12, 4),  # 宽幅
    "square": (6, 6),  # 方形
    "tall": (6, 8),  # 高图
}


# =============================================================================
# 图表生成函数
# =============================================================================


def setup_matplotlib():
    """设置 matplotlib 样式。"""
    try:
        import matplotlib.pyplot as plt

        plt.rcParams.update(FIGURE_STYLE)
        return plt
    except ImportError:
        print("  Warning: matplotlib not available")
        return None


def plot_challenge_comparison(
    results: list[dict],
    challenge: str,
    metrics: list[str],
    target: float,
    output_path: Optional[Path] = None,
    title: Optional[str] = None,
) -> Any:
    """
    绘制单个 Challenge 的策略对比图。

    Args:
        results: [{"strategy": str, "metrics": {"accuracy": 0.9, ...}}, ...]
        challenge: 挑战名称
        metrics: 要展示的指标列表
        target: 目标线
        output_path: 输出路径
        title: 图表标题

    Returns:
        matplotlib Figure 对象
    """
    plt = setup_matplotlib()
    if plt is None:
        return None

    fig, ax = plt.subplots(figsize=FIGURE_SIZES["single"])

    strategies = [r["strategy"] for r in results]
    x = np.arange(len(strategies))
    width = 0.8 / len(metrics)

    # 绘制每个指标的柱状图
    for i, metric in enumerate(metrics):
        values = [r["metrics"].get(metric, 0) * 100 for r in results]
        offset = (i - len(metrics) / 2 + 0.5) * width
        bars = ax.bar(x + offset, values, width, label=metric.replace("_", " ").title())

        # 在柱子上标注数值
        for bar, val in zip(bars, values):
            height = bar.get_height()
            ax.annotate(
                f"{val:.1f}",
                xy=(bar.get_x() + bar.get_width() / 2, height),
                xytext=(0, 3),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=8,
            )

    # 目标线
    ax.axhline(
        y=target * 100,
        color=COLORS["target_line"],
        linestyle="--",
        linewidth=2,
        label=f"Target ({target * 100:.0f}%)",
    )

    # 设置
    ax.set_xlabel("Strategy")
    ax.set_ylabel("Score (%)")
    ax.set_title(title or f"{challenge.title()} Challenge: Strategy Comparison")
    ax.set_xticks(x)
    ax.set_xticklabels([s.replace("_", " ").title() for s in strategies], rotation=15, ha="right")
    ax.set_ylim(0, 105)
    ax.legend(loc="upper right")

    plt.tight_layout()

    # 保存
    if output_path:
        fig.savefig(output_path, format="pdf", bbox_inches="tight")
        # 同时保存 PNG
        png_path = output_path.with_suffix(".png")
        fig.savefig(png_path, format="png", dpi=300, bbox_inches="tight")

    return fig


def plot_scaling_curve(
    results: dict[str, list[tuple[float, float]]],
    x_label: str,
    y_label: str,
    title: str,
    output_path: Optional[Path] = None,
    log_x: bool = False,
) -> Any:
    """
    绘制 Scaling 曲线图。

    Args:
        results: {"strategy_name": [(x1, y1), (x2, y2), ...], ...}
        x_label: X轴标签
        y_label: Y轴标签
        title: 标题
        output_path: 输出路径
        log_x: X轴是否使用对数刻度

    Returns:
        matplotlib Figure 对象
    """
    plt = setup_matplotlib()
    if plt is None:
        return None

    fig, ax = plt.subplots(figsize=FIGURE_SIZES["single"])

    for strategy, points in results.items():
        x_vals = [p[0] for p in points]
        y_vals = [p[1] * 100 for p in points]  # 转换为百分比
        color = STRATEGY_COLORS.get(strategy, COLORS["primary"])
        ax.plot(
            x_vals,
            y_vals,
            "o-",
            label=strategy.replace("_", " ").title(),
            color=color,
            linewidth=2,
            markersize=6,
        )

    if log_x:
        ax.set_xscale("log")

    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    ax.set_title(title)
    ax.legend(loc="best")
    ax.grid(True, alpha=0.3)

    plt.tight_layout()

    if output_path:
        fig.savefig(output_path, format="pdf", bbox_inches="tight")
        png_path = output_path.with_suffix(".png")
        fig.savefig(png_path, format="png", dpi=300, bbox_inches="tight")

    return fig


def plot_error_breakdown(
    errors: dict[str, dict[str, int]],
    challenge: str,
    output_path: Optional[Path] = None,
) -> Any:
    """
    绘制错误类型分解图。

    Args:
        errors: {"strategy": {"error_type": count, ...}, ...}
        challenge: 挑战名称
        output_path: 输出路径

    Returns:
        matplotlib Figure 对象
    """
    plt = setup_matplotlib()
    if plt is None:
        return None

    fig, axes = plt.subplots(1, len(errors), figsize=(4 * len(errors), 4))
    if len(errors) == 1:
        axes = [axes]

    colors = list(COLORS.values())[:6]

    for ax, (strategy, error_counts) in zip(axes, errors.items()):
        labels = list(error_counts.keys())
        sizes = list(error_counts.values())

        if sum(sizes) > 0:
            ax.pie(sizes, labels=labels, autopct="%1.1f%%", colors=colors[: len(labels)])
        else:
            ax.text(0.5, 0.5, "No Errors", ha="center", va="center")

        ax.set_title(strategy.replace("_", " ").title())

    fig.suptitle(f"{challenge.title()} Challenge: Error Breakdown")
    plt.tight_layout()

    if output_path:
        fig.savefig(output_path, format="pdf", bbox_inches="tight")
        png_path = output_path.with_suffix(".png")
        fig.savefig(png_path, format="png", dpi=300, bbox_inches="tight")

    return fig


def plot_ablation_heatmap(
    ablation_results: dict[str, dict[str, float]],
    title: str,
    output_path: Optional[Path] = None,
) -> Any:
    """
    绘制消融实验热力图。

    Args:
        ablation_results: {"config_name": {"metric1": 0.9, "metric2": 0.8}, ...}
        title: 标题
        output_path: 输出路径

    Returns:
        matplotlib Figure 对象
    """
    plt = setup_matplotlib()
    if plt is None:
        return None

    configs = list(ablation_results.keys())
    metrics = list(next(iter(ablation_results.values())).keys())

    data = np.array([[ablation_results[c][m] * 100 for m in metrics] for c in configs])

    fig, ax = plt.subplots(figsize=FIGURE_SIZES["square"])

    im = ax.imshow(data, cmap="RdYlGn", aspect="auto", vmin=0, vmax=100)

    # 设置标签
    ax.set_xticks(np.arange(len(metrics)))
    ax.set_yticks(np.arange(len(configs)))
    ax.set_xticklabels([m.replace("_", " ").title() for m in metrics])
    ax.set_yticklabels([c.replace("_", " ").title() for c in configs])

    # 旋转 x 标签
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")

    # 添加数值标注
    for i in range(len(configs)):
        for j in range(len(metrics)):
            ax.text(j, i, f"{data[i, j]:.1f}", ha="center", va="center", color="black", fontsize=9)

    ax.set_title(title)
    fig.colorbar(im, ax=ax, label="Score (%)")

    plt.tight_layout()

    if output_path:
        fig.savefig(output_path, format="pdf", bbox_inches="tight")
        png_path = output_path.with_suffix(".png")
        fig.savefig(png_path, format="png", dpi=300, bbox_inches="tight")

    return fig


def plot_cross_dataset_comparison(
    results: dict[str, dict[str, float]],
    metric: str,
    output_path: Optional[Path] = None,
) -> Any:
    """
    绘制跨数据集对比图。

    Args:
        results: {"strategy": {"dataset1": 0.9, "dataset2": 0.8}, ...}
        metric: 指标名称
        output_path: 输出路径

    Returns:
        matplotlib Figure 对象
    """
    plt = setup_matplotlib()
    if plt is None:
        return None

    strategies = list(results.keys())
    datasets = list(next(iter(results.values())).keys())

    x = np.arange(len(datasets))
    width = 0.8 / len(strategies)

    fig, ax = plt.subplots(figsize=FIGURE_SIZES["wide"])

    for i, strategy in enumerate(strategies):
        values = [results[strategy].get(d, 0) * 100 for d in datasets]
        offset = (i - len(strategies) / 2 + 0.5) * width
        color = STRATEGY_COLORS.get(strategy.split(".")[-1], COLORS["primary"])
        ax.bar(x + offset, values, width, label=strategy.replace("_", " ").title(), color=color)

    ax.set_xlabel("Dataset")
    ax.set_ylabel(f"{metric.replace('_', ' ').title()} (%)")
    ax.set_title(f"Cross-Dataset Comparison: {metric.replace('_', ' ').title()}")
    ax.set_xticks(x)
    ax.set_xticklabels(datasets)
    ax.legend(loc="upper right", ncol=2)
    ax.set_ylim(0, 105)

    plt.tight_layout()

    if output_path:
        fig.savefig(output_path, format="pdf", bbox_inches="tight")
        png_path = output_path.with_suffix(".png")
        fig.savefig(png_path, format="png", dpi=300, bbox_inches="tight")

    return fig


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
    生成主结果 LaTeX 表格。

    Returns:
        LaTeX 表格字符串
    """
    latex = r"""
\begin{table}[t]
\centering
\caption{Main Results across Three Challenges}
\label{tab:main_results}
\begin{tabular}{llccc}
\toprule
\textbf{Challenge} & \textbf{Strategy} & \textbf{Primary} & \textbf{Secondary} & \textbf{Target Met} \\
\midrule
"""

    # Timing 结果
    for r in timing_results:
        acc = r["metrics"].get("accuracy", 0) * 100
        prec = r["metrics"].get("precision", 0) * 100
        passed = "\\cmark" if r.get("passed", False) else "\\xmark"
        latex += f"Timing & {r['strategy']} & {acc:.1f}\\% & {prec:.1f}\\% & {passed} \\\\\n"

    latex += r"\midrule" + "\n"

    # Planning 结果
    for r in planning_results:
        success = r["metrics"].get("plan_success_rate", 0) * 100
        step_acc = r["metrics"].get("step_accuracy", 0) * 100
        passed = "\\cmark" if r.get("passed", False) else "\\xmark"
        latex += (
            f"Planning & {r['strategy']} & {success:.1f}\\% & {step_acc:.1f}\\% & {passed} \\\\\n"
        )

    latex += r"\midrule" + "\n"

    # Selection 结果
    for r in selection_results:
        topk = r["metrics"].get("top_k_accuracy", 0) * 100
        mrr = r["metrics"].get("mrr", 0) * 100
        passed = "\\cmark" if r.get("passed", False) else "\\xmark"
        latex += f"Selection & {r['strategy']} & {topk:.1f}\\% & {mrr:.1f}\\% & {passed} \\\\\n"

    latex += r"""
\bottomrule
\end{tabular}
\end{table}
"""

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(latex)

    return latex


def generate_detailed_table(
    results: list[dict],
    challenge: str,
    metrics: list[str],
    output_path: Optional[Path] = None,
) -> str:
    """
    生成详细结果 LaTeX 表格。

    Returns:
        LaTeX 表格字符串
    """
    metric_headers = " & ".join([f"\\textbf{{{m.replace('_', ' ').title()}}}" for m in metrics])

    latex = f"""
\\begin{{table}}[t]
\\centering
\\caption{{{challenge.title()} Challenge: Detailed Results}}
\\label{{tab:{challenge}_detailed}}
\\begin{{tabular}}{{l{"c" * len(metrics)}}}
\\toprule
\\textbf{{Strategy}} & {metric_headers} \\\\
\\midrule
"""

    for r in results:
        values = " & ".join([f"{r['metrics'].get(m, 0) * 100:.1f}\\%" for m in metrics])
        latex += f"{r['strategy']} & {values} \\\\\n"

    latex += r"""
\bottomrule
\end{tabular}
\end{table}
"""

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(latex)

    return latex


# =============================================================================
# 批量生成
# =============================================================================


def generate_all_figures(
    results_dir: Optional[Path] = None,
    output_dir: Optional[Path] = None,
) -> dict[str, Path]:
    """
    从结果目录生成所有图表。

    Args:
        results_dir: 结果目录 (默认 .sage/benchmark/paper1/)
        output_dir: 输出目录 (默认 results_dir/figures/)

    Returns:
        {figure_name: output_path}
    """
    import json

    from .exp_utils import DEFAULT_OUTPUT_DIR, get_figures_dir

    results_dir = results_dir or DEFAULT_OUTPUT_DIR
    output_dir = output_dir or get_figures_dir()

    print(f"\n  Generating figures from: {results_dir}")
    print(f"  Output directory: {output_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)
    generated = {}

    # 加载结果文件
    def load_json(path):
        if path.exists():
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        return None

    # Figure 1: Main Results Comparison
    section_5_2 = results_dir / "section_5_2_main"
    timing = load_json(section_5_2 / "timing_results.json")
    planning = load_json(section_5_2 / "planning_results.json")
    selection = load_json(section_5_2 / "selection_results.json")

    if timing:
        results = timing.get("results", [])
        if results:
            path = output_dir / "fig1_timing_comparison.pdf"
            plot_challenge_comparison(
                results=[r.get("metrics", {}) for r in results],
                labels=[r.get("strategy", "") for r in results],
                metric="accuracy",
                title="RQ1: Timing Detection",
                target=0.95,
                output_path=path,
            )
            generated["timing_comparison"] = path
            print(f"    Generated: {path.name}")

    if planning:
        results = planning.get("results", [])
        if results:
            path = output_dir / "fig2_planning_comparison.pdf"
            plot_challenge_comparison(
                results=[r.get("metrics", {}) for r in results],
                labels=[r.get("strategy", "") for r in results],
                metric="plan_success_rate",
                title="RQ2: Task Planning",
                target=0.90,
                output_path=path,
            )
            generated["planning_comparison"] = path
            print(f"    Generated: {path.name}")

    if selection:
        results = selection.get("results", [])
        if results:
            path = output_dir / "fig3_selection_comparison.pdf"
            plot_challenge_comparison(
                results=[r.get("metrics", {}) for r in results],
                labels=[r.get("strategy", "") for r in results],
                metric="top_k_accuracy",
                title="RQ3: Tool Selection",
                target=0.95,
                output_path=path,
            )
            generated["selection_comparison"] = path
            print(f"    Generated: {path.name}")

    # Figure 4: Error Breakdown
    section_5_3 = results_dir / "section_5_3_analysis"
    error_data = load_json(section_5_3 / "error_analysis.json")
    if error_data:
        path = output_dir / "fig4_error_breakdown.pdf"
        plot_error_breakdown(error_data, output_path=path)
        generated["error_breakdown"] = path
        print(f"    Generated: {path.name}")

    # Figure 5: Scaling Analysis
    scaling_data = load_json(section_5_3 / "scaling_analysis.json")
    if scaling_data and "tool_scaling" in scaling_data:
        path = output_dir / "fig5_tool_scaling.pdf"
        plot_scaling_curve(
            data=scaling_data["tool_scaling"],
            x_label="Number of Tools",
            y_label="Top-K Accuracy",
            title="Tool Set Size Scaling",
            output_path=path,
        )
        generated["tool_scaling"] = path
        print(f"    Generated: {path.name}")

    # Figure 6: Ablation Heatmap
    ablation_data = load_json(section_5_3 / "ablation_results.json")
    if ablation_data:
        path = output_dir / "fig6_ablation_heatmap.pdf"
        plot_ablation_heatmap(ablation_data, output_path=path)
        generated["ablation_heatmap"] = path
        print(f"    Generated: {path.name}")

    # Figure 7: Cross-Dataset
    section_5_4 = results_dir / "section_5_4_generalization"
    cross_data = load_json(section_5_4 / "cross_dataset_results.json")
    if cross_data:
        path = output_dir / "fig7_cross_dataset.pdf"
        plot_cross_dataset_comparison(cross_data, output_path=path)
        generated["cross_dataset"] = path
        print(f"    Generated: {path.name}")

    print(f"\n  Total figures generated: {len(generated)}")
    return generated
