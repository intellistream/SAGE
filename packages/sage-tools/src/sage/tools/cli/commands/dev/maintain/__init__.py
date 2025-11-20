"""
维护工具命令组

提供项目维护、Submodule 管理、Git hooks、安全检查等功能。
"""

import subprocess
from pathlib import Path

import typer
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
        # 设置超时避免卡住（doctor 命令30秒超时，其他命令60秒）
        timeout = 30 if command == "doctor" else 60
        result = subprocess.run(cmd, cwd=project_root, timeout=timeout)
        return result.returncode
    except subprocess.TimeoutExpired:
        console.print(f"[red]执行超时: 命令运行超过 {timeout} 秒[/red]")
        console.print("[yellow]提示: 如果是 doctor 命令，可能是环境问题导致检查变慢[/yellow]")
        return 1
    except Exception as e:
        console.print(f"[red]执行失败: {e}[/red]")
        return 1


@app.command(name="doctor")
def doctor():
    """
    🔍 健康检查

    运行完整的项目健康检查，诊断常见问题。

    示例：
        sage-dev maintain doctor
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
        sage-dev maintain submodule init
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
        sage-dev maintain submodule status
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
        sage-dev maintain submodule switch
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
        sage-dev maintain submodule update
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
        sage-dev maintain submodule fix-conflict
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
        sage-dev maintain submodule cleanup
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
        sage-dev maintain submodule bootstrap
    """
    console.print("\n[bold blue]⚡ Bootstrap Submodules[/bold blue]\n")
    exit_code = run_maintenance_script("submodule", "bootstrap")
    if exit_code != 0:
        raise typer.Exit(exit_code)


app.add_typer(submodule_app, name="submodule")


# Git Hooks 管理子命令组
hooks_app = typer.Typer(
    name="hooks",
    help="🪝 Git Hooks 管理",
    no_args_is_help=True,
)

HOOK_MODES = ("lightweight", "full")


def _validate_hook_mode(value: str) -> str:
    normalized = value.lower()
    if normalized not in HOOK_MODES:
        raise typer.BadParameter(f"无效的 hooks 模式: {value}. 可选值: {', '.join(HOOK_MODES)}")
    return normalized


@hooks_app.command(name="install")
def hooks_install(
    quiet: bool = typer.Option(False, "--quiet", "-q", help="静默模式，只显示错误"),
    root_dir: str = typer.Option(None, "--root", help="项目根目录（默认自动检测）"),
    mode: str = typer.Option(
        "lightweight",
        "--mode",
        "-m",
        callback=_validate_hook_mode,
        help="选择 hooks 安装模式: lightweight (默认) 或 full",
    ),
):
    """
    安装 SAGE Git hooks。

    安装 pre-commit hook 用于代码质量检查、架构合规性验证和文档规范检查。

    示例:
        sage-dev maintain hooks install
        sage-dev maintain hooks install --quiet
    """
    from pathlib import Path

    from sage.tools.dev.hooks import HooksInstaller

    root_path = Path(root_dir) if root_dir else None
    installer = HooksInstaller(root_dir=root_path, quiet=quiet, mode=mode)

    try:
        success = installer.install()
        if success:
            if not quiet:
                console.print("\n[green]✅ Git hooks 安装成功！[/green]")
        else:
            console.print("\n[red]❌ Git hooks 安装失败[/red]")
            raise typer.Exit(1)
    except Exception as e:
        console.print(f"\n[red]❌ 安装过程中出错: {e}[/red]")
        raise typer.Exit(1)


