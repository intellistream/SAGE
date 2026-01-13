#!/usr/bin/env python3
"""
'ENDOFFILE'1: vs  单节点
============================

        super().__init__()

'ENDOFFILE''ENDOFFILE''ENDOFFILE':
- 单节点: LocalEnvironment, 1 node
- 多节点: RemoteEnvironment, 4/8/16/30 nodes
- 任务类型: RAG Pipeline (检索+LLM生成)
- 测量指标: 吞吐量、延迟、节点分布

:
    python run_experiment.py                    # 'ENDOFFILE'
    python run_experiment.py --quick            # 快速测试模式
    python run_experiment.py --nodes 4 8        # 指定节点数
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

# 添加项目路径
SCRIPT_DIR = Path(__file__).resolve().parent
EXPERIMENT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(EXPERIMENT_ROOT))

from common.models import BenchmarkConfig, BenchmarkMetrics
from common.pipeline import SchedulingBenchmarkPipeline
from common.visualization import (
    generate_comparison_report,
    plot_results,
    save_detailed_results,
)

# 实验配置
EXPERIMENT_CONFIGS = {
    "single_node": {
        "description": "单节点 ",
        "use_remote": True,
        "num_nodes": 1,
        "parallelism": 4,
    },
    "multi_4_nodes": {
        "description": "多节点 (4 nodes)",
        "use_remote": True,
        "num_nodes": 4,
        "parallelism": 4,
        "scheduler_type": "load_aware",
        "scheduler_strategy": "spread",
    },
    "multi_8_nodes": {
        "description": "多节点 (8 nodes)",
        "use_remote": True,
        "num_nodes": 8,
        "parallelism": 32,
        "scheduler_type": "load_aware",
        "scheduler_strategy": "spread",
    },
    "multi_16_nodes": {
        "description": "多节点 (16 nodes)",
        "use_remote": True,
        "num_nodes": 16,
        "parallelism": 64,
        "scheduler_type": "load_aware",
        "scheduler_strategy": "spread",
    },
    "multi_30_nodes": {
        "description": "多节点 (30 nodes)",
        "use_remote": True,
        "num_nodes": 30,
        "parallelism": 120,
        "scheduler_type": "load_aware",
        "scheduler_strategy": "spread",
    },
}

# 不同任务规模
TASK_SCALES = {
    "small": 100,
    "medium": 500,
    "large": 1000,
}


def run_single_experiment(
    name: str,
    config_override: dict,
    num_tasks: int,
    output_dir: str,
    pipeline_type: str = "rag",
) -> BenchmarkMetrics:
    """运行单个实验配置"""
    print(f"\n{'=' * 70}")
    print(f"Running: {name}")
    print(f"Tasks: {num_tasks}, Pipeline: {pipeline_type}")
    print(f"{'=' * 70}")

    # 创建配置
    config = BenchmarkConfig(
        experiment_name=name,
        num_tasks=num_tasks,
        **config_override,
    )

    # 创建并运行 Pipeline
    pipeline = SchedulingBenchmarkPipeline(config)

    if pipeline_type == "rag":
        pipeline.build_rag_pipeline(name)
    elif pipeline_type == "rag_service":
        pipeline.build_rag_service_pipeline(name)
    elif pipeline_type == "simple_rag":
        pipeline.build_simple_rag_pipeline(name)
    elif pipeline_type == "llm":
        pipeline.build_llm_pipeline(name)
    elif pipeline_type == "compute":
        pipeline.build_compute_pipeline(name)
    elif pipeline_type == "adaptive_rag":
        # Adaptive-RAG: 根据 num_tasks 从 SAMPLE_QUERIES 生成 queries
        from common.operators import SAMPLE_QUERIES
        queries = []
        for i in range(num_tasks):
            queries.append(SAMPLE_QUERIES[i % len(SAMPLE_QUERIES)])
        pipeline.build_adaptive_rag_pipeline(name, queries=queries, max_iterations=3)
    else:
        pipeline.build_mixed_pipeline(name)

    metrics = pipeline.run()

    # 保存单个实验结果
    save_detailed_results(metrics, output_dir, name)

    # 打印摘要
    metrics.print_summary()

    return metrics


def run_node_scaling_experiment(
    num_tasks: int = 500,
    node_counts: list[int] | None = None,
    output_dir: str | None = None,
    pipeline_type: str = "compute",
) -> list[tuple[str, BenchmarkMetrics]]:
    """
    运行节点扩展实验。

    对比不同节点数下的性能变化。
    """
    if node_counts is None:
        node_counts = [1, 4, 8, 16]

    if output_dir is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = str(SCRIPT_DIR / "results" / f"node_scaling_{timestamp}")

    os.makedirs(output_dir, exist_ok=True)

    results = []

    for num_nodes in node_counts:
        if num_nodes == 1:
            config_name = "single_node"
            config_override = EXPERIMENT_CONFIGS["single_node"].copy()
            # 移除 BenchmarkConfig 不接受的字段
            config_override.pop("description", None)
        else:
            config_name = f"multi_{num_nodes}_nodes"
            config_override = {
                "use_remote": True,
                "num_nodes": num_nodes,
                "parallelism": num_nodes,  # 每节点 1 个并行度
                "scheduler_type": "load_aware",
                "scheduler_strategy": "spread",
            }

        try:
            metrics = run_single_experiment(
                name=config_name,
                config_override=config_override,
                num_tasks=num_tasks,
                output_dir=output_dir,
                pipeline_type=pipeline_type,
            )
            results.append((config_name, metrics))
        except Exception as e:
            print(f"Error running {config_name}: {e}")
            import traceback

            traceback.print_exc()

    # 生成对比报告
    if results:
        generate_comparison_report(results, output_dir, "node_scaling_comparison")
        plot_results(results, output_dir, "node_scaling")

    return results


def run_task_scaling_experiment(
    task_counts: list[int] | None = None,
    num_nodes: int = 4,
    output_dir: str | None = None,
    pipeline_type: str = "compute",
) -> list[tuple[str, BenchmarkMetrics]]:
    """
    运行任务规模扩展实验。

    在固定节点数下，测试不同任务数
    """
    if task_counts is None:
        task_counts = [100, 500, 1000]

    if output_dir is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = str(SCRIPT_DIR / "results" / f"task_scaling_{timestamp}")

    os.makedirs(output_dir, exist_ok=True)

    results = []

    for num_tasks in task_counts:
        config_name = f"tasks_{num_tasks}_nodes_{num_nodes}"

        if num_nodes == 1:
            config_override = {"use_remote": False, "num_nodes": 1, "parallelism": 4}
        else:
            config_override = {
                "use_remote": True,
                "num_nodes": num_nodes,
                "parallelism": num_nodes * 4,
                "scheduler_type": "load_aware",
                "scheduler_strategy": "spread",
            }

        try:
            metrics = run_single_experiment(
                name=config_name,
                config_override=config_override,
                num_tasks=num_tasks,
                output_dir=output_dir,
                pipeline_type=pipeline_type,
            )
            results.append((config_name, metrics))
        except Exception as e:
            print(f"Error running {config_name}: {e}")

    # 生成对比报告
    if results:
        generate_comparison_report(results, output_dir, "task_scaling_comparison")
        plot_results(results, output_dir, "task_scaling")

    return results


def run_full_experiment(
    quick_mode: bool = False,
    pipeline_type: str = "compute",
) -> None:
    """运行完整实验"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = str(SCRIPT_DIR / "results" / f"full_experiment_{timestamp}")
    os.makedirs(output_dir, exist_ok=True)

    print(f"\n{'#' * 70}")
    print("Experiment 1: Single Node vs Multi Node Comparison")
    print(f"{'#' * 70}")
    print(f"Output directory: {output_dir}")
    print(f"Pipeline type: {pipeline_type}")
    print(f"Quick mode: {quick_mode}")

    all_results = []

    # 1. 节点扩展实验
    if quick_mode:
        node_counts = [1, 4]
        num_tasks = 50
    else:
        node_counts = [1, 4, 8, 16]
        num_tasks = 500

    print(f"\n--- Part 1: Node Scaling (tasks={num_tasks}) ---")
    node_results = run_node_scaling_experiment(
        num_tasks=num_tasks,
        node_counts=node_counts,
        output_dir=os.path.join(output_dir, "node_scaling"),
        pipeline_type=pipeline_type,
    )
    all_results.extend(node_results)

    # 2. 任务规模扩展实验 (固定 4 节点)
    if quick_mode:
        task_counts = [50, 100]
    else:
        task_counts = [100, 500, 1000]

    print("\n--- Part 2: Task Scaling (nodes=4) ---")
    task_results = run_task_scaling_experiment(
        task_counts=task_counts,
        num_nodes=4,
        output_dir=os.path.join(output_dir, "task_scaling"),
        pipeline_type=pipeline_type,
    )
    all_results.extend(task_results)

    # 生成总体报
    if all_results:
        generate_comparison_report(all_results, output_dir, "full_experiment_report")
        plot_results(all_results, output_dir, "full_experiment")

    print(f"\n{'=' * 70}")
    print("Experiment completed.")
    print(f"Results saved to: {output_dir}")
    print(f"{'=' * 70}")


def main():
    parser = argparse.ArgumentParser(description="Experiment 1: Single vs Multi Node")
    parser.add_argument("--quick", action="store_true", help="Quick test mode")
    parser.add_argument("--nodes", nargs="+", type=int, help="Node counts to test")
    parser.add_argument("--tasks", type=int, default=500, help="Number of tasks")
    parser.add_argument(
        "--pipeline",
        choices=["compute", "llm", "rag", "rag_service", "simple_rag", "adaptive_rag", "mixed"],
        default="compute",
        help="Pipeline type",
    )
    parser.add_argument("--output", type=str, help="Output directory")

    parser.add_argument(
        "--llm-output", type=str, help="File path to save LLM responses (JSONL format)"
    )
    args = parser.parse_args()

    if args.nodes:
        # 指定节点数的实验
        run_node_scaling_experiment(
            num_tasks=args.tasks,
            node_counts=args.nodes,
            output_dir=args.output,
            pipeline_type=args.pipeline,
        )
    else:
        # 完整实验
        run_full_experiment(
            quick_mode=args.quick,
            pipeline_type=args.pipeline,
        )


if __name__ == "__main__":
    main()
