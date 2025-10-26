"""
SAGE Dev 命令组 - 简化版本

这个模块提供统一的dev命令接口，调用sage.tools.dev中的核心功能。
"""

from pathlib import Path

import typer
from rich.console import Console

from sage.tools.utils.diagnostics import (
    collect_packages_status,
    print_packages_status,
    print_packages_status_summary,
    run_installation_diagnostics,
)

console = Console()
app = typer.Typer(help="SAGE 开发工具集")

# 添加Issues管理子命令
try:
    from sage.tools.dev.issues.cli import app as issues_app

    app.add_typer(issues_app, name="issues", help="🐛 Issues管理 - GitHub Issues下载、分析和管理")
except ImportError as e:
    console.print(f"[yellow]警告: Issues管理功能不可用: {e}[/yellow]")

# 添加PyPI管理子命令
try:
    from sage.tools.cli.commands.pypi import app as pypi_app

    app.add_typer(pypi_app, name="pypi", help="📦 PyPI发布管理 - 发布准备验证、构建和管理")
except ImportError as e:
    console.print(f"[yellow]警告: PyPI发布管理功能不可用: {e}[/yellow]")

# 删除：CI 子命令（已由 GitHub Workflows 承担 CI/CD）
# 过去这里会 add_typer(ci_app, name="ci", ...)
# 现在不再提供本地 CI 包装命令，建议直接依赖 GitHub Actions。

# 添加版本管理子命令
try:
    from .version import app as version_app

    app.add_typer(version_app, name="version", help="🏷️ 版本管理 - 管理各个子包的版本信息")
except ImportError as e:
    console.print(f"[yellow]警告: 版本管理功能不可用: {e}[/yellow]")

# 添加模型缓存管理子命令
try:
    from .models import app as models_app

    app.add_typer(
        models_app,
        name="models",
        help="🤖 Embedding 模型缓存管理",
    )
except ImportError as e:
    console.print(f"[yellow]警告: 模型缓存功能不可用: {e}[/yellow]")


