"""
SAGE Bench CLI - 统一 Benchmark 命令入口

提供所有 Benchmark 的统一子命令：

命令结构:
    sage bench agent paper1 run --quick    # Paper 1 Agent Benchmark
    sage bench agent paper2                # Paper 2 (Coming Soon)
    sage bench control-plane run ...       # Control Plane Benchmark

快捷方式 (向后兼容):
    sage bench run --quick                 # 等同于 sage bench agent paper1 run
    sage bench eval --dataset sage         # 等同于 sage bench agent paper1 eval

Benchmark 类型:
    - agent: Agent 能力评测 (工具选择/规划/时机判断)
    - control-plane: 调度策略评测 (LLM/Hybrid)
    - rag: RAG 评测 (预留)
    - memory: 内存管理评测 (预留)
"""

from __future__ import annotations

import sys
from enum import Enum
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

console = Console()

# =========================================================================
# 三层 Typer 应用结构
# =========================================================================

# 顶层: sage bench
app = typer.Typer(
    name="bench",
    help="🧪 Benchmark - 统一评测入口 (Agent, Control Plane, RAG, ...)",
    no_args_is_help=True,
)

# Agent 层: sage bench agent
agent_app = typer.Typer(
    name="agent",
    help="🤝 Agent Benchmarks - 多篇论文的 Agent 能力评测",
    no_args_is_help=True,
)

# Paper 1 层: sage bench agent paper1
paper1_app = typer.Typer(
    name="paper1",
    help="📊 Paper 1: SAGE-Bench - 工具选择/规划/时机判断评测框架",
    no_args_is_help=True,
)

# Paper 2 层 (预留): sage bench agent paper2
paper2_app = typer.Typer(
    name="paper2",
    help="📝 Paper 2: SAGE-Agent - Streaming Adaptive Learning",
    no_args_is_help=False,
)


@paper2_app.callback(invoke_without_command=True)
def paper2_placeholder(ctx: typer.Context):
    """Paper 2: SAGE-Agent (Coming Soon)"""
    if ctx.invoked_subcommand is None:
        console.print("[yellow]📝 Paper 2: SAGE-Agent 即将推出...[/yellow]")
        console.print("[dim]敬请期待更多 Agent 评测实验。[/dim]")


@paper2_app.command("status")
def paper2_status():
    """查看 Paper 2 实现状态"""
    table = Table(title="📊 Paper 2: SAGE-Agent 实现状态", show_header=True)
    table.add_column("模块", style="cyan", width=25)
    table.add_column("状态", width=10)
    table.add_column("备注", width=30)

    modules = [
        ("流式数据处理", "🚧 开发中", "Streaming data pipeline"),
        ("自适应学习策略", "📋 规划中", "Adaptive learning policy"),
        ("Agent 评测框架", "📋 规划中", "Evaluation framework"),
        ("训练脚本", "📋 规划中", "Training scripts"),
    ]

    for module, status, note in modules:
        table.add_row(module, status, note)

    console.print(table)
    console.print("\n[dim]预计完成时间: TBD[/dim]")


# 注册层级关系
agent_app.add_typer(paper1_app, name="paper1", rich_help_panel="Papers")
agent_app.add_typer(paper2_app, name="paper2", rich_help_panel="Papers")
app.add_typer(agent_app, name="agent", rich_help_panel="Benchmarks")

# Control Plane Benchmark (调度策略评测)
try:
    from sage.benchmark.benchmark_control_plane.cli import create_app as create_cp_cli

    _cp_app = create_cp_cli()
except ImportError as e:  # pragma: no cover - optional dependency
    _cp_app = None
    console.print(f"[yellow]⚠️  未安装 control-plane benchmark 依赖: {e}[/yellow]")
else:
    if _cp_app is not None:
        app.add_typer(
            _cp_app,
            name="control-plane",
            help="🧠 Control Plane Benchmark - 调度策略/混合模式评测",
            rich_help_panel="Benchmarks",
        )
        app.add_typer(
            _cp_app,
            name="cp",
            help="Control Plane Benchmark (别名)",
            hidden=True,
        )


# =========================================================================
# Agent list 命令 - 列出所有可用的 papers
# =========================================================================


