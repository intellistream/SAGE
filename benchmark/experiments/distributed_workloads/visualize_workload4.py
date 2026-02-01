#!/usr/bin/env python3
"""
Workload 4 Visualization Script

生成 Workload 4 基准测试的可视化图表。

用法:
    python visualize_workload4.py /tmp/sage_metrics_workload4/
    python visualize_workload4.py /tmp/sage_metrics_workload4/ --output ./report/
"""

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def load_metrics(metrics_dir: Path) -> pd.DataFrame:
    """加载指标 CSV 文件"""
    metrics_path = metrics_dir / "metrics.csv"
    if not metrics_path.exists():
        print(f"❌ 指标文件不存在: {metrics_path}")
        sys.exit(1)

    df = pd.read_csv(metrics_path)
    print(f"✅ 已加载 {len(df)} 条记录")
    return df


def plot_latency_distribution(df: pd.DataFrame, output_dir: Path) -> None:
    """绘制延迟分布直方图"""
    latencies = df["end_to_end_time"] * 1000  # 转换为 ms

    plt.figure(figsize=(12, 6))

    # 直方图
    plt.subplot(1, 2, 1)
    plt.hist(latencies, bins=50, color="skyblue", edgecolor="black", alpha=0.7)
    plt.axvline(
        latencies.quantile(0.50),
        color="green",
        linestyle="--",
        label=f"P50: {latencies.quantile(0.50):.1f} ms",
    )
    plt.axvline(
        latencies.quantile(0.95),
        color="orange",
        linestyle="--",
        label=f"P95: {latencies.quantile(0.95):.1f} ms",
    )
    plt.axvline(
        latencies.quantile(0.99),
        color="red",
        linestyle="--",
        label=f"P99: {latencies.quantile(0.99):.1f} ms",
    )
    plt.xlabel("End-to-End Latency (ms)")
    plt.ylabel("Frequency")
    plt.title("Latency Distribution")
    plt.legend()
    plt.grid(alpha=0.3)

    # 箱线图
    plt.subplot(1, 2, 2)
    plt.boxplot(latencies, vert=True, patch_artist=True)
    plt.ylabel("Latency (ms)")
    plt.title("Latency Box Plot")
    plt.grid(alpha=0.3)

    plt.tight_layout()
    output_path = output_dir / "latency_distribution.png"
    plt.savefig(output_path, dpi=300)
    print(f"✅ 已生成: {output_path}")
    plt.close()


def plot_stage_latencies(df: pd.DataFrame, output_dir: Path) -> None:
    """绘制各 Stage 延迟对比"""
    stages = {
        "Semantic Join": (df["join_time"] - df["query_arrival_time"]) * 1000,
        "VDB1": (df["vdb1_end_time"] - df["vdb1_start_time"]) * 1000,
        "VDB2": (df["vdb2_end_time"] - df["vdb2_start_time"]) * 1000,
        "Graph Memory": (df["graph_end_time"] - df["graph_start_time"]) * 1000,
        "Clustering": df["clustering_time"] * 1000,
        "Reranking": df["reranking_time"] * 1000,
        "Batch Wait": df["batch_time"] * 1000,
        "Generation": df["generation_time"] * 1000,
    }

    # 计算统计
    stage_names = list(stages.keys())
    p50_values = [stages[name].quantile(0.50) for name in stage_names]
    p95_values = [stages[name].quantile(0.95) for name in stage_names]
    p99_values = [stages[name].quantile(0.99) for name in stage_names]

    plt.figure(figsize=(14, 6))

    # P50/P95/P99 对比
    x = np.arange(len(stage_names))
    width = 0.25

    plt.bar(x - width, p50_values, width, label="P50", color="green", alpha=0.8)
    plt.bar(x, p95_values, width, label="P95", color="orange", alpha=0.8)
    plt.bar(x + width, p99_values, width, label="P99", color="red", alpha=0.8)

    plt.xlabel("Stage")
    plt.ylabel("Latency (ms)")
    plt.title("Stage Latency Comparison (P50/P95/P99)")
    plt.xticks(x, stage_names, rotation=45, ha="right")
    plt.legend()
    plt.grid(alpha=0.3, axis="y")
    plt.tight_layout()

    output_path = output_dir / "stage_latencies.png"
    plt.savefig(output_path, dpi=300)
    print(f"✅ 已生成: {output_path}")
    plt.close()


