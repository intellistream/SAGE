#!/usr/bin/env python3
"""
SAGE Benchmark CLI - 统一交互式入口

支持两篇论文的实验：
- Paper 1 (Benchmark): SAGE-Bench 评测框架，对比现有 SOTA 方法
- Paper 2 (Method): SAGE 原创方法 (Coreset + Continual Learning)

Usage:
    # 交互式运行
    python sage_benchmark_cli.py

    # 直接指定 Paper 和实验
    python sage_benchmark_cli.py --paper 1 --experiment tool_selection
    python sage_benchmark_cli.py --paper 2 --experiment training

    # 列出所有可用实验
    python sage_benchmark_cli.py --list
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# 获取脚本目录
SCRIPT_DIR = Path(__file__).resolve().parent


@dataclass
class Experiment:
    """实验配置"""

    id: str
    name: str
    description: str
    paper: int  # 1 or 2
    script: str
    default_args: list[str]
    requires_gpu: bool = False
    estimated_time: str = "?"


# =============================================================================
# Paper 1: Benchmark 实验 (对比现有 SOTA 方法)
# =============================================================================

PAPER1_EXPERIMENTS = [
    Experiment(
        id="timing",
        name="Challenge 1: Timing Judgment",
        description="评测何时调用工具 vs 直接回答 (Target: ≥95%)",
        paper=1,
        script="run_all_experiments.py",
        default_args=["--challenge", "timing", "--eval-only"],
        estimated_time="~10 min",
    ),
    Experiment(
        id="planning",
        name="Challenge 2: Task Planning",
        description="评测任务分解与多步规划 (Target: ≥90%)",
        paper=1,
        script="run_all_experiments.py",
        default_args=["--challenge", "planning", "--eval-only"],
        estimated_time="~15 min",
    ),
    Experiment(
        id="tool_selection",
        name="Challenge 3: Tool Selection",
        description="评测工具检索与选择 (Target: ≥95%)",
        paper=1,
        script="run_all_experiments.py",
        default_args=["--challenge", "tool_selection", "--eval-only"],
        estimated_time="~20 min",
    ),
    Experiment(
        id="all_challenges",
        name="All Challenges (完整评测)",
        description="运行所有 3 个 Challenge 的完整评测",
        paper=1,
        script="run_all_experiments.py",
        default_args=["--eval-only"],
        estimated_time="~2 hours",
    ),
    Experiment(
        id="cross_dataset",
        name="Cross-Dataset Comparison",
        description="跨数据集对比 (SAGE + ACEBench + ToolBench)",
        paper=1,
        script="run_unified_eval.py",
        default_args=[
            "--dataset",
            "all",
            "--methods",
            "keyword,embedding,hybrid",
            "--samples",
            "90",
        ],
        estimated_time="~30 min",
    ),
    Experiment(
        id="quick_benchmark",
        name="Quick Benchmark (快速)",
        description="快速评测，跳过 LLM 方法",
        paper=1,
        script="run_all_experiments.py",
        default_args=["--quick", "--skip-llm"],
        estimated_time="~30 min",
    ),
]

# =============================================================================
# Paper 2: Method 实验 (SAGE 原创方法)
# =============================================================================

PAPER2_EXPERIMENTS = [
    Experiment(
        id="training_quick",
        name="Training Comparison (Quick)",
        description="快速训练对比: SAGE_baseline vs SAGE_coreset vs SAGE_continual",
        paper=2,
        script="run_full_training_comparison.py",
        default_args=["--quick"],
        requires_gpu=True,
        estimated_time="~1 hour",
    ),
    Experiment(
        id="training_full",
        name="Training Comparison (Full)",
        description="完整训练对比: 所有 SAGE 方法",
        paper=2,
        script="run_full_training_comparison.py",
        default_args=["--full"],
        requires_gpu=True,
        estimated_time="~6 hours",
    ),
    Experiment(
        id="sage_baseline",
        name="SAGE_baseline_sft",
        description="基准 SFT 训练",
        paper=2,
        script="run_full_training_comparison.py",
        default_args=["--method", "SAGE_baseline_sft"],
        requires_gpu=True,
        estimated_time="~2 hours",
    ),
    Experiment(
        id="sage_coreset",
        name="SAGE_coreset_hybrid",
        description="Coreset 混合策略 (60% loss + 40% diversity)",
        paper=2,
        script="run_full_training_comparison.py",
        default_args=["--method", "SAGE_coreset_hybrid"],
        requires_gpu=True,
        estimated_time="~1.5 hours",
    ),
    Experiment(
        id="sage_continual",
        name="SAGE_continual",
        description="持续学习 + 经验回放",
        paper=2,
        script="run_full_training_comparison.py",
        default_args=["--method", "SAGE_continual"],
        requires_gpu=True,
        estimated_time="~2.5 hours",
    ),
    Experiment(
        id="sage_combined",
        name="SAGE_combined (推荐)",
        description="完整方案: Coreset + Continual Learning",
        paper=2,
        script="run_full_training_comparison.py",
        default_args=["--method", "SAGE_combined"],
        requires_gpu=True,
        estimated_time="~2 hours",
    ),
    Experiment(
        id="ablation",
        name="Ablation Study",
        description="消融实验: 各组件贡献分析",
        paper=2,
        script="run_full_training_comparison.py",
        default_args=["--ablation"],
        requires_gpu=True,
        estimated_time="~4 hours",
    ),
]

ALL_EXPERIMENTS = PAPER1_EXPERIMENTS + PAPER2_EXPERIMENTS


def print_banner():
    """打印欢迎 banner"""
    print("""
