#!/usr/bin/env python3
"""
SAGE PyPI命令模块

提供PyPI相关的开发命令，包括包验证、发布准备等功能。
"""

import datetime
import shutil
import subprocess
import sys
import time
from pathlib import Path

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from sage.tools.cli.utils.dev_check import require_source_code

console = Console()
app = typer.Typer(help="📦 PyPI发布管理命令")


@app.command()
@require_source_code
def validate(
    test_dir: str | None = typer.Option(None, "--test-dir", help="指定测试目录"),
    skip_wheel: bool = typer.Option(False, "--skip-wheel", help="跳过wheel构建"),
    cleanup: bool = typer.Option(True, "--cleanup/--no-cleanup", help="测试完成后清理临时文件"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="显示详细输出"),
    fast: bool = typer.Option(False, "--fast", help="使用快速验证模式"),
    check_auth: bool = typer.Option(True, "--check-auth/--skip-auth", help="检查PyPI认证配置"),
):
    """验证SAGE代码的PyPI发布准备状态（仅开发模式）

    这个命令会模拟完整的PyPI发布和用户安装流程，确保：

    📦 发布准备验证：
    - wheel包能够正确构建
    - 包的元数据和依赖关系正确
    - 代码结构符合PyPI发布要求

    🔧 用户安装体验验证（使用本地构建的wheel包）：
    - 模拟用户执行 "pip install isage" 的完整过程
    - 验证安装后核心功能正常工作
    - 确保命令行工具可用（完整模式）
    - 验证开发工具正常（完整模式）
    - 测试示例代码能正常运行（完整模式）

    ⚡ 使用 --fast 选项可以进行快速验证，只测试核心功能
    🔬 完整模式会进行全面的发布准备验证

    📝 注意：此命令使用本地构建的wheel包进行验证
    💡 发布到TestPyPI后，请使用以下命令测试实际安装：
       pip install --index-url https://test.pypi.org/simple/ \\
                   --extra-index-url https://pypi.org/simple/ isage

    💡 建议在每次准备发布到PyPI前运行此命令！
    """
    console.print("🧪 [bold blue]SAGE PyPI发布准备验证[/bold blue]")
    console.print("=" * 60)

    # 检查PyPI认证配置（如果启用）
    if check_auth:
        console.print("\n🔐 [blue]检查PyPI认证配置...[/blue]")

        # 查找项目根目录
        current_dir = Path(__file__).resolve()
        project_root = current_dir

        while project_root.parent != project_root:
            if (project_root / "packages").exists():
                break
            project_root = project_root.parent

        pypirc_exists = False
        pypirc_paths = [
            project_root / ".pypirc",
            Path.home() / ".pypirc",
        ]

        for path in pypirc_paths:
            if path.exists():
                console.print(f"✅ 找到配置文件: {path}")
                pypirc_exists = True
                break

        if not pypirc_exists:
            console.print("[yellow]⚠️  未找到.pypirc配置文件[/yellow]")
            console.print("💡 [blue]发布时需要配置PyPI认证，运行以下命令查看配置帮助:[/blue]")
            console.print("   [cyan]sage dev pypi publish --help[/cyan]")
        else:
            console.print("✅ [green]PyPI认证配置已就绪[/green]")

    # 根据模式选择测试器
    if fast:
        console.print("\n⚡ [yellow]使用快速验证模式（核心功能验证）[/yellow]")
        script_name = "validate_pip_fast.py"
        class_name = "FastPipValidator"
        run_method = "run_fast_validation"
    else:
        console.print("\n🔬 [blue]使用完整验证模式（全面发布准备验证）[/blue]")
        script_name = "validate_pip_install_complete.py"
        class_name = "CompletePipInstallTester"
        run_method = "run_all_tests"

    # 导入测试器
    try:
        # 找到SAGE项目根目录
        current_dir = Path(__file__).resolve()
        project_root = current_dir

        # 向上查找SAGE项目根目录
        while project_root.parent != project_root:
            if (project_root / "packages").exists():
                break
            project_root = project_root.parent
        else:
            console.print("[red]❌ 未找到packages目录[/red]")
            console.print("[yellow]请确保在SAGE项目根目录中运行此命令[/yellow]")
            raise typer.Exit(1)

        # 查找测试脚本
        script_path = project_root / "packages" / "sage-tools" / "tests" / "pypi" / script_name
        if not script_path.exists():
            console.print(f"[red]❌ 测试脚本不存在: {script_path}[/red]")
            raise typer.Exit(1)

        # 动态导入测试器类
        script_dir = script_path.parent
        sys.path.insert(0, str(script_dir))
        module_name = script_path.stem
        tester_module = __import__(module_name)
        TesterClass = getattr(tester_module, class_name)

        # 创建测试器实例
        tester = TesterClass(test_dir, skip_wheel)

    except ImportError as e:
        console.print(f"[red]❌ 无法导入测试器: {e}[/red]")
        console.print("[yellow]验证模块导入失败，请检查安装[/yellow]")
        raise typer.Exit(1)

    # 创建测试器
    tester = TesterClass(test_dir, skip_wheel)

    # 设置详细输出
    if verbose:
        console.print(f"📁 测试目录: {tester.test_dir}")
        console.print(f"🏠 项目根目录: {tester.project_root}")

    try:
        # 运行测试
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            task = progress.add_task("正在执行PyPI发布准备验证...", total=None)

            # 动态调用运行方法
            run_func = getattr(tester, run_method)
            success = run_func()

            progress.update(task, completed=True)

        if success:
            console.print("\n🎉 [bold green]PyPI发布准备验证全部通过！[/bold green]")
            console.print("📦 [green]代码已准备好发布到PyPI[/green]")
            console.print("✨ [green]用户pip install isage后将获得完整功能[/green]")
        else:
            console.print("\n⚠️  [bold yellow]PyPI发布准备验证部分失败[/bold yellow]")
            console.print("🔧 [yellow]建议在发布到PyPI前修复这些问题[/yellow]")

            if not cleanup:
                console.print(f"💡 [blue]测试环境保留在: {tester.test_dir}[/blue]")
                console.print("💡 [blue]可以手动检查或重新运行测试[/blue]")

        # 清理
        if cleanup and success:
            with Progress(
                SpinnerColumn(),
                TextColumn("正在清理测试环境..."),
                console=console,
                transient=True,
            ) as progress:
                task = progress.add_task("清理中...", total=None)
                tester.cleanup()
                progress.update(task, completed=True)
            console.print("🧹 [green]测试环境已清理[/green]")

        return success

    except KeyboardInterrupt:
        console.print("\n⚠️  [yellow]测试被用户中断[/yellow]")
        if cleanup:
            tester.cleanup()
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"\n❌ [red]测试过程中发生异常: {e}[/red]")
        if verbose:
            import traceback

            console.print(traceback.format_exc())
        raise typer.Exit(1)


