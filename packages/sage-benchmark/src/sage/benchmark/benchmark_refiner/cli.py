#!/usr/bin/env python3
"""
Refiner Benchmark CLI
=====================

Command-line interface for running Refiner algorithm benchmarks.

Usage:
    # Quick comparison of algorithms
    sage-refiner-bench compare --algorithms baseline,longrefiner,reform --samples 100

    # Run from config file
    sage-refiner-bench run --config experiment.yaml

    # Budget sweep
    sage-refiner-bench sweep --algorithm longrefiner --budgets 512,1024,2048,4096

    # Head analysis for REFORM
    sage-refiner-bench heads --model llama-3.1-8b --dataset nq --samples 100
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        prog="sage-refiner-bench",
        description="🚀 SAGE Refiner Algorithm Benchmark",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Quick algorithm comparison
  %(prog)s compare --algorithms baseline,longrefiner,reform,provence --samples 50

  # Run from YAML config
  %(prog)s run --config my_experiment.yaml

  # Sweep different budgets
  %(prog)s sweep --algorithm longrefiner --budgets 512,1024,2048,4096

  # Generate example config
  %(prog)s config --output experiment.yaml

  # Run head analysis (for REFORM)
  %(prog)s heads --model /path/to/model --dataset nq --samples 100
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # ========================================================================
    # compare command
    # ========================================================================
    compare_parser = subparsers.add_parser(
        "compare",
        help="Compare multiple Refiner algorithms",
    )
    compare_parser.add_argument(
        "--algorithms",
        "-a",
        type=str,
        default="baseline,longrefiner,reform,provence",
        help="Comma-separated list of algorithms to compare",
    )
    compare_parser.add_argument(
        "--samples",
        "-n",
        type=int,
        default=50,
        help="Number of samples to evaluate",
    )
    compare_parser.add_argument(
        "--budget",
        "-b",
        type=int,
        default=2048,
        help="Token budget for compression",
    )
    compare_parser.add_argument(
        "--datasets",
        type=str,
        default="nq",
        help="Comma-separated dataset names: nq,hotpotqa,triviaqa,2wikimultihopqa,asqa,musique,popqa,webq. Use 'all' for all datasets.",
    )
    compare_parser.add_argument(
        "--dataset",
        "-d",
        type=str,
        default=None,
        help="[Deprecated] Single dataset. Use --datasets instead.",
    )
    compare_parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="./.benchmarks/refiner",
        help="Output directory",
    )
    compare_parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress progress output",
    )

    # ========================================================================
    # run command
    # ========================================================================
    run_parser = subparsers.add_parser(
        "run",
        help="Run experiment from config file",
    )
    run_parser.add_argument(
        "--config",
        "-c",
        type=str,
        required=True,
        help="Path to YAML config file",
    )
    run_parser.add_argument(
        "--type",
        "-t",
        type=str,
        default="comparison",
        choices=["comparison", "quality", "latency", "compression"],
        help="Experiment type",
    )
    run_parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress progress output",
    )

    # ========================================================================
    # sweep command
    # ========================================================================
    sweep_parser = subparsers.add_parser(
        "sweep",
        help="Sweep across different budgets for an algorithm",
    )
    sweep_parser.add_argument(
        "--algorithm",
        "-a",
        type=str,
        required=True,
        help="Algorithm to sweep",
    )
    sweep_parser.add_argument(
        "--budgets",
        "-b",
        type=str,
        default="512,1024,2048,4096",
        help="Comma-separated list of budgets to test",
    )
    sweep_parser.add_argument(
        "--samples",
        "-n",
        type=int,
        default=50,
        help="Number of samples per budget",
    )
    sweep_parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="./.benchmarks/refiner",
        help="Output directory",
    )
    sweep_parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress progress output",
    )

    # ========================================================================
    # config command
    # ========================================================================
    config_parser = subparsers.add_parser(
        "config",
        help="Generate example configuration file",
    )
    config_parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="refiner_experiment.yaml",
        help="Output file path",
    )

    # ========================================================================
    # heads command
    # ========================================================================
    heads_parser = subparsers.add_parser(
        "heads",
        help="Run attention head analysis (for REFORM)",
    )
    heads_parser.add_argument(
        "--config",
        "-c",
        type=str,
        help="Path to head analysis config file",
    )
    heads_parser.add_argument(
        "--model",
        "-m",
        type=str,
        help="Model name or path",
    )
    heads_parser.add_argument(
        "--dataset",
        "-d",
        type=str,
        default="nq",
        help="Dataset to use",
    )
    heads_parser.add_argument(
        "--samples",
        "-n",
        type=int,
        default=100,
        help="Number of samples",
    )
    heads_parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="./.benchmarks/head_analysis",
        help="Output directory",
    )
    heads_parser.add_argument(
        "--device",
        type=str,
        default="cuda",
        help="Device to use (cuda, cpu)",
    )
    heads_parser.add_argument(
        "--top-k",
        type=int,
        default=20,
        help="Number of top heads to report",
    )

    # ========================================================================
    # report command - LaTeX table export
    # ========================================================================
    report_parser = subparsers.add_parser(
        "report",
        help="Generate LaTeX tables from experiment results",
    )
    report_parser.add_argument(
        "results_file",
        type=str,
        help="Path to results JSON file",
    )
    report_parser.add_argument(
        "--format",
        "-f",
        type=str,
        default="latex",
        choices=["latex", "markdown", "both"],
        help="Output format",
    )
    report_parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="./tables",
        help="Output directory for generated tables",
    )
    report_parser.add_argument(
        "--baseline",
        "-b",
        type=str,
        default="baseline",
        help="Baseline algorithm name for significance tests",
    )
    report_parser.add_argument(
        "--metrics",
        "-m",
        type=str,
        default="f1,compression_rate,total_time",
        help="Comma-separated metrics to include in main table",
    )
    report_parser.add_argument(
        "--no-significance",
        action="store_true",
        help="Disable significance markers in tables",
    )

    return parser


def cmd_compare(args: argparse.Namespace) -> int:
    """Run algorithm comparison."""
    from sage.benchmark.benchmark_refiner.experiments.base_experiment import (
        AVAILABLE_DATASETS,
    )
    from sage.benchmark.benchmark_refiner.experiments.runner import (
        RefinerExperimentRunner,
    )

    algorithms = [a.strip() for a in args.algorithms.split(",")]

    # 处理数据集参数
    if args.dataset:  # 向后兼容：优先使用旧参数
        datasets = [args.dataset.strip()]
        print("\n⚠️  Warning: --dataset is deprecated, use --datasets instead.")
    elif args.datasets == "all":
        datasets = AVAILABLE_DATASETS.copy()
    else:
        datasets = [d.strip() for d in args.datasets.split(",")]

    # 验证数据集
    invalid_datasets = [d for d in datasets if d not in AVAILABLE_DATASETS]
    if invalid_datasets:
        print(f"\n❌ Unknown datasets: {invalid_datasets}")
        print(f"   Available: {AVAILABLE_DATASETS}")
        return 1

    print(f"\n🚀 Comparing Refiner algorithms: {', '.join(algorithms)}")
    print(f"   Samples: {args.samples}")
    print(f"   Budget: {args.budget}")
    print(f"   Datasets: {', '.join(datasets)}")
    print(f"   Output: {args.output}")

    runner = RefinerExperimentRunner(verbose=not args.quiet)
    result = runner.quick_compare(
        algorithms=algorithms,
        max_samples=args.samples,
        budget=args.budget,
        datasets=datasets,
        output_dir=args.output,
    )

    if result.success:
        runner.print_comparison_table(result)
        print(f"\n✅ Results saved to: {args.output}")
        return 0
    else:
        print(f"\n❌ Experiment failed: {result.error}")
        return 1


def cmd_run(args: argparse.Namespace) -> int:
    """Run experiment from config."""
    from sage.benchmark.benchmark_refiner.experiments.runner import (
        RefinerExperimentRunner,
    )

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"❌ Config file not found: {config_path}")
        return 1

    print(f"\n📄 Loading config from: {config_path}")

    runner = RefinerExperimentRunner(verbose=not args.quiet)
    result = runner.run_from_config(str(config_path), args.type)

    if result.success:
        runner.print_comparison_table(result)
        return 0
    else:
        print(f"\n❌ Experiment failed: {result.error}")
        return 1


def cmd_sweep(args: argparse.Namespace) -> int:
    """Run budget sweep."""
    from sage.benchmark.benchmark_refiner.experiments.runner import (
        RefinerExperimentRunner,
    )

    budgets = [int(b.strip()) for b in args.budgets.split(",")]

    print(f"\n📊 Sweeping budgets for algorithm: {args.algorithm}")
    print(f"   Budgets: {budgets}")
    print(f"   Samples: {args.samples}")

    runner = RefinerExperimentRunner(verbose=not args.quiet)
    results = runner.compare_budgets(
        algorithm=args.algorithm,
        budgets=budgets,
        max_samples=args.samples,
        output_dir=args.output,
    )

    # Print summary table
    print("\n" + "=" * 60)
    print("                   Budget Sweep Results")
    print("=" * 60)
    print(f"| {'Budget':^10} | {'F1 Score':^12} | {'Compression':^12} |")
    print("|" + "-" * 12 + "|" + "-" * 14 + "|" + "-" * 14 + "|")

    for budget, result in results.items():
        if result.algorithm_metrics:
            metrics = list(result.algorithm_metrics.values())[0]
            print(
                f"| {budget:^10} | {metrics.avg_f1:^12.4f} | {metrics.avg_compression_rate:^12.2f}x |"
            )

    print("=" * 60)
    print(f"\n✅ Results saved to: {args.output}")

    return 0


def cmd_config(args: argparse.Namespace) -> int:
    """Generate example config."""
    from sage.benchmark.benchmark_refiner.experiments.base_experiment import (
        RefinerExperimentConfig,
    )

    config = RefinerExperimentConfig(
        name="example_experiment",
        description="Example Refiner benchmark experiment",
        algorithms=["baseline", "longrefiner", "reform", "provence"],
        max_samples=100,
        budget=2048,
    )

    output_path = Path(args.output)
    config.save_yaml(str(output_path))

    print(f"✅ Example config saved to: {output_path}")
    return 0


def cmd_heads(args: argparse.Namespace) -> int:
    """Run head analysis."""
    import subprocess

    # 使用已有的 find_heads.py 脚本
    cmd = [
        sys.executable,
        "-m",
        "sage.benchmark.benchmark_refiner.analysis.find_heads",
    ]

    if args.config:
        cmd.extend(["--config", args.config])
    else:
        # 需要配置文件，生成临时配置
        import tempfile

        import yaml

        if not args.model:
            print("❌ Either --config or --model must be specified")
            return 1

        config = {
            "model": args.model,
            "dataset": args.dataset,
            "num_samples": args.samples,
            "device": args.device,
            "dtype": "bfloat16",
            "top_k": args.top_k,
            "output_dir": args.output,
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config, f)
            temp_config = f.name

        cmd.extend(["--config", temp_config])

    print("\n🔍 Running head analysis...")
    result = subprocess.run(cmd)
    return result.returncode


def cmd_report(args: argparse.Namespace) -> int:
    """Generate LaTeX tables from experiment results."""
    import json

    from sage.benchmark.benchmark_refiner.analysis.latex_export import (
        generate_latency_breakdown_table,
        generate_main_results_table,
        generate_significance_table,
    )
    from sage.benchmark.benchmark_refiner.experiments.base_experiment import (
        AlgorithmMetrics,
    )

    results_path = Path(args.results_file)
    if not results_path.exists():
        print(f"❌ Results file not found: {results_path}")
        return 1

    print(f"\n📄 Loading results from: {results_path}")

    with open(results_path) as f:
        data = json.load(f)

    # 解析结果数据
    # 支持两种格式:
    # 1. 单数据集: {"algorithm_metrics": {...}, "raw_results": [...]}
    # 2. 多数据集: {"datasets": {"nq": {...}, "hotpotqa": {...}}}

    results: dict[str, dict[str, AlgorithmMetrics]] = {}
    raw_results: dict[str, dict[str, list[dict[str, Any]]]] = {}

    if "datasets" in data:
        # 多数据集格式
        for ds_name, ds_data in data["datasets"].items():
            results[ds_name] = {}
            raw_results[ds_name] = {}
            algo_metrics = ds_data.get("algorithm_metrics", {})
            for algo_name, metrics_dict in algo_metrics.items():
                results[ds_name][algo_name] = _dict_to_algorithm_metrics(algo_name, metrics_dict)
            # 原始结果按算法分组
            for sample in ds_data.get("raw_results", []):
                algo = sample.get("algorithm", "unknown")
                if algo not in raw_results[ds_name]:
                    raw_results[ds_name][algo] = []
                raw_results[ds_name][algo].append(sample)
    elif "algorithm_metrics" in data:
        # 单数据集格式
        ds_name = data.get("config", {}).get("dataset", "default")
        results[ds_name] = {}
        raw_results[ds_name] = {}
        for algo_name, metrics_dict in data["algorithm_metrics"].items():
            results[ds_name][algo_name] = _dict_to_algorithm_metrics(algo_name, metrics_dict)
        # 原始结果按算法分组
        for sample in data.get("raw_results", []):
            algo = sample.get("algorithm", "unknown")
            if algo not in raw_results[ds_name]:
                raw_results[ds_name][algo] = []
            raw_results[ds_name][algo].append(sample)
    else:
        print("❌ Unrecognized results format")
        return 1

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    metrics = [m.strip() for m in args.metrics.split(",")]

    print("\n📊 Generating tables...")
    print(f"   Baseline: {args.baseline}")
    print(f"   Metrics: {metrics}")
    print(f"   Datasets: {list(results.keys())}")
    print(f"   Output: {output_dir}")

    if args.format in ("latex", "both"):
        # 生成主结果表格
        main_table = generate_main_results_table(
            results,
            baseline=args.baseline,
            metrics=metrics,
            include_significance=not args.no_significance,
            raw_results=raw_results if not args.no_significance else None,
        )
        main_path = output_dir / "main_results.tex"
        main_path.write_text(main_table, encoding="utf-8")
        print(f"   ✅ Main results: {main_path}")

        # 延迟分解表格 (使用第一个数据集)
        if results:
            first_ds = list(results.keys())[0]
            latency_table = generate_latency_breakdown_table(results[first_ds])
            latency_path = output_dir / "latency_breakdown.tex"
            latency_path.write_text(latency_table, encoding="utf-8")
            print(f"   ✅ Latency breakdown: {latency_path}")

        # 显著性表格
        if raw_results and not args.no_significance:
            first_ds = list(raw_results.keys())[0]
            sig_table = generate_significance_table(
                raw_results[first_ds],
                baseline=args.baseline,
            )
            sig_path = output_dir / "significance.tex"
            sig_path.write_text(sig_table, encoding="utf-8")
            print(f"   ✅ Significance: {sig_path}")

    if args.format in ("markdown", "both"):
        # 生成 Markdown 格式的报告
        from sage.benchmark.benchmark_refiner.analysis.statistical import (
            generate_significance_report,
        )

        if raw_results:
            first_ds = list(raw_results.keys())[0]
            # 将原始结果转换为分数列表
            f1_results = {}
            for algo, samples in raw_results[first_ds].items():
                f1_results[algo] = [s.get("f1", s.get("avg_f1", 0)) for s in samples]

            if f1_results:
                md_report = generate_significance_report(
                    f1_results,
                    baseline_name=args.baseline,
                )
                md_path = output_dir / "significance_report.md"
                md_path.write_text(md_report, encoding="utf-8")
                print(f"   ✅ Markdown report: {md_path}")

    print(f"\n✅ Tables generated in: {output_dir}")
    return 0


def _dict_to_algorithm_metrics(name: str, data: dict[str, Any]):
    """将字典转换为 AlgorithmMetrics 对象"""
    from sage.benchmark.benchmark_refiner.experiments.base_experiment import (
        AlgorithmMetrics,
    )

    # 处理嵌套结构
    quality = data.get("quality", {})
    compression = data.get("compression", {})
    latency = data.get("latency", {})

    return AlgorithmMetrics(
        algorithm=name,
        num_samples=data.get("num_samples", 0),
        avg_f1=quality.get("avg_f1", data.get("avg_f1", 0)),
        avg_recall=quality.get("avg_recall", data.get("avg_recall", 0)),
        avg_rouge_l=quality.get("avg_rouge_l", data.get("avg_rouge_l", 0)),
        avg_accuracy=quality.get("avg_accuracy", data.get("avg_accuracy", 0)),
        avg_compression_rate=compression.get(
            "avg_compression_rate", data.get("avg_compression_rate", 0)
        ),
        avg_original_tokens=compression.get(
            "avg_original_tokens", data.get("avg_original_tokens", 0)
        ),
        avg_compressed_tokens=compression.get(
            "avg_compressed_tokens", data.get("avg_compressed_tokens", 0)
        ),
        avg_retrieve_time=latency.get("avg_retrieve_time", data.get("avg_retrieve_time", 0)),
        avg_refine_time=latency.get("avg_refine_time", data.get("avg_refine_time", 0)),
        avg_generate_time=latency.get("avg_generate_time", data.get("avg_generate_time", 0)),
        avg_total_time=latency.get("avg_total_time", data.get("avg_total_time", 0)),
        std_f1=quality.get("std_f1", data.get("std_f1", 0)),
        std_compression_rate=compression.get(
            "std_compression_rate", data.get("std_compression_rate", 0)
        ),
        std_total_time=latency.get("std_total_time", data.get("std_total_time", 0)),
    )


def main() -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 0

    commands: dict[str, Any] = {
        "compare": cmd_compare,
        "run": cmd_run,
        "sweep": cmd_sweep,
        "config": cmd_config,
        "heads": cmd_heads,
        "report": cmd_report,
    }

    handler = commands.get(args.command)
    if handler:
        return handler(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
