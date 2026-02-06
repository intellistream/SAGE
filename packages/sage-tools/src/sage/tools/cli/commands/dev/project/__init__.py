"""
项目管理命令组

提供项目状态、分析、测试、清理等功能。
"""

import typer
from rich.console import Console

app = typer.Typer(
    name="project",
    help="📊 项目管理 - 状态、分析、测试、清理",
    no_args_is_help=True,
)

console = Console()


@app.command(name="status")
def project_status(
    project_root: str = typer.Option(".", help="项目根目录"),
    verbose: bool = typer.Option(False, help="详细输出"),
    output_format: str = typer.Option("summary", help="输出格式: summary, json, full, markdown"),
    packages_only: bool = typer.Option(False, "--packages", help="只显示包状态信息"),
    check_versions: bool = typer.Option(False, "--versions", help="检查所有包的版本信息"),
    check_dependencies: bool = typer.Option(False, "--deps", help="检查包依赖状态"),
    quick: bool = typer.Option(True, "--quick/--full", help="快速模式（跳过耗时检查）"),
):
    """📊 项目状态检查 - 检查各包状态和版本"""
    from ..main import status

    return status(
        project_root=project_root,
        verbose=verbose,
        output_format=output_format,
        packages_only=packages_only,
        check_versions=check_versions,
        check_dependencies=check_dependencies,
        quick=quick,
    )


@app.command(name="analyze")
def project_analyze(
    analysis_type: str = typer.Option("all", help="分析类型: all, health, report"),
    output_format: str = typer.Option("summary", help="输出格式: summary, json, markdown"),
    project_root: str = typer.Option(".", help="项目根目录"),
):
    """🔍 依赖分析 - 分析项目依赖关系"""
    from ..main import analyze

    return analyze(
        analysis_type=analysis_type,
        output_format=output_format,
        project_root=project_root,
    )


@app.command(name="clean")
def project_clean(
    target: str = typer.Option(
        "all",
        help="清理目标: all, all-deep, cache, build, logs, empty-dirs, cmake, temp, node-modules",
    ),
    project_root: str = typer.Option(".", help="项目根目录"),
    dry_run: bool = typer.Option(False, help="预览模式，不实际删除"),
):
    """🧹 清理项目 - 清理缓存和临时文件"""
    from ..main import clean

    return clean(target=target, project_root=project_root, dry_run=dry_run)


@app.command(name="test")
def project_test(
    test_type: str = typer.Option(
        "all", "--test-type", help="测试类型: all, unit, integration, quick"
    ),
    project_root: str = typer.Option(".", "--project-root", help="项目根目录"),
    verbose: bool = typer.Option(False, "--verbose", help="详细输出"),
    packages: str = typer.Option("", "--packages", help="指定测试的包，逗号分隔"),
    jobs: int = typer.Option(4, "--jobs", "-j", help="并行任务数量"),
    timeout: int = typer.Option(300, "--timeout", "-t", help="每个包的超时时间(秒)"),
    failed_only: bool = typer.Option(False, "--failed", help="只重新运行失败的测试"),
    continue_on_error: bool = typer.Option(True, "--continue-on-error", help="遇到错误继续执行"),
    summary_only: bool = typer.Option(False, "--summary", help="只显示摘要结果"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="静默模式"),
    report_file: str = typer.Option("", "--report", help="测试报告输出文件路径"),
    diagnose: bool = typer.Option(False, "--diagnose", help="运行诊断模式"),
    coverage: bool = typer.Option(False, "--coverage", help="启用测试覆盖率分析"),
    coverage_report: str = typer.Option(
        "term,html,xml", "--coverage-report", help="覆盖率报告格式 (逗号分隔)"
    ),
    skip_quality_check: bool = typer.Option(
        True, "--quality-check/--skip-quality-check", help="运行测试前进行代码质量检查（默认跳过）"
    ),
    debug: bool = typer.Option(False, "--debug", help="启用调试模式，输出详细执行信息"),
):
    """
    🧪 运行项目测试

    运行单元测试、集成测试等。

    示例：
        sage-dev project test                     # 运行所有测试
        sage-dev project test --test-type unit    # 只运行单元测试
        sage-dev project test --packages sage-libs,sage-kernel  # 测试特定包
        sage-dev project test --failed            # 只运行失败的测试
        sage-dev project test --coverage          # 运行测试并生成覆盖率报告
    """
    from sage.tools.cli.commands.dev.main import test

    test(
        test_type=test_type,
        project_root=project_root,
        verbose=verbose,
        packages=packages,
        jobs=jobs,
        timeout=timeout,
        failed_only=failed_only,
        continue_on_error=continue_on_error,
        summary_only=summary_only,
        quiet=quiet,
        report_file=report_file,
        diagnose=diagnose,
        coverage=coverage,
        coverage_report=coverage_report,
        skip_quality_check=skip_quality_check,
        debug=debug,
    )


@app.command(name="architecture")
def show_architecture(
    show_dependencies: bool = typer.Option(
        True, "--dependencies/--no-dependencies", help="显示依赖关系"
    ),
    show_layers: bool = typer.Option(True, "--layers/--no-layers", help="显示层级定义"),
    package: str = typer.Option(None, "--package", help="显示特定包的信息"),
    output_format: str = typer.Option("text", "--format", help="输出格式: text, json, markdown"),
):
    """
    🏗️ 显示架构信息

    显示 SAGE 的分层架构定义和包依赖关系。

    示例:
        sage-dev project architecture               # 文本格式
        sage-dev project architecture -f json       # JSON 格式
        sage-dev project architecture -f markdown   # Markdown 格式
    """
    from sage.tools.cli.commands.dev.main import architecture

    architecture(
        show_dependencies=show_dependencies,
        show_layers=show_layers,
        package=package,
        output_format=output_format,
    )


@app.command(name="home")
def project_home(
    action: str = typer.Argument("status", help="操作: init, clean, status"),
    path: str = typer.Option("", help="SAGE目录路径"),
):
    """🏠 SAGE目录管理 - 管理SAGE工作目录"""
    from ..main import home

    return home(action=action, path=path)


__all__ = ["app"]