@agent_app.command("list")
def list_agent_papers():
    """列出所有 Agent Benchmark papers"""
    table = Table(title="📚 Available Agent Benchmarks", show_header=True)
    table.add_column("Paper", style="cyan", width=10)
    table.add_column("Description", width=45)
    table.add_column("Status", style="green", width=8)

    papers = [
        ("paper1", "SAGE-Bench - Agent 能力评测框架\n工具选择/任务规划/时机判断评测", "✅ Ready"),
        ("paper2", "SAGE-Agent - Streaming Adaptive Learning\n流式自适应学习方法", "🚧 WIP"),
    ]

    for paper, desc, status in papers:
        table.add_row(paper, desc, status)

    console.print(table)
    console.print("\n[dim]Usage:[/dim]")
    console.print("  sage bench agent paper1 run --quick")
    console.print("  sage bench agent paper2")


# =========================================================================
# Paper 1 Agent Benchmark 实现 (SAGE-Bench 评测框架)
# =========================================================================


class Section(str, Enum):
    """论文章节"""

    ALL = "all"
    SEC_5_2 = "5.2"
    SEC_5_3 = "5.3"
    SEC_5_4 = "5.4"
    SEC_5_5 = "5.5"


class Experiment(str, Enum):
    """单个实验"""

    TIMING = "timing"
    PLANNING = "planning"
    SELECTION = "selection"
    ERROR = "error"
    SCALING = "scaling"
    ROBUSTNESS = "robustness"
    ABLATION = "ablation"
    CROSS_DATASET = "cross-dataset"
    TRAINING = "training"


# ============================================================================
# Run Command
# ============================================================================


def _run_agent_experiments(
    section: Optional[Section],
    exp: Optional[Experiment],
    quick: bool,
    skip_llm: bool,
    skip_llm_scaling: bool,
    generate_paper: bool,
    output_dir: Optional[str],
):
    """
    运行 Paper 1 Benchmark 实验

    示例:
        sage bench agent paper1 run --quick         # 快速测试
        sage bench agent paper1 run --section 5.2   # 主要评测
        sage bench run --quick                      # 快捷方式
    """
    try:
        # 添加实验脚本**父目录**到 sys.path，使得 run_paper1_experiments.py
        # 中的 "from experiments.xxx" 导入能正常工作
        # 注意：必须是父目录，因为 Python 需要从 sys.path 下查找 "experiments" 模块
        from pathlib import Path

        import sage.benchmark.benchmark_agent.scripts.experiments as exp_module

        exp_dir = Path(exp_module.__file__).parent
        scripts_dir = exp_dir.parent  # .../scripts/ 目录
        if str(scripts_dir) not in sys.path:
            sys.path.insert(0, str(scripts_dir))

        from sage.benchmark.benchmark_agent.scripts.experiments.run_paper1_experiments import (
            main as run_main,
        )

        # 构建参数
        sys.argv = ["run_paper1_experiments.py"]

        if section:
            sys.argv.extend(["--section", section.value])
        if exp:
            sys.argv.extend(["--exp", exp.value])
        if quick:
            sys.argv.append("--quick")
        if skip_llm:
            sys.argv.append("--skip-llm")
        if skip_llm_scaling:
            sys.argv.append("--skip-llm-scaling")
        if generate_paper:
            sys.argv.append("--generate-paper")
        if output_dir:
            sys.argv.extend(["--output-dir", output_dir])

        run_main()

    except ImportError as e:
        console.print("[red]错误: 无法导入 benchmark 模块[/red]")
        console.print("[yellow]请确保已安装 sage-benchmark: pip install isage-benchmark[/yellow]")
        console.print(f"[dim]详细错误: {e}[/dim]")
        raise typer.Exit(1)


@paper1_app.command("run")
@app.command("run", rich_help_panel="Quick Access (Paper 1)")
def run_experiments(
    section: Optional[Section] = typer.Option(
        None, "--section", "-s", help="运行特定章节 (5.2/5.3/5.4/5.5/all)"
    ),
    exp: Optional[Experiment] = typer.Option(
        None, "--exp", "-e", help="运行单个实验 (timing/planning/selection/...)"
    ),
    quick: bool = typer.Option(False, "--quick", "-q", help="快速模式 (减少样本量)"),
    skip_llm: bool = typer.Option(False, "--skip-llm", help="跳过 LLM-based 方法"),
    skip_llm_scaling: bool = typer.Option(
        False, "--skip-llm-scaling", help="跳过 LLM Scaling 测试"
    ),
    generate_paper: bool = typer.Option(False, "--generate-paper", help="生成论文图表和表格"),
    output_dir: Optional[str] = typer.Option(
        None, "--output", "-o", help="输出目录 (默认 .sage/benchmark/paper1/)"
    ),
):
    """Paper 1 Agent Benchmark - 运行实验 (快捷方式: `sage bench run`)"""

    _run_agent_experiments(
        section,
        exp,
        quick,
        skip_llm,
        skip_llm_scaling,
        generate_paper,
        output_dir,
    )