def plot_resource_usage(df: pd.DataFrame, output_dir: Path) -> None:
    """绘制资源使用图"""
    plt.figure(figsize=(14, 5))

    # CPU 时间分布
    plt.subplot(1, 2, 1)
    plt.hist(df["cpu_time"], bins=30, color="lightcoral", edgecolor="black", alpha=0.7)
    plt.axvline(
        df["cpu_time"].mean(),
        color="red",
        linestyle="--",
        label=f"Mean: {df['cpu_time'].mean():.2f} s",
    )
    plt.xlabel("CPU Time (s)")
    plt.ylabel("Frequency")
    plt.title("CPU Time Distribution")
    plt.legend()
    plt.grid(alpha=0.3)

    # 内存峰值分布
    plt.subplot(1, 2, 2)
    plt.hist(df["memory_peak_mb"], bins=30, color="lightgreen", edgecolor="black", alpha=0.7)
    plt.axvline(
        df["memory_peak_mb"].mean(),
        color="green",
        linestyle="--",
        label=f"Mean: {df['memory_peak_mb'].mean():.1f} MB",
    )
    plt.xlabel("Memory Peak (MB)")
    plt.ylabel("Frequency")
    plt.title("Memory Usage Distribution")
    plt.legend()
    plt.grid(alpha=0.3)

    plt.tight_layout()
    output_path = output_dir / "resource_usage.png"
    plt.savefig(output_path, dpi=300)
    print(f"✅ 已生成: {output_path}")
    plt.close()


def plot_quality_metrics(df: pd.DataFrame, output_dir: Path) -> None:
    """绘制质量指标"""
    plt.figure(figsize=(14, 10))

    # Join 匹配文档数分布
    plt.subplot(2, 3, 1)
    plt.hist(df["join_matched_docs"], bins=30, color="skyblue", edgecolor="black", alpha=0.7)
    plt.xlabel("Matched Docs")
    plt.ylabel("Frequency")
    plt.title("Join Matched Docs Distribution")
    plt.grid(alpha=0.3)

    # VDB1 结果数分布
    plt.subplot(2, 3, 2)
    plt.hist(df["vdb1_results"], bins=30, color="lightcoral", edgecolor="black", alpha=0.7)
    plt.xlabel("VDB1 Results")
    plt.ylabel("Frequency")
    plt.title("VDB1 Results Distribution")
    plt.grid(alpha=0.3)

    # VDB2 结果数分布
    plt.subplot(2, 3, 3)
    plt.hist(df["vdb2_results"], bins=30, color="lightgreen", edgecolor="black", alpha=0.7)
    plt.xlabel("VDB2 Results")
    plt.ylabel("Frequency")
    plt.title("VDB2 Results Distribution")
    plt.grid(alpha=0.3)

    # 图遍历节点数分布
    plt.subplot(2, 3, 4)
    plt.hist(df["graph_nodes_visited"], bins=30, color="plum", edgecolor="black", alpha=0.7)
    plt.xlabel("Nodes Visited")
    plt.ylabel("Frequency")
    plt.title("Graph Traversal Nodes")
    plt.grid(alpha=0.3)

    # 聚类数分布
    plt.subplot(2, 3, 5)
    plt.hist(
        df["clusters_found"],
        bins=range(0, int(df["clusters_found"].max()) + 2),
        color="gold",
        edgecolor="black",
        alpha=0.7,
    )
    plt.xlabel("Clusters")
    plt.ylabel("Frequency")
    plt.title("Clustering Results")
    plt.grid(alpha=0.3)

    # 去重文档数分布
    plt.subplot(2, 3, 6)
    plt.hist(df["duplicates_removed"], bins=30, color="salmon", edgecolor="black", alpha=0.7)
    plt.xlabel("Duplicates Removed")
    plt.ylabel("Frequency")
    plt.title("Deduplication Results")
    plt.grid(alpha=0.3)

    plt.tight_layout()
    output_path = output_dir / "quality_metrics.png"
    plt.savefig(output_path, dpi=300)
    print(f"✅ 已生成: {output_path}")
    plt.close()