@app.command()
def quality(
    fix: bool = typer.Option(True, "--fix/--no-fix", help="自动修复质量问题"),
    check_only: bool = typer.Option(False, "--check-only", help="仅检查，不修复"),
    all_files: bool = typer.Option(False, "--all-files", help="检查所有文件（而不仅是变更的文件）"),
    # 选择性运行特定检查
    hook: str = typer.Option(None, "--hook", help="只运行指定的 pre-commit hook"),
    # 其他选项
    warn_only: bool = typer.Option(False, "--warn-only", help="只给警告，不中断运行"),
    project_root: str = typer.Option(".", help="项目根目录"),
    # 保留向后兼容的选项（但现在都通过 pre-commit 实现）
    format_code: bool = typer.Option(True, "--format/--no-format", help="运行代码格式化"),
    sort_imports: bool = typer.Option(
        True, "--sort-imports/--no-sort-imports", help="运行导入排序"
    ),
    lint_ruff: bool = typer.Option(True, "--ruff/--no-ruff", help="运行Ruff检查"),
    type_check: bool = typer.Option(True, "--type-check/--no-type-check", help="运行类型检查"),
):
    """代码质量检查和修复（基于 pre-commit）

    这是 pre-commit 的友好包装器，提供统一的质量检查接口。
    所有配置都在 tools/pre-commit-config.yaml 中管理，确保一致性。

    示例：
        sage dev quality                    # 运行所有检查（自动修复）
        sage dev quality --check-only       # 只检查不修复
        sage dev quality --all-files        # 检查所有文件
        sage dev quality --hook black       # 只运行 black
        sage dev quality --no-format        # 跳过格式化
    """
    import subprocess
    from pathlib import Path


    # 使用不同的变量名避免类型冲突
    project_dir = Path(project_root).resolve()

    if not project_dir.exists():
        console.print(f"[red]❌ 项目根目录不存在: {project_dir}[/red]")
        raise typer.Exit(1)

    console.print(f"📁 项目根目录: {project_dir}")

    # 配置文件路径
    tools_dir = project_dir / "tools"
    precommit_config = tools_dir / "pre-commit-config.yaml"

    if not precommit_config.exists():
        console.print(f"[red]❌ pre-commit 配置文件不存在: {precommit_config}[/red]")
        raise typer.Exit(1)

    # 检查 pre-commit 是否安装
    try:
        subprocess.run(
            ["pre-commit", "--version"],
            capture_output=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        console.print("[red]❌ pre-commit 未安装[/red]")
        console.print("[yellow]💡 请安装: pip install pre-commit[/yellow]")
        raise typer.Exit(1)

    console.print("\n🔍 运行代码质量检查（基于 pre-commit）...")
    console.print(f"📝 配置文件: {precommit_config}")

    # 构建 pre-commit 命令
    cmd = ["pre-commit", "run"]

    # 添加配置文件路径
    cmd.extend(["--config", str(precommit_config)])

    # 如果指定了特定 hook
    if hook:
        cmd.append(hook)
        console.print(f"🎯 只运行 hook: {hook}")
    else:
        # 根据选项跳过某些 hooks
        skip_hooks = []
        if not format_code:
            skip_hooks.append("black")
        if not sort_imports:
            skip_hooks.append("isort")
        if not lint_ruff:
            skip_hooks.append("ruff")
        if not type_check:
            skip_hooks.append("mypy")

        if skip_hooks:
            console.print(f"⏭️  跳过: {', '.join(skip_hooks)}")
            # pre-commit 没有直接的 --skip 选项，我们需要设置环境变量
            import os

            os.environ["SKIP"] = ",".join(skip_hooks)

    # 检查所有文件还是只检查变更的
    if all_files:
        cmd.append("--all-files")
        console.print("📂 检查所有文件")
    else:
        console.print("📝 检查已暂存的文件（git staged）")

    # 显示更多输出
    cmd.append("--verbose")

    # 运行 pre-commit
    console.print(f"\n🚀 执行命令: {' '.join(cmd)}\n")

    try:
        result = subprocess.run(
            cmd,
            cwd=str(project_dir),
            check=False,  # 不自动抛出异常，我们自己处理返回码
        )

        # pre-commit 返回码：
        # 0 = 所有检查通过
        # 1 = 有检查失败或文件被修改
        if result.returncode == 0:
            console.print("\n[green]✅ 所有质量检查通过！[/green]")
            return
        elif warn_only:
            console.print("\n[yellow]⚠️ 发现质量问题，但继续执行（warn-only 模式）[/yellow]")
            return
        else:
            console.print("\n[red]❌ 质量检查失败[/red]")
            if not all_files:
                console.print(
                    "[yellow]💡 提示: 使用 --all-files 检查所有文件，或修复上述问题后重新运行[/yellow]"
                )
            raise typer.Exit(1)

    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️ 用户中断[/yellow]")
        raise typer.Exit(130)
    except Exception as e:
        console.print(f"\n[red]❌ 运行失败: {e}[/red]")
        raise typer.Exit(1)


# ============================================================================
# 下面保留旧的辅助函数供其他命令使用
# ============================================================================


def _save_quality_error_log(logs_dir: Path, tool_name: str, content: str):
    """保存质量检查错误日志"""
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = logs_dir / f"{tool_name}_errors.log"
    log_file.write_text(content, encoding="utf-8")


# ============================================================================
# 以下是旧版本的实现，保留供参考或特殊场景使用
# 如果完全迁移到 pre-commit 后可以删除
# ============================================================================
@app.command()
def analyze(
    analysis_type: str = typer.Option("all", help="分析类型: all, health, report"),
    output_format: str = typer.Option("summary", help="输出格式: summary, json, markdown"),
    project_root: str = typer.Option(".", help="项目根目录"),
):
    """分析项目依赖和结构"""
    try:
        from sage.tools.dev.tools.dependency_analyzer import DependencyAnalyzer

        analyzer = DependencyAnalyzer(project_root)

        if analysis_type == "all":
            result = analyzer.analyze_all_dependencies()
        elif analysis_type == "health":
            result = analyzer.check_dependency_health()
        elif analysis_type == "report":
            result = analyzer.generate_dependency_report(output_format="dict")
        else:
            console.print(f"[red]不支持的分析类型: {analysis_type}[/red]")
            console.print("支持的类型: all, health, report")
            raise typer.Exit(1)

        # 输出结果
        if output_format == "json":
            import json

            # 处理可能的set对象
            def serialize_sets(obj):
                if isinstance(obj, set):
                    return list(obj)
                elif isinstance(obj, dict):
                    return {k: serialize_sets(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [serialize_sets(item) for item in obj]
                return obj

            serializable_result = serialize_sets(result)
            console.print(json.dumps(serializable_result, indent=2, ensure_ascii=False))
        elif output_format == "markdown":
            # Markdown格式输出
            markdown_output = _generate_markdown_output(result, analysis_type)
            console.print(markdown_output)
        else:
            # 简要输出
            if isinstance(result, dict):
                console.print("📊 分析结果:")
                if "summary" in result:
                    summary = result["summary"]
                    console.print(f"  📦 总包数: {summary.get('total_packages', 0)}")
                    console.print(f"  📚 总依赖: {summary.get('total_dependencies', 0)}")
                    if "dependency_conflicts" in summary:
                        conflicts = summary["dependency_conflicts"]
                        console.print(
                            f"  ⚠️ 冲突: {len(conflicts) if isinstance(conflicts, list) else 0}"
                        )
                elif "health_score" in result:
                    console.print(f"  💯 健康评分: {result.get('health_score', 'N/A')}")
                    console.print(f"  📊 等级: {result.get('grade', 'N/A')}")
                else:
                    console.print("  📋 分析完成")
            console.print("[green]✅ 分析完成[/green]")

    except Exception as e:
        console.print(f"[red]分析失败: {e}[/red]")
        import traceback

        console.print(f"[red]详细错误:\n{traceback.format_exc()}[/red]")
        raise typer.Exit(1)


@app.command()
def clean(
    target: str = typer.Option("all", help="清理目标: all, cache, build, logs"),
    project_root: str = typer.Option(".", help="项目根目录"),
    dry_run: bool = typer.Option(False, help="预览模式，不实际删除"),
):
    """清理项目文件"""
    try:
        import shutil
        from pathlib import Path

        project_path = Path(project_root).resolve()

        if dry_run:
            console.print("[yellow]预览模式 - 不会实际删除文件[/yellow]")

        cleaned_items = []

        # 定义要清理的目录和文件模式
        clean_targets = {
            "cache": [
                "__pycache__",
                "*.pyc",
                "*.pyo",
                ".pytest_cache",
                ".coverage",
                "htmlcov",
            ],
            "build": ["build", "dist", "*.egg-info", ".eggs"],
            "logs": ["*.log", "logs/*.log"],
        }

        targets_to_clean = []
        if target == "all":
            for t in clean_targets.values():
                targets_to_clean.extend(t)
        elif target in clean_targets:
            targets_to_clean = clean_targets[target]
        else:
            console.print(f"[red]不支持的清理目标: {target}[/red]")
            console.print("支持的目标: all, cache, build, logs")
            raise typer.Exit(1)

        # 执行清理（统一处理：匹配到的路径若为目录则递归删除，若为文件则删除文件）
        for pattern in targets_to_clean:
            for path in project_path.rglob(pattern):
                rel = str(path.relative_to(project_path))
                try:
                    if path.is_dir():
                        cleaned_items.append(rel + "/")
                        if not dry_run:
                            shutil.rmtree(path)
                    elif path.is_file():
                        cleaned_items.append(rel)
                        if not dry_run:
                            path.unlink()
                except Exception as e:
                    console.print(f"[yellow]⚠️ 无法删除 {rel}: {e}[/yellow]")

        # 报告结果
        if cleaned_items:
            console.print(
                f"[green]{'预览' if dry_run else '已清理'} {len(cleaned_items)} 个项目:[/green]"
            )
            for item in cleaned_items[:10]:  # 限制显示数量
                console.print(f"  📁 {item}")
            if len(cleaned_items) > 10:
                console.print(f"  ... 还有 {len(cleaned_items) - 10} 个项目")
        else:
            console.print("[blue]没有找到需要清理的项目[/blue]")

        console.print("[green]✅ 清理完成[/green]")

    except Exception as e:
        console.print(f"[red]清理失败: {e}[/red]")
        import traceback

        console.print(f"[red]详细错误:\n{traceback.format_exc()}[/red]")
        raise typer.Exit(1)


@app.command()
def status(
    project_root: str = typer.Option(".", help="项目根目录"),
    verbose: bool = typer.Option(False, help="详细输出"),
    output_format: str = typer.Option("summary", help="输出格式: summary, json, full, markdown"),
    packages_only: bool = typer.Option(False, "--packages", help="只显示包状态信息"),
    check_versions: bool = typer.Option(False, "--versions", help="检查所有包的版本信息"),
    check_dependencies: bool = typer.Option(False, "--deps", help="检查包依赖状态"),
    quick: bool = typer.Option(True, "--quick/--full", help="快速模式（跳过耗时检查）"),
):
    """显示项目状态 - 集成包状态检查功能"""
    try:
        # 延迟导入以减少启动时间
        from pathlib import Path

        from sage.tools.dev.tools.project_status_checker import ProjectStatusChecker

        # 自动检测项目根目录
        project_path = Path(project_root).resolve()
        if not (project_path / "packages").exists():
            current = project_path
            while current.parent != current:
                if (current / "packages").exists():
                    project_path = current
                    break
                current = current.parent

        checker = ProjectStatusChecker(str(project_path))

        # 如果只检查包状态
        if packages_only:
            print_packages_status(
                project_path,
                console=console,
                verbose=verbose,
                check_versions=check_versions,
                check_dependencies=check_dependencies,
            )
            return

        if output_format == "json":
            # JSON格式输出
            import json

            status_data = checker.check_all(verbose=False, quick=quick)
            # 添加包状态信息
            status_data["packages_status"] = collect_packages_status(project_path)
            console.print(json.dumps(status_data, indent=2, ensure_ascii=False))
        elif output_format == "full":
            # 完整详细输出
            status_data = checker.check_all(verbose=True, quick=False)  # 完整输出不使用快速模式
            console.print("\n" + "=" * 60)
            console.print(checker.generate_status_summary(status_data))
            console.print("=" * 60)
            # 添加包状态信息
            console.print("\n📦 包状态详情:")
            print_packages_status(
                project_path,
                console=console,
                verbose=True,
                check_versions=check_versions,
                check_dependencies=check_dependencies,
            )
        elif output_format == "markdown":
            # Markdown格式输出
            status_data = checker.check_all(verbose=verbose, quick=quick)
            markdown_output = _generate_status_markdown_output(status_data)
            console.print(markdown_output)
        else:
            # 简要摘要输出 (默认) - 使用快速模式
            console.print("🔍 检查项目状态...")
            status_data = checker.check_all(verbose=False, quick=quick)

            # 显示摘要
            summary = checker.generate_status_summary(status_data)
            console.print(f"\n{summary}")

            # 显示包状态摘要
            print_packages_status_summary(project_path, console=console)

            # 显示关键信息和警告
            issues = []

            # 检查环境问题
            env_data = status_data["checks"].get("environment", {}).get("data", {})
            if env_data.get("sage_home") == "Not set":
                issues.append("⚠️  SAGE_HOME 环境变量未设置")

            # 检查包安装问题
            pkg_data = status_data["checks"].get("packages", {}).get("data", {})
            if pkg_data.get("summary", {}).get("installed", 0) == 0:
                issues.append("⚠️  SAGE 包尚未安装，请运行 ./quickstart.sh")

            # 检查依赖问题
            deps_data = status_data["checks"].get("dependencies", {}).get("data", {})
            failed_imports = [
                name
                for name, test in deps_data.get("import_tests", {}).items()
                if test != "success"
            ]
            if failed_imports:
                issues.append(f"⚠️  缺少依赖: {', '.join(failed_imports)}")

            # 检查服务问题
            svc_data = status_data["checks"].get("services", {}).get("data", {})
            if not svc_data.get("ray", {}).get("running", False):
                issues.append("ℹ️  Ray 集群未运行 (可选)")

            # 检查失败的项目
            failed_checks = [
                name
                for name, check in status_data["checks"].items()
                if check["status"] != "success"
            ]

            if issues:
                console.print("\n📋 需要注意的问题:")
                for issue in issues[:5]:  # 限制显示数量
                    console.print(f"  {issue}")

            if failed_checks:
                console.print(f"\n❌ 失败的检查项目: {', '.join(failed_checks)}")
                console.print("💡 使用 --output-format full 查看详细信息")
            elif not issues:
                console.print("\n[green]✅ 所有检查项目都通过了![/green]")
            else:
                console.print("\n💡 使用 --output-format full 查看详细信息")

    except Exception as e:
        console.print(f"[red]状态检查失败: {e}[/red]")
        if verbose:
            import traceback

            console.print(f"[red]详细错误信息:\n{traceback.format_exc()}[/red]")
        raise typer.Exit(1)


@app.command()
def test(
    test_type: str = typer.Option("all", help="测试类型: all, unit, integration, quick"),
    project_root: str = typer.Option(".", help="项目根目录"),
    verbose: bool = typer.Option(False, help="详细输出"),
    packages: str = typer.Option("", help="指定测试的包，逗号分隔 (例: sage-libs,sage-kernel)"),
    jobs: int = typer.Option(4, "--jobs", "-j", help="并行任务数量"),
    timeout: int = typer.Option(300, "--timeout", "-t", help="每个包的超时时间(秒)"),
    failed_only: bool = typer.Option(False, "--failed", help="只重新运行失败的测试"),
    continue_on_error: bool = typer.Option(
        True, "--continue-on-error", help="遇到错误继续执行其他包"
    ),
    summary_only: bool = typer.Option(False, "--summary", help="只显示摘要结果"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="静默模式"),
    report_file: str = typer.Option("", "--report", help="测试报告输出文件路径"),
    diagnose: bool = typer.Option(False, "--diagnose", help="运行诊断模式"),
    issues_manager: bool = typer.Option(False, "--issues-manager", help="包含 issues manager 测试"),
    # 质量检查选项
    skip_quality_check: bool = typer.Option(
        False, "--skip-quality-check", help="跳过代码质量检查和修复"
    ),
    quality_fix: bool = typer.Option(
        True, "--quality-fix/--no-quality-fix", help="自动修复代码质量问题"
    ),
    quality_format: bool = typer.Option(
        True, "--quality-format/--no-quality-format", help="运行代码格式化检查"
    ),
    quality_imports: bool = typer.Option(
        True, "--quality-imports/--no-quality-imports", help="运行导入排序检查"
    ),
    quality_lint: bool = typer.Option(
        True, "--quality-lint/--no-quality-lint", help="运行代码质量检查"
    ),
):
    """运行项目测试 - 集成从 tools/ 脚本迁移的高级功能"""
    try:
        import time
        from pathlib import Path

        from rich.rule import Rule

        from sage.tools.dev.tools.enhanced_test_runner import EnhancedTestRunner

        # 0. 测试目录获取
        if not quiet:
            console.print(Rule("[bold cyan]🔍 正在寻找项目根目录...[/bold cyan]"))

        # 自动检测项目根目录
        project_path = Path(project_root).resolve()

        # 设置一个标志，表示是否已找到根目录
        found_root = (project_path / "packages").exists()

        # 如果在初始路径没找到，则向上遍历查找
        if not found_root:
            current = project_path
            # 循环向上查找，直到文件系统的根目录
            while current.parent != current:
                current = current.parent
                if (current / "packages").exists():
                    project_path = current
                    found_root = True
                    break  # 找到后立即退出循环

        # 如果最终还是没有找到根目录，则报错退出
        if not found_root:
            console.print("[red]❌ 无法找到 SAGE 项目根目录[/red]")
            console.print(f"起始搜索目录: {Path(project_root).resolve()}")
            console.print("请确保在 SAGE 项目目录中运行，或使用 --project-root 指定正确的路径")
            raise typer.Exit(1)

        if not quiet:
            console.print(f"📁 项目根目录: {project_path}")

        # 1. 代码质量检查和修复 (在测试前运行)
        if not skip_quality_check:
            if not quiet:
                console.print(Rule("[bold cyan]🔍 执行测试前代码质量检查...[/bold cyan]"))

            # 调用质量检查函数，使用warn_only模式，不中断测试
            has_quality_issues = _run_quality_check(
                project_path=str(project_path),
                fix=quality_fix,
                check_only=not quality_fix,
                format_code=quality_format,
                sort_imports=quality_imports,
                lint_code=quality_lint,
                quiet=quiet,
                warn_only=True,  # 在测试模式下只警告，不中断
            )

            if has_quality_issues and not quiet:
                console.print("[yellow]⚠️ 发现代码质量问题，但继续运行测试[/yellow]")
            elif not quiet:
                console.print("[green]🎉 所有代码质量检查通过，继续运行测试[/green]")
        elif not quiet:
            console.print("[yellow]⚠️ 跳过代码质量检查[/yellow]")

        # 诊断模式
        if diagnose:
            console.print(Rule("[bold cyan]🔍 运行诊断模式...[/bold cyan]"))
            run_installation_diagnostics(project_path, console=console)
            return

        # Issues Manager 测试
        if issues_manager:
            console.print(Rule("[bold cyan]🔍 运行 Issues Manager 测试...[/bold cyan]"))
            _run_issues_manager_test(str(project_path), verbose)
            return

        runner = EnhancedTestRunner(str(project_path))

        # 解析包列表
        target_packages = []
        if packages:
            target_packages = [pkg.strip() for pkg in packages.split(",")]
            console.print(f"🎯 指定测试包: {target_packages}")

        # 配置测试参数
        test_config = {
            "verbose": verbose and not quiet,
            "workers": jobs,
            "timeout": timeout,
            "continue_on_error": continue_on_error,
            "target_packages": target_packages,
            "failed_only": failed_only,
        }

        if not quiet:
            console.print(Rule(f"[bold cyan]🧪 运行 {test_type} 测试...[/bold cyan]"))
            console.print(
                f"测试配置: {jobs} 线程测试,     {timeout}s 超时退出,     {'遇到错误继续执行模式' if continue_on_error else '遇错停止模式'}"
            )

        start_time = time.time()

        # 执行测试
        if test_type == "quick":
            result = _run_quick_tests(runner, test_config, quiet)
        elif test_type == "all":
            result = _run_all_tests(runner, test_config, quiet)
        elif test_type == "unit":
            result = _run_unit_tests(runner, test_config, quiet)
        elif test_type == "integration":
            result = _run_integration_tests(runner, test_config, quiet)
        else:
            console.print(f"[red]不支持的测试类型: {test_type}[/red]")
            console.print("支持的类型: all, unit, integration, quick")
            raise typer.Exit(1)

        execution_time = time.time() - start_time

        # 生成报告
        if report_file:
            _generate_test_report(result, report_file, test_type, execution_time, test_config)

        # 显示结果
        _display_test_results(result, summary_only, quiet, execution_time)

        # 检查结果并退出
        if result and result.get("status") == "success":
            if not quiet:
                console.print("[green]✅ 所有测试通过[/green]")
        else:
            if not quiet:
                console.print("[red]❌ 测试失败[/red]")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]测试运行失败: {e}[/red]")
        if verbose:
            import traceback

            console.print(f"[red]详细错误:\n{traceback.format_exc()}[/red]")
        raise typer.Exit(1)


@app.command()
def home(
    action: str = typer.Argument(..., help="操作: init, clean, status"),
    path: str = typer.Option("", help="SAGE目录路径"),
):
    """管理SAGE目录"""
    try:
        from sage.common.config.output_paths import (
            get_sage_paths,
            initialize_sage_paths,
        )

        # 使用统一的路径系统
        if path:
            sage_paths = get_sage_paths(path)
        else:
            sage_paths = get_sage_paths()

        if action == "init":
            # 初始化SAGE路径和环境
            initialize_sage_paths(path if path else None)
            console.print("[green]✅ SAGE目录初始化完成[/green]")
            console.print(f"  📁 SAGE目录: {sage_paths.sage_dir}")
            console.print(f"  📊 项目根目录: {sage_paths.project_root}")
            console.print(
                f"  🌍 环境类型: {'pip安装' if sage_paths.is_pip_environment else '开发环境'}"
            )

        elif action == "clean":
            # 清理旧日志文件
            import time

            logs_dir = sage_paths.logs_dir
            if not logs_dir.exists():
                console.print("[yellow]⚠️ 日志目录不存在[/yellow]")
                return

            current_time = time.time()
            cutoff_time = current_time - (7 * 24 * 60 * 60)  # 7天前

            files_removed = 0
            for log_file in logs_dir.glob("*.log"):
                if log_file.stat().st_mtime < cutoff_time:
                    log_file.unlink()
                    files_removed += 1

            console.print(f"[green]✅ 清理完成: 删除了 {files_removed} 个旧日志文件[/green]")

        elif action == "status":
            console.print("🏠 SAGE目录状态:")
            console.print(f"  📁 SAGE目录: {sage_paths.sage_dir}")
            console.print(f"  ✅ 存在: {'是' if sage_paths.sage_dir.exists() else '否'}")
            console.print(f"  📊 项目根目录: {sage_paths.project_root}")
            console.print(
                f"  🌍 环境类型: {'pip安装' if sage_paths.is_pip_environment else '开发环境'}"
            )

            # 显示各个子目录状态
            subdirs: list[tuple[str, Path]] = [
                ("logs", sage_paths.logs_dir),
                ("output", sage_paths.output_dir),
                ("temp", sage_paths.temp_dir),
                ("cache", sage_paths.cache_dir),
                ("reports", sage_paths.reports_dir),
            ]

            for name, dir_path in subdirs:
                status = "存在" if dir_path.exists() else "不存在"
                if dir_path.exists():
                    size = sum(f.stat().st_size for f in dir_path.rglob("*") if f.is_file())
                    file_count = len(list(dir_path.rglob("*")))
                    console.print(f"  � {name}: {status} ({file_count} 个文件, {size} 字节)")
                else:
                    console.print(f"  � {name}: {status}")

        else:
            console.print(f"[red]不支持的操作: {action}[/red]")
            console.print("支持的操作: init, clean, status")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]SAGE目录操作失败: {e}[/red]")
        import traceback

        console.print(f"[red]详细错误:\n{traceback.format_exc()}[/red]")
        raise typer.Exit(1)


def _generate_status_markdown_output(status_data):
    """生成Markdown格式的状态输出"""
    import datetime

    markdown_lines = []

    # 添加标题和时间戳
    markdown_lines.append("# SAGE 项目状态报告")
    markdown_lines.append("")
    markdown_lines.append(f"**生成时间**: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    markdown_lines.append("")

    if isinstance(status_data, dict):
        # 添加总体状态
        overall_status = status_data.get("overall_status", "unknown")
        status_emoji = {
            "success": "✅",
            "warning": "⚠️",
            "error": "❌",
            "unknown": "❓",
        }.get(overall_status, "❓")

        markdown_lines.append("## 📊 总体状态")
        markdown_lines.append("")
        markdown_lines.append(f"**状态**: {status_emoji} {overall_status.upper()}")
        markdown_lines.append("")

        # 处理检查结果
        if "checks" in status_data:
            checks = status_data["checks"]
            markdown_lines.append("## 🔍 详细检查结果")
            markdown_lines.append("")

            # 创建状态表格
            markdown_lines.append("| 检查项目 | 状态 | 说明 |")
            markdown_lines.append("|----------|------|------|")

            for check_name, check_data in checks.items():
                if isinstance(check_data, dict):
                    status = check_data.get("status", "unknown")
                    status_emoji = {
                        "success": "✅",
                        "warning": "⚠️",
                        "error": "❌",
                        "unknown": "❓",
                    }.get(status, "❓")

                    message = check_data.get("message", "")
                    # 清理消息中的markdown特殊字符
                    if isinstance(message, str):
                        message = message.replace("|", "\\|").replace("\n", " ")
                    else:
                        message = str(message)

                    markdown_lines.append(
                        f"| {check_name.replace('_', ' ').title()} | {status_emoji} {status} | {message} |"
                    )

            markdown_lines.append("")

            # 详细信息部分
            for check_name, check_data in checks.items():
                if isinstance(check_data, dict) and "data" in check_data:
                    data = check_data["data"]
                    if data:  # 只显示有数据的检查项目
                        markdown_lines.append(f"### {check_name.replace('_', ' ').title()}")
                        markdown_lines.append("")

                        if check_name == "environment":
                            if isinstance(data, dict):
                                markdown_lines.append("**环境变量**:")
                                for key, value in data.items():
                                    # Safely convert value to string
                                    value_str = str(value) if value is not None else "None"
                                    markdown_lines.append(f"- **{key}**: {value_str}")

                        elif check_name == "packages":
                            if isinstance(data, dict):
                                summary = data.get("summary", {})
                                if summary:
                                    markdown_lines.append("**包安装摘要**:")
                                    markdown_lines.append(
                                        f"- 已安装: {summary.get('installed', 0)}"
                                    )
                                    markdown_lines.append(f"- 总计: {summary.get('total', 0)}")

                                packages = data.get("packages", [])
                                if packages and isinstance(packages, (list, dict)):
                                    markdown_lines.append("")
                                    markdown_lines.append("**已安装的包**:")
                                    if isinstance(packages, list):
                                        # Safely slice the list
                                        display_packages = (
                                            packages[:10] if len(packages) > 10 else packages
                                        )
                                        for pkg in display_packages:
                                            markdown_lines.append(f"- {str(pkg)}")
                                        if len(packages) > 10:
                                            markdown_lines.append(
                                                f"- ... 还有 {len(packages) - 10} 个包"
                                            )
                                    elif isinstance(packages, dict):
                                        count = 0
                                        for pkg_name, pkg_info in packages.items():
                                            if count >= 10:
                                                break
                                            markdown_lines.append(f"- {pkg_name}: {str(pkg_info)}")
                                            count += 1
                                        if len(packages) > 10:
                                            markdown_lines.append(
                                                f"- ... 还有 {len(packages) - 10} 个包"
                                            )

                        elif check_name == "dependencies":
                            if isinstance(data, dict):
                                import_tests = data.get("import_tests", {})
                                if import_tests:
                                    markdown_lines.append("**导入测试结果**:")
                                    for dep, result in import_tests.items():
                                        status_icon = "✅" if result == "success" else "❌"
                                        markdown_lines.append(f"- {status_icon} {dep}: {result}")

                        elif check_name == "services":
                            if isinstance(data, dict):
                                markdown_lines.append("**服务状态**:")
                                for service, info in data.items():
                                    if isinstance(info, dict):
                                        running = info.get("running", False)
                                        status_icon = "✅" if running else "❌"
                                        markdown_lines.append(
                                            f"- {status_icon} {service}: {'运行中' if running else '未运行'}"
                                        )
                                        if "details" in info and info["details"]:
                                            markdown_lines.append(f"  - 详情: {info['details']}")

                        else:
                            # 通用数据显示
                            try:
                                if isinstance(data, dict):
                                    for key, value in data.items():
                                        value_str = str(value) if value is not None else "None"
                                        markdown_lines.append(f"- **{key}**: {value_str}")
                                elif isinstance(data, list):
                                    # Safely handle list slicing
                                    display_items = data[:5] if len(data) > 5 else data
                                    for item in display_items:
                                        markdown_lines.append(f"- {str(item)}")
                                    if len(data) > 5:
                                        markdown_lines.append(f"- ... 还有 {len(data) - 5} 项")
                                else:
                                    markdown_lines.append(f"数据: {str(data)}")
                            except Exception as e:
                                markdown_lines.append(f"数据显示错误: {str(e)}")

                        markdown_lines.append("")

        # 添加摘要信息
        if "summary" in status_data:
            summary = status_data["summary"]
            markdown_lines.append("## 📋 状态摘要")
            markdown_lines.append("")
            markdown_lines.append("```")
            markdown_lines.append(summary)
            markdown_lines.append("```")
            markdown_lines.append("")
    else:
        # 处理非字典状态数据
        markdown_lines.append("## 状态数据")
        markdown_lines.append("")
        markdown_lines.append("```")
        markdown_lines.append(str(status_data))
        markdown_lines.append("```")

    # 添加底部信息
    markdown_lines.append("---")
    markdown_lines.append("*由 SAGE 开发工具自动生成*")

    return "\n".join(markdown_lines)


def _generate_markdown_output(result, analysis_type):
    """生成Markdown格式的分析输出"""
    import datetime

    markdown_lines = []

    # 添加标题和时间戳
    markdown_lines.append("# SAGE 项目依赖分析报告")
    markdown_lines.append("")
    markdown_lines.append(f"**分析类型**: {analysis_type}")
    markdown_lines.append(f"**生成时间**: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    markdown_lines.append("")

    if isinstance(result, dict):
        # 处理包含summary的结果
        if "summary" in result:
            summary = result["summary"]
            markdown_lines.append("## 📊 分析摘要")
            markdown_lines.append("")
            markdown_lines.append(f"- **总包数**: {summary.get('total_packages', 0)}")
            markdown_lines.append(f"- **总依赖**: {summary.get('total_dependencies', 0)}")

            if "dependency_conflicts" in summary:
                conflicts = summary["dependency_conflicts"]
                conflict_count = len(conflicts) if isinstance(conflicts, list) else 0
                markdown_lines.append(f"- **依赖冲突**: {conflict_count}")

                if conflict_count > 0 and isinstance(conflicts, list):
                    markdown_lines.append("")
                    markdown_lines.append("### ⚠️ 依赖冲突详情")
                    markdown_lines.append("")
                    for i, conflict in enumerate(conflicts, 1):
                        if isinstance(conflict, dict):
                            markdown_lines.append(f"{i}. **{conflict.get('package', 'Unknown')}**")
                            markdown_lines.append(
                                f"   - 冲突类型: {conflict.get('type', 'Unknown')}"
                            )
                            markdown_lines.append(
                                f"   - 描述: {conflict.get('description', 'No description')}"
                            )
                        else:
                            markdown_lines.append(f"{i}. {str(conflict)}")

            markdown_lines.append("")

        # 处理健康评分结果
        if "health_score" in result:
            markdown_lines.append("## 💯 项目健康评分")
            markdown_lines.append("")
            health_score = result.get("health_score", "N/A")
            grade = result.get("grade", "N/A")
            markdown_lines.append(f"- **健康评分**: {health_score}")
            markdown_lines.append(f"- **等级**: {grade}")

            # 添加评分说明
            if isinstance(health_score, (int, float)):
                if health_score >= 90:
                    status = "🟢 优秀"
                elif health_score >= 70:
                    status = "🟡 良好"
                elif health_score >= 50:
                    status = "🟠 一般"
                else:
                    status = "🔴 需要改进"
                markdown_lines.append(f"- **状态**: {status}")

            markdown_lines.append("")

        # 处理详细依赖信息
        if "dependencies" in result:
            deps = result["dependencies"]
            markdown_lines.append("## 📚 依赖详情")
            markdown_lines.append("")

            if isinstance(deps, dict):
                for package, package_deps in deps.items():
                    markdown_lines.append(f"### 📦 {package}")
                    markdown_lines.append("")
                    if isinstance(package_deps, list):
                        if package_deps:
                            markdown_lines.append("**依赖列表**:")
                            for dep in package_deps:
                                markdown_lines.append(f"- {dep}")
                        else:
                            markdown_lines.append("- 无外部依赖")
                    elif isinstance(package_deps, dict):
                        for key, value in package_deps.items():
                            markdown_lines.append(f"- **{key}**: {value}")
                    else:
                        markdown_lines.append(f"- {package_deps}")
                    markdown_lines.append("")

        # 处理包信息
        if "packages" in result:
            packages = result["packages"]
            markdown_lines.append("## 📦 包信息")
            markdown_lines.append("")

            if isinstance(packages, dict):
                markdown_lines.append("| 包名 | 版本 | 状态 |")
                markdown_lines.append("|------|------|------|")
                for package, info in packages.items():
                    if isinstance(info, dict):
                        version = info.get("version", "Unknown")
                        status = info.get("status", "Unknown")
                        markdown_lines.append(f"| {package} | {version} | {status} |")
                    else:
                        markdown_lines.append(f"| {package} | - | {info} |")
            elif isinstance(packages, list):
                markdown_lines.append("**已安装的包**:")
                for package in packages:
                    markdown_lines.append(f"- {package}")

            markdown_lines.append("")

        # 处理其他字段
        for key, value in result.items():
            if key not in [
                "summary",
                "health_score",
                "grade",
                "dependencies",
                "packages",
            ]:
                markdown_lines.append(f"## {key.replace('_', ' ').title()}")
                markdown_lines.append("")
                if isinstance(value, (list, dict)):
                    markdown_lines.append("```json")
                    import json

                    try:
                        # 处理set对象
                        def serialize_sets(obj):
                            if isinstance(obj, set):
                                return list(obj)
                            elif isinstance(obj, dict):
                                return {k: serialize_sets(v) for k, v in obj.items()}
                            elif isinstance(obj, list):
                                return [serialize_sets(item) for item in obj]
                            return obj

                        serializable_value = serialize_sets(value)
                        markdown_lines.append(
                            json.dumps(serializable_value, indent=2, ensure_ascii=False)
                        )
                    except Exception:
                        markdown_lines.append(str(value))
                    markdown_lines.append("```")
                else:
                    markdown_lines.append(f"{value}")
                markdown_lines.append("")
    else:
        # 处理非字典结果
        markdown_lines.append("## 分析结果")
        markdown_lines.append("")
        markdown_lines.append("```")
        markdown_lines.append(str(result))
        markdown_lines.append("```")

    # 添加底部信息
    markdown_lines.append("---")
    markdown_lines.append("*由 SAGE 开发工具自动生成*")

    return "\n".join(markdown_lines)


# ===================================
# 测试功能辅助函数 (从 tools/ 脚本迁移)
# ===================================


def _run_diagnose_mode(project_root: str):
    """Backward-compatible wrapper using the shared diagnostics utility."""

    run_installation_diagnostics(project_root, console=console)


def _run_issues_manager_test(project_root: str, verbose: bool):
    """运行 Issues Manager 测试"""
    try:
        console.print("🔧 运行 Issues Manager 测试...")

        # 导入并运行新的Python测试模块
        from sage.tools.dev.issues.tests import IssuesTestSuite

        test_suite = IssuesTestSuite()
        success = test_suite.run_all_tests()

        if success:
            console.print("✅ Issues Manager 测试通过")
        else:
            console.print("❌ Issues Manager 测试失败")

    except Exception as e:
        console.print(f"[red]Issues Manager 测试失败: {e}[/red]")


def _run_quick_tests(runner, config: dict, quiet: bool):
    """运行快速测试 (类似 quick_test.sh)"""
    # 快速测试包列表
    quick_packages = [
        "sage-common",
        "sage-tools",
        "sage-kernel",
        "sage-libs",
        "sage-middleware",
    ]

    if not quiet:
        console.print(f"🚀 快速测试模式 - 测试包: {quick_packages}")

    # 重写配置为快速模式
    quick_config = config.copy()
    quick_config.update(
        {
            "timeout": 120,  # 2分钟超时
            "jobs": 3,  # 3并发
            "target_packages": quick_packages,
        }
    )

    return runner.run_tests(mode="all", **quick_config)


def _run_all_tests(runner, config: dict, quiet: bool):
    """运行全部测试"""
    return runner.run_tests(mode="all", **config)


def _run_unit_tests(runner, config: dict, quiet: bool):
    """运行单元测试"""
    if not quiet:
        console.print("🔬 单元测试模式")

    # 可以在这里添加单元测试特定的逻辑
    return runner.run_tests(mode="all", **config)


def _run_integration_tests(runner, config: dict, quiet: bool):
    """运行集成测试"""
    if not quiet:
        console.print("🔗 集成测试模式")

    # 可以在这里添加集成测试特定的逻辑
    return runner.run_tests(mode="all", **config)


def _generate_test_report(
    result: dict, report_file: str, test_type: str, execution_time: float, config: dict
):
    """生成测试报告文件"""
    try:
        import json
        from datetime import datetime
        from pathlib import Path

        report_data = {
            "timestamp": datetime.now().isoformat(),
            "test_type": test_type,
            "execution_time": execution_time,
            "config": config,
            "result": result,
            "summary": {
                "status": result.get("status", "unknown"),
                "total_tests": result.get("total", 0),
                "passed": result.get("passed", 0),
                "failed": result.get("failed", 0),
                "errors": result.get("errors", 0),
            },
        }

        report_path = Path(report_file)
        report_path.parent.mkdir(parents=True, exist_ok=True)

        if report_file.endswith(".json"):
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)
        else:
            # 生成 Markdown 格式报告
            with open(report_path, "w", encoding="utf-8") as f:
                f.write("# SAGE 测试报告\n\n")
                f.write("**测试类型**: {test_type}\n")
                f.write("**生成时间**: {report_data['timestamp']}\n")
                f.write("**执行时间**: {execution_time:.2f}秒\n\n")
                f.write("## 测试结果\n\n")
                f.write("- 状态: {result.get('status', '未知')}\n")
                f.write("- 总测试数: {result.get('total', 0)}\n")
                f.write("- 通过: {result.get('passed', 0)}\n")
                f.write("- 失败: {result.get('failed', 0)}\n")
                f.write("- 错误: {result.get('errors', 0)}\n\n")

                if result.get("failed_tests"):
                    f.write("## 失败的测试\n\n")
                    for test in result["failed_tests"]:
                        f.write(f"- {test}\n")

        console.print(f"📊 测试报告已保存到: {report_path}")

    except Exception as e:
        console.print(f"[red]生成测试报告失败: {e}[/red]")


def _display_test_results(result: dict, summary_only: bool, quiet: bool, execution_time: float):
    """显示测试结果"""
    if quiet:
        return

    console.print("\n📊 测试结果摘要")
    console.print("=" * 50)

    if result:
        status = result.get("status", "unknown")
        if status == "success":
            console.print("✅ 状态: 成功")
        else:
            console.print("❌ 状态: 失败")

        console.print(f"⏱️ 执行时间: {execution_time:.2f}秒")

        # Get summary data from either top level or summary sub-dict
        summary = result.get("summary", result)
        console.print(f"📊 总测试数: {summary.get('total', 0)}")
        console.print(f"✅ 通过: {summary.get('passed', 0)}")
        console.print(f"❌ 失败: {summary.get('failed', 0)}")
        console.print(f"💥 错误: {summary.get('errors', 0)}")

        if not summary_only and result.get("failed_tests"):
            console.print("\n❌ 失败的测试:")
            for test in result["failed_tests"]:
                console.print(f"  - {test}")
    else:
        console.print("❓ 无法获取测试结果")


# ===================================
# 包状态检查辅助函数 (从 check_packages_status.sh 迁移)
# ===================================


def _get_packages_status_data(project_path) -> dict:
    """保持向后兼容，委托给共享的诊断工具。"""

    return collect_packages_status(project_path)


def _show_packages_status_summary(project_path):
    """向后兼容: 使用新的包状态摘要渲染函数。"""

    print_packages_status_summary(project_path, console=console)


def _show_packages_status(
    project_path, verbose: bool, check_versions: bool, check_dependencies: bool
):
    """显示详细包状态 (保持向后兼容)。"""

    print_packages_status(
        project_path,
        console=console,
        verbose=verbose,
        check_versions=check_versions,
        check_dependencies=check_dependencies,
    )


def _check_package_dependencies(package_name: str, verbose: bool):
    """保持原有函数存在以防外部引用。"""

    if verbose:
        console.print("    ℹ️ 依赖检查已迁移到 `sage doctor packages --deps`，当前调用保持兼容")


if __name__ == "__main__":
    app()