# ============================================================================
# Eval Command
# ============================================================================


def _run_agent_evaluation(dataset: str, samples: int, top_k: int) -> None:
    """
    工具选择评测

    示例:
        sage bench agent paper1 eval --dataset sage --samples 100
        sage bench agent paper1 eval --dataset all  # 跨数据集
        sage bench eval --dataset sage              # 快捷方式
    """
    try:
        # 添加实验脚本父目录到 sys.path
        from pathlib import Path

        import sage.benchmark.benchmark_agent.scripts.experiments as exp_module

        exp_dir = Path(exp_module.__file__).parent
        scripts_dir = exp_dir.parent
        if str(scripts_dir) not in sys.path:
            sys.path.insert(0, str(scripts_dir))

        from sage.benchmark.benchmark_agent.scripts.experiments.exp_utils import (
            setup_experiment_env,
        )

        setup_experiment_env()

        if dataset == "all":
            from sage.benchmark.benchmark_agent.scripts.experiments.exp_cross_dataset import (
                run_cross_dataset_evaluation,
            )

            run_cross_dataset_evaluation(
                datasets=["sage", "acebench"],
                max_samples=samples,
                verbose=True,
            )
        else:
            from sage.benchmark.benchmark_agent.scripts.experiments.exp_main_selection import (
                run_selection_experiment,
            )

            run_selection_experiment(
                max_samples=samples,
                top_k=top_k,
                skip_llm=False,
                verbose=True,
            )

    except ImportError as e:
        console.print(f"[red]错误: 无法导入 benchmark 模块: {e}[/red]")
        raise typer.Exit(1)


@paper1_app.command("eval")
@app.command("eval", rich_help_panel="Quick Access (Paper 1)")
def eval_agent(
    dataset: str = typer.Option("sage", "--dataset", "-d", help="数据集 (sage/acebench/all)"),
    samples: int = typer.Option(100, "--samples", "-n", help="样本数量"),
    top_k: int = typer.Option(5, "--top-k", "-k", help="Top-K 工具数"),
):
    """Paper 1 Agent Benchmark - 工具选择评测 (快捷方式: `sage bench eval`)"""

    _run_agent_evaluation(dataset, samples, top_k)


# ============================================================================
# Train Command
# ============================================================================


def _run_agent_training(
    methods: str,
    model: str,
    quick: bool,
    dry_run: bool,
):
    """
    训练方法对比 (Section 5.5)

    示例:
        sage bench agent paper1 train --dry-run          # 模拟运行
        sage bench agent paper1 train --methods A_baseline  # 单个方法
        sage bench train --quick                         # 快捷方式
    """
    try:
        # 添加实验脚本父目录到 sys.path
        from pathlib import Path

        import sage.benchmark.benchmark_agent.scripts.experiments as exp_module

        exp_dir = Path(exp_module.__file__).parent
        scripts_dir = exp_dir.parent
        if str(scripts_dir) not in sys.path:
            sys.path.insert(0, str(scripts_dir))

        from sage.benchmark.benchmark_agent.scripts.experiments.exp_training_comparison import (
            run_training_comparison,
        )

        method_list = methods.split(",")
        run_training_comparison(
            methods=method_list,
            base_model=model,
            quick=quick,
            dry_run=dry_run,
            verbose=True,
        )

    except ImportError as e:
        console.print(f"[red]错误: 无法导入训练模块: {e}[/red]")
        raise typer.Exit(1)


@paper1_app.command("train")
@app.command("train", rich_help_panel="Quick Access (Paper 1)")
def train_agent(
    methods: str = typer.Option(
        "A_baseline,D_combined", "--methods", "-m", help="训练方法 (逗号分隔)"
    ),
    model: str = typer.Option("Qwen/Qwen2.5-1.5B-Instruct", "--model", help="基础模型"),
    quick: bool = typer.Option(False, "--quick", "-q", help="快速模式"),
    dry_run: bool = typer.Option(False, "--dry-run", help="模拟运行 (不实际训练)"),
):
    """Paper 1 Agent Benchmark - 训练方法对比 (快捷方式: `sage bench train`)"""

    _run_agent_training(methods, model, quick, dry_run)