@app.command()
@require_source_code
def check(
    package: str = typer.Option("sage", help="要检查的包名"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="显示详细输出"),
):
    """检查SAGE包的构建状态（仅开发模式）

    检查wheel包是否已构建，以及基本的包信息。
    """
    console.print(f"🔍 [bold blue]检查包构建状态: {package}[/bold blue]")

    # 查找项目根目录
    current_dir = Path.cwd()
    project_root = current_dir

    # 向上查找SAGE项目根目录
    while project_root.parent != project_root:
        if (project_root / "packages" / package).exists():
            break
        project_root = project_root.parent
    else:
        console.print(f"[red]❌ 未找到{package}包目录[/red]")
        raise typer.Exit(1)

    package_dir = project_root / "packages" / package
    dist_dir = package_dir / "dist"

    console.print(f"📁 包目录: {package_dir}")

    if not dist_dir.exists():
        console.print(f"[yellow]⚠️  dist目录不存在: {dist_dir}[/yellow]")
        console.print("[blue]💡 运行 sage dev pypi build 构建包[/blue]")
        return False

    # 查找wheel文件
    wheel_files = list(dist_dir.glob("*.whl"))
    if not wheel_files:
        console.print(f"[yellow]⚠️  未找到wheel文件在: {dist_dir}[/yellow]")
        console.print("[blue]💡 运行 sage dev pypi build 构建包[/blue]")
        return False

    console.print(f"✅ [green]找到 {len(wheel_files)} 个wheel文件:[/green]")
    for wheel_file in wheel_files:
        file_size = wheel_file.stat().st_size / 1024  # KB
        file_time = time.ctime(wheel_file.stat().st_mtime)
        console.print(f"  📦 {wheel_file.name} ({file_size:.1f}KB, {file_time})")

        if verbose:
            # 显示wheel内容概览
            try:
                result = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "wheel",
                        "unpack",
                        "--dest",
                        "/tmp",
                        str(wheel_file),
                    ],
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0:
                    console.print("    📋 wheel内容检查通过")
                else:
                    console.print(f"    ⚠️  wheel内容检查失败: {result.stderr}")
            except FileNotFoundError:
                console.print("    💡 安装wheel工具以获取更详细信息: pip install wheel")

    return True


