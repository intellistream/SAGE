#!/usr/bin/env python3
"""
SAGE-Bench Paper 1 Experiment Runner

统一入口，按论文 Experiment Section 顺序运行所有实验。

Usage:
    # 运行所有实验
    python run_paper1_experiments.py

    # 快速模式 (少量样本)
    python run_paper1_experiments.py --quick

    # 仅主实验 (Section 5.2)
    python run_paper1_experiments.py --section 5.2

    # 仅分析实验 (Section 5.3)
    python run_paper1_experiments.py --section 5.3

    # 单独运行某个实验
    python run_paper1_experiments.py --exp timing
    python run_paper1_experiments.py --exp scaling
    python run_paper1_experiments.py --exp cross-dataset

    # 跳过 LLM 方法 (快速测试)
    python run_paper1_experiments.py --skip-llm

输出目录:
    .sage/benchmark/paper1/
    ├── section_5_2_main/
    ├── section_5_3_analysis/
    ├── section_5_4_generalization/
    ├── figures/
    └── tables/
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

# 添加实验模块路径
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))


def print_banner():
    """打印启动 banner。"""
    banner = """
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║   ███████╗ █████╗  ██████╗ ███████╗      ██████╗ ███████╗███╗   ██╗  ║
║   ██╔════╝██╔══██╗██╔════╝ ██╔════╝      ██╔══██╗██╔════╝████╗  ██║  ║
║   ███████╗███████║██║  ███╗█████╗  █████╗██████╔╝█████╗  ██╔██╗ ██║  ║
║   ╚════██║██╔══██║██║   ██║██╔══╝  ╚════╝██╔══██╗██╔══╝  ██║╚██╗██║  ║
║   ███████║██║  ██║╚██████╔╝███████╗      ██████╔╝███████╗██║ ╚████║  ║
║   ╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝      ╚═════╝ ╚══════╝╚═╝  ╚═══╝  ║
║                                                                      ║
║            Paper 1: Benchmark Experiments Runner                     ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
"""
    print(banner)


def run_section_5_2(args) -> dict[str, Any]:
    """
    Section 5.2: Main Results (RQ1-RQ3)
    """
    print("\n" + "=" * 70)
    print("📊 SECTION 5.2: MAIN RESULTS")
    print("=" * 70)

    results = {}
    max_samples = 50 if args.quick else 150

    # RQ1: Timing Detection
    if not args.exp or args.exp in ["timing", "all"]:
        print("\n▶ Running RQ1: Timing Detection...")
        try:
            from experiments.exp_main_timing import run_timing_experiment

            results["timing"] = run_timing_experiment(
                max_samples=max_samples,
                skip_llm=args.skip_llm,
                verbose=args.verbose,
            )
        except Exception as e:
            print(f"  ❌ Timing experiment failed: {e}")
            results["timing"] = None

    # RQ2: Task Planning
    if not args.exp or args.exp in ["planning", "all"]:
        print("\n▶ Running RQ2: Task Planning...")
        try:
            from experiments.exp_main_planning import run_planning_experiment

            results["planning"] = run_planning_experiment(
                max_samples=max_samples,
                skip_llm=args.skip_llm,
                verbose=args.verbose,
            )
        except Exception as e:
            print(f"  ❌ Planning experiment failed: {e}")
            results["planning"] = None

    # RQ3: Tool Selection
    if not args.exp or args.exp in ["selection", "all"]:
        print("\n▶ Running RQ3: Tool Selection...")
        try:
            from experiments.exp_main_selection import run_selection_experiment

            results["selection"] = run_selection_experiment(
                max_samples=max_samples,
                top_k=5,
                skip_llm=args.skip_llm,
                verbose=args.verbose,
            )
        except Exception as e:
            print(f"  ❌ Selection experiment failed: {e}")
            results["selection"] = None

    return results


def run_section_5_3(args) -> dict[str, Any]:
    """
    Section 5.3: Analysis & Discussion
    """
    print("\n" + "=" * 70)
    print("🔬 SECTION 5.3: ANALYSIS & DISCUSSION")
    print("=" * 70)

    results = {}
    max_samples = 30 if args.quick else 100

    # 5.3.1 Error Analysis
    if not args.exp or args.exp in ["error", "all"]:
        print("\n▶ Running 5.3.1: Error Analysis...")
        try:
            from experiments.exp_analysis_error import run_error_analysis

            results["error_analysis"] = run_error_analysis(
                challenge="all",
                verbose=args.verbose,
            )
        except Exception as e:
            print(f"  ❌ Error analysis failed: {e}")
            results["error_analysis"] = None

    # 5.3.2 Scaling Analysis
    if not args.exp or args.exp in ["scaling", "all"]:
        print("\n▶ Running 5.3.2: Scaling Analysis...")
        try:
            from experiments.exp_analysis_scaling import run_scaling_analysis

            # 判断是否运行真实 LLM Scaling
            run_llm_scaling = not args.skip_llm and not getattr(args, "skip_llm_scaling", False)

            results["scaling_analysis"] = run_scaling_analysis(
                tool_scaling=True,
                llm_scaling=run_llm_scaling,
                max_samples=max_samples,
                verbose=args.verbose,
            )
        except Exception as e:
            print(f"  ❌ Scaling analysis failed: {e}")
            results["scaling_analysis"] = None

    # 5.3.3 Robustness Analysis
    if not args.exp or args.exp in ["robustness", "all"]:
        print("\n▶ Running 5.3.3: Robustness Analysis...")
        try:
            from experiments.exp_analysis_robustness import run_robustness_analysis

            results["robustness_analysis"] = run_robustness_analysis(
                semantic_variation=True,
                instruction_quality=True,
                reliability=True,
                max_samples=max_samples,
                verbose=args.verbose,
            )
        except Exception as e:
            print(f"  ❌ Robustness analysis failed: {e}")
            results["robustness_analysis"] = None

    # 5.3.4 Ablation Studies
    if not args.exp or args.exp in ["ablation", "all"]:
        print("\n▶ Running 5.3.4: Ablation Studies...")
        try:
            from experiments.exp_analysis_ablation import run_ablation_study

            results["ablation_study"] = run_ablation_study(
                prompt_ablation=True,
                hybrid_ablation=True,
                max_samples=max_samples,
                verbose=args.verbose,
            )
        except Exception as e:
            print(f"  ❌ Ablation study failed: {e}")
            results["ablation_study"] = None

    return results


def run_section_5_4(args) -> dict[str, Any]:
    """
    Section 5.4: Cross-Dataset Generalization
    """
    print("\n" + "=" * 70)
    print("🌐 SECTION 5.4: CROSS-DATASET GENERALIZATION")
    print("=" * 70)

    results = {}
    max_samples = 50 if args.quick else 100

    if not args.exp or args.exp in ["cross-dataset", "all"]:
        print("\n▶ Running Cross-Dataset Evaluation...")
        try:
            from experiments.exp_cross_dataset import run_cross_dataset_evaluation

            results["cross_dataset"] = run_cross_dataset_evaluation(
                datasets=["sage", "acebench"],
                max_samples=max_samples,
                verbose=args.verbose,
            )
        except Exception as e:
            print(f"  ❌ Cross-dataset evaluation failed: {e}")
            results["cross_dataset"] = None

    return results


def print_final_summary(all_results: dict[str, Any], elapsed_time: float):
    """打印最终汇总。"""
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 20 + "EXPERIMENT SUMMARY" + " " * 30 + "║")
    print("╚" + "═" * 68 + "╝")

    # Section 5.2 Summary
    if "section_5_2" in all_results:
        print("\n📊 Section 5.2: Main Results")
        print("-" * 50)
        for challenge, result in all_results["section_5_2"].items():
            if result and hasattr(result, "target_met"):
                status = "✅ PASS" if result.target_met else "❌ FAIL"
                best = f"{result.best_metric * 100:.1f}%" if result.best_metric else "N/A"
                print(f"  {challenge:15s}: {best:>8s} {status}")

    # Section 5.3 Summary
    if "section_5_3" in all_results:
        print("\n🔬 Section 5.3: Analysis")
        print("-" * 50)
        for analysis, result in all_results["section_5_3"].items():
            status = "✅ Done" if result else "❌ Failed"
            print(f"  {analysis:20s}: {status}")

    # Section 5.4 Summary
    if "section_5_4" in all_results:
        print("\n🌐 Section 5.4: Generalization")
        print("-" * 50)
        for eval_name, result in all_results["section_5_4"].items():
            status = "✅ Done" if result else "❌ Failed"
            print(f"  {eval_name:20s}: {status}")

    # Section 5.5 Summary
    if "section_5_5" in all_results:
        print("\n🎓 Section 5.5: Training Comparison")
        print("-" * 50)
        tc = all_results["section_5_5"].get("training_comparison")
        if tc and hasattr(tc, "best_method"):
            print(f"  Best method: {tc.best_method}")
            print(f"  Best score: {tc.best_score * 100:.1f}%")
        elif tc:
            status = "✅ Done"
            print(f"  training_comparison: {status}")
        else:
            print("  training_comparison: ❌ Failed")

    # Timing
    print("\n" + "=" * 50)
    print(f"  Total time: {elapsed_time / 60:.1f} minutes")
    print(f"  Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)


def run_section_5_5(args) -> dict[str, Any]:
    """
    Section 5.5: Training Method Comparison
    """
    print("\n" + "=" * 70)
    print("🎓 SECTION 5.5: TRAINING METHOD COMPARISON")
    print("=" * 70)

    results = {}

    if not args.exp or args.exp in ["training", "all"]:
        print("\n▶ Running Training Method Comparison...")
        try:
            from experiments.exp_training_comparison import run_training_comparison

            # Paper 1 compares published SOTA training methods
            # SIAS methods (B_coreset, C_continual, D_combined) are for Paper 2
            if args.train_methods:
                methods = args.train_methods.split(",")
            else:
                # Paper 1 default: compare published SOTA methods
                methods = [
                    "A_baseline",  # Standard SFT (full params)
                    "A_lora",  # LoRA (Hu et al., 2021)
                    "A_qlora",  # QLoRA (Dettmers et al., 2023)
                    "A_fireact",  # FireAct trajectory tuning
                    "A_agenttuning",  # AgentTuning multi-task
                ]

            results["training_comparison"] = run_training_comparison(
                methods=methods,
                base_model=args.train_model,
                quick=args.quick,
                dry_run=args.dry_run,
                verbose=args.verbose,
            )
        except Exception as e:
            print(f"  ❌ Training comparison failed: {e}")
            results["training_comparison"] = None

    return results


def generate_paper_materials(all_results: dict[str, Any], output_dir: Path):
    """生成论文所需的 figures 和 tables。"""
    print("\n" + "=" * 70)
    print("📝 GENERATING PAPER MATERIALS")
    print("=" * 70)

    try:
        from experiments.table_generator import generate_all_tables

        # 收集所有结果
        collected = {
            "timing": [],
            "planning": [],
            "selection": [],
            "training": [],
            "ablation": {},
            "cross_dataset": {},
        }

        # 从 section_5_2 收集
        if "section_5_2" in all_results:
            s52 = all_results["section_5_2"]
            if s52.get("timing"):
                collected["timing"] = [
                    r.to_dict() if hasattr(r, "to_dict") else r
                    for r in (s52["timing"].results if hasattr(s52["timing"], "results") else [])
                ]
            if s52.get("planning"):
                collected["planning"] = [
                    r.to_dict() if hasattr(r, "to_dict") else r
                    for r in (
                        s52["planning"].results if hasattr(s52["planning"], "results") else []
                    )
                ]
            if s52.get("selection"):
                collected["selection"] = [
                    r.to_dict() if hasattr(r, "to_dict") else r
                    for r in (
                        s52["selection"].results if hasattr(s52["selection"], "results") else []
                    )
                ]

        # 从 section_5_5 收集训练结果
        if "section_5_5" in all_results:
            s55 = all_results["section_5_5"]
            if s55.get("training_comparison"):
                tc = s55["training_comparison"]
                if hasattr(tc, "results"):
                    collected["training"] = [r.to_dict() for r in tc.results]

        # 生成表格
        generate_all_tables(collected, output_dir / "tables")
        print("  ✓ LaTeX tables generated")

    except Exception as e:
        print(f"  ⚠️  Failed to generate tables: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="SAGE-Bench Paper 1 Experiment Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all experiments
  python run_paper1_experiments.py

  # Quick mode (fewer samples)
  python run_paper1_experiments.py --quick

  # Run specific section
  python run_paper1_experiments.py --section 5.2    # Main results only
  python run_paper1_experiments.py --section 5.5    # Training comparison

  # Run specific experiment
  python run_paper1_experiments.py --exp timing
  python run_paper1_experiments.py --exp training

  # Skip LLM-based methods (faster)
  python run_paper1_experiments.py --skip-llm

  # Training method comparison
  python run_paper1_experiments.py --exp training --train-methods A_baseline,D_combined
  python run_paper1_experiments.py --exp training --dry-run

  # LLM service management
  python run_paper1_experiments.py --llm-status
  python run_paper1_experiments.py --llm-start
  python run_paper1_experiments.py --llm-stop
        """,
    )

    parser.add_argument(
        "--section",
        type=str,
        choices=["5.2", "5.3", "5.4", "5.5", "all"],
        default="all",
        help="Run specific section (default: all)",
    )

    parser.add_argument(
        "--exp",
        type=str,
        choices=[
            "timing",
            "planning",
            "selection",  # 5.2
            "error",
            "scaling",
            "robustness",
            "ablation",  # 5.3
            "cross-dataset",  # 5.4
            "training",  # 5.5
            "all",
        ],
        default=None,
        help="Run specific experiment only",
    )

    parser.add_argument(
        "--quick",
        action="store_true",
        help="Quick mode with fewer samples",
    )

    parser.add_argument(
        "--skip-llm",
        action="store_true",
        help="Skip LLM-based methods (faster)",
    )

    parser.add_argument(
        "--skip-llm-scaling",
        action="store_true",
        help="Skip real LLM Scaling test (uses estimates instead)",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        default=True,
        help="Verbose output",
    )

    # Training comparison arguments
    parser.add_argument(
        "--train-methods",
        type=str,
        default=None,
        help="Training methods to compare, comma-separated (e.g., A_baseline,D_combined)",
    )

    parser.add_argument(
        "--train-model",
        type=str,
        default="Qwen/Qwen2.5-1.5B-Instruct",
        help="Base model for training comparison",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate training without actual model training",
    )

    # LLM service management
    parser.add_argument(
        "--llm-status",
        action="store_true",
        help="Check LLM service status",
    )

    parser.add_argument(
        "--llm-start",
        action="store_true",
        help="Start LLM service",
    )

    parser.add_argument(
        "--llm-stop",
        action="store_true",
        help="Stop LLM service",
    )

    parser.add_argument(
        "--llm-model",
        type=str,
        default="Qwen/Qwen2.5-0.5B-Instruct",
        help="Model for LLM service",
    )

    parser.add_argument(
        "--llm-port",
        type=int,
        default=8901,
        help="Port for LLM service",
    )

    # Output
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Output directory for results",
    )

    parser.add_argument(
        "--generate-paper",
        action="store_true",
        help="Generate paper materials (figures and tables)",
    )

    args = parser.parse_args()

    # Handle LLM service commands
    if args.llm_status or args.llm_start or args.llm_stop:
        from experiments.llm_service import (
            print_llm_status,
            start_llm_service,
            stop_llm_service,
        )

        if args.llm_status:
            print_llm_status()
            return

        if args.llm_start:
            start_llm_service(model=args.llm_model, port=args.llm_port)
            return

        if args.llm_stop:
            stop_llm_service()
            return

    # 打印 banner
    print_banner()

    print("Configuration:")
    print(f"  Section: {args.section}")
    print(f"  Experiment: {args.exp or 'all'}")
    print(f"  Quick mode: {args.quick}")
    print(f"  Skip LLM: {args.skip_llm}")
    if args.train_methods:
        print(f"  Train methods: {args.train_methods}")

    # Check LLM availability (unless skipping)
    if not args.skip_llm:
        print("\n📡 Checking LLM service...")
        from experiments.llm_service import ensure_llm_available

        if not ensure_llm_available(auto_start=False):
            print("  ⚠️  No LLM service available. Use --llm-start or --skip-llm")

    start_time = time.time()
    all_results = {}

    # 运行各 section
    if args.section in ["5.2", "all"]:
        all_results["section_5_2"] = run_section_5_2(args)

    if args.section in ["5.3", "all"]:
        all_results["section_5_3"] = run_section_5_3(args)

    if args.section in ["5.4", "all"]:
        all_results["section_5_4"] = run_section_5_4(args)

    if args.section in ["5.5", "all"] or args.exp == "training":
        all_results["section_5_5"] = run_section_5_5(args)

    elapsed_time = time.time() - start_time

    # 生成论文材料
    if args.generate_paper:
        from experiments.exp_utils import DEFAULT_OUTPUT_DIR

        output_dir = Path(args.output_dir) if args.output_dir else DEFAULT_OUTPUT_DIR
        generate_paper_materials(all_results, output_dir)

    # 打印最终汇总
    print_final_summary(all_results, elapsed_time)


if __name__ == "__main__":
    main()