# ============================================================================
# LLM Subcommand
# ============================================================================

llm_app = typer.Typer(help="Paper 1 LLM 服务管理")
paper1_app.add_typer(llm_app, name="llm")
app.add_typer(llm_app, name="llm", hidden=True)


@llm_app.command("status")
def llm_status():
    """查看 LLM 服务状态"""
    try:
        # 添加实验脚本父目录到 sys.path
        from pathlib import Path

        import sage.benchmark.benchmark_agent.scripts.experiments as exp_module

        exp_dir = Path(exp_module.__file__).parent
        scripts_dir = exp_dir.parent
        if str(scripts_dir) not in sys.path:
            sys.path.insert(0, str(scripts_dir))

        from sage.benchmark.benchmark_agent.scripts.experiments.llm_service import (
            print_llm_status,
        )

        print_llm_status()

    except ImportError as e:
        console.print(f"[red]错误: 无法导入 LLM 服务模块: {e}[/red]")
        raise typer.Exit(1)


@llm_app.command("start")
def llm_start(
    model: str = typer.Option("Qwen/Qwen2.5-1.5B-Instruct", "--model", "-m", help="模型名称"),
    port: int = typer.Option(8901, "--port", "-p", help="服务端口"),
    gpu_memory: float = typer.Option(0.9, "--gpu-memory", help="GPU 显存占用比例"),
):
    """启动 LLM 服务"""
    try:
        # 添加实验脚本父目录到 sys.path
        from pathlib import Path

        import sage.benchmark.benchmark_agent.scripts.experiments as exp_module

        exp_dir = Path(exp_module.__file__).parent
        scripts_dir = exp_dir.parent
        if str(scripts_dir) not in sys.path:
            sys.path.insert(0, str(scripts_dir))

        from sage.benchmark.benchmark_agent.scripts.experiments.llm_service import (
            start_llm_service,
        )

        success = start_llm_service(
            model=model,
            port=port,
            gpu_memory=gpu_memory,
        )
        if not success:
            raise typer.Exit(1)

    except ImportError as e:
        console.print(f"[red]错误: 无法导入 LLM 服务模块: {e}[/red]")
        raise typer.Exit(1)


@llm_app.command("stop")
def llm_stop():
    """停止 LLM 服务"""
    try:
        # 添加实验脚本父目录到 sys.path
        from pathlib import Path

        import sage.benchmark.benchmark_agent.scripts.experiments as exp_module

        exp_dir = Path(exp_module.__file__).parent
        scripts_dir = exp_dir.parent
        if str(scripts_dir) not in sys.path:
            sys.path.insert(0, str(scripts_dir))

        from sage.benchmark.benchmark_agent.scripts.experiments.llm_service import (
            stop_llm_service,
        )

        success = stop_llm_service()
        if not success:
            raise typer.Exit(1)

    except ImportError as e:
        console.print(f"[red]错误: 无法导入 LLM 服务模块: {e}[/red]")
        raise typer.Exit(1)


# ============================================================================
# List Command
# ============================================================================


def _list_resources(resource: str) -> None:
    if resource == "experiments":
        _list_experiments()
    elif resource == "datasets":
        _list_datasets()
    elif resource == "methods":
        _list_methods()
    else:
        console.print(f"[red]未知资源类型: {resource}[/red]")
        console.print("可用: experiments, datasets, methods")
        raise typer.Exit(1)


@paper1_app.command("list")
def list_resources(
    resource: str = typer.Argument("experiments", help="资源类型 (experiments/datasets/methods)"),
):
    """列出 Paper 1 可用资源"""

    _list_resources(resource)


def _list_experiments():
    """列出可用实验"""
    table = Table(title="📋 可用实验", show_header=True)
    table.add_column("章节", style="cyan")
    table.add_column("实验", style="green")
    table.add_column("描述")

    experiments = [
        ("5.2", "timing", "工具调用时机评测"),
        ("5.2", "planning", "任务规划能力评测"),
        ("5.2", "selection", "工具选择准确率评测"),
        ("5.3", "error", "错误类型分布分析"),
        ("5.3", "scaling", "工具数量扩展性分析"),
        ("5.3", "robustness", "鲁棒性分析"),
        ("5.3", "ablation", "消融实验"),
        ("5.4", "cross-dataset", "跨数据集泛化评测"),
        ("5.5", "training", "训练方法对比"),
    ]

    for section, exp, desc in experiments:
        table.add_row(section, exp, desc)

    console.print(table)


