#!/usr/bin/env python3
"""
'ENDOFFILE'2: 高负载流
============================

        self.total_latency = 0.0Sage 的流水线并行调度能力。

'ENDOFFILE''ENDOFFILE''ENDOFFILE':
- 不同负载级别: 低(4并行)、中(16并行)、高(64并行)、极高(128并行)
- 不同调度策略对比: FIFO, LoadAware, RoundRobin, Priority
- 不同流水线深度: 2阶段, 3阶段, 5阶段


:
    python run_experiment.py                    # 运行全部实验
    python run_experiment.py --quick            # 快速测试模式
    python run_experiment.py --schedulers fifo load_aware  # 指定调度器
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

# 负载级别配置
LOAD_LEVELS = {
    "low": {
        "description": "低负载 (4 并行)",
        "parallelism": 4,
        "num_nodes": 2,
        "num_tasks": 100,
    },
    "medium": {
        "description": "中负载 (16 并行)",
        "parallelism": 16,
        "num_nodes": 4,
        "num_tasks": 200,
    },
    "high": {
        "description": "高负载 (64 并行)",
        "parallelism": 64,
        "num_nodes": 8,
        "num_tasks": 500,
    },
    "extreme": {
        "description": "极高负载 (128 并行)",
        "parallelism": 128,
        "num_nodes": 16,
        "num_tasks": 1000,
    },
}

# 调度器配置
SCHEDULERS = {
    "fifo": {"scheduler_type": "fifo"},
    "load_aware_spread": {"scheduler_type": "load_aware", "scheduler_strategy": "spread"},
    "load_aware_pack": {"scheduler_type": "load_aware", "scheduler_strategy": "pack"},
    "round_robin": {"scheduler_type": "round_robin"},
    "priority": {"scheduler_type": "priority"},
}

# 流水线深度配置
PIPELINE_DEPTHS = {
    "shallow": {"pipeline_stages": 2, "description": "2阶段流水线"},
    "medium": {"pipeline_stages": 3, "description": "3阶段流水线"},
    "deep": {"pipeline_stages": 5, "description": "5阶段流水线"},
}


def run_single_experiment(
    name: str,
    config_dict: dict,
    output_dir: str,
) -> BenchmarkMetrics:
    """运行单个实验配置"""
    print(f"\n{'=' * 70}")
    print(f"Running: {name}")
    print(f"Config: {config_dict}")
    print(f"{'=' * 70}")

    config = BenchmarkConfig(
        experiment_name=name,
        use_remote=config_dict.get("use_remote", True),
        **{k: v for k, v in config_dict.items() if k != "use_remote"},
    )

    pipeline = SchedulingBenchmarkPipeline(config)
    pipeline.build_compute_pipeline(name)

    if config.use_remote:
        metrics = pipeline.run_with_warmup()
    else:
        metrics = pipeline.run()

    save_detailed_results(metrics, output_dir, name)
    metrics.print_summary()

    return metrics


def run_load_level_experiment(
    load_levels: list[str] | None = None,
    scheduler_type: str = "load_aware",
    output_dir: str | None = None,
) -> list[tuple[str, BenchmarkMetrics]]:
    """
    不同负载级别对比实验。

    固定调度策略，测试不同负载级别下的性能。
    """
    if load_levels is None:
        load_levels = ["low", "medium", "high"]

    if output_dir is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = str(SCRIPT_DIR / "results" / f"load_levels_{timestamp}")

    os.makedirs(output_dir, exist_ok=True)

    results = []

    for level in load_levels:
        if level not in LOAD_LEVELS:
            print(f"Unknown load level: {level}, skipping")
            continue

        level_config = LOAD_LEVELS[level].copy()
        config_name = f"load_{level}_{scheduler_type}"

        # 添加调度器配置
        if scheduler_type in SCHEDULERS:
            level_config.update(SCHEDULERS[scheduler_type])
        else:
            level_config["scheduler_type"] = scheduler_type

        try:
            metrics = run_single_experiment(
                name=config_name,
                config_dict=level_config,
                output_dir=output_dir,
            )
            results.append((config_name, metrics))
        except Exception as e:
            print(f"Error running {config_name}: {e}")
            import traceback

            traceback.print_exc()

    if results:
        generate_comparison_report(results, output_dir, "load_levels_comparison")
        plot_results(results, output_dir, "load_levels")

    return results


def run_scheduler_comparison_experiment(
    schedulers: list[str] | None = None,
    load_level: str = "medium",
    output_dir: str | None = None,
) -> list[tuple[str, BenchmarkMetrics]]:
    """
    调度策略对比实验。

    固定负载级别，对比不同调度策略的性能。
    """
    if schedulers is None:
        schedulers = ["fifo", "load_aware_spread", "round_robin"]

    if output_dir is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = str(SCRIPT_DIR / "results" / f"scheduler_comparison_{timestamp}")

    os.makedirs(output_dir, exist_ok=True)

    base_config = LOAD_LEVELS.get(load_level, LOAD_LEVELS["medium"]).copy()
    results = []

    for scheduler in schedulers:
        config_name = f"scheduler_{scheduler}_{load_level}"
        config = base_config.copy()

        if scheduler in SCHEDULERS:
            config.update(SCHEDULERS[scheduler])
        else:
            config["scheduler_type"] = scheduler

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
        generate_comparison_report(results, output_dir, "scheduler_comparison")
        plot_results(results, output_dir, "scheduler")

    return results


def run_pipeline_depth_experiment(
    depths: list[str] | None = None,
    load_level: str = "medium",
    output_dir: str | None = None,
) -> list[tuple[str, BenchmarkMetrics]]:
    """
    流水线深度对比实验。

    测试不同流水线阶段数对性能的影响。
    """
    if depths is None:
        depths = ["shallow", "medium", "deep"]

    if output_dir is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = str(SCRIPT_DIR / "results" / f"pipeline_depth_{timestamp}")

    os.makedirs(output_dir, exist_ok=True)

    base_config = LOAD_LEVELS.get(load_level, LOAD_LEVELS["medium"]).copy()
    base_config.update(SCHEDULERS["load_aware_spread"])
    results = []

    for depth in depths:
        if depth not in PIPELINE_DEPTHS:
            print(f"Unknown depth: {depth}, skipping")
            continue

        config_name = f"depth_{depth}_{load_level}"
        config = base_config.copy()
        config["pipeline_stages"] = PIPELINE_DEPTHS[depth]["pipeline_stages"]

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
        generate_comparison_report(results, output_dir, "pipeline_depth_comparison")
        plot_results(results, output_dir, "pipeline_depth")

    return results


def run_full_experiment(quick_mode: bool = False) -> None:
    """运行完整实验"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = str(SCRIPT_DIR / "results" / f"full_experiment_{timestamp}")
    os.makedirs(output_dir, exist_ok=True)

    print(f"\n{'#' * 70}")
    print("Experiment 2: High Load Pipeline Parallel Scheduling")
    print(f"{'#' * 70}")
    print(f"Output directory: {output_dir}")
    print(f"Quick mode: {quick_mode}")

    all_results = []

    # 1. 负载级别实验
    if quick_mode:
        load_levels = ["low", "medium"]
    else:
        load_levels = ["low", "medium", "high"]

    print("\n--- Part 1: Load Level Comparison ---")
    load_results = run_load_level_experiment(
        load_levels=load_levels,
        scheduler_type="load_aware",
        output_dir=os.path.join(output_dir, "load_levels"),
    )
    all_results.extend(load_results)

    # 2. 调度策略对比
    if quick_mode:
        schedulers = ["fifo", "load_aware_spread"]
    else:
        schedulers = ["fifo", "load_aware_spread", "load_aware_pack", "round_robin"]

    print("\n--- Part 2: Scheduler Comparison ---")
    scheduler_results = run_scheduler_comparison_experiment(
        schedulers=schedulers,
        load_level="medium",
        output_dir=os.path.join(output_dir, "scheduler_comparison"),
    )
    all_results.extend(scheduler_results)

    # 3. 流水线深度实验
    if quick_mode:
        depths = ["shallow", "medium"]
    else:
        depths = ["shallow", "medium", "deep"]

    print("\n--- Part 3: Pipeline Depth Comparison ---")
    depth_results = run_pipeline_depth_experiment(
        depths=depths,
        load_level="medium",
        output_dir=os.path.join(output_dir, "pipeline_depth"),
    )
    all_results.extend(depth_results)

    # 生成总体报告
    if all_results:
        generate_comparison_report(all_results, output_dir, "full_experiment_report")
        plot_results(all_results, output_dir, "full_experiment")

    print(f"\n{'=' * 70}")
    print("Experiment completed.")
    print(f"Results saved to: {output_dir}")
    print(f"{'=' * 70}")


def main():
    parser = argparse.ArgumentParser(description="Experiment 2: High Load Parallel Scheduling")
    parser.add_argument("--quick", action="store_true", help="Quick test mode")
    parser.add_argument("--schedulers", nargs="+", help="Schedulers to test")
    parser.add_argument("--load-levels", nargs="+", help="Load levels to test")
    parser.add_argument("--depths", nargs="+", help="Pipeline depths to test")
    parser.add_argument("--output", type=str, help="Output directory")

    args = parser.parse_args()

    if args.schedulers:
        run_scheduler_comparison_experiment(
            schedulers=args.schedulers,
            output_dir=args.output,
        )
    elif args.load_levels:
        run_load_level_experiment(
            load_levels=args.load_levels,
            output_dir=args.output,
        )
    elif args.depths:
        run_pipeline_depth_experiment(
            depths=args.depths,
            output_dir=args.output,
        )
    else:
        run_full_experiment(quick_mode=args.quick)


if __name__ == "__main__":
    main()
