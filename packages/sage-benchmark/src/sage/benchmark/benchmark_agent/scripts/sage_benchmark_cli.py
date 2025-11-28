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

    # LLM 服务管理
    python sage_benchmark_cli.py --start-llm                    # 启动本地 LLM 服务
    python sage_benchmark_cli.py --start-llm --llm-model Qwen/Qwen2.5-7B-Instruct
    python sage_benchmark_cli.py --llm-status                   # 检查服务状态
    python sage_benchmark_cli.py --stop-llm                     # 停止服务
"""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import httpx

# 获取脚本目录
SCRIPT_DIR = Path(__file__).resolve().parent

# LLM 服务配置 - 从统一配置导入
try:
    from sage.common.config.ports import SagePorts

    DEFAULT_LLM_PORT = SagePorts.BENCHMARK_LLM
except ImportError:
    DEFAULT_LLM_PORT = 8901  # Fallback

DEFAULT_LLM_MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
LLM_PID_FILE = Path.home() / ".sage" / "benchmark_llm.pid"


# =============================================================================
# LLM 服务管理
# =============================================================================


def check_llm_service(port: int = DEFAULT_LLM_PORT) -> dict:
    """检查 LLM 服务状态"""
    result = {"running": False, "port": port, "model": None, "error": None}

    try:
        response = httpx.get(f"http://localhost:{port}/v1/models", timeout=5.0)
        if response.status_code == 200:
            data = response.json()
            models = data.get("data", [])
            if models:
                result["running"] = True
                result["model"] = models[0].get("id", "unknown")
        else:
            result["error"] = f"HTTP {response.status_code}"
    except httpx.ConnectError:
        result["error"] = "Connection refused"
    except httpx.TimeoutException:
        result["error"] = "Timeout"
    except Exception as e:
        result["error"] = str(e)

    return result


def start_llm_service(
    model: str = DEFAULT_LLM_MODEL,
    port: int = DEFAULT_LLM_PORT,
    gpu_memory: float = 0.5,
) -> bool:
    """启动本地 vLLM 服务"""
    # 检查是否已运行
    status = check_llm_service(port)
    if status["running"]:
        print(f"✅ LLM 服务已在运行 (port={port}, model={status['model']})")
        return True

    print("🚀 启动 LLM 服务...")
    print(f"   模型: {model}")
    print(f"   端口: {port}")
    print(f"   GPU 显存: {gpu_memory * 100:.0f}%")

    # 确保 PID 文件目录存在
    LLM_PID_FILE.parent.mkdir(parents=True, exist_ok=True)

    # 构建 vLLM 命令
    cmd = [
        sys.executable,
        "-m",
        "vllm.entrypoints.openai.api_server",
        "--model",
        model,
        "--port",
        str(port),
        "--gpu-memory-utilization",
        str(gpu_memory),
        "--trust-remote-code",
    ]

    try:
        # 后台启动
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )

        # 保存 PID
        with open(LLM_PID_FILE, "w") as f:
            f.write(str(process.pid))

        print(f"   PID: {process.pid}")
        print("   等待服务启动...")

        # 等待服务就绪 (最多 120 秒)
        for i in range(120):
            time.sleep(1)
            status = check_llm_service(port)
            if status["running"]:
                print(f"\n✅ LLM 服务已启动 (耗时 {i + 1}s)")
                print(f"   端点: http://localhost:{port}/v1")
                print(f"   模型: {status['model']}")
                return True
            if i % 10 == 9:
                print(f"   已等待 {i + 1}s...")

        print("\n❌ 服务启动超时")
        return False

    except FileNotFoundError:
        print("❌ vLLM 未安装，请运行: pip install vllm")
        return False
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        return False


def stop_llm_service() -> bool:
    """停止 LLM 服务"""
    if not LLM_PID_FILE.exists():
        print("ℹ️  没有找到运行中的 LLM 服务")
        return True

    try:
        with open(LLM_PID_FILE) as f:
            pid = int(f.read().strip())

        print(f"🛑 停止 LLM 服务 (PID={pid})...")
        os.kill(pid, signal.SIGTERM)

        # 等待进程结束
        for _ in range(10):
            time.sleep(1)
            try:
                os.kill(pid, 0)  # 检查进程是否存在
            except OSError:
                break

        LLM_PID_FILE.unlink(missing_ok=True)
        print("✅ LLM 服务已停止")
        return True

    except ProcessLookupError:
        print("ℹ️  进程已不存在")
        LLM_PID_FILE.unlink(missing_ok=True)
        return True
    except Exception as e:
        print(f"❌ 停止失败: {e}")
        return False


def print_llm_status():
    """打印 LLM 服务状态"""
    print("\n📡 LLM 服务状态")
    print("=" * 50)

    # 检查所有可能的 LLM 端口
    try:
        from sage.common.config.ports import SagePorts

        ports_to_check = [SagePorts.BENCHMARK_LLM] + SagePorts.get_llm_ports()
    except ImportError:
        ports_to_check = [DEFAULT_LLM_PORT, 8001, 8000]

    # 去重并保持顺序
    seen = set()
    unique_ports = []
    for p in ports_to_check:
        if p not in seen:
            seen.add(p)
            unique_ports.append(p)

    for port in unique_ports:
        status = check_llm_service(port)
        if status["running"]:
            print(f"  ✅ Port {port}: 运行中")
            print(f"     模型: {status['model']}")
            print(f"     端点: http://localhost:{port}/v1")
        else:
            print(f"  ❌ Port {port}: {status['error'] or '未运行'}")

    print()


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
        description="跨数据集对比 (SAGE + ACEBench + APIBank + ToolAlpaca)",
        paper=1,
        script="run_unified_eval.py",
        default_args=[
            "--dataset",
            "all",
            "--methods",
            "keyword,embedding,hybrid,gorilla,dfsdt",
            "--samples",
            "100",
        ],
        estimated_time="~30 min",
    ),
    Experiment(
        id="list_datasets",
        name="List Available Datasets",
        description="列出所有可用的评测数据集",
        paper=1,
        script="run_unified_eval.py",
        default_args=["--list-datasets"],
        estimated_time="<1 min",
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


def run_experiment(exp: Experiment, extra_args: list[str] = None, skip_confirm: bool = False):
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

    # 确认运行 (可跳过)
    if not skip_confirm:
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

    # LLM 服务管理
    python sage_benchmark_cli.py --start-llm                                    # 启动默认模型
    python sage_benchmark_cli.py --start-llm --llm-model Qwen/Qwen2.5-7B-Instruct
    python sage_benchmark_cli.py --llm-status                                   # 检查状态
    python sage_benchmark_cli.py --stop-llm                                     # 停止服务
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
        "--yes",
        "-y",
        action="store_true",
        help="跳过确认提示，直接运行",
    )

    # LLM 服务管理参数
    llm_group = parser.add_argument_group("LLM 服务管理")
    llm_group.add_argument(
        "--start-llm",
        action="store_true",
        help="启动本地 vLLM 服务",
    )
    llm_group.add_argument(
        "--stop-llm",
        action="store_true",
        help="停止本地 vLLM 服务",
    )
    llm_group.add_argument(
        "--llm-status",
        action="store_true",
        help="检查 LLM 服务状态",
    )
    llm_group.add_argument(
        "--llm-model",
        type=str,
        default=DEFAULT_LLM_MODEL,
        help=f"LLM 模型 (默认: {DEFAULT_LLM_MODEL})",
    )
    llm_group.add_argument(
        "--llm-port",
        type=int,
        default=DEFAULT_LLM_PORT,
        help=f"LLM 服务端口 (默认: {DEFAULT_LLM_PORT})",
    )
    llm_group.add_argument(
        "--gpu-memory",
        type=float,
        default=0.5,
        help="GPU 显存使用比例 (默认: 0.5)",
    )

    parser.add_argument(
        "extra_args",
        nargs="*",
        help="传递给实验脚本的额外参数",
    )

    args = parser.parse_args()

    # LLM 服务管理命令
    if args.llm_status:
        print_llm_status()
        return 0

    if args.stop_llm:
        return 0 if stop_llm_service() else 1

    if args.start_llm:
        success = start_llm_service(
            model=args.llm_model,
            port=args.llm_port,
            gpu_memory=args.gpu_memory,
        )
        return 0 if success else 1

    # 列出实验
    if args.list:
        print_banner()
        print_experiments()
        print_llm_status()
        return 0

    # 直接指定实验
    if args.experiment:
        exp = find_experiment(args.paper, args.experiment)
        if exp is None:
            print(f"❌ 未找到实验: {args.experiment}")
            print("使用 --list 查看可用实验")
            return 1

        # 检查 LLM 服务（对于需要 LLM 的实验）
        if exp.requires_gpu or "llm" in exp.id.lower():
            status = check_llm_service()
            if not status["running"]:
                print("⚠️  LLM 服务未运行，某些方法可能无法使用")
                print("   使用 --start-llm 启动服务")
                print()

        success = run_experiment(exp, args.extra_args, skip_confirm=args.yes)
        return 0 if success else 1

    # 交互式模式
    print_banner()
    print_llm_status()

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
