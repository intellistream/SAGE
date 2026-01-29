#!/usr/bin/env python3
"""
'ENDOFFILE'3: 调度延迟
================================

--------的延迟和吞吐量。

'ENDOFFILE''ENDOFFILE''ENDOFFILE':
- 调度延迟分解: 调度延迟、排队延迟、执行延迟
- 吞吐量曲线: 不同并发度下的吞吐量变化
- 延迟分布: P50/P95/P99 延迟统计
- 调度器开销: 对比不同调度器的调度开销

:
    python run_experiment.py                    # 运行全部实验
    python run_experiment.py --quick            # 快速测试模式
    python run_experiment.py --concurrency 4 8 16 32  # 指定并发度
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# 添加项目路径
SCRIPT_DIR = Path(__file__).resolve().parent
EXPERIMENT_ROOT = SCRIPT_DIR.parent
REPO_ROOT = EXPERIMENT_ROOT.parents[0]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(EXPERIMENT_ROOT))

from common.models import BenchmarkConfig, BenchmarkMetrics
from common.pipeline import SchedulingBenchmarkPipeline
from common.visualization import (
    generate_comparison_report,
    plot_results,
    save_detailed_results,
)


def run_single_experiment(
    name: str,
    config_dict: dict,
    output_dir: str,
    pipeline_type: str = "compute",
) -> BenchmarkMetrics:
    """运行单个实验配置"""
    print(f"\n{'=' * 70}")
    print(f"Running: {name}")
    print(f"{'=' * 70}")

    config = BenchmarkConfig(
        experiment_name=name,
        **config_dict,
    )

    pipeline = SchedulingBenchmarkPipeline(config)

    if pipeline_type == "compute":
        pipeline.build_compute_pipeline(name)
    elif pipeline_type == "llm":
        pipeline.build_llm_pipeline(name)
    else:
        pipeline.build_rag_pipeline(name)

    metrics = pipeline.run()

    save_detailed_results(metrics, output_dir, name)
    metrics.print_summary()

    return metrics


def run_concurrency_scaling_experiment(
    concurrency_levels: list[int] = None,
    num_tasks: int = 500,
    num_nodes: int = 4,
    output_dir: str = None,
    pipeline_type: str = "compute",
) -> list[tuple[str, BenchmarkMetrics]]:
    """
    并发度扩展实验。


    """
    if concurrency_levels is None:
        concurrency_levels = [1, 2, 4, 8, 16, 32]

    if output_dir is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = str(SCRIPT_DIR / "results" / f"concurrency_scaling_{timestamp}")

    os.makedirs(output_dir, exist_ok=True)

    results = []

    for parallelism in concurrency_levels:
        config_name = f"concurrency_{parallelism}"

        # 低并发用 Local，高并发用 Remote
        use_remote = parallelism > 4

        config = {
            "num_tasks": num_tasks,
            "parallelism": parallelism,
            "num_nodes": num_nodes if use_remote else 1,
            "use_remote": use_remote,
            "scheduler_type": "load_aware" if use_remote else "fifo",
            "scheduler_strategy": "spread",
            "task_complexity": "medium",
        }

        try:
            metrics = run_single_experiment(
                name=config_name,
                config_dict=config,
                output_dir=output_dir,
                pipeline_type=pipeline_type,
            )
            results.append((config_name, metrics))
        except Exception as e:
            print(f"Error running {config_name}: {e}")
            import traceback

            traceback.print_exc()

    if results:
        generate_comparison_report(results, output_dir, "concurrency_scaling_comparison")
        plot_results(results, output_dir, "concurrency_scaling")

        # 生成吞吐量曲线数据
        save_throughput_curve(results, output_dir)

    return results


def run_latency_breakdown_experiment(
    parallelism: int = 16,
    num_tasks: int = 500,
    num_nodes: int = 4,
    output_dir: str = None,
) -> list[tuple[str, BenchmarkMetrics]]:
    """
    延迟分解实验。


    """
    if output_dir is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = str(SCRIPT_DIR / "results" / f"latency_breakdown_{timestamp}")

    os.makedirs(output_dir, exist_ok=True)

    complexities = ["light", "medium", "heavy"]
    results = []

    for complexity in complexities:
        config_name = f"complexity_{complexity}"

        config = {
            "num_tasks": num_tasks,
            "parallelism": parallelism,
            "num_nodes": num_nodes,
            "use_remote": True,
            "scheduler_type": "load_aware",
            "scheduler_strategy": "spread",
            "task_complexity": complexity,
        }

        try:
            metrics = run_single_experiment(
                name=config_name,
                config_dict=config,
                output_dir=output_dir,
            )
            results.append((config_name, metrics))
        except Exception as e:
            print(f"Error running {config_name}: {e}")

    if results:
        generate_comparison_report(results, output_dir, "latency_breakdown_comparison")
        save_latency_breakdown(results, output_dir)

    return results


def run_scheduler_overhead_experiment(
    schedulers: list[str] = None,
    num_tasks: int = 500,
    parallelism: int = 16,
    output_dir: str = None,
) -> list[tuple[str, BenchmarkMetrics]]:
    """
    调度器开销对比实验。

        self._cache_time 0.0 =
    """
    if schedulers is None:
        schedulers = ["fifo", "load_aware", "round_robin", "priority"]

    if output_dir is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = str(SCRIPT_DIR / "results" / f"scheduler_overhead_{timestamp}")

    os.makedirs(output_dir, exist_ok=True)

    results = []

    for scheduler in schedulers:
        config_name = f"scheduler_{scheduler}"

        config = {
            "num_tasks": num_tasks,
            "parallelism": parallelism,
            "num_nodes": 4,
            "use_remote": True,
            "scheduler_type": scheduler,
            "scheduler_strategy": "spread",
        }

        try:
            metrics = run_single_experiment(
                name=config_name,
                config_dict=config,
                output_dir=output_dir,
            )
            results.append((config_name, metrics))
        except Exception as e:
            print(f"Error running {config_name}: {e}")

    if results:
        generate_comparison_report(results, output_dir, "scheduler_overhead_comparison")
        save_scheduler_overhead(results, output_dir)

    return results


def save_throughput_curve(
    results: list[tuple[str, BenchmarkMetrics]],
    output_dir: str,
) -> str:
    """保存吞吐量曲线'ENDOFFILE'"""
    filepath = os.path.join(output_dir, "throughput_curve.json")

    data = {
        "concurrency_levels": [],
        "throughput": [],
        "avg_latency_ms": [],
        "p99_latency_ms": [],
    }

    for name, metrics in results:
        # 从名称解析并发度
        try:
            parallelism = int(name.split("_")[-1])
        except ValueError:
            parallelism = 0

        data["concurrency_levels"].append(parallelism)
        data["throughput"].append(metrics.throughput)
        data["avg_latency_ms"].append(metrics.avg_latency_ms)
        data["p99_latency_ms"].append(metrics.p99_latency_ms)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    # 生成文本报告
    report_file = os.path.join(output_dir, "throughput_curve_report.txt")
    with open(report_file, "w", encoding="utf-8") as f:
        f.write("Throughput vs Concurrency\n")
        f.write("=" * 60 + "\n\n")
        f.write(
            f"{'Concurrency':>12} {'Throughput':>15} {'Avg Lat (ms)':>15} {'P99 Lat (ms)':>15}\n"
        )
        f.write("-" * 60 + "\n")
        for i in range(len(data["concurrency_levels"])):
            f.write(
                f"{data['concurrency_levels'][i]:>12} "
                f"{data['throughput'][i]:>13.2f}/s "
                f"{data['avg_latency_ms'][i]:>15.1f} "
                f"{data['p99_latency_ms'][i]:>15.1f}\n"
            )

    print(f"Throughput curve data saved to: {filepath}")
    return filepath


def save_latency_breakdown(
    results: list[tuple[str, BenchmarkMetrics]],
    output_dir: str,
) -> str:
    """保存延迟分解数据"""
    filepath = os.path.join(output_dir, "latency_breakdown.json")

    data = []
    for name, metrics in results:
        data.append(
            {
                "name": name,
                "scheduling_latency_ms": metrics.avg_scheduling_latency_ms,
                "queue_latency_ms": metrics.avg_queue_latency_ms,
                "execution_latency_ms": metrics.avg_execution_latency_ms,
                "total_latency_ms": metrics.avg_latency_ms,
            }
        )

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    # 生成文本报告
    report_file = os.path.join(output_dir, "latency_breakdown_report.txt")
    with open(report_file, "w", encoding="utf-8") as f:
        f.write("Latency Breakdown Analysis\n")
        f.write("=" * 80 + "\n\n")
        f.write(
            f"{'Complexity':>15} {'Scheduling':>12} {'Queue':>12} {'Execution':>12} {'Total':>12}\n"
        )
        f.write("-" * 80 + "\n")
        for d in data:
            f.write(
                f"{d['name']:>15} "
                f"{d['scheduling_latency_ms']:>10.2f}ms "
                f"{d['queue_latency_ms']:>10.2f}ms "
                f"{d['execution_latency_ms']:>10.2f}ms "
                f"{d['total_latency_ms']:>10.2f}ms\n"
            )

    print(f"Latency breakdown data saved to: {filepath}")
    return filepath


def save_scheduler_overhead(
    results: list[tuple[str, BenchmarkMetrics]],
    output_dir: str,
) -> str:
    """保存调度器开销数据"""
    filepath = os.path.join(output_dir, "scheduler_overhead.json")

    data = []
    for name, metrics in results:
        scheduler = name.replace("scheduler_", "")
        data.append(
            {
                "scheduler": scheduler,
                "scheduling_latency_ms": metrics.avg_scheduling_latency_ms,
                "throughput": metrics.throughput,
                "node_balance_score": metrics.node_balance_score,
            }
        )

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    # 生成文本
    report_file = os.path.join(output_dir, "scheduler_overhead_report.txt")
    with open(report_file, "w", encoding="utf-8") as f:
        f.write("Scheduler Overhead Comparison\n")
        f.write("=" * 70 + "\n\n")
        f.write(f"{'Scheduler':>15} {'Sched Latency':>15} {'Throughput':>15} {'Balance':>12}\n")
        f.write("-" * 70 + "\n")
        for d in data:
            f.write(
                f"{d['scheduler']:>15} "
                f"{d['scheduling_latency_ms']:>13.2f}ms "
                f"{d['throughput']:>13.2f}/s "
                f"{d['node_balance_score']:>11.1%}\n"
            )

    print(f"Scheduler overhead data saved to: {filepath}")
    return filepath


def run_full_experiment(quick_mode: bool = False) -> None:
    """运行完整实验"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = str(SCRIPT_DIR / "results" / f"full_experiment_{timestamp}")
    os.makedirs(output_dir, exist_ok=True)

    print(f"\n{'#' * 70}")
    print("Experiment 3: Latency and Throughput Measurement")
    print(f"{'#' * 70}")
    print(f"Output directory: {output_dir}")
    print(f"Quick mode: {quick_mode}")

    all_results = []

    # 1. 并发度扩展实验
    if quick_mode:
        concurrency_levels = [1, 4, 8]
        num_tasks = 100
    else:
        concurrency_levels = [1, 2, 4, 8, 16, 32]
        num_tasks = 500

    print("\n--- Part 1: Concurrency Scaling ---")
    concurrency_results = run_concurrency_scaling_experiment(
        concurrency_levels=concurrency_levels,
        num_tasks=num_tasks,
        output_dir=os.path.join(output_dir, "concurrency_scaling"),
    )
    all_results.extend(concurrency_results)

    # 2. 延迟分解实验
    print("\n--- Part 2: Latency Breakdown ---")
    latency_results = run_latency_breakdown_experiment(
        parallelism=8 if quick_mode else 16,
        num_tasks=100 if quick_mode else 500,
        output_dir=os.path.join(output_dir, "latency_breakdown"),
    )
    all_results.extend(latency_results)

    # 3. 调度器开销实验
    if quick_mode:
        schedulers = ["fifo", "load_aware"]
    else:
        schedulers = ["fifo", "load_aware", "round_robin", "priority"]

    print("\n--- Part 3: Scheduler Overhead ---")
    overhead_results = run_scheduler_overhead_experiment(
        schedulers=schedulers,
        num_tasks=100 if quick_mode else 500,
        output_dir=os.path.join(output_dir, "scheduler_overhead"),
    )
    all_results.extend(overhead_results)

    # 生成总体报告
    if all_results:
        generate_comparison_report(all_results, output_dir, "full_experiment_report")
        plot_results(all_results, output_dir, "full_experiment")

    print(f"\n{'=' * 70}")
    print("Experiment completed.")
    print(f"Results saved to: {output_dir}")
    print(f"{'=' * 70}")