╔═══════════════════════════════════════════════════════════════════════════╗
║                     SAGE Benchmark CLI v1.0                               ║
║                                                                           ║
║  Paper 1: SAGE-Bench - Unified Benchmark for Agent Capabilities           ║
║  Paper 2: SAGE Methods - Coreset Selection + Continual Learning           ║
╚═══════════════════════════════════════════════════════════════════════════╝
""")


def print_experiments(paper: Optional[int] = None):
    """打印可用实验列表"""
    if paper is None or paper == 1:
        print("\n📘 Paper 1: Benchmark (现有 SOTA 方法对比)")
        print("=" * 70)
        for i, exp in enumerate(PAPER1_EXPERIMENTS, 1):
            gpu_tag = " [GPU]" if exp.requires_gpu else ""
            print(f"  [{i}] {exp.name}{gpu_tag}")
            print(f"      {exp.description}")
            print(f"      预计时间: {exp.estimated_time}")
            print()

    if paper is None or paper == 2:
        print("\n📙 Paper 2: Method (SAGE 原创方法)")
        print("=" * 70)
        offset = len(PAPER1_EXPERIMENTS) if paper is None else 0
        for i, exp in enumerate(PAPER2_EXPERIMENTS, 1):
            gpu_tag = " [GPU]" if exp.requires_gpu else ""
            print(f"  [{offset + i}] {exp.name}{gpu_tag}")
            print(f"      {exp.description}")
            print(f"      预计时间: {exp.estimated_time}")
            print()


def select_experiment_interactive() -> Optional[Experiment]:
    """交互式选择实验"""
    print_banner()

    # 选择 Paper
    print("请选择论文:")
    print("  [1] Paper 1: Benchmark (评测现有方法)")
    print("  [2] Paper 2: Method (SAGE 原创方法)")
    print("  [0] 退出")
    print()

    try:
        paper_choice = input("请输入选项 (1/2/0): ").strip()
        if paper_choice == "0":
            return None
        paper = int(paper_choice)
        if paper not in [1, 2]:
            print("无效选项")
            return None
    except (ValueError, KeyboardInterrupt):
        return None

    # 选择实验
    experiments = PAPER1_EXPERIMENTS if paper == 1 else PAPER2_EXPERIMENTS
    print_experiments(paper)

    try:
        exp_choice = input(f"请选择实验 (1-{len(experiments)}, 0 返回): ").strip()
        if exp_choice == "0":
            return select_experiment_interactive()
        idx = int(exp_choice) - 1
        if 0 <= idx < len(experiments):
            return experiments[idx]
        else:
            print("无效选项")
            return None
    except (ValueError, KeyboardInterrupt):
        return None


def run_experiment(exp: Experiment, extra_args: list[str] = None):
    """运行实验"""
    script_path = SCRIPT_DIR / exp.script
    if not script_path.exists():
        print(f"❌ 脚本不存在: {script_path}")
        return False

    # 构建命令
    cmd = [sys.executable, str(script_path)] + exp.default_args
    if extra_args:
        cmd.extend(extra_args)

    print(f"\n{'=' * 70}")
    print(f"🚀 运行实验: {exp.name}")
    print(f"   脚本: {exp.script}")
    print(f"   参数: {' '.join(exp.default_args)}")
    print(f"   预计时间: {exp.estimated_time}")
    if exp.requires_gpu:
        print("   ⚠️  需要 GPU")
    print(f"{'=' * 70}\n")

    # 确认运行
    try:
        confirm = input("确认运行? (y/n): ").strip().lower()
        if confirm != "y":
            print("已取消")
            return False
    except KeyboardInterrupt:
        print("\n已取消")
        return False

    # 运行
    print(f"\n执行命令: {' '.join(cmd)}\n")
    try:
        result = subprocess.run(cmd, cwd=str(SCRIPT_DIR))
        return result.returncode == 0
    except KeyboardInterrupt:
        print("\n⚠️  用户中断")
        return False


def find_experiment(paper: Optional[int], exp_id: str) -> Optional[Experiment]:
    """根据 ID 查找实验"""
    experiments = ALL_EXPERIMENTS
    if paper == 1:
        experiments = PAPER1_EXPERIMENTS
    elif paper == 2:
        experiments = PAPER2_EXPERIMENTS

    for exp in experiments:
        if exp.id == exp_id:
            return exp
    return None


def main():
    parser = argparse.ArgumentParser(
        description="SAGE Benchmark CLI - 统一交互式入口",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # 交互式运行
    python sage_benchmark_cli.py

    # 直接运行 Paper 1 实验
    python sage_benchmark_cli.py --paper 1 --experiment tool_selection

    # 直接运行 Paper 2 实验
    python sage_benchmark_cli.py --paper 2 --experiment sage_combined

    # 列出所有实验
    python sage_benchmark_cli.py --list
        """,
    )

    parser.add_argument(
        "--paper",
        "-p",
        type=int,
        choices=[1, 2],
        help="选择论文: 1=Benchmark, 2=Method",
    )
    parser.add_argument(
        "--experiment",
        "-e",
        type=str,
        help="实验 ID (使用 --list 查看可用实验)",
    )
    parser.add_argument(
        "--list",
        "-l",
        action="store_true",
        help="列出所有可用实验",
    )
    parser.add_argument(
        "extra_args",
        nargs="*",
        help="传递给实验脚本的额外参数",
    )

    args = parser.parse_args()

    # 列出实验
    if args.list:
        print_banner()
        print_experiments()
        return 0

    # 直接指定实验
    if args.experiment:
        exp = find_experiment(args.paper, args.experiment)
        if exp is None:
            print(f"❌ 未找到实验: {args.experiment}")
            print("使用 --list 查看可用实验")
            return 1
        success = run_experiment(exp, args.extra_args)
        return 0 if success else 1

    # 交互式模式
    while True:
        exp = select_experiment_interactive()
        if exp is None:
            print("\n👋 再见!")
            break

        run_experiment(exp, args.extra_args)

        # 询问是否继续
        try:
            print()
            cont = input("继续运行其他实验? (y/n): ").strip().lower()
            if cont != "y":
                print("\n👋 再见!")
                break
        except KeyboardInterrupt:
            print("\n👋 再见!")
            break

    return 0


if __name__ == "__main__":
    sys.exit(main())