@app.command()
@require_source_code
def build(
    package: str = typer.Option("sage", help="要构建的包名"),
    clean: bool = typer.Option(True, "--clean/--no-clean", help="构建前清理旧文件"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="显示详细输出"),
):
    """构建SAGE wheel包（仅开发模式）

    清理并重新构建指定的包。
    """
    console.print(f"🔨 [bold blue]构建包: {package}[/bold blue]")

    # 查找项目根目录
    current_dir = Path.cwd()
    project_root = current_dir

    # 向上查找SAGE项目根目录
    while project_root.parent != project_root:
        if (project_root / "packages" / package).exists():
            break
        project_root = project_root.parent
    else:
        console.print(f"[red]❌ 未找到{package}包目录[/red]")
        raise typer.Exit(1)

    package_dir = project_root / "packages" / package
    console.print(f"📁 包目录: {package_dir}")

    if not (package_dir / "setup.py").exists():
        console.print(f"[red]❌ 未找到setup.py在: {package_dir}[/red]")
        raise typer.Exit(1)

    try:
        # 清理旧文件
        if clean:
            with Progress(
                SpinnerColumn(),
                TextColumn("正在清理旧文件..."),
                console=console,
                transient=True,
            ) as progress:
                task = progress.add_task("清理中...", total=None)

                for dir_name in ["dist", "build", f"{package}.egg-info"]:
                    dir_path = package_dir / dir_name
                    if dir_path.exists():
                        shutil.rmtree(dir_path)
                        if verbose:
                            console.print(f"🧹 清理: {dir_path}")

                progress.update(task, completed=True)
            console.print("✅ [green]清理完成[/green]")

        # 构建wheel包
        with Progress(
            SpinnerColumn(),
            TextColumn("正在构建wheel包..."),
            console=console,
            transient=True,
        ) as progress:
            task = progress.add_task("构建中...", total=None)

            cmd = [sys.executable, "setup.py", "bdist_wheel"]
            if not verbose:
                cmd.append("--quiet")

            result = subprocess.run(
                cmd, cwd=package_dir, capture_output=not verbose, text=True, timeout=300
            )

            progress.update(task, completed=True)

        if result.returncode == 0:
            console.print("✅ [green]构建成功[/green]")

            # 显示构建结果
            dist_dir = package_dir / "dist"
            if dist_dir.exists():
                wheel_files = list(dist_dir.glob("*.whl"))
                if wheel_files:
                    console.print(f"📦 [green]生成了 {len(wheel_files)} 个wheel文件:[/green]")
                    for wheel_file in wheel_files:
                        file_size = wheel_file.stat().st_size / 1024  # KB
                        console.print(f"  • {wheel_file.name} ({file_size:.1f}KB)")

            return True
        else:
            console.print("[red]❌ 构建失败[/red]")
            if not verbose and result.stderr:
                console.print(f"错误信息: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        console.print("[red]❌ 构建超时[/red]")
        return False
    except Exception as e:
        console.print(f"[red]❌ 构建异常: {e}[/red]")
        return False


@app.command()
@require_source_code
def clean(
    package: str = typer.Option("sage", help="要清理的包名"),
    all_packages: bool = typer.Option(False, "--all", help="清理所有包"),
):
    """清理构建文件（仅开发模式）

    清理指定包或所有包的构建文件。
    """
    if all_packages:
        console.print("🧹 [bold blue]清理所有包的构建文件[/bold blue]")
    else:
        console.print(f"🧹 [bold blue]清理包构建文件: {package}[/bold blue]")

    # 查找项目根目录
    current_dir = Path.cwd()
    project_root = current_dir

    # 向上查找SAGE项目根目录
    while project_root.parent != project_root:
        if (project_root / "packages").exists():
            break
        project_root = project_root.parent
    else:
        console.print("[red]❌ 未找到packages目录[/red]")
        raise typer.Exit(1)

    packages_dir = project_root / "packages"

    if all_packages:
        target_packages = [p.name for p in packages_dir.iterdir() if p.is_dir()]
    else:
        target_packages = [package]

    cleaned_count = 0

    for pkg_name in target_packages:
        pkg_dir = packages_dir / pkg_name
        if not pkg_dir.exists():
            console.print(f"[yellow]⚠️  包目录不存在: {pkg_dir}[/yellow]")
            continue

        console.print(f"📁 清理包: {pkg_name}")

        for dir_name in ["dist", "build", f"{pkg_name}.egg-info"]:
            dir_path = pkg_dir / dir_name
            if dir_path.exists():
                try:
                    shutil.rmtree(dir_path)
                    console.print(f"  ✅ 清理: {dir_name}")
                    cleaned_count += 1
                except Exception as e:
                    console.print(f"  ❌ 清理失败 {dir_name}: {e}")
            else:
                console.print(f"  ℹ️  不存在: {dir_name}")

    console.print(f"🎉 [green]清理完成，处理了 {cleaned_count} 个目录[/green]")


@app.command()
@require_source_code
def publish(
    dry_run: bool = typer.Option(False, "--dry-run", help="发布到TestPyPI进行测试"),
    skip_build: bool = typer.Option(False, "--skip-build", help="跳过构建步骤"),
    packages: list[str] | None = typer.Option(None, "--package", help="指定要发布的包"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="显示详细输出"),
):
    """发布SAGE包到PyPI（仅开发模式）

    按照正确的依赖顺序构建和发布所有SAGE包到PyPI。

    🚀 发布流程：
    - 清理旧的构建文件
    - 按依赖顺序构建包
    - 上传到PyPI或TestPyPI
    - 生成发布报告

    ⚡ 使用 --dry-run 可以先发布到TestPyPI进行测试
    📦 使用 --package 可以指定发布特定的包

    🧪 TestPyPI测试安装：
    发布到TestPyPI后，使用以下命令测试安装：
        pip install --index-url https://test.pypi.org/simple/ \\
                    --extra-index-url https://pypi.org/simple/ isage

    注意：--extra-index-url 参数很重要！
    TestPyPI可能缺少某些依赖包（如fastapi、uvicorn等），
    添加此参数后会自动从正式PyPI获取这些依赖。

    💡 建议发布前先运行: sage dev pypi validate
    """
    if dry_run:
        console.print("🧪 [bold yellow]PyPI发布 - TestPyPI模式（预演）[/bold yellow]")
    else:
        console.print("🚀 [bold blue]PyPI发布 - 正式发布模式[/bold blue]")

    console.print("=" * 60)

    # 查找项目根目录
    current_dir = Path(__file__).resolve()
    project_root = current_dir

    while project_root.parent != project_root:
        if (project_root / "packages").exists():
            break
        project_root = project_root.parent
    else:
        console.print("[red]❌ 未找到packages目录[/red]")
        raise typer.Exit(1)

    # 检查依赖
    if not _check_publish_dependencies():
        raise typer.Exit(1)

    # 检查PyPI认证配置
    if not _check_pypi_credentials(project_root, dry_run):
        raise typer.Exit(1)

    # 创建发布器
    publisher = PyPIPublisher(project_root, dry_run, verbose)

    try:
        # 清理构建文件
        if not skip_build:
            publisher.clean_build_artifacts()

        # 发布包
        success = publisher.publish_packages(packages, skip_build)

        if success:
            if dry_run:
                console.print("\n🎉 [bold green]TestPyPI发布成功！[/bold green]")
                console.print("🔍 [green]请在TestPyPI上验证包的完整性[/green]")
                console.print("\n📝 [cyan]从TestPyPI安装测试（需要指定正式PyPI作为后备源）:[/cyan]")
                console.print(
                    "   [yellow]pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ isage[/yellow]"
                )
                console.print(
                    "\n💡 [dim]--extra-index-url 参数确保从正式PyPI获取依赖包（如fastapi、uvicorn等）[/dim]"
                )
                console.print("💡 [blue]验证无误后可运行正式发布: sage dev pypi publish[/blue]")
            else:
                console.print("\n🎉 [bold green]PyPI发布成功！[/bold green]")
                console.print("📦 [green]所有包已成功发布到PyPI[/green]")
                console.print("✨ [green]用户现在可以通过pip install isage安装[/green]")
        else:
            console.print("\n⚠️  [bold yellow]发布过程中遇到问题[/bold yellow]")
            console.print("🔧 [yellow]请查看日志并解决问题后重试[/yellow]")
            raise typer.Exit(1)

    except KeyboardInterrupt:
        console.print("\n⚠️  [yellow]发布被用户中断[/yellow]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"\n❌ [red]发布过程中发生异常: {e}[/red]")
        if verbose:
            import traceback

            console.print(traceback.format_exc())
        raise typer.Exit(1)


def _check_publish_dependencies() -> bool:
    """检查发布所需的依赖"""
    console.print("🔍 [blue]检查发布依赖...[/blue]")

    # 检查twine
    try:
        result = subprocess.run(["twine", "--version"], capture_output=True, text=True)
        if result.returncode != 0:
            console.print("[red]❌ twine未正确安装[/red]")
            return False
        console.print("✅ twine已安装")
    except FileNotFoundError:
        console.print("[red]❌ twine未安装，请运行: pip install twine[/red]")
        return False

    # 检查build
    try:
        result = subprocess.run(
            [sys.executable, "-m", "build", "--help"], capture_output=True, text=True
        )
        if result.returncode != 0:
            console.print("[red]❌ build模块未正确安装[/red]")
            return False
        console.print("✅ build模块已安装")
    except FileNotFoundError:
        console.print("[red]❌ build模块未安装，请运行: pip install build[/red]")
        return False

    console.print("✅ [green]所有发布依赖检查通过[/green]")
    return True


def _check_pypi_credentials(project_root: Path, dry_run: bool = False) -> bool:
    """检查PyPI认证配置"""
    console.print("🔐 [blue]检查PyPI认证配置...[/blue]")

    # 检查配置文件位置
    pypirc_paths = [
        project_root / ".pypirc",  # 项目目录
        Path.home() / ".pypirc",  # 用户主目录
    ]

    pypirc_found = None
    for path in pypirc_paths:
        if path.exists():
            pypirc_found = path
            break

    if not pypirc_found:
        console.print("[red]❌ 未找到.pypirc配置文件[/red]")
        console.print("\n📝 [yellow]首次使用需要配置PyPI认证信息：[/yellow]")

        # 提示配置步骤
        console.print("\n🔧 [bold blue]配置步骤：[/bold blue]")
        console.print("1️⃣  获取PyPI API令牌：")
        console.print("   • 正式PyPI: https://pypi.org/manage/account/token/")
        console.print("   • 测试PyPI: https://test.pypi.org/manage/account/token/")

        console.print(f"\n2️⃣  创建配置文件: {project_root}/.pypirc")
        console.print("   [dim]（或者 ~/.pypirc 用于全局配置）[/dim]")

        console.print("\n3️⃣  配置文件内容示例：")
        console.print("[dim]# 在项目根目录或用户主目录创建 .pypirc 文件[/dim]")
        console.print(
            """[cyan]
[pypi]
  username = __token__
  password = pypi-YOUR_PYPI_TOKEN_HERE

[testpypi]
  username = __token__
  password = pypi-YOUR_TESTPYPI_TOKEN_HERE[/cyan]"""
        )

        console.print("\n💡 [yellow]提示：[/yellow]")
        console.print("• 令牌以 'pypi-' 开头")
        console.print("• 正式发布前建议先用 --dry-run 测试")
        console.print("• 配置文件会被自动检测并使用")

        return False

    console.print(f"✅ 找到配置文件: {pypirc_found}")

    # 验证配置文件格式
    try:
        with open(pypirc_found, encoding="utf-8") as f:
            content = f.read()

        # 检查必要的配置节
        target_section = "testpypi" if dry_run else "pypi"

        if f"[{target_section}]" not in content:
            console.print(f"[red]❌ 配置文件缺少 [{target_section}] 节[/red]")
            console.print(f"💡 [yellow]请在 {pypirc_found} 中添加 {target_section} 配置[/yellow]")
            return False

        if "username" not in content or "password" not in content:
            console.print("[red]❌ 配置文件缺少username或password字段[/red]")
            return False

        console.print(f"✅ {target_section} 配置检查通过")

    except Exception as e:
        console.print(f"[red]❌ 读取配置文件失败: {e}[/red]")
        return False

    return True


class PyPIPublisher:
    """PyPI发布管理器"""

    def __init__(self, project_root: Path, dry_run: bool = False, verbose: bool = False):
        self.project_root = project_root
        self.dry_run = dry_run
        self.verbose = verbose

        # 创建日志目录
        self.log_dir = project_root / "logs" / "pypi"
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # 生成日志文件
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        mode = "testpypi" if dry_run else "pypi"
        self.log_file = self.log_dir / f"publish_{mode}_{timestamp}.log"

        console.print(f"📝 详细日志: {self.log_file}")

        # 初始化日志
        with open(self.log_file, "w", encoding="utf-8") as f:
            f.write(f"[{datetime.datetime.now()}] ======== SAGE PyPI发布开始 ========\n")

        # 发布顺序（按依赖关系）
        self.publish_order = [
            "sage-common",  # 基础工具包
            "sage-kernel",  # 内核
            "sage-tools",  # CLI工具（依赖common和kernel）
            "sage-middleware",  # 中间件
            "sage-libs",  # 应用库
            "sage-apps",  # 应用示例（依赖common、kernel、middleware、libs）
            "sage-benchmark",  # 基准测试（依赖common、kernel、middleware、libs）
            "sage-studio",  # Studio低代码界面（依赖common、kernel、middleware、libs）
            "sage",  # Meta包，依赖所有其他包
        ]

    def log_to_file(self, message: str):
        """写入日志文件"""
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.datetime.now()}] {message}\n")

    def clean_build_artifacts(self):
        """清理构建文件"""
        console.print("\n🧹 [blue]清理构建产物...[/blue]")

        packages_dir = self.project_root / "packages"
        cleaned_count = 0

        for package_dir in packages_dir.iterdir():
            if not package_dir.is_dir():
                continue

            # 清理每个包的构建文件
            for pattern in ["dist", "build", "*.egg-info"]:
                if pattern.startswith("*"):
                    # 处理通配符模式
                    for item in package_dir.glob(pattern):
                        if item.is_dir():
                            shutil.rmtree(item)
                            cleaned_count += 1
                            if self.verbose:
                                console.print(f"  清理: {item}")
                else:
                    # 处理普通目录
                    item = package_dir / pattern
                    if item.exists():
                        shutil.rmtree(item)
                        cleaned_count += 1
                        if self.verbose:
                            console.print(f"  清理: {item}")

        console.print(f"✅ [green]清理完成，处理了 {cleaned_count} 个目录[/green]")
        self.log_to_file(f"构建产物清理完成，处理了 {cleaned_count} 个目录")

    def build_package(self, package_path: Path) -> bool:
        """构建单个包"""
        package_name = package_path.name

        if not (package_path / "pyproject.toml").exists():
            console.print(f"  ❌ {package_name}: 缺少pyproject.toml")
            self.log_to_file(f"{package_name}: 构建失败 - 缺少pyproject.toml")
            return False

        # 构建包
        self.log_to_file(f"{package_name}: 开始构建")

        try:
            result = subprocess.run(
                [sys.executable, "-m", "build", "--wheel"],
                cwd=package_path,
                capture_output=True,
                text=True,
                timeout=300,
            )

            # 记录详细输出到日志文件
            self.log_to_file(f"{package_name}: 构建命令输出:")
            self.log_to_file(result.stdout)
            if result.stderr:
                self.log_to_file(f"{package_name}: 构建错误输出:")
                self.log_to_file(result.stderr)

            if result.returncode == 0:
                console.print(f"  ✅ {package_name}: 构建完成")
                self.log_to_file(f"{package_name}: 构建成功")
                return True
            else:
                console.print(f"  ❌ {package_name}: 构建失败")
                self.log_to_file(f"{package_name}: 构建失败，退出码: {result.returncode}")
                return False

        except subprocess.TimeoutExpired:
            console.print(f"  ❌ {package_name}: 构建超时")
            self.log_to_file(f"{package_name}: 构建超时")
            return False
        except Exception as e:
            console.print(f"  ❌ {package_name}: 构建异常 - {e}")
            self.log_to_file(f"{package_name}: 构建异常 - {e}")
            return False

    def upload_package(self, package_path: Path) -> bool:
        """上传单个包"""
        package_name = package_path.name
        dist_dir = package_path / "dist"

        if not dist_dir.exists():
            console.print(f"  ❌ {package_name}: 缺少dist目录")
            self.log_to_file(f"{package_name}: 上传失败 - 缺少dist目录")
            return False

        # 检查配置文件
        pypirc_path = self.project_root / ".pypirc"
        if not pypirc_path.exists():
            pypirc_path = Path.home() / ".pypirc"

        # 构建上传命令
        cmd = ["twine", "upload"]
        if pypirc_path.exists():
            cmd.extend(["--config-file", str(pypirc_path)])

        if self.dry_run:
            cmd.extend(["--repository", "testpypi"])

        if self.verbose:
            cmd.append("--verbose")

        cmd.append("dist/*")

        self.log_to_file(f"{package_name}: 开始上传到 {'TestPyPI' if self.dry_run else 'PyPI'}")
        self.log_to_file(f"{package_name}: 使用配置文件: {pypirc_path}")
        self.log_to_file(f"{package_name}: 上传命令: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd, cwd=package_path, capture_output=True, text=True, timeout=300
            )

            # 记录详细输出到日志文件
            self.log_to_file(f"{package_name}: 上传命令输出:")
            self.log_to_file(result.stdout)
            if result.stderr:
                self.log_to_file(f"{package_name}: 上传错误输出:")
                self.log_to_file(result.stderr)

            if result.returncode == 0:
                console.print(f"  ✅ {package_name}: 上传成功")
                self.log_to_file(f"{package_name}: 上传成功")
                return True
            else:
                # 检查具体错误类型
                error_output = result.stdout + result.stderr
                error_lower = error_output.lower()

                # 如果是400错误但不是verbose模式，重试一次获取详细信息
                if "400" in error_output and not self.verbose and "warning" in error_lower:
                    self.log_to_file(f"{package_name}: 检测到400错误，重试获取详细信息...")

                    # 重新构建带verbose的命令
                    verbose_cmd = cmd[:-1] + ["--verbose"] + [cmd[-1]]
                    verbose_result = subprocess.run(
                        verbose_cmd,
                        cwd=package_path,
                        capture_output=True,
                        text=True,
                        timeout=300,
                    )

                    # 使用verbose结果进行判断
                    error_output = verbose_result.stdout + verbose_result.stderr
                    error_lower = error_output.lower()

                    self.log_to_file(f"{package_name}: verbose重试输出:")
                    self.log_to_file(error_output)

                if any(
                    phrase in error_lower for phrase in ["file already exists", "already exists"]
                ):
                    console.print(f"  ⚠️  {package_name}: 版本已存在，跳过")
                    self.log_to_file(f"{package_name}: 版本已存在，跳过")
                    return True
                elif "401" in error_output or "unauthorized" in error_lower:
                    console.print(f"  ❌ {package_name}: 认证失败")
                    console.print("     💡 请检查PyPI令牌配置")
                    self.log_to_file(f"{package_name}: 认证失败")
                    return False
                elif "403" in error_output or "forbidden" in error_lower:
                    console.print(f"  ❌ {package_name}: 无权限上传")
                    console.print("     💡 请检查包名和权限")
                    self.log_to_file(f"{package_name}: 无权限上传")
                    return False
                elif "400" in error_output or "bad request" in error_lower:
                    console.print(f"  ❌ {package_name}: 上传请求无效")
                    console.print("     💡 可能是包元数据有问题")
                    if self.dry_run:
                        console.print("     💡 TestPyPI也需要有效的认证配置")
                    self.log_to_file(f"{package_name}: 上传请求无效 (400)")
                    return False
                else:
                    console.print(f"  ❌ {package_name}: 上传失败")
                    console.print(f"     错误详情: {error_output[:100]}")
                    self.log_to_file(f"{package_name}: 上传失败，退出码: {result.returncode}")
                    return False

        except subprocess.TimeoutExpired:
            console.print(f"  ❌ {package_name}: 上传超时")
            self.log_to_file(f"{package_name}: 上传超时")
            return False
        except Exception as e:
            console.print(f"  ❌ {package_name}: 上传异常 - {e}")
            self.log_to_file(f"{package_name}: 上传异常 - {e}")
            return False

    def publish_packages(
        self, specified_packages: list[str] | None = None, skip_build: bool = False
    ) -> bool:
        """发布包"""
        packages_dir = self.project_root / "packages"

        # 确定要发布的包
        if specified_packages:
            packages_to_publish = specified_packages
        else:
            packages_to_publish = self.publish_order

        # 统计
        success_count = 0
        failed_count = 0
        skipped_count = 0

        # 创建结果表格
        table = Table(title="发布结果")
        table.add_column("包名", style="cyan")
        table.add_column("构建", style="green")
        table.add_column("上传", style="blue")
        table.add_column("状态", style="bold")

        for package_name in packages_to_publish:
            package_path = packages_dir / package_name

            if not package_path.exists():
                console.print(f"\n⚠️  {package_name}: 目录不存在，跳过")
                skipped_count += 1
                table.add_row(package_name, "N/A", "N/A", "❌ 跳过")
                continue

            console.print(f"\n📦 [bold]处理包: {package_name}[/bold]")

            build_success = True
            upload_success = True

            # 构建包
            if not skip_build:
                console.print("  🔨 构建中...")
                build_success = self.build_package(package_path)
                if not build_success:
                    failed_count += 1
                    table.add_row(package_name, "❌ 失败", "N/A", "❌ 失败")
                    continue

            # 上传包
            console.print("  ⬆️  上传中...")
            upload_success = self.upload_package(package_path)

            if upload_success:
                success_count += 1
                build_status = "✅ 成功" if not skip_build else "⏭️ 跳过"
                table.add_row(package_name, build_status, "✅ 成功", "✅ 成功")
            else:
                failed_count += 1
                build_status = "✅ 成功" if not skip_build else "⏭️ 跳过"
                table.add_row(package_name, build_status, "❌ 失败", "❌ 失败")

        # 显示结果
        console.print("\n")
        console.print(table)

        console.print("\n📊 [bold]发布摘要:[/bold]")
        console.print(f"✅ 成功: {success_count}")
        console.print(f"⚠️  跳过: {skipped_count}")
        console.print(f"❌ 失败: {failed_count}")
        console.print(f"📈 总计: {success_count + skipped_count + failed_count}")

        # 记录摘要到日志
        self.log_to_file(
            f"发布摘要: 成功={success_count}, 跳过={skipped_count}, 失败={failed_count}"
        )

        return failed_count == 0


if __name__ == "__main__":
    app()