def plot_latency_waterfall(df: pd.DataFrame, output_dir: Path) -> None:
    """绘制延迟瀑布图（堆叠图）"""
    # 计算各 stage 的平均延迟
    stages = {
        "Query Embedding": (df["query_embedding_time"]) * 1000,
        "Doc Embedding": (df["doc_embedding_time"]) * 1000,
        "Semantic Join": (df["join_time"] - df["query_arrival_time"]) * 1000,
        "Graph Memory": (df["graph_end_time"] - df["graph_start_time"]) * 1000,
        "VDB1": (df["vdb1_end_time"] - df["vdb1_start_time"]) * 1000,
        "VDB2": (df["vdb2_end_time"] - df["vdb2_start_time"]) * 1000,
        "Aggregation": 15,  # 估算
        "Clustering": df["clustering_time"] * 1000,
        "Reranking": df["reranking_time"] * 1000,
        "MMR": 10,  # 估算
        "Batch Wait": df["batch_time"] * 1000,
        "Generation": df["generation_time"] * 1000,
    }

    stage_names = list(stages.keys())
    stage_means = [
        stages[name].mean() if hasattr(stages[name], "mean") else stages[name]
        for name in stage_names
    ]

    # 堆叠柱状图
    plt.figure(figsize=(14, 6))
    colors = plt.cm.Set3(np.linspace(0, 1, len(stage_names)))

    bottom = 0
    for i, (name, mean) in enumerate(zip(stage_names, stage_means)):
        plt.barh(0, mean, left=bottom, height=0.5, color=colors[i], label=name, edgecolor="black")
        # 添加标签
        if mean > 20:  # 只显示超过 20ms 的标签
            plt.text(
                bottom + mean / 2,
                0,
                f"{mean:.0f}ms",
                ha="center",
                va="center",
                fontsize=9,
                fontweight="bold",
            )
        bottom += mean

    plt.xlabel("Latency (ms)")
    plt.title(f"Latency Waterfall (Total: {bottom:.1f} ms)")
    plt.yticks([])
    plt.legend(bbox_to_anchor=(1.05, 1), loc="upper left")
    plt.grid(alpha=0.3, axis="x")
    plt.tight_layout()

    output_path = output_dir / "latency_waterfall.png"
    plt.savefig(output_path, dpi=300)
    print(f"✅ 已生成: {output_path}")
    plt.close()


def main():
    parser = argparse.ArgumentParser(description="Visualize Workload 4 metrics")
    parser.add_argument("metrics_dir", type=Path, help="Directory containing metrics.csv")
    parser.add_argument(
        "--output", type=Path, help="Output directory for plots (default: metrics_dir)"
    )

    args = parser.parse_args()

    # 确定输出目录
    output_dir = args.output if args.output else args.metrics_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    # 加载数据
    df = load_metrics(args.metrics_dir)

    # 生成图表
    print("\n📊 正在生成可视化图表...")
    plot_latency_distribution(df, output_dir)
    plot_stage_latencies(df, output_dir)
    plot_resource_usage(df, output_dir)
    plot_quality_metrics(df, output_dir)
    plot_latency_waterfall(df, output_dir)

    print(f"\n✅ 所有图表已保存到: {output_dir}")


if __name__ == "__main__":
    main()
