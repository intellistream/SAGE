"""
Distributed Scheduling Benchmark - Visualization
=================================================


"""

from __future__ import annotations

import json
import os
from datetime import datetime

try:
    from .models import BenchmarkMetrics
except ImportError:
    from models import BenchmarkMetrics


def save_metrics_to_json(
    metrics: BenchmarkMetrics,
    output_dir: str,
    filename: str = "metrics.json",
) -> str:
    """保存指标到 JSON 文件"""
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, filename)

    data = {
        "timestamp": datetime.now().isoformat(),
        "metrics": metrics.to_dict(),
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Metrics saved to: {filepath}")
    return filepath


def save_detailed_results(
    metrics: BenchmarkMetrics,
    output_dir: str,
    experiment_name: str,
) -> dict[str, str]:
    """保存详细结果到多个文件"""
    os.makedirs(output_dir, exist_ok=True)
    files = {}

    # 1. 摘要文件 (文本)
    summary_file = os.path.join(output_dir, f"{experiment_name}_summary.txt")
    with open(summary_file, "w", encoding="utf-8") as f:
        f.write(f"{'=' * 70}\n")
        f.write(f"Benchmark Results: {experiment_name}\n")
        f.write(f"{'=' * 70}\n")
        f.write(f"Timestamp: {datetime.now().isoformat()}\n\n")

        f.write("Configuration:\n")
        if metrics.config:
            for k, v in metrics.config.to_dict().items():
                f.write(f"  {k}: {v}\n")
        f.write("\n")

        f.write("Results:\n")
        f.write(f"  Total Tasks:       {metrics.total_tasks}\n")
        f.write(f"  Successful:        {metrics.successful_tasks}\n")
        f.write(f"  Failed:            {metrics.failed_tasks}\n")
        f.write(f"  Duration:          {metrics.total_duration:.2f}s\n")
        f.write("\n")
        f.write(f"  Throughput:        {metrics.throughput:.2f} tasks/sec\n")
        f.write(f"  Avg Latency:       {metrics.avg_latency_ms:.2f} ms\n")
        f.write(f"  P50 Latency:       {metrics.p50_latency_ms:.2f} ms\n")
        f.write(f"  P95 Latency:       {metrics.p95_latency_ms:.2f} ms\n")
        f.write(f"  P99 Latency:       {metrics.p99_latency_ms:.2f} ms\n")
        f.write("\n")
        f.write(f"  Scheduling Latency: {metrics.avg_scheduling_latency_ms:.2f} ms\n")
        f.write(f"  Queue Latency:      {metrics.avg_queue_latency_ms:.2f} ms\n")
        f.write(f"  Execution Latency:  {metrics.avg_execution_latency_ms:.2f} ms\n")
        f.write("\n")
        f.write(f"  Node Balance:      {metrics.node_balance_score:.2%}\n")

        if metrics.node_distribution:
            f.write("\n  Node Distribution:\n")
            for node, count in sorted(metrics.node_distribution.items()):
                pct = count / metrics.successful_tasks * 100 if metrics.successful_tasks > 0 else 0
                f.write(f"    {node}: {count} ({pct:.1f}%)\n")

        f.write(f"\n{'=' * 70}\n")
    files["summary"] = summary_file

    # 2. JSON 完整数据
    json_file = os.path.join(output_dir, f"{experiment_name}_metrics.json")
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(
            {
                "timestamp": datetime.now().isoformat(),
                "experiment_name": experiment_name,
                "metrics": metrics.to_dict(),
                "latency_details": {
                    "total_latencies_ms": [lat * 1000 for lat in metrics.total_latencies],
                    "scheduling_latencies_ms": [lat * 1000 for lat in metrics.scheduling_latencies],
                    "execution_latencies_ms": [lat * 1000 for lat in metrics.execution_latencies],
                },
                "node_latencies_ms": {
                    node: [lat * 1000 for lat in lats]
                    for node, lats in metrics.node_latencies.items()
                },
            },
            f,
            indent=2,
        )
    files["json"] = json_file

    # 3. CSV 延迟数据 (便于后续分析)
    csv_file = os.path.join(output_dir, f"{experiment_name}_latencies.csv")
    with open(csv_file, "w", encoding="utf-8") as f:
        f.write("task_index,total_latency_ms,scheduling_latency_ms,execution_latency_ms\n")
        for i in range(len(metrics.total_latencies)):
            total = metrics.total_latencies[i] * 1000 if i < len(metrics.total_latencies) else 0
            sched = (
                metrics.scheduling_latencies[i] * 1000
                if i < len(metrics.scheduling_latencies)
                else 0
            )
            exec_ = (
                metrics.execution_latencies[i] * 1000 if i < len(metrics.execution_latencies) else 0
            )
            f.write(f"{i},{total:.2f},{sched:.2f},{exec_:.2f}\n")
    files["csv"] = csv_file

    print(f"Detailed results saved to: {output_dir}")
    return files


def generate_comparison_report(
    results: list[tuple[str, BenchmarkMetrics]],
    output_dir: str,
    report_name: str = "comparison_report",
) -> str:
    """生成多实验对比"""
    os.makedirs(output_dir, exist_ok=True)
    report_file = os.path.join(output_dir, f"{report_name}.txt")

    with open(report_file, "w", encoding="utf-8") as f:
        f.write(f"{'=' * 90}\n")
        f.write("Benchmark Comparison Report\n")
        f.write(f"{'=' * 90}\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write(f"Number of experiments: {len(results)}\n\n")

        # 表头
        f.write(
            f"{'Experiment':<25} {'Tasks':>8} {'Throughput':>12} {'Avg Lat':>10} {'P99 Lat':>10} {'Balance':>10}\n"
        )
        f.write(f"{'-' * 25} {'-' * 8} {'-' * 12} {'-' * 10} {'-' * 10} {'-' * 10}\n")

        for name, metrics in results:
            f.write(
                f"{name:<25} {metrics.successful_tasks:>8} "
                f"{metrics.throughput:>10.2f}/s "
                f"{metrics.avg_latency_ms:>8.1f}ms "
                f"{metrics.p99_latency_ms:>8.1f}ms "
                f"{metrics.node_balance_score:>9.1%}\n"
            )

        f.write(f"\n{'=' * 90}\n")

        # 详细对比
        f.write("\nDetailed Comparison:\n")
        f.write("-" * 90 + "\n")

        for name, metrics in results:
            f.write(f"\n[{name}]\n")
            f.write(f"  Config: tasks={metrics.total_tasks}, ")
            if metrics.config:
                f.write(f"parallelism={metrics.config.parallelism}, ")
                f.write(f"nodes={metrics.config.num_nodes}, ")
                f.write(f"scheduler={metrics.config.scheduler_type}\n")
            f.write(f"  Throughput: {metrics.throughput:.2f} tasks/sec\n")
            f.write(
                f"  Latency: avg={metrics.avg_latency_ms:.1f}ms, p50={metrics.p50_latency_ms:.1f}ms, p99={metrics.p99_latency_ms:.1f}ms\n"
            )
            f.write(
                f"  Scheduling: {metrics.avg_scheduling_latency_ms:.1f}ms, Execution: {metrics.avg_execution_latency_ms:.1f}ms\n"
            )
            if metrics.node_distribution:
                f.write(
                    f"  Nodes: {len(metrics.node_distribution)}, Balance: {metrics.node_balance_score:.1%}\n"
                )

    print(f"Comparison report saved to: {report_file}")
    return report_file


def plot_results(
    results: list[tuple[str, BenchmarkMetrics]],
    output_dir: str,
    plot_name: str = "benchmark_plots",
) -> dict[str, str]:
    """
    生成可视化图表。

    需要 matplotlib，如果不可用则跳过。
    """
    try:
        import matplotlib
        import matplotlib.pyplot as plt

        matplotlib.use("Agg")  # 非交互式后端
    except ImportError:
        print("Warning: matplotlib not available, skipping plots")
        return {}

    os.makedirs(output_dir, exist_ok=True)
    files = {}

    names = [name for name, _ in results]
    throughputs = [m.throughput for _, m in results]
    avg_latencies = [m.avg_latency_ms for _, m in results]
    p99_latencies = [m.p99_latency_ms for _, m in results]

    # 1. 吞吐量对比图
    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.bar(names, throughputs, color="steelblue")
    ax.set_xlabel("Experiment")
    ax.set_ylabel("Throughput (tasks/sec)")
    ax.set_title("Throughput Comparison")
    ax.tick_params(axis="x", rotation=45)
    for bar, val in zip(bars, throughputs):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.1,
            f"{val:.1f}",
            ha="center",
            va="bottom",
            fontsize=9,
        )
    plt.tight_layout()
    throughput_file = os.path.join(output_dir, f"{plot_name}_throughput.png")
    plt.savefig(throughput_file, dpi=150)
    plt.close()
    files["throughput"] = throughput_file

    # 2. 延迟对比图
    fig, ax = plt.subplots(figsize=(10, 6))
    x = range(len(names))
    width = 0.35
    ax.bar([i - width / 2 for i in x], avg_latencies, width, label="Avg Latency", color="steelblue")
    ax.bar([i + width / 2 for i in x], p99_latencies, width, label="P99 Latency", color="coral")
    ax.set_xlabel("Experiment")
    ax.set_ylabel("Latency (ms)")
    ax.set_title("Latency Comparison")
    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=45, ha="right")
    ax.legend()
    plt.tight_layout()
    latency_file = os.path.join(output_dir, f"{plot_name}_latency.png")
    plt.savefig(latency_file, dpi=150)
    plt.close()
    files["latency"] = latency_file

    # 3. 节点分布图 (取最后一个实验)
    if results:
        _, last_metrics = results[-1]
        if last_metrics.node_distribution:
            fig, ax = plt.subplots(figsize=(10, 6))
            nodes = list(last_metrics.node_distribution.keys())
            counts = list(last_metrics.node_distribution.values())
            ax.bar(nodes, counts, color="steelblue")
            ax.set_xlabel("Node")
            ax.set_ylabel("Task Count")
            ax.set_title(f"Node Distribution ({results[-1][0]})")
            ax.tick_params(axis="x", rotation=45)
            plt.tight_layout()
            node_file = os.path.join(output_dir, f"{plot_name}_nodes.png")
            plt.savefig(node_file, dpi=150)
            plt.close()
            files["nodes"] = node_file

    print(f"Plots saved to: {output_dir}")
    return files
