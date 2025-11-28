"""
SAGE-Bench Internal Module: Interactive Mode

WARNING: This is an internal module. Do not call directly.
Please use: sage-bench interactive
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class Experiment:
    """实验配置"""

    id: str
    name: str
    description: str
    paper: int
    command: str  # CLI 命令
    estimated_time: str = "?"
    requires_gpu: bool = False


# Paper 1: Benchmark 实验
PAPER1_EXPERIMENTS = [
    Experiment(
        id="timing",
        name="Challenge 1: Timing Judgment",
        description="评测何时调用工具 vs 直接回答 (Target: ≥95%)",
        paper=1,
        command="sage-bench run --challenge timing",
        estimated_time="~10 min",
    ),
    Experiment(
        id="planning",
        name="Challenge 2: Task Planning",
        description="评测任务分解与多步规划 (Target: ≥90%)",
        paper=1,
        command="sage-bench run --challenge planning",
        estimated_time="~15 min",
    ),
    Experiment(
        id="tool_selection",
        name="Challenge 3: Tool Selection",
        description="评测工具检索与选择 (Target: ≥95%)",
        paper=1,
        command="sage-bench run --challenge tool_selection",
        estimated_time="~20 min",
    ),
    Experiment(
        id="cross_dataset",
        name="Cross-Dataset Comparison",
        description="跨数据集对比 (SAGE + ACEBench + APIBank + ToolAlpaca)",
        paper=1,
        command="sage-bench eval --dataset all --methods keyword,embedding,hybrid,gorilla,dfsdt --samples 100",
        estimated_time="~30 min",
    ),
    Experiment(
        id="quick_benchmark",
        name="Quick Benchmark (快速)",
        description="快速评测，跳过 LLM 方法",
        paper=1,
        command="sage-bench run --quick --skip-llm",
        estimated_time="~30 min",
    ),
]

# Paper 2: Method 实验
PAPER2_EXPERIMENTS = [
    Experiment(
        id="training_quick",
        name="Training Comparison (Quick)",
        description="快速训练对比: SAGE_baseline vs SAGE_combined",
        paper=2,
        command="sage-bench train --quick",
        requires_gpu=True,
        estimated_time="~1 hour",
    ),
    Experiment(
        id="training_full",
        name="Training Comparison (Full)",
        description="完整训练对比: 所有 SAGE 方法",
        paper=2,
        command="sage-bench train",
        requires_gpu=True,
        estimated_time="~6 hours",
    ),
    Experiment(
        id="ablation",
        name="Ablation Study",
        description="消融实验: 各组件贡献分析",
        paper=2,
        command="sage-bench train --methods A_baseline,B_coreset,C_continual,D_combined",
        requires_gpu=True,
        estimated_time="~4 hours",
    ),
]

ALL_EXPERIMENTS = PAPER1_EXPERIMENTS + PAPER2_EXPERIMENTS


def print_banner():
    """打印欢迎 banner"""
    print("""
╔═══════════════════════════════════════════════════════════════════════════╗
║                       SAGE-Bench CLI v2.0                                 ║
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
            print(f"      命令: {exp.command}")
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
            print(f"      命令: {exp.command}")
            print(f"      预计时间: {exp.estimated_time}")
            print()


def print_llm_status():
    """打印 LLM 服务状态"""
    import httpx

    print("\n📡 LLM 服务状态")
    print("=" * 50)

    try:
        from sage.common.config.ports import SagePorts

        ports = [SagePorts.BENCHMARK_LLM, 8001, 8000]
    except ImportError:
        ports = [8901, 8001, 8000]

    seen = set()
    for port in ports:
        if port in seen:
            continue
        seen.add(port)
        try:
            response = httpx.get(f"http://localhost:{port}/v1/models", timeout=3.0)
            if response.status_code == 200:
                data = response.json()
                models = data.get("data", [])
                if models:
                    model = models[0].get("id", "unknown")
                    print(f"  ✅ Port {port}: 运行中 (model: {model})")
                    continue
        except Exception:
            pass
        print(f"  ❌ Port {port}: 未运行")
    print()


def run_experiment(exp: Experiment, skip_confirm: bool = False) -> bool:
    """运行实验"""
    import subprocess

    print(f"\n{'=' * 70}")
    print(f"🚀 运行实验: {exp.name}")
    print(f"   命令: {exp.command}")
    print(f"   预计时间: {exp.estimated_time}")
    if exp.requires_gpu:
        print("   ⚠️  需要 GPU")
    print(f"{'=' * 70}\n")

    if not skip_confirm:
        try:
            confirm = input("确认运行? (y/n): ").strip().lower()
            if confirm != "y":
                print("已取消")
                return False
        except KeyboardInterrupt:
            print("\n已取消")
            return False

    # 解析并执行命令
    parts = exp.command.split()
    # 将 sage-bench 替换为当前 CLI 脚本
    script_dir = Path(__file__).parent.parent
    cli_script = script_dir / "sage_bench"

    cmd = [sys.executable, str(cli_script)] + parts[1:]  # 跳过 sage-bench

    print(f"执行: {' '.join(cmd)}\n")
    try:
        result = subprocess.run(cmd)
        return result.returncode == 0
    except KeyboardInterrupt:
        print("\n⚠️  用户中断")
        return False


def select_experiment_interactive() -> Optional[Experiment]:
    """交互式选择实验"""
    print("\n请选择论文:")
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


def run_interactive_mode() -> int:
    """运行交互式模式"""
    print_banner()
    print_llm_status()

    while True:
        exp = select_experiment_interactive()
        if exp is None:
            print("\n👋 再见!")
            break

        run_experiment(exp)

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
    print("=" * 70)
    print("WARNING: This is an internal module.")
    print("Please use the CLI instead:")
    print()
    print("    sage-bench interactive")
    print("=" * 70)
    sys.exit(1)