@hooks_app.command(name="uninstall")
def hooks_uninstall(
    quiet: bool = typer.Option(False, "--quiet", "-q", help="静默模式，只显示错误"),
    root_dir: str = typer.Option(None, "--root", help="项目根目录（默认自动检测）"),
):
    """
    卸载 SAGE Git hooks。

    移除已安装的 pre-commit hook 和 pre-commit 框架配置。

    示例:
        sage-dev maintain hooks uninstall
    """
    from pathlib import Path

    from sage.tools.dev.hooks import HooksInstaller

    root_path = Path(root_dir) if root_dir else None
    installer = HooksInstaller(root_dir=root_path, quiet=quiet)

    try:
        success = installer.uninstall()
        if success:
            if not quiet:
                console.print("\n[green]✅ Git hooks 卸载成功！[/green]")
        else:
            console.print("\n[red]❌ Git hooks 卸载失败[/red]")
            raise typer.Exit(1)
    except Exception as e:
        console.print(f"\n[red]❌ 卸载过程中出错: {e}[/red]")
        raise typer.Exit(1)


@hooks_app.command(name="status")
def hooks_status(
    root_dir: str = typer.Option(None, "--root", help="项目根目录（默认自动检测）"),
    json_output: bool = typer.Option(False, "--json", help="以 JSON 格式输出"),
):
    """
    检查 Git hooks 的安装状态。

    显示 pre-commit hook、pre-commit 框架和各种检查工具的状态。

    示例:
        sage-dev maintain hooks status
        sage-dev maintain hooks status --json
    """
    from pathlib import Path

    from sage.tools.dev.hooks import HooksInstaller

    root_path = Path(root_dir) if root_dir else None
    installer = HooksInstaller(root_dir=root_path, quiet=True)

    try:
        if json_output:
            import json

            status_info = installer.status()
            console.print(json.dumps(status_info, indent=2))
        else:
            installer.print_status()
    except Exception as e:
        console.print(f"\n[red]❌ 检查状态时出错: {e}[/red]")
        raise typer.Exit(1)


@hooks_app.command(name="reinstall")
def hooks_reinstall(
    quiet: bool = typer.Option(False, "--quiet", "-q", help="静默模式，只显示错误"),
    root_dir: str = typer.Option(None, "--root", help="项目根目录（默认自动检测）"),
    mode: str = typer.Option(
        "lightweight",
        "--mode",
        "-m",
        callback=_validate_hook_mode,
        help="选择 hooks 安装模式: lightweight (默认) 或 full",
    ),
):
    """
    重新安装 SAGE Git hooks。

    先卸载现有的 hooks，然后重新安装。用于更新 hooks 到最新版本。

    示例:
        sage-dev maintain hooks reinstall
    """
    from pathlib import Path

    from sage.tools.dev.hooks import HooksManager

    root_path = Path(root_dir) if root_dir else None
    manager = HooksManager(root_dir=root_path, mode=mode)

    try:
        # Uninstall first
        if not quiet:
            console.print("[blue]🔄 正在卸载现有 hooks...[/blue]")
        manager.uninstall(quiet=True)

        # Then install
        if not quiet:
            console.print("[blue]🔄 正在重新安装 hooks...[/blue]\n")
        success = manager.install(quiet=quiet)

        if success:
            if not quiet:
                console.print("\n[green]✅ Git hooks 重新安装成功！[/green]")
        else:
            console.print("\n[red]❌ Git hooks 重新安装失败[/red]")
            raise typer.Exit(1)
    except Exception as e:
        console.print(f"\n[red]❌ 重新安装过程中出错: {e}[/red]")
        raise typer.Exit(1)


app.add_typer(hooks_app, name="hooks")


@app.command(name="security")
def security_check():
    """
    🔒 安全检查

    检查敏感信息泄露、密钥等安全问题。

    示例：
        sage-dev maintain security
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
        sage-dev maintain clean        # 标准清理
        sage-dev maintain clean --deep # 深度清理
    """
    console.print("\n[bold blue]🧹 清理项目[/bold blue]\n")

    command = "clean-deep" if deep else "clean"
    exit_code = run_maintenance_script(command)

    if exit_code != 0:
        raise typer.Exit(exit_code)


__all__ = ["app"]
