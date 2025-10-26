"""
维护工具命令组

提供项目维护、Submodule 管理、Git hooks、安全检查等功能。
"""

import subprocess
import typer
from pathlib import Path
from rich.console import Console

app = typer.Typer(
    name="maintain",
    help="🔧 维护工具 - Submodule、Hooks、诊断",
    no_args_is_help=True,
)

console = Console()


def get_project_root() -> Path:
    """获取项目根目录"""
    current = Path.cwd()
    # 向上查找包含 .git 的目录
    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent
    return Path.cwd()


def run_maintenance_script(command: str, *args) -> int:
    """运行 sage-maintenance.sh 脚本"""
    project_root = get_project_root()
    script_path = project_root / "tools" / "maintenance" / "sage-maintenance.sh"
    
    if not script_path.exists():
        console.print(f"[red]错误: 未找到维护脚本 {script_path}[/red]")
        return 1
    
    cmd = ["bash", str(script_path), command, *args]
    
    try:
        result = subprocess.run(cmd, cwd=project_root)
        return result.returncode
    except Exception as e:
        console.print(f"[red]执行失败: {e}[/red]")
        return 1


@app.command(name="doctor")
def doctor():
    """
    🔍 健康检查
    
    运行完整的项目健康检查，诊断常见问题。
    
    示例：
        sage dev maintain doctor
    """
    console.print("\n[bold blue]🔍 运行项目健康检查[/bold blue]\n")
    exit_code = run_maintenance_script("doctor")
    if exit_code != 0:
        raise typer.Exit(exit_code)


# Submodule 管理子命令组
submodule_app = typer.Typer(
    name="submodule",
    help="📦 Submodule 管理",
    no_args_is_help=True,
)


@submodule_app.command(name="init")
def submodule_init():
    """
    🚀 初始化 Submodules
    
    初始化所有 submodules 并切换到正确的分支。
    
    示例：
        sage dev maintain submodule init
    """
    console.print("\n[bold blue]🚀 初始化 Submodules[/bold blue]\n")
    exit_code = run_maintenance_script("submodule", "init")
    if exit_code != 0:
        raise typer.Exit(exit_code)


@submodule_app.command(name="status")
def submodule_status():
    """
    📊 查看 Submodule 状态
    
    显示所有 submodules 的状态和分支信息。
    
    示例：
        sage dev maintain submodule status
    """
    console.print("\n[bold blue]📊 Submodule 状态[/bold blue]\n")
    exit_code = run_maintenance_script("submodule", "status")
    if exit_code != 0:
        raise typer.Exit(exit_code)


@submodule_app.command(name="switch")
def submodule_switch():
    """
    🔄 切换 Submodule 分支
    
    根据当前 SAGE 分支切换 submodules 到对应分支。
    
    示例：
        sage dev maintain submodule switch
    """
    console.print("\n[bold blue]🔄 切换 Submodule 分支[/bold blue]\n")
    exit_code = run_maintenance_script("submodule", "switch")
    if exit_code != 0:
        raise typer.Exit(exit_code)


@submodule_app.command(name="update")
def submodule_update():
    """
    ⬆️ 更新 Submodules
    
    更新所有 submodules 到远程最新版本。
    
    示例：
        sage dev maintain submodule update
    """
    console.print("\n[bold blue]⬆️ 更新 Submodules[/bold blue]\n")
    exit_code = run_maintenance_script("submodule", "update")
    if exit_code != 0:
        raise typer.Exit(exit_code)


@submodule_app.command(name="fix-conflict")
def submodule_fix_conflict():
    """
    🔧 解决 Submodule 冲突
    
    自动解决 submodule 冲突。
    
    示例：
        sage dev maintain submodule fix-conflict
    """
    console.print("\n[bold blue]🔧 解决 Submodule 冲突[/bold blue]\n")
    exit_code = run_maintenance_script("submodule", "fix-conflict")
    if exit_code != 0:
        raise typer.Exit(exit_code)


@submodule_app.command(name="cleanup")
def submodule_cleanup():
    """
    🧹 清理 Submodule 配置
    
    清理旧的 submodule 配置。
    
    示例：
        sage dev maintain submodule cleanup
    """
    console.print("\n[bold blue]🧹 清理 Submodule 配置[/bold blue]\n")
    exit_code = run_maintenance_script("submodule", "cleanup")
    if exit_code != 0:
        raise typer.Exit(exit_code)


@submodule_app.command(name="bootstrap")
def submodule_bootstrap():
    """
    ⚡ 快速初始化（bootstrap）
    
    一键初始化和配置所有 submodules。
    
    示例：
        sage dev maintain submodule bootstrap
    """
    console.print("\n[bold blue]⚡ Bootstrap Submodules[/bold blue]\n")
    exit_code = run_maintenance_script("submodule", "bootstrap")
    if exit_code != 0:
        raise typer.Exit(exit_code)


app.add_typer(submodule_app, name="submodule")


@app.command(name="hooks")
def setup_hooks(
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="强制重新安装",
    ),
):
    """
    🪝 安装 Git Hooks
    
    安装或更新项目的 Git hooks。
    
    示例：
        sage dev maintain hooks           # 安装 hooks
        sage dev maintain hooks --force   # 强制重新安装
    """
    console.print("\n[bold blue]🪝 安装 Git Hooks[/bold blue]\n")
    
    args = []
    if force:
        args.append("--force")
    
    exit_code = run_maintenance_script("setup-hooks", *args)
    if exit_code != 0:
        raise typer.Exit(exit_code)


@app.command(name="security")
def security_check():
    """
    🔒 安全检查
    
    检查敏感信息泄露、密钥等安全问题。
    
    示例：
        sage dev maintain security
    """
    console.print("\n[bold blue]🔒 安全检查[/bold blue]\n")
    exit_code = run_maintenance_script("security-check")
    if exit_code != 0:
        raise typer.Exit(exit_code)


@app.command(name="clean")
def clean_project(
    deep: bool = typer.Option(
        False,
        "--deep",
        help="深度清理",
    ),
):
    """
    🧹 清理项目
    
    清理构建产物、缓存等。
    
    示例：
        sage dev maintain clean        # 标准清理
        sage dev maintain clean --deep # 深度清理
    """
    console.print("\n[bold blue]🧹 清理项目[/bold blue]\n")
    
    command = "clean-deep" if deep else "clean"
    exit_code = run_maintenance_script(command)
    
    if exit_code != 0:
        raise typer.Exit(exit_code)


__all__ = ["app"]
