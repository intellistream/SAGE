#!/usr/bin/env python3
"""
Workload 4 Metrics Analysis Script

用于分析 Workload 4 基准测试的性能指标。

用法:
    python analyze_workload4_metrics.py /tmp/sage_metrics_workload4/metrics.csv
    python analyze_workload4_metrics.py /tmp/sage_metrics_workload4/metrics.csv --output report.html
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


def load_metrics(metrics_path: Path) -> pd.DataFrame:
    """加载指标 CSV 文件"""
    if not metrics_path.exists():
        print(f"❌ 指标文件不存在: {metrics_path}")
        sys.exit(1)

    df = pd.read_csv(metrics_path)
    print(f"✅ 已加载 {len(df)} 条记录")
    return df


def compute_latency_stats(df: pd.DataFrame) -> dict[str, Any]:
    """计算延迟统计"""
    latencies = df["end_to_end_time"] * 1000  # 转换为 ms

    stats = {
        "count": len(latencies),
        "mean": latencies.mean(),
        "std": latencies.std(),
        "min": latencies.min(),
        "p50": latencies.quantile(0.50),
        "p90": latencies.quantile(0.90),
        "p95": latencies.quantile(0.95),
        "p99": latencies.quantile(0.99),
        "max": latencies.max(),
    }

    return stats


def compute_stage_stats(df: pd.DataFrame) -> dict[str, dict[str, float]]:
    """计算各 stage 延迟统计"""
    stages = {
        "query_embedding": df["query_embedding_time"],
        "doc_embedding": df["doc_embedding_time"],
        "semantic_join": df["join_time"] - df["query_arrival_time"],
        "vdb1_retrieval": df["vdb1_end_time"] - df["vdb1_start_time"],
        "vdb2_retrieval": df["vdb2_end_time"] - df["vdb2_start_time"],
        "graph_memory": df["graph_end_time"] - df["graph_start_time"],
        "clustering": df["clustering_time"],
        "reranking": df["reranking_time"],
        "batch_wait": df["batch_time"],
        "generation": df["generation_time"],
    }

    stats = {}
    for stage_name, stage_times in stages.items():
        stage_times_ms = stage_times * 1000
        stats[stage_name] = {
            "p50": stage_times_ms.quantile(0.50),
            "p95": stage_times_ms.quantile(0.95),
            "p99": stage_times_ms.quantile(0.99),
            "mean": stage_times_ms.mean(),
        }

    return stats


def compute_resource_stats(df: pd.DataFrame) -> dict[str, Any]:
    """计算资源使用统计"""
    stats = {
        "cpu_time": {
            "mean": df["cpu_time"].mean(),
            "max": df["cpu_time"].max(),
        },
        "memory_peak_mb": {
            "mean": df["memory_peak_mb"].mean(),
            "max": df["memory_peak_mb"].max(),
        },
    }

    return stats


def compute_quality_stats(df: pd.DataFrame) -> dict[str, Any]:
    """计算质量指标统计"""
    stats = {
        "join_success_rate": (df["join_matched_docs"] > 0).mean() * 100,
        "avg_matched_docs": df["join_matched_docs"].mean(),
        "avg_vdb1_results": df["vdb1_results"].mean(),
        "avg_vdb2_results": df["vdb2_results"].mean(),
        "avg_graph_nodes": df["graph_nodes_visited"].mean(),
        "avg_clusters": df["clusters_found"].mean(),
        "dedup_rate": (df["duplicates_removed"] / (df["vdb1_results"] + df["vdb2_results"])).mean() * 100,
        "avg_final_topk": df["final_top_k"].mean(),
    }

    return stats


def print_summary(stats: dict[str, Any]) -> None:
    """打印统计摘要"""
    print("\n" + "=" * 80)
    print("Workload 4 Performance Summary")
    print("=" * 80)

    # 延迟统计
    latency = stats["latency"]
    print("\n📊 延迟统计 (ms):")
    print(f"  总任务数: {latency['count']}")
    print(f"  平均延迟: {latency['mean']:.1f} ms")
    print(f"  标准差:   {latency['std']:.1f} ms")
    print(f"  P50:      {latency['p50']:.1f} ms")
    print(f"  P90:      {latency['p90']:.1f} ms")
    print(f"  P95:      {latency['p95']:.1f} ms")
    print(f"  P99:      {latency['p99']:.1f} ms")
    print(f"  最大:     {latency['max']:.1f} ms")

    # Stage 统计
    print("\n⏱️  各 Stage 延迟 (P50/P95/P99 ms):")
    for stage_name, stage_stats in stats["stages"].items():
        print(
            f"  {stage_name:20s}: "
            f"{stage_stats['p50']:6.1f} / {stage_stats['p95']:6.1f} / {stage_stats['p99']:6.1f}"
        )

    # 资源统计
    resource = stats["resource"]
    print("\n💻 资源使用:")
    print(f"  平均 CPU 时间: {resource['cpu_time']['mean']:.2f} s")
    print(f"  峰值 CPU 时间: {resource['cpu_time']['max']:.2f} s")
    print(f"  平均内存峰值: {resource['memory_peak_mb']['mean']:.1f} MB")
    print(f"  最大内存峰值: {resource['memory_peak_mb']['max']:.1f} MB")

    # 质量统计
    quality = stats["quality"]
    print("\n✅ 质量指标:")
    print(f"  Join 成功率:    {quality['join_success_rate']:.1f}%")
    print(f"  平均匹配文档:   {quality['avg_matched_docs']:.1f}")
    print(f"  平均 VDB1 结果: {quality['avg_vdb1_results']:.1f}")
    print(f"  平均 VDB2 结果: {quality['avg_vdb2_results']:.1f}")
    print(f"  平均图节点:     {quality['avg_graph_nodes']:.1f}")
    print(f"  平均聚类数:     {quality['avg_clusters']:.1f}")
    print(f"  去重率:         {quality['dedup_rate']:.1f}%")
    print(f"  最终 Top-K:     {quality['avg_final_topk']:.1f}")

    print("\n" + "=" * 80)


def generate_html_report(stats: dict[str, Any], output_path: Path) -> None:
    """生成 HTML 报告"""
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Workload 4 Performance Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        h1 {{ color: #333; }}
        h2 {{ color: #555; margin-top: 30px; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; }}
        tr:nth-child(even) {{ background-color: #f2f2f2; }}
        .metric {{ font-weight: bold; }}
    </style>
</head>
<body>
    <h1>Workload 4 Performance Report</h1>
    
    <h2>延迟统计</h2>
    <table>
        <tr><th>指标</th><th>值 (ms)</th></tr>
        <tr><td>总任务数</td><td>{stats['latency']['count']}</td></tr>
        <tr><td>平均延迟</td><td>{stats['latency']['mean']:.1f}</td></tr>
        <tr><td>P50</td><td>{stats['latency']['p50']:.1f}</td></tr>
        <tr><td>P95</td><td>{stats['latency']['p95']:.1f}</td></tr>
        <tr><td>P99</td><td>{stats['latency']['p99']:.1f}</td></tr>
    </table>
    
    <h2>各 Stage 延迟</h2>
    <table>
        <tr><th>Stage</th><th>P50 (ms)</th><th>P95 (ms)</th><th>P99 (ms)</th></tr>
"""

    for stage_name, stage_stats in stats["stages"].items():
        html += f"""        <tr>
            <td>{stage_name}</td>
            <td>{stage_stats['p50']:.1f}</td>
            <td>{stage_stats['p95']:.1f}</td>
            <td>{stage_stats['p99']:.1f}</td>
        </tr>
"""

    html += """    </table>
    
    <h2>资源使用</h2>
    <table>
        <tr><th>指标</th><th>平均值</th><th>最大值</th></tr>
        <tr>
            <td>CPU 时间 (s)</td>
            <td>{:.2f}</td>
            <td>{:.2f}</td>
        </tr>
        <tr>
            <td>内存峰值 (MB)</td>
            <td>{:.1f}</td>
            <td>{:.1f}</td>
        </tr>
    </table>
    
    <h2>质量指标</h2>
    <table>
        <tr><th>指标</th><th>值</th></tr>
        <tr><td>Join 成功率</td><td>{:.1f}%</td></tr>
        <tr><td>平均匹配文档</td><td>{:.1f}</td></tr>
        <tr><td>去重率</td><td>{:.1f}%</td></tr>
    </table>
</body>
</html>
""".format(
        stats["resource"]["cpu_time"]["mean"],
        stats["resource"]["cpu_time"]["max"],
        stats["resource"]["memory_peak_mb"]["mean"],
        stats["resource"]["memory_peak_mb"]["max"],
        stats["quality"]["join_success_rate"],
        stats["quality"]["avg_matched_docs"],
        stats["quality"]["dedup_rate"],
    )

    output_path.write_text(html)
    print(f"✅ HTML 报告已生成: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Analyze Workload 4 metrics")
    parser.add_argument("metrics_file", type=Path, help="Path to metrics CSV file")
    parser.add_argument("--output", type=Path, help="Output HTML report path")
    parser.add_argument("--json", action="store_true", help="Output JSON format")

    args = parser.parse_args()

    # 加载数据
    df = load_metrics(args.metrics_file)

    # 计算统计
    stats = {
        "latency": compute_latency_stats(df),
        "stages": compute_stage_stats(df),
        "resource": compute_resource_stats(df),
        "quality": compute_quality_stats(df),
    }

    # 打印摘要
    print_summary(stats)

    # JSON 输出
    if args.json:
        json_output = args.metrics_file.parent / "analysis.json"
        json_output.write_text(json.dumps(stats, indent=2))
        print(f"✅ JSON 报告已生成: {json_output}")

    # HTML 输出
    if args.output:
        generate_html_report(stats, args.output)


if __name__ == "__main__":
    main()
