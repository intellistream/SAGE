#!/usr/bin/env python3
"""
实验4: 并行作业执行能力测试
============================

测试 SAGE 同时执行多个不同 Pipeline 的能力。

实验场景:
- 多个 Pipeline 同时启动/延迟启动
- Pipeline 类型: compute, llm, rag
- 测量指标: 每个 Pipeline 的吞吐量、延迟、资源竞争影响

使用示例:
    python run_experiment.py                           # 运行默认实验
    python run_experiment.py --quick                   # 快速测试模式
    python run_experiment.py --pipelines rag compute llm  # 指定 pipeline 类型
    python run_experiment.py --pipelines rag rag rag --delay 2.0  # 3个RAG，间隔2秒启动
    python run_experiment.py --pipelines compute llm --tasks 100 200  # 每个pipeline不同任务数
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any

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


class ParallelJobResult:
    """单个并行作业的结果"""

    def __init__(
        self,
        job_id: int,
        pipeline_type: str,
        metrics: BenchmarkMetrics | None = None,
        error: str | None = None,
        start_time: float = 0.0,
        end_time: float = 0.0,
    ):
        self.job_id = job_id
        self.pipeline_type = pipeline_type
        self.metrics = metrics
        self.error = error
        self.start_time = start_time
        self.end_time = end_time

    @property
    def duration(self) -> float:
        """作业执行时长（秒）"""
        if self.end_time > 0 and self.start_time > 0:
            return self.end_time - self.start_time
        return 0.0

    @property
    def success(self) -> bool:
        """作业是否成功"""
        return self.metrics is not None and self.error is None


def run_single_pipeline(
    job_id: int,
    pipeline_type: str,
    config_dict: dict,
    output_dir: str,
    start_delay: float = 0.0,
) -> ParallelJobResult:
    """
    运行单个 Pipeline（在独立线程中执行）

    Args:
        job_id: 作业ID
        pipeline_type: Pipeline类型 (compute, llm, rag)
        config_dict: 配置字典
        output_dir: 输出目录
        start_delay: 启动延迟（秒）

    Returns:
        ParallelJobResult: 作业执行结果
    """
    if start_delay > 0:
        time.sleep(start_delay)

    name = f"job{job_id}_{pipeline_type}"
    start_time = time.time()

    try:
        print(f"\n[Job {job_id}] Starting {pipeline_type} pipeline at {time.strftime('%H:%M:%S')}")

        config = BenchmarkConfig(experiment_name=name, **config_dict)
        pipeline = SchedulingBenchmarkPipeline(config)

        # 根据类型构建不同的 pipeline
        if pipeline_type == "compute":
            pipeline.build_compute_pipeline(name)
        elif pipeline_type == "llm":
            pipeline.build_llm_pipeline(name)
        elif pipeline_type == "rag":
            pipeline.build_rag_pipeline(name)
        elif pipeline_type == "rag_service":
            pipeline.build_rag_service_pipeline(name)
        elif pipeline_type == "simple_rag":
            pipeline.build_simple_rag_pipeline(name)
        elif pipeline_type == "adaptive_rag":
            # Adaptive-RAG: 根据 num_tasks 生成 queries
            from common.operators import SAMPLE_QUERIES
            num_tasks = config_dict.get("num_tasks", 100)
            queries = [SAMPLE_QUERIES[i % len(SAMPLE_QUERIES)] for i in range(num_tasks)]
            pipeline.build_adaptive_rag_pipeline(name, queries=queries, max_iterations=3)
        elif pipeline_type == "mixed":
            pipeline.build_mixed_pipeline(name)
        else:
            raise ValueError(f"Unknown pipeline type: {pipeline_type}")

        metrics = pipeline.run()
        end_time = time.time()

        save_detailed_results(metrics, output_dir, name)
        print(f"[Job {job_id}] Completed in {end_time - start_time:.1f}s")

        return ParallelJobResult(
            job_id=job_id,
            pipeline_type=pipeline_type,
            metrics=metrics,
            start_time=start_time,
            end_time=end_time,
        )

    except Exception as e:
        end_time = time.time()
        error_msg = str(e)
        print(f"[Job {job_id}] Error: {error_msg}")
        return ParallelJobResult(
            job_id=job_id,
            pipeline_type=pipeline_type,
            error=error_msg,
            start_time=start_time,
            end_time=end_time,
        )


def run_parallel_jobs_experiment(
    pipeline_types: list[str],
    start_delay: float = 0.0,
    num_tasks_per_job: list[int] | None = None,
    parallelism: int = 8,
    num_nodes: int = 4,
    output_dir: str | None = None,
) -> list[ParallelJobResult]:
    """
    并行作业执行实验

    Args:
        pipeline_types: Pipeline类型列表，如 ["rag", "compute", "llm"]
        start_delay: 相邻作业的启动延迟（秒），0表示同时启动
        num_tasks_per_job: 每个作业的任务数，None表示所有作业使用相同任务数
        parallelism: 每个作业的并行度
        num_nodes: 集群节点数
        output_dir: 输出目录

    Returns:
        list[ParallelJobResult]: 所有作业的执行结果
    """
    if output_dir is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pipelines_str = "_".join(pipeline_types)
        delay_str = f"delay{int(start_delay * 1000)}ms" if start_delay > 0 else "concurrent"
        output_dir = str(
            SCRIPT_DIR / "results" / f"parallel_{len(pipeline_types)}jobs_{pipelines_str}_{delay_str}_{timestamp}"
        )

    os.makedirs(output_dir, exist_ok=True)

    # 默认每个作业200个任务
    if num_tasks_per_job is None:
        num_tasks_per_job = [200] * len(pipeline_types)
    elif len(num_tasks_per_job) == 1:
        # 如果只提供一个值，复制给所有作业
        num_tasks_per_job = num_tasks_per_job * len(pipeline_types)
    elif len(num_tasks_per_job) != len(pipeline_types):
        raise ValueError(
            f"num_tasks_per_job length ({len(num_tasks_per_job)}) must match pipeline_types length ({len(pipeline_types)})"
        )

    print(f"\n{'=' * 70}")
    print(f"Running Parallel Jobs Experiment")
    print(f"{'=' * 70}")
    print(f"Pipelines: {pipeline_types}")
    print(f"Start delay: {start_delay}s")
    print(f"Tasks per job: {num_tasks_per_job}")
    print(f"Parallelism: {parallelism}")
    print(f"Nodes: {num_nodes}")
    print(f"Output: {output_dir}")
    print(f"{'=' * 70}\n")

    # 准备所有作业的配置
    job_configs = []
    for i, (pipeline_type, num_tasks) in enumerate(zip(pipeline_types, num_tasks_per_job)):
        config = {
            "num_tasks": num_tasks,
            "parallelism": parallelism,
            "num_nodes": num_nodes,
            "use_remote": True,
            "scheduler_type": "load_aware",
            "scheduler_strategy": "spread",
        }
        job_configs.append((i, pipeline_type, config, output_dir, i * start_delay))

    # 使用线程并行启动所有作业
    results = []
    threads = []

    experiment_start_time = time.time()

    for job_id, pipeline_type, config, out_dir, delay in job_configs:
        thread = threading.Thread(
            target=lambda j, pt, cfg, od, d: results.append(
                run_single_pipeline(j, pt, cfg, od, d)
            ),
            args=(job_id, pipeline_type, config, out_dir, delay),
        )
        threads.append(thread)
        thread.start()

    # 等待所有作业完成
    for thread in threads:
        thread.join()

    experiment_end_time = time.time()
    total_duration = experiment_end_time - experiment_start_time

    # 对结果按 job_id 排序
    results.sort(key=lambda r: r.job_id)

    # 保存并打印结果
    save_parallel_experiment_results(results, output_dir, total_duration)
    print_parallel_results_summary(results, total_duration)

    # 如果有成功的作业，生成对比报告
    successful_results = [(f"job{r.job_id}_{r.pipeline_type}", r.metrics) for r in results if r.success]
    if successful_results:
        generate_comparison_report(successful_results, output_dir, "parallel_jobs_comparison")

    return results


def save_parallel_experiment_results(
    results: list[ParallelJobResult],
    output_dir: str,
    total_duration: float,
) -> None:
    """保存并行实验结果"""
    # JSON 格式
    json_file = os.path.join(output_dir, "parallel_jobs_summary.json")
    data = {
        "total_duration": total_duration,
        "num_jobs": len(results),
        "num_successful": sum(1 for r in results if r.success),
        "num_failed": sum(1 for r in results if not r.success),
        "jobs": [],
    }

    for result in results:
        job_data = {
            "job_id": result.job_id,
            "pipeline_type": result.pipeline_type,
            "success": result.success,
            "duration": result.duration,
            "start_time": result.start_time,
            "end_time": result.end_time,
        }

        if result.success and result.metrics:
            job_data.update(
                {
                    "throughput": result.metrics.throughput,
                    "avg_latency_ms": result.metrics.avg_latency_ms,
                    "p95_latency_ms": result.metrics.p95_latency_ms,
                    "p99_latency_ms": result.metrics.p99_latency_ms,
                    "total_tasks": result.metrics.total_tasks,
                    "node_balance_score": result.metrics.node_balance_score,
                }
            )
        else:
            job_data["error"] = result.error

        data["jobs"].append(job_data)

    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    # 文本报告
    txt_file = os.path.join(output_dir, "parallel_jobs_report.txt")
    with open(txt_file, "w", encoding="utf-8") as f:
        f.write("Parallel Jobs Execution Report\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Total Duration: {total_duration:.2f}s\n")
        f.write(f"Total Jobs: {len(results)}\n")
        f.write(f"Successful: {data['num_successful']}\n")
        f.write(f"Failed: {data['num_failed']}\n\n")

        f.write("Individual Job Results:\n")
        f.write("-" * 80 + "\n")
        f.write(
            f"{'Job ID':>6} {'Pipeline':>10} {'Status':>10} {'Duration':>10} "
            f"{'Throughput':>12} {'Avg Lat':>10} {'P99 Lat':>10}\n"
        )
        f.write("-" * 80 + "\n")

        for result in results:
            status = "SUCCESS" if result.success else "FAILED"
            if result.success and result.metrics:
                f.write(
                    f"{result.job_id:>6} {result.pipeline_type:>10} {status:>10} "
                    f"{result.duration:>9.1f}s {result.metrics.throughput:>10.2f}/s "
                    f"{result.metrics.avg_latency_ms:>9.1f}ms "
                    f"{result.metrics.p99_latency_ms:>9.1f}ms\n"
                )
            else:
                f.write(
                    f"{result.job_id:>6} {result.pipeline_type:>10} {status:>10} "
                    f"{result.duration:>9.1f}s {'N/A':>12} {'N/A':>10} {'N/A':>10}\n"
                )

        if data["num_failed"] > 0:
            f.write("\nFailed Jobs:\n")
            f.write("-" * 80 + "\n")
            for result in results:
                if not result.success:
                    f.write(f"Job {result.job_id} ({result.pipeline_type}): {result.error}\n")

    print(f"\nResults saved to: {output_dir}")


def print_parallel_results_summary(results: list[ParallelJobResult], total_duration: float) -> None:
    """打印并行实验结果摘要"""
    print(f"\n{'=' * 70}")
    print("Parallel Jobs Execution Summary")
    print(f"{'=' * 70}")
    print(f"Total Duration: {total_duration:.2f}s")
    print(f"Total Jobs: {len(results)}")
    print(f"Successful: {sum(1 for r in results if r.success)}")
    print(f"Failed: {sum(1 for r in results if not r.success)}")
    print()

    print(f"{'Job ID':>6} {'Pipeline':>10} {'Status':>10} {'Duration':>10} {'Throughput':>12} {'P99 Lat':>10}")
    print("-" * 70)

    for result in results:
        status = "✓" if result.success else "✗"
        if result.success and result.metrics:
            print(
                f"{result.job_id:>6} {result.pipeline_type:>10} {status:>10} "
                f"{result.duration:>9.1f}s {result.metrics.throughput:>10.2f}/s "
                f"{result.metrics.p99_latency_ms:>9.1f}ms"
            )
        else:
            print(
                f"{result.job_id:>6} {result.pipeline_type:>10} {status:>10} "
                f"{result.duration:>9.1f}s {'N/A':>12} {'N/A':>10}"
            )

    print(f"{'=' * 70}\n")


def run_concurrent_vs_staggered_experiment(
    pipeline_types: list[str] | None = None,
    delays: list[float] | None = None,
    num_tasks: int = 200,
    output_dir: str | None = None,
) -> dict[str, list[ParallelJobResult]]:
    """
    对比同时启动 vs 延迟启动的影响

    Args:
        pipeline_types: Pipeline类型列表
        delays: 要测试的延迟值列表（秒）
        num_tasks: 每个作业的任务数
        output_dir: 输出目录

    Returns:
        dict: 不同延迟配置的结果
    """
    if pipeline_types is None:
        pipeline_types = ["rag", "compute", "llm"]

    if delays is None:
        delays = [0.0, 1.0, 2.0, 5.0]

    if output_dir is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = str(SCRIPT_DIR / "results" / f"concurrent_vs_staggered_{timestamp}")

    os.makedirs(output_dir, exist_ok=True)

    all_results = {}

    for delay in delays:
        print(f"\n{'#' * 70}")
        print(f"Testing with start delay: {delay}s")
        print(f"{'#' * 70}")

        delay_dir = os.path.join(output_dir, f"delay_{int(delay * 1000)}ms")
        results = run_parallel_jobs_experiment(
            pipeline_types=pipeline_types,
            start_delay=delay,
            num_tasks_per_job=[num_tasks],
            output_dir=delay_dir,
        )
        all_results[f"delay_{delay}s"] = results

    # 生成对比报告
    generate_staggered_comparison_report(all_results, output_dir)

    return all_results


def generate_staggered_comparison_report(
    all_results: dict[str, list[ParallelJobResult]],
    output_dir: str,
) -> None:
    """生成延迟启动对比报告"""
    report_file = os.path.join(output_dir, "staggered_comparison_report.txt")

    with open(report_file, "w", encoding="utf-8") as f:
        f.write("Concurrent vs Staggered Start Comparison\n")
        f.write("=" * 80 + "\n\n")

        # 按延迟统计平均性能
        f.write(f"{'Start Delay':>15} {'Avg Throughput':>15} {'Avg P99 Lat':>15} {'Success Rate':>15}\n")
        f.write("-" * 80 + "\n")

        for delay_key, results in sorted(all_results.items()):
            successful = [r for r in results if r.success]
            if successful:
                avg_throughput = sum(r.metrics.throughput for r in successful) / len(successful)
                avg_p99 = sum(r.metrics.p99_latency_ms for r in successful) / len(successful)
                success_rate = len(successful) / len(results)

                f.write(f"{delay_key:>15} {avg_throughput:>13.2f}/s {avg_p99:>13.1f}ms {success_rate:>14.1%}\n")

    print(f"Staggered comparison report saved to: {report_file}")


def run_scaling_experiment(
    base_pipeline: str = "rag",
    num_jobs_list: list[int] | None = None,
    num_tasks: int = 100,
    output_dir: str | None = None,
) -> dict[int, list[ParallelJobResult]]:
    """
    测试作业数量扩展性

    Args:
        base_pipeline: 基础 Pipeline 类型
        num_jobs_list: 要测试的作业数量列表
        num_tasks: 每个作业的任务数
        output_dir: 输出目录

    Returns:
        dict: 不同作业数量的结果
    """
    if num_jobs_list is None:
        num_jobs_list = [1, 2, 4, 8]

    if output_dir is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = str(SCRIPT_DIR / "results" / f"scaling_{base_pipeline}_{timestamp}")

    os.makedirs(output_dir, exist_ok=True)

    all_results = {}

    for num_jobs in num_jobs_list:
        print(f"\n{'#' * 70}")
        print(f"Testing with {num_jobs} concurrent {base_pipeline} jobs")
        print(f"{'#' * 70}")

        pipeline_types = [base_pipeline] * num_jobs
        jobs_dir = os.path.join(output_dir, f"jobs_{num_jobs}")

        results = run_parallel_jobs_experiment(
            pipeline_types=pipeline_types,
            start_delay=0.0,  # 同时启动
            num_tasks_per_job=[num_tasks],
            output_dir=jobs_dir,
        )
        all_results[num_jobs] = results

    # 生成扩展性报告
    generate_scaling_report(all_results, output_dir, base_pipeline)

    return all_results


def generate_scaling_report(
    all_results: dict[int, list[ParallelJobResult]],
    output_dir: str,
    pipeline_type: str,
) -> None:
    """生成扩展性报告"""
    report_file = os.path.join(output_dir, "scaling_report.txt")

    with open(report_file, "w", encoding="utf-8") as f:
        f.write(f"Job Scaling Analysis - {pipeline_type} Pipeline\n")
        f.write("=" * 80 + "\n\n")

        f.write(
            f"{'Num Jobs':>10} {'Total Throughput':>18} {'Avg Job Throughput':>20} "
            f"{'Avg P99 Lat':>15} {'Success Rate':>15}\n"
        )
        f.write("-" * 80 + "\n")

        for num_jobs, results in sorted(all_results.items()):
            successful = [r for r in results if r.success]
            if successful:
                total_throughput = sum(r.metrics.throughput for r in successful)
                avg_throughput = total_throughput / len(successful)
                avg_p99 = sum(r.metrics.p99_latency_ms for r in successful) / len(successful)
                success_rate = len(successful) / len(results)

                f.write(
                    f"{num_jobs:>10} {total_throughput:>16.2f}/s {avg_throughput:>18.2f}/s "
                    f"{avg_p99:>13.1f}ms {success_rate:>14.1%}\n"
                )

    print(f"Scaling report saved to: {report_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Experiment 4: Parallel Jobs Execution",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run default experiment (3 pipelines: rag, compute, llm)
  python run_experiment.py

  # Specify pipeline types
  python run_experiment.py --pipelines rag compute llm

  # Run same pipeline multiple times with delay
  python run_experiment.py --pipelines rag rag rag --delay 2.0

  # Different tasks per pipeline
  python run_experiment.py --pipelines compute llm --tasks 100 200

  # Quick test mode
  python run_experiment.py --quick

  # Test concurrent vs staggered start
  python run_experiment.py --experiment staggered --pipelines rag compute

  # Test scaling (1, 2, 4, 8 jobs)
  python run_experiment.py --experiment scaling --base-pipeline rag --num-jobs 1 2 4 8
        """,
    )

    parser.add_argument(
        "--pipelines",
        nargs="+",
        choices=["compute", "llm", "rag"],
        default=["rag", "compute", "llm"],
        help="Pipeline types to run (can repeat, default: rag compute llm)",
    )

    parser.add_argument(
        "--delay",
        type=float,
        default=0.0,
        help="Start delay between adjacent pipelines in seconds (default: 0.0 = concurrent)",
    )

    parser.add_argument(
        "--tasks",
        nargs="+",
        type=int,
        default=[200],
        help="Number of tasks per pipeline (default: 200 for all)",
    )

    parser.add_argument(
        "--parallelism",
        type=int,
        default=8,
        help="Parallelism degree for each pipeline (default: 8)",
    )

    parser.add_argument(
        "--nodes",
        type=int,
        default=4,
        help="Number of cluster nodes (default: 4)",
    )

    parser.add_argument(
        "--output",
        type=str,
        help="Output directory (default: auto-generated)",
    )

    parser.add_argument(
        "--quick",
        action="store_true",
        help="Quick test mode (fewer tasks)",
    )

    parser.add_argument(
        "--experiment",
        choices=["basic", "staggered", "scaling"],
        default="basic",
        help="Experiment type: basic (default), staggered (compare delays), scaling (scale num jobs)",
    )

    parser.add_argument(
        "--base-pipeline",
        choices=["compute", "llm", "rag"],
        default="rag",
        help="Base pipeline type for scaling experiment (default: rag)",
    )

    parser.add_argument(
        "--num-jobs",
        nargs="+",
        type=int,
        default=[1, 2, 4, 8],
        help="Number of jobs for scaling experiment (default: 1 2 4 8)",
    )

    args = parser.parse_args()

    if args.quick:
        args.tasks = [50]
        args.nodes = 2

    if args.experiment == "basic":
        # 基础并行作业实验
        run_parallel_jobs_experiment(
            pipeline_types=args.pipelines,
            start_delay=args.delay,
            num_tasks_per_job=args.tasks,
            parallelism=args.parallelism,
            num_nodes=args.nodes,
            output_dir=args.output,
        )

    elif args.experiment == "staggered":
        # 同时启动 vs 延迟启动对比
        run_concurrent_vs_staggered_experiment(
            pipeline_types=args.pipelines,
            delays=[0.0, 1.0, 2.0, 5.0] if not args.quick else [0.0, 2.0],
            num_tasks=args.tasks[0],
            output_dir=args.output,
        )

    elif args.experiment == "scaling":
        # 作业数量扩展性测试
        run_scaling_experiment(
            base_pipeline=args.base_pipeline,
            num_jobs_list=args.num_jobs,
            num_tasks=args.tasks[0],
            output_dir=args.output,
        )


if __name__ == "__main__":
    main()