def _list_datasets():
    """列出可用数据集"""
    table = Table(title="📊 可用数据集", show_header=True)
    table.add_column("名称", style="cyan")
    table.add_column("描述")
    table.add_column("样本数", style="green")

    datasets = [
        ("sage", "SAGE 内置工具选择数据集", "~1000"),
        ("acebench", "ACEBench 外部数据集", "~500"),
    ]

    for name, desc, samples in datasets:
        table.add_row(name, desc, samples)

    console.print(table)


def _list_methods():
    """列出可用方法"""
    table = Table(title="🔧 可用方法", show_header=True)
    table.add_column("类型", style="cyan")
    table.add_column("方法 ID", style="green")
    table.add_column("描述")

    methods = [
        ("Timing", "rule_based", "关键词匹配 + 正则模式"),
        ("Timing", "llm_based", "直接用 LLM 判断"),
        ("Timing", "hybrid", "Rule 初筛 + LLM 精判"),
        ("Planning", "simple", "简单贪心规划"),
        ("Planning", "react", "ReAct 方法"),
        ("Planning", "tot", "Tree-of-Thoughts"),
        ("Selection", "keyword", "关键词匹配"),
        ("Selection", "embedding", "语义相似度"),
        ("Selection", "gorilla", "Gorilla 方法"),
        ("Selection", "dfsdt", "DFSDT 方法"),
        ("Training", "A_baseline", "基础 SFT"),
        ("Training", "D_combined", "组合方法 (Coreset + Continual)"),
    ]

    for typ, method_id, desc in methods:
        table.add_row(typ, method_id, desc)

    console.print(table)


# ============================================================================
# Figures & Tables
# ============================================================================


def _generate_figures(output_dir: Optional[str]) -> None:
    try:
        from sage.benchmark.benchmark_agent.scripts.experiments.figure_generator import (
            generate_all_figures,
        )

        generate_all_figures(output_dir=output_dir)
        console.print("[green]✅ 图表生成完成[/green]")

    except ImportError as e:
        console.print(f"[red]错误: 无法导入图表生成模块: {e}[/red]")
        raise typer.Exit(1)


@paper1_app.command("figures")
def generate_figures(
    output_dir: Optional[str] = typer.Option(None, "--output", "-o", help="输出目录"),
):
    """生成 Paper 1 图表"""

    _generate_figures(output_dir)


def _generate_tables(output_dir: Optional[str]) -> None:
    try:
        from sage.benchmark.benchmark_agent.scripts.experiments.table_generator import (
            generate_all_tables,
        )

        generate_all_tables(output_dir=output_dir)
        console.print("[green]✅ 表格生成完成[/green]")

    except ImportError as e:
        console.print(f"[red]错误: 无法导入表格生成模块: {e}[/red]")
        raise typer.Exit(1)


@paper1_app.command("tables")
def generate_tables(
    output_dir: Optional[str] = typer.Option(None, "--output", "-o", help="输出目录"),
):
    """生成 Paper 1 LaTeX 表格"""

    _generate_tables(output_dir)


@app.command("list", rich_help_panel="Quick Access (Paper 1)")
def list_default(
    resource: str = typer.Argument("experiments", help="资源类型 (experiments/datasets/methods)"),
):
    """Paper 1 - 列出资源 (兼容 `sage bench list`)"""

    _list_resources(resource)


@app.command("figures", rich_help_panel="Quick Access (Paper 1)")
def figures_default(
    output_dir: Optional[str] = typer.Option(None, "--output", "-o", help="输出目录"),
):
    """Paper 1 - 生成图表 (兼容 `sage bench figures`)"""

    _generate_figures(output_dir)


@app.command("tables", rich_help_panel="Quick Access (Paper 1)")
def tables_default(
    output_dir: Optional[str] = typer.Option(None, "--output", "-o", help="输出目录"),
):
    """Paper 1 - 生成表格 (兼容 `sage bench tables`)"""

    _generate_tables(output_dir)