def main():
    parser = argparse.ArgumentParser(description="Experiment 3: Latency and Throughput")
    parser.add_argument("--quick", action="store_true", help="Quick test mode")
    parser.add_argument("--concurrency", nargs="+", type=int, help="Concurrency levels to test")
    parser.add_argument("--tasks", type=int, default=500, help="Number of tasks")
    parser.add_argument("--nodes", type=int, default=8, help="Number of nodes")
    parser.add_argument("--parallelism", type=int, default=32, help="Parallelism level")
    parser.add_argument("--output", type=str, help="Output directory")
    parser.add_argument(
        "--pipeline",
        type=str,
        default="compute",
        choices=["compute", "llm", "rag"],
        help="Pipeline type: compute (default), llm, or rag",
    )
    parser.add_argument(
        "--latency-breakdown",
        action="store_true",
        help="Run latency breakdown experiment (light/medium/heavy complexity)",
    )
    parser.add_argument(
        "--scheduler-overhead",
        action="store_true",
        help="Run scheduler overhead comparison experiment",
    )
    parser.add_argument(
        "--schedulers",
        nargs="+",
        default=["fifo", "load_aware", "round_robin", "priority"],
        help="Schedulers to test for overhead experiment",
    )

    args = parser.parse_args()

    if args.latency_breakdown:
        run_latency_breakdown_experiment(
            parallelism=args.parallelism,
            num_tasks=args.tasks,
            num_nodes=args.nodes,
            output_dir=args.output,
        )
    elif args.scheduler_overhead:
        run_scheduler_overhead_experiment(
            schedulers=args.schedulers,
            num_tasks=args.tasks,
            parallelism=args.parallelism,
            output_dir=args.output,
        )
    elif args.concurrency:
        run_concurrency_scaling_experiment(
            concurrency_levels=args.concurrency,
            num_tasks=args.tasks,
            output_dir=args.output,
            pipeline_type=args.pipeline,
        )
    else:
        run_full_experiment(quick_mode=args.quick)


if __name__ == "__main__":
    main()
