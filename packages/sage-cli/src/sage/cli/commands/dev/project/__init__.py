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
    package: str = typer.Option(
        None,
        "--package",
        "-p",
        help="指定包名",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="详细输出",
    ),
    markdown: bool = typer.Option(
        False,
        "--markdown",
        help="Markdown 格式输出",
    ),
):
    """
    📊 查看项目状态

    显示包版本、依赖、测试状态等信息。

    示例：
        sage dev project status                # 查看所有包状态
        sage dev project status -p sage-libs   # 查看特定包
        sage dev project status --markdown     # Markdown 格式
    """
    from sage.cli.commands.dev.main import status

    status(
        package=package,
        verbose=verbose,
        markdown=markdown,
    )


@app.command(name="analyze")
def project_analyze(
    analysis_type: str = typer.Option(
        "all",
        "--type",
        "-t",
        help="分析类型: dependencies, complexity, quality, all",
    ),
    package: str = typer.Option(
        None,
        "--package",
        "-p",
        help="指定包名",
    ),
    output: str = typer.Option(
        None,
        "--output",
        "-o",
        help="输出文件路径",
    ),
    format: str = typer.Option(
        "text",
        "--format",
        "-f",
        help="输出格式: text, json, markdown",
    ),
):
    """
    🔍 代码分析

    分析代码依赖、复杂度、质量等。

    示例：
        sage dev project analyze                          # 分析所有内容
        sage dev project analyze -t dependencies          # 只分析依赖
        sage dev project analyze -p sage-libs             # 分析特定包
        sage dev project analyze -f json -o report.json   # JSON 输出
    """
    from sage.cli.commands.dev.main import analyze

    analyze(
        analysis_type=analysis_type,
        package=package,
        output=output,
        format=format,
    )


@app.command(name="clean")
def project_clean(
    deep: bool = typer.Option(
        False,
        "--deep",
        help="深度清理（包括缓存）",
    ),
    build: bool = typer.Option(
        True,
        "--build/--no-build",
        help="清理构建产物",
    ),
    cache: bool = typer.Option(
        True,
        "--cache/--no-cache",
        help="清理缓存",
    ),
    logs: bool = typer.Option(
        True,
        "--logs/--no-logs",
        help="清理日志",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="只显示将要删除的内容",
    ),
):
    """
    🧹 清理构建产物和缓存

    清理 __pycache__, .pytest_cache, build/ 等。

    示例：
        sage dev project clean              # 标准清理
        sage dev project clean --deep       # 深度清理
        sage dev project clean --dry-run    # 预览清理内容
    """
    from sage.cli.commands.dev.main import clean

    clean(
        deep=deep,
        build=build,
        cache=cache,
        logs=logs,
        dry_run=dry_run,
    )


@app.command(name="test")
def project_test(
    test_type: str = typer.Option(
        "all",
        "--test-type",
        help="测试类型: all, unit, integration, quick",
    ),
    project_root: str = typer.Option(
        ".",
        "--project-root",
        help="项目根目录",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        help="详细输出",
    ),
    packages: str = typer.Option(
        None,
        "--packages",
        help="指定测试的包，逗号分隔",
    ),
    jobs: int = typer.Option(
        4,
        "--jobs",
        "-j",
        help="并行任务数量",
    ),
    timeout: int = typer.Option(
        300,
        "--timeout",
        "-t",
        help="每个包的超时时间(秒)",
    ),
    failed: bool = typer.Option(
        False,
        "--failed",
        help="只重新运行失败的测试",
    ),
    continue_on_error: bool = typer.Option(
        True,
        "--continue-on-error",
        help="遇到错误继续执行",
    ),
    summary: bool = typer.Option(
        False,
        "--summary",
        help="只显示摘要结果",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help="静默模式",
    ),
    report: str = typer.Option(
        None,
        "--report",
        help="测试报告输出文件路径",
    ),
):
    """
    🧪 运行项目测试

    运行单元测试、集成测试等。

    示例：
        sage dev project test                     # 运行所有测试
        sage dev project test --test-type unit    # 只运行单元测试
        sage dev project test --packages sage-libs,sage-kernel  # 测试特定包
        sage dev project test --failed            # 只运行失败的测试
    """
    from sage.cli.commands.dev.main import test

    test(
        test_type=test_type,
        project_root=project_root,
        verbose=verbose,
        packages=packages,
        jobs=jobs,
        timeout=timeout,
        failed=failed,
        continue_on_error=continue_on_error,
        summary=summary,
        quiet=quiet,
        report=report,
        diagnose=False,
        issues_manager=False,
        skip_quality_check=True,
        quality_fix=False,
        quality_format=False,
        quality_imports=False,
        quality_lint=False,
    )


@app.command(name="architecture")
def show_architecture(
    format: str = typer.Option(
        "text",
        "--format",
        "-f",
        help="输出格式: text, json, markdown",
    ),
):
    """
    🏗️ 显示架构信息

    显示 SAGE 的分层架构定义和包依赖关系。

    示例:
        sage dev project architecture               # 文本格式
        sage dev project architecture -f json       # JSON 格式
        sage dev project architecture -f markdown   # Markdown 格式
    """
    from sage.cli.commands.dev.main import architecture

    architecture(format=format)


@app.command(name="home")
def project_home(
    open_browser: bool = typer.Option(
        True,
        "--open/--no-open",
        help="在浏览器中打开",
    ),
):
    """
    🏠 项目主页

    显示项目主页和相关链接。

    示例：
        sage dev project home              # 显示主页
        sage dev project home --no-open    # 不打开浏览器
    """
    from sage.cli.commands.dev.main import home

    home(open_browser=open_browser)


__all__ = ["app"]
