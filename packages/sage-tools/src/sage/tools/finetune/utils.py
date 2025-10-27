#!/usr/bin/env python3
"""
Finetune CLI - Utility Functions
工具函数：依赖检查、路径处理、UI显示等
"""

import os
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


def get_sage_root() -> Path:
    """获取SAGE项目根目录"""
    # 从当前文件向上查找
    current = Path(__file__).resolve()
    while current.parent != current:
        if (current / ".git").exists():
            return current
        current = current.parent

    # 如果没找到，使用当前工作目录
    return Path.cwd()


def get_sage_config_dir() -> Path:
    """获取 SAGE 配置目录（~/.sage）

    Returns:
        Path: SAGE 配置目录路径，如果不存在会自动创建
    """
    sage_dir = Path.home() / ".sage"
    sage_dir.mkdir(parents=True, exist_ok=True)
    return sage_dir


def get_finetune_output_dir() -> Path:
    """获取 finetune 默认输出目录（~/.sage/finetune_output）

    Returns:
        Path: Finetune 输出目录路径，如果不存在会自动创建
    """
    output_dir = get_sage_config_dir() / "finetune_output"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def check_training_dependencies() -> bool:
    """检查微调训练依赖是否已安装"""
    try:
        import accelerate  # noqa: F401
        import peft  # noqa: F401

        return True
    except ImportError:
        return False


def show_install_instructions() -> None:
    """显示微调依赖安装说明"""
    console.print(
        Panel.fit(
            "[bold yellow]⚠️  微调依赖未安装[/bold yellow]\n\n"
            "微调功能需要安装 SAGE 微调依赖包\n\n"
            "[bold cyan]推荐安装方式（从 SAGE 根目录）:[/bold cyan]\n"
            "[green]pip install -e packages/sage-libs[finetune][/green]\n\n"
            "这将安装以下依赖:\n"
            "  • peft (LoRA支持)\n"
            "  • accelerate (训练加速)\n"
            "  • trl (RLHF/DPO支持)\n"
            "  • tensorboard (可视化)\n"
            "  • wandb (实验追踪)\n\n"
            "[bold]其他安装选项:[/bold]\n"
            "  • 分布式训练: [cyan]pip install -e packages/sage-libs[finetune-full][/cyan]\n"
            "  • 完整功能: [cyan]pip install -e packages/sage-libs[full][/cyan]\n\n"
            "[bold yellow]注意:[/bold yellow] SAGE 使用自研训练脚本，无需安装 LLaMA-Factory\n"
            "如需使用 LLaMA-Factory，请手动安装: [cyan]pip install llmtuner[/cyan]\n"
            "(注意：llmtuner 与 transformers 4.56+ 存在兼容性问题)",
            border_style="yellow",
            title="📦 安装说明",
        )
    )


def collect_sage_code_files(
    root_dir: Path, extensions: list[str] | None = None, exclude_dirs: list[str] | None = None
) -> list[Path]:
    """收集SAGE代码文件"""
    if extensions is None:
        extensions = [".py", ".yaml", ".yml", ".toml", ".md", ".rst"]

    if exclude_dirs is None:
        exclude_dirs = [
            ".git",
            "__pycache__",
            ".pytest_cache",
            "node_modules",
            "venv",
            ".venv",
            "env",
            ".env",
            "build",
            "dist",
            "*.egg-info",
            ".mypy_cache",
            ".tox",
            "logs",
            "data",
        ]

    files = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("🔍 扫描代码文件...", total=None)

        for root, dirs, filenames in os.walk(root_dir):
            # 过滤排除目录
            dirs[:] = [
                d
                for d in dirs
                if not any(d.startswith(ex.rstrip("*")) or d == ex for ex in exclude_dirs)
            ]

            for filename in filenames:
                if any(filename.endswith(ext) for ext in extensions):
                    file_path = Path(root) / filename
                    files.append(file_path)

        progress.update(task, completed=True)

    return files
