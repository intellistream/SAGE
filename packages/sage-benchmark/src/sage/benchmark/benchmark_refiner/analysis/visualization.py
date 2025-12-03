"""
可视化工具
=========

提供 Refiner 算法评测结果的可视化功能:
- 注意力头分析 (MNR 曲线)
- 算法性能对比柱状图
- Pareto 前沿图 (F1 vs Compression)
- 延迟分解堆叠图
- 跨数据集热力图
- 多维度雷达图
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from sage.benchmark.benchmark_refiner.experiments.base_experiment import (
        AlgorithmMetrics,
    )

# ============================================================================
# 配色方案 (统一的颜色配置)
# ============================================================================

# 算法配色映射
ALGORITHM_COLORS: dict[str, str] = {
    "baseline": "#7f7f7f",  # 灰色
    "longrefiner": "#1f77b4",  # 蓝色
    "reform": "#ff7f0e",  # 橙色
    "provence": "#2ca02c",  # 绿色
    "longllmlingua": "#d62728",  # 红色
    "llmlingua2": "#9467bd",  # 紫色
}

# 算法标记映射 (用于散点图)
ALGORITHM_MARKERS: dict[str, str] = {
    "baseline": "o",
    "longrefiner": "s",
    "reform": "^",
    "provence": "D",
    "longllmlingua": "v",
    "llmlingua2": "p",
}

# 默认配色（用于未知算法）
DEFAULT_COLORS = plt.cm.tab10.colors  # type: ignore[attr-defined]


def _get_algorithm_color(algorithm: str, idx: int = 0) -> str:
    """获取算法对应的颜色"""
    if algorithm.lower() in ALGORITHM_COLORS:
        return ALGORITHM_COLORS[algorithm.lower()]
    return DEFAULT_COLORS[idx % len(DEFAULT_COLORS)]  # type: ignore[return-value]


def _get_algorithm_marker(algorithm: str) -> str:
    """获取算法对应的标记"""
    return ALGORITHM_MARKERS.get(algorithm.lower(), "o")


# ============================================================================
# 注意力头分析可视化
# ============================================================================


def plot_mnr_curve(
    results_df: pd.DataFrame,
    output_path: str | Path,
    dataset_name: str = "dataset",
    top_k: int = 30,
) -> None:
    """绘制 MNR 曲线（Top-K 头的 MNR 分数）

    Args:
        results_df: 结果 DataFrame (columns: layer, head, head_type, mnr, mnr_std)
        output_path: 保存路径
        dataset_name: 数据集名称
        top_k: 显示前 k 个头
    """
    # 按 MNR 排序并取 top-k
    top_heads = results_df.nsmallest(top_k, "mnr")

    # 创建标签
    labels = [
        f"{row['head_type']}-L{int(row['layer'])}H{int(row['head'])}"
        for _, row in top_heads.iterrows()
    ]
    mnr_scores = top_heads["mnr"].values
    mnr_stds = top_heads["mnr_std"].values

    # 绘图
    plt.figure(figsize=(14, 8))

    # 主曲线
    x = range(len(labels))
    plt.plot(x, mnr_scores, "o-", linewidth=2, markersize=8, label="MNR Score")
    plt.fill_between(x, mnr_scores - mnr_stds, mnr_scores + mnr_stds, alpha=0.2, label="±1 std")

    # 设置
    plt.xticks(x, labels, rotation=45, ha="right")
    plt.xlabel("Attention Head (Type-Layer-Head)", fontsize=12)
    plt.ylabel("Mean Normalized Rank (MNR)", fontsize=12)
    plt.title(
        f"Top-{top_k} Attention Heads by Retrieval Performance ({dataset_name.upper()})",
        fontsize=14,
    )
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()

    # 保存
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()

    print(f"Saved MNR curve to {output_path}")


# ============================================================================
# 算法对比可视化
# ============================================================================


def plot_algorithm_comparison(
    results: dict[str, AlgorithmMetrics],
    metric: str = "f1",
    output_path: str | Path | None = None,
    title: str | None = None,
    figsize: tuple[float, float] = (10, 6),
) -> plt.Figure:
    """
    绘制多算法在单一指标上的对比柱状图

    Args:
        results: 算法名到 AlgorithmMetrics 的映射
        metric: 要展示的指标，可选 "f1", "compression_rate", "total_time", "refine_time"
        output_path: 保存路径（可选）
        title: 图表标题（可选）
        figsize: 图表大小

    Returns:
        matplotlib Figure 对象
    """
    # 指标映射
    metric_map = {
        "f1": ("avg_f1", "std_f1", "F1 Score", True),
        "compression_rate": (
            "avg_compression_rate",
            "std_compression_rate",
            "Compression Rate",
            True,
        ),
        "total_time": ("avg_total_time", "std_total_time", "Total Latency (s)", False),
        "refine_time": ("avg_refine_time", None, "Refine Latency (s)", False),
        "retrieve_time": ("avg_retrieve_time", None, "Retrieve Latency (s)", False),
        "generate_time": ("avg_generate_time", None, "Generate Latency (s)", False),
    }

    if metric not in metric_map:
        raise ValueError(f"Unknown metric: {metric}. Available: {list(metric_map.keys())}")

    avg_attr, std_attr, ylabel, higher_is_better = metric_map[metric]

    # 提取数据
    algorithms = list(results.keys())
    values = [getattr(results[algo], avg_attr, 0.0) for algo in algorithms]
    errors = []
    if std_attr:
        errors = [getattr(results[algo], std_attr, 0.0) for algo in algorithms]

    # 找出最佳值
    if higher_is_better:
        best_idx = np.argmax(values)
    else:
        best_idx = np.argmin([v if v > 0 else float("inf") for v in values])

    # 创建图表
    fig, ax = plt.subplots(figsize=figsize)

    x = np.arange(len(algorithms))
    colors = [_get_algorithm_color(algo, i) for i, algo in enumerate(algorithms)]

    # 绘制柱状图
    if errors:
        bars = ax.bar(
            x, values, yerr=errors, capsize=5, color=colors, edgecolor="black", linewidth=1
        )
    else:
        bars = ax.bar(x, values, color=colors, edgecolor="black", linewidth=1)

    # 高亮最佳值
    bars[best_idx].set_edgecolor("gold")
    bars[best_idx].set_linewidth(3)

    # 在柱状图上标注数值
    for i, (bar, val) in enumerate(zip(bars, values)):
        height = bar.get_height()
        label = f"{val:.3f}" if metric == "f1" else f"{val:.2f}"
        if i == best_idx:
            label = f"**{label}**"
        ax.annotate(
            label,
            xy=(bar.get_x() + bar.get_width() / 2, height),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=10,
            fontweight="bold" if i == best_idx else "normal",
        )

    # 设置标签
    ax.set_xticks(x)
    ax.set_xticklabels(algorithms, rotation=45, ha="right")
    ax.set_ylabel(ylabel, fontsize=12)
    ax.set_xlabel("Algorithm", fontsize=12)

    if title:
        ax.set_title(title, fontsize=14)
    else:
        ax.set_title(f"Algorithm Comparison - {ylabel}", fontsize=14)

    ax.grid(True, alpha=0.3, axis="y")
    ax.set_axisbelow(True)

    plt.tight_layout()

    # 保存
    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        print(f"Saved algorithm comparison to {output_path}")

    return fig


def plot_pareto_frontier(
    results: dict[str, AlgorithmMetrics],
    x_metric: str = "compression_rate",
    y_metric: str = "f1",
    output_path: str | Path | None = None,
    title: str | None = None,
    figsize: tuple[float, float] = (10, 8),
) -> plt.Figure:
    """
    绘制 F1 vs Compression 的 Pareto 前沿图

    Args:
        results: 算法名到 AlgorithmMetrics 的映射
        x_metric: X 轴指标 (默认 compression_rate)
        y_metric: Y 轴指标 (默认 f1)
        output_path: 保存路径（可选）
        title: 图表标题（可选）
        figsize: 图表大小

    Returns:
        matplotlib Figure 对象
    """
    # 提取数据
    algorithms = list(results.keys())
    x_values = [getattr(results[algo], f"avg_{x_metric}", 0.0) for algo in algorithms]
    y_values = [getattr(results[algo], f"avg_{y_metric}", 0.0) for algo in algorithms]

    # 计算 Pareto 前沿点
    # 对于 F1 vs Compression，两者都是越大越好
    pareto_indices = _compute_pareto_frontier(x_values, y_values, maximize_x=True, maximize_y=True)

    # 创建图表
    fig, ax = plt.subplots(figsize=figsize)

    # 绘制所有点
    for i, algo in enumerate(algorithms):
        color = _get_algorithm_color(algo, i)
        marker = _get_algorithm_marker(algo)
        is_pareto = i in pareto_indices

        ax.scatter(
            x_values[i],
            y_values[i],
            c=color,
            marker=marker,
            s=200 if is_pareto else 150,
            edgecolors="gold" if is_pareto else "black",
            linewidths=3 if is_pareto else 1,
            label=f"{algo} {'(Pareto)' if is_pareto else ''}",
            zorder=10 if is_pareto else 5,
        )

        # 标注算法名
        ax.annotate(
            algo,
            (x_values[i], y_values[i]),
            xytext=(5, 5),
            textcoords="offset points",
            fontsize=10,
            fontweight="bold" if is_pareto else "normal",
        )

    # 绘制 Pareto 前沿线
    if len(pareto_indices) > 1:
        pareto_x = [x_values[i] for i in sorted(pareto_indices, key=lambda i: x_values[i])]
        pareto_y = [
            y_values[pareto_indices[sorted(pareto_indices, key=lambda i: x_values[i]).index(i)]]
            for i in sorted(pareto_indices, key=lambda i: x_values[i])
        ]
        # 重新按 x 排序
        sorted_indices = sorted(pareto_indices, key=lambda i: x_values[i])
        pareto_x = [x_values[i] for i in sorted_indices]
        pareto_y = [y_values[i] for i in sorted_indices]
        ax.plot(pareto_x, pareto_y, "g--", linewidth=2, alpha=0.7, label="Pareto Frontier")

    # 设置标签
    x_label_map = {
        "compression_rate": "Compression Rate (higher is better)",
        "total_time": "Total Latency (s) (lower is better)",
    }
    y_label_map = {
        "f1": "F1 Score (higher is better)",
        "compression_rate": "Compression Rate (higher is better)",
    }

    ax.set_xlabel(x_label_map.get(x_metric, x_metric), fontsize=12)
    ax.set_ylabel(y_label_map.get(y_metric, y_metric), fontsize=12)

    if title:
        ax.set_title(title, fontsize=14)
    else:
        ax.set_title(
            f"Pareto Frontier: {y_metric.upper()} vs {x_metric.replace('_', ' ').title()}",
            fontsize=14,
        )

    ax.legend(loc="best", fontsize=10)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()

    # 保存
    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        print(f"Saved Pareto frontier to {output_path}")

    return fig


def _compute_pareto_frontier(
    x_values: list[float],
    y_values: list[float],
    maximize_x: bool = True,
    maximize_y: bool = True,
) -> list[int]:
    """
    计算 Pareto 前沿点的索引

    Args:
        x_values: X 轴值列表
        y_values: Y 轴值列表
        maximize_x: X 轴是否越大越好
        maximize_y: Y 轴是否越大越好

    Returns:
        Pareto 最优点的索引列表
    """
    n = len(x_values)
    pareto_indices = []

    for i in range(n):
        is_dominated = False
        for j in range(n):
            if i == j:
                continue

            # 检查 j 是否支配 i
            x_better = (x_values[j] > x_values[i]) if maximize_x else (x_values[j] < x_values[i])
            y_better = (y_values[j] > y_values[i]) if maximize_y else (y_values[j] < y_values[i])
            x_not_worse = (
                (x_values[j] >= x_values[i]) if maximize_x else (x_values[j] <= x_values[i])
            )
            y_not_worse = (
                (y_values[j] >= y_values[i]) if maximize_y else (y_values[j] <= y_values[i])
            )

            if x_not_worse and y_not_worse and (x_better or y_better):
                is_dominated = True
                break

        if not is_dominated:
            pareto_indices.append(i)

    return pareto_indices


def plot_latency_breakdown(
    results: dict[str, AlgorithmMetrics],
    output_path: str | Path | None = None,
    title: str | None = None,
    figsize: tuple[float, float] = (12, 6),
) -> plt.Figure:
    """
    绘制各算法的延迟分解堆叠图

    Args:
        results: 算法名到 AlgorithmMetrics 的映射
        output_path: 保存路径（可选）
        title: 图表标题（可选）
        figsize: 图表大小

    Returns:
        matplotlib Figure 对象
    """
    algorithms = list(results.keys())

    # 提取延迟数据
    retrieve_times = [results[algo].avg_retrieve_time for algo in algorithms]
    refine_times = [results[algo].avg_refine_time for algo in algorithms]
    generate_times = [results[algo].avg_generate_time for algo in algorithms]

    # 创建图表
    fig, ax = plt.subplots(figsize=figsize)

    x = np.arange(len(algorithms))
    width = 0.6

    # 堆叠柱状图
    ax.bar(x, retrieve_times, width, label="Retrieve", color="#1f77b4", edgecolor="black")
    ax.bar(
        x,
        refine_times,
        width,
        bottom=retrieve_times,
        label="Refine",
        color="#ff7f0e",
        edgecolor="black",
    )
    bars3 = ax.bar(
        x,
        generate_times,
        width,
        bottom=np.array(retrieve_times) + np.array(refine_times),
        label="Generate",
        color="#2ca02c",
        edgecolor="black",
    )

    # 计算总延迟并标注
    total_times = np.array(retrieve_times) + np.array(refine_times) + np.array(generate_times)
    for i, (bar, total) in enumerate(zip(bars3, total_times)):
        ax.annotate(
            f"{total:.2f}s",
            xy=(bar.get_x() + bar.get_width() / 2, total),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=10,
            fontweight="bold",
        )

    # 设置标签
    ax.set_xticks(x)
    ax.set_xticklabels(algorithms, rotation=45, ha="right")
    ax.set_ylabel("Latency (seconds)", fontsize=12)
    ax.set_xlabel("Algorithm", fontsize=12)

    if title:
        ax.set_title(title, fontsize=14)
    else:
        ax.set_title("Latency Breakdown by Algorithm", fontsize=14)

    ax.legend(loc="upper right", fontsize=10)
    ax.grid(True, alpha=0.3, axis="y")
    ax.set_axisbelow(True)

    plt.tight_layout()

    # 保存
    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        print(f"Saved latency breakdown to {output_path}")

    return fig


def plot_dataset_heatmap(
    results: dict[str, dict[str, AlgorithmMetrics]],
    metric: str = "f1",
    output_path: str | Path | None = None,
    title: str | None = None,
    figsize: tuple[float, float] = (12, 8),
    cmap: str = "RdYlGn",
    annotate: bool = True,
) -> plt.Figure:
    """
    绘制算法×数据集的性能热力图

    Args:
        results: {dataset: {algorithm: AlgorithmMetrics}} 嵌套字典
        metric: 要展示的指标
        output_path: 保存路径（可选）
        title: 图表标题（可选）
        figsize: 图表大小
        cmap: 颜色映射
        annotate: 是否在格子内标注数值

    Returns:
        matplotlib Figure 对象
    """
    # 提取数据集和算法列表
    datasets = list(results.keys())
    if not datasets:
        raise ValueError("Empty results dictionary")

    # 获取所有算法（从第一个数据集）
    algorithms = list(results[datasets[0]].keys())

    # 创建数据矩阵
    data = np.zeros((len(algorithms), len(datasets)))
    attr_name = f"avg_{metric}"

    for j, dataset in enumerate(datasets):
        for i, algo in enumerate(algorithms):
            if algo in results[dataset]:
                data[i, j] = getattr(results[dataset][algo], attr_name, 0.0)

    # 创建图表
    fig, ax = plt.subplots(figsize=figsize)

    # 绘制热力图
    im = ax.imshow(data, cmap=cmap, aspect="auto")

    # 设置刻度
    ax.set_xticks(np.arange(len(datasets)))
    ax.set_yticks(np.arange(len(algorithms)))
    ax.set_xticklabels(datasets, rotation=45, ha="right")
    ax.set_yticklabels(algorithms)

    # 添加颜色条
    cbar = fig.colorbar(im, ax=ax, shrink=0.8)
    metric_labels = {
        "f1": "F1 Score",
        "compression_rate": "Compression Rate",
        "total_time": "Total Latency (s)",
    }
    cbar.set_label(metric_labels.get(metric, metric), fontsize=12)

    # 标注数值
    if annotate:
        for i in range(len(algorithms)):
            for j in range(len(datasets)):
                val = data[i, j]
                # 根据背景色选择文字颜色
                text_color = "white" if val < (data.max() + data.min()) / 2 else "black"
                format_str = ".3f" if metric == "f1" else ".2f"
                ax.text(
                    j,
                    i,
                    f"{val:{format_str}}",
                    ha="center",
                    va="center",
                    color=text_color,
                    fontsize=9,
                )

    # 高亮每列（每个数据集）的最佳值
    for j in range(len(datasets)):
        col = data[:, j]
        if metric in ["f1", "compression_rate"]:
            best_idx = np.argmax(col)
        else:
            best_idx = np.argmin(col) if col.min() > 0 else np.argmax(col)
        ax.add_patch(
            plt.Rectangle(
                (j - 0.5, best_idx - 0.5), 1, 1, fill=False, edgecolor="gold", linewidth=3
            )
        )

    # 设置标签
    ax.set_xlabel("Dataset", fontsize=12)
    ax.set_ylabel("Algorithm", fontsize=12)

    if title:
        ax.set_title(title, fontsize=14)
    else:
        ax.set_title(
            f"Algorithm Performance Heatmap - {metric_labels.get(metric, metric)}", fontsize=14
        )

    plt.tight_layout()

    # 保存
    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        print(f"Saved dataset heatmap to {output_path}")

    return fig


def plot_radar_chart(
    results: dict[str, AlgorithmMetrics],
    metrics: list[str] | None = None,
    output_path: str | Path | None = None,
    title: str | None = None,
    figsize: tuple[float, float] = (10, 10),
) -> plt.Figure:
    """
    多维度对比雷达图

    Args:
        results: 算法名到 AlgorithmMetrics 的映射
        metrics: 要展示的指标列表 (默认: f1, compression_rate, speed)
        output_path: 保存路径（可选）
        title: 图表标题（可选）
        figsize: 图表大小

    Returns:
        matplotlib Figure 对象
    """
    if metrics is None:
        metrics = ["f1", "compression_rate", "speed"]

    algorithms = list(results.keys())
    n_metrics = len(metrics)

    # 收集原始值
    raw_values: dict[str, list[float]] = {algo: [] for algo in algorithms}

    metric_labels = {
        "f1": "F1 Score",
        "compression_rate": "Compression",
        "speed": "Speed",
        "total_time": "Total Time",
        "refine_time": "Refine Time",
    }

    for metric in metrics:
        for algo in algorithms:
            if metric == "speed":
                # speed = 1 / total_time，越快越好
                time_val = results[algo].avg_total_time
                val = 1.0 / time_val if time_val > 0 else 0.0
            else:
                val = getattr(results[algo], f"avg_{metric}", 0.0)
            raw_values[algo].append(val)

    # 归一化到 0-1
    normalized: dict[str, list[float]] = {algo: [] for algo in algorithms}
    for i in range(n_metrics):
        metric_vals = [raw_values[algo][i] for algo in algorithms]
        min_val, max_val = min(metric_vals), max(metric_vals)
        range_val = max_val - min_val if max_val != min_val else 1.0

        for algo in algorithms:
            norm_val = (raw_values[algo][i] - min_val) / range_val
            normalized[algo].append(norm_val)

    # 创建雷达图
    angles = np.linspace(0, 2 * np.pi, n_metrics, endpoint=False).tolist()
    angles += angles[:1]  # 闭合

    fig, ax = plt.subplots(figsize=figsize, subplot_kw={"polar": True})

    # 绘制每个算法
    for i, algo in enumerate(algorithms):
        values = normalized[algo] + normalized[algo][:1]  # 闭合
        color = _get_algorithm_color(algo, i)
        ax.plot(angles, values, "o-", linewidth=2, label=algo, color=color)
        ax.fill(angles, values, alpha=0.1, color=color)

    # 设置标签
    labels = [metric_labels.get(m, m) for m in metrics]
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=11)

    # 设置径向刻度
    ax.set_ylim(0, 1)
    ax.set_yticks([0.2, 0.4, 0.6, 0.8, 1.0])
    ax.set_yticklabels(["0.2", "0.4", "0.6", "0.8", "1.0"], fontsize=9)

    if title:
        ax.set_title(title, fontsize=14, y=1.08)
    else:
        ax.set_title("Multi-Dimensional Algorithm Comparison", fontsize=14, y=1.08)

    ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.0), fontsize=10)

    plt.tight_layout()

    # 保存
    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        print(f"Saved radar chart to {output_path}")

    return fig


# ============================================================================
# 综合可视化报告
# ============================================================================


def generate_visualization_report(
    results: dict[str, AlgorithmMetrics],
    multi_dataset_results: dict[str, dict[str, AlgorithmMetrics]] | None = None,
    output_dir: str | Path = ".",
    formats: list[str] | None = None,
) -> dict[str, Path]:
    """
    生成完整的可视化报告

    Args:
        results: 聚合后的算法指标 (单数据集或跨数据集聚合)
        multi_dataset_results: 多数据集结果 (可选，用于热力图)
        output_dir: 输出目录
        formats: 输出格式列表 (默认: ["pdf", "png"])

    Returns:
        生成的文件路径字典
    """
    if formats is None:
        formats = ["pdf", "png"]

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    generated_files: dict[str, Path] = {}

    for fmt in formats:
        # 1. 算法对比柱状图 (F1)
        path = output_dir / f"algorithm_comparison_f1.{fmt}"
        plot_algorithm_comparison(results, metric="f1", output_path=path)
        generated_files[f"comparison_f1_{fmt}"] = path
        plt.close()

        # 2. 算法对比柱状图 (Compression)
        path = output_dir / f"algorithm_comparison_compression.{fmt}"
        plot_algorithm_comparison(results, metric="compression_rate", output_path=path)
        generated_files[f"comparison_compression_{fmt}"] = path
        plt.close()

        # 3. Pareto 前沿图
        path = output_dir / f"pareto_frontier.{fmt}"
        plot_pareto_frontier(results, output_path=path)
        generated_files[f"pareto_{fmt}"] = path
        plt.close()

        # 4. 延迟分解图
        path = output_dir / f"latency_breakdown.{fmt}"
        plot_latency_breakdown(results, output_path=path)
        generated_files[f"latency_{fmt}"] = path
        plt.close()

        # 5. 雷达图
        path = output_dir / f"radar_chart.{fmt}"
        plot_radar_chart(results, output_path=path)
        generated_files[f"radar_{fmt}"] = path
        plt.close()

        # 6. 热力图 (如果有多数据集结果)
        if multi_dataset_results:
            path = output_dir / f"dataset_heatmap_f1.{fmt}"
            plot_dataset_heatmap(multi_dataset_results, metric="f1", output_path=path)
            generated_files[f"heatmap_f1_{fmt}"] = path
            plt.close()

            path = output_dir / f"dataset_heatmap_compression.{fmt}"
            plot_dataset_heatmap(multi_dataset_results, metric="compression_rate", output_path=path)
            generated_files[f"heatmap_compression_{fmt}"] = path
            plt.close()

    print(f"Generated {len(generated_files)} visualization files in {output_dir}")
    return generated_files
