"""
sage-dev 命令组 - 简化版本

这个模块提供统一的dev命令接口，调用sage.tools.dev中的核心功能。
"""

from pathlib import Path

import typer
from rich.console import Console

from sage.cli.utils.diagnostics import (
    collect_packages_status,
    print_packages_status,
    print_packages_status_summary,
    run_installation_diagnostics,
)

console = Console()
app = typer.Typer(help="SAGE 开发工具集")

# 注意: Issues管理功能已独立为 sage-github-manager 项目
# 安装: pip install sage-github-manager
# 使用: github-manager <command>

# 注意: PyPI 管理已整合到 package 命令组
# 说明: pypi 子命令已移除，改用独立工具 sage-pypi-publisher

# 删除：CI 子命令（已由 GitHub Workflows 承担 CI/CD）
# 过去这里会 add_typer(ci_app, name="ci", ...)
# 现在不再提供本地 CI 包装命令，建议直接依赖 GitHub Actions。

# 添加版本管理子命令
try:
    from .package_version import app as version_app

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

# 添加 Examples 测试工具子命令
try:
    from .examples import app as examples_app

    app.add_typer(
        examples_app,
        name="examples",
        help="🔬 Examples 测试工具 - 测试和验证示例代码（需要开发环境）",
    )
except ImportError as e:
    console.print(f"[yellow]警告: Examples 测试功能不可用: {e}[/yellow]")

# 添加 Data 数据集管理子命令
try:
    from .data import app as data_app

    app.add_typer(
        data_app,
        name="data",
        help="📊 数据集管理 - 查看和管理 SAGE 数据集",
    )
except ImportError as e:
    console.print(f"[yellow]警告: 数据集管理功能不可用: {e}[/yellow]")


@app.command()
def quality(
    fix: bool = typer.Option(True, "--fix/--no-fix", help="自动修复质量问题"),
    check_only: bool = typer.Option(False, "--check-only", help="仅检查，不修复"),
    all_files: bool = typer.Option(False, "--all-files", help="检查所有文件（而不仅是变更的文件）"),
    # 选择性运行特定检查
    hook: str | None = typer.Option(None, "--hook", help="只运行指定的 pre-commit hook"),
    # 架构和文档检查选项
    architecture: bool = typer.Option(
        True, "--architecture/--no-architecture", help="运行架构合规性检查"
    ),
    devnotes: bool = typer.Option(
        True, "--devnotes/--no-devnotes", help="运行 dev-notes 文档规范检查"
    ),
    readme: bool = typer.Option(False, "--readme", help="运行包 README 质量检查"),
    examples: bool = typer.Option(
        True, "--examples/--no-examples", help="运行 examples 目录结构检查"
    ),
    # Submodule 选项
    include_submodules: bool = typer.Option(
        False, "--include-submodules", help="包含 submodules 进行质量检查（默认跳过）"
    ),
    submodules_only: bool = typer.Option(
        False, "--submodules-only", help="仅检查 submodules（跳过主仓库）"
    ),
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
    """代码质量检查和修复（基于 pre-commit + 架构检查）

    这是 pre-commit 的友好包装器，提供统一的质量检查接口。
    所有配置都在 tools/pre-commit-config.yaml 中管理，确保一致性。

    额外集成了架构合规性检查、dev-notes 文档规范检查和 README 质量检查。

    默认情况下会跳过所有 submodules（docs-public, sageLLM, sageVDB等），
    避免修改外部依赖的代码。如需检查 submodules，请使用 --include-submodules。

    示例：
        sage-dev quality                        # 运行所有检查（自动修复，跳过submodules）
        sage-dev quality --check-only           # 只检查不修复
        sage-dev quality --all-files            # 检查所有文件
        sage-dev quality --hook black           # 只运行 black
        sage-dev quality --no-format            # 跳过格式化
        sage-dev quality --no-architecture      # 跳过架构检查
        sage-dev quality --no-devnotes          # 跳过文档检查
        sage-dev quality --readme               # 包含 README 质量检查
        sage-dev quality --include-submodules   # 包含 submodules 进行检查
        sage-dev quality --submodules-only      # 仅检查 submodules
    """
    import subprocess
    from pathlib import Path

    # 使用不同的变量名避免类型冲突
    project_dir = Path(project_root).resolve()

    if not project_dir.exists():
        console.print(f"[red]❌ 项目根目录不存在: {project_dir}[/red]")
        raise typer.Exit(1)

    console.print(f"📁 项目根目录: {project_dir}")

    # 处理 submodule 选项的冲突
    if submodules_only and not include_submodules:
        include_submodules = True

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

    # 显示 submodule 检查模式
    if submodules_only:
        console.print("\n🔍 运行代码质量检查（仅检查 submodules）...")
    elif include_submodules:
        console.print("\n🔍 运行代码质量检查（包含 submodules）...")
    else:
        console.print("\n🔍 运行代码质量检查（跳过 submodules）...")
    console.print(f"📝 配置文件: {precommit_config}")

    # 获取 submodule 列表
    def get_submodule_paths():
        """获取所有 submodule 的路径"""
        try:
            result = subprocess.run(
                ["git", "config", "--file", ".gitmodules", "--get-regexp", "path"],
                cwd=str(project_dir),
                capture_output=True,
                text=True,
                check=True,
            )
            paths = []
            for line in result.stdout.strip().split("\n"):
                if line:
                    # 格式: submodule.<name>.path <path>
                    parts = line.split()
                    if len(parts) >= 2:
                        paths.append(parts[1])
            return paths
        except (subprocess.CalledProcessError, FileNotFoundError):
            return []

    submodule_paths = get_submodule_paths()
    if submodule_paths:
        console.print(
            f"📦 检测到 {len(submodule_paths)} 个 submodules: {', '.join(submodule_paths)}"
        )

    # 构建 pre-commit 命令
    if submodules_only and submodule_paths:
        # 仅检查 submodules - 对每个 submodule 单独运行
        console.print("\n🎯 仅检查 submodules 模式")
        failed_submodules = []

        for submodule_path in submodule_paths:
            submodule_dir = project_dir / submodule_path
            if not submodule_dir.exists():
                console.print(f"[yellow]⚠️  跳过不存在的 submodule: {submodule_path}[/yellow]")
                continue

            console.print(f"\n{'=' * 60}")
            console.print(f"🔍 检查 submodule: {submodule_path}")
            console.print(f"{'=' * 60}")

            cmd = ["pre-commit", "run"]
            cmd.extend(["--config", str(precommit_config)])

            if hook:
                cmd.append(hook)
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
                    import os

                    os.environ["SKIP"] = ",".join(skip_hooks)

            if all_files:
                cmd.append("--all-files")

            cmd.append("--verbose")

            # 对 submodule 中的文件运行检查
            cmd.extend(["--files", f"{submodule_path}/**/*"])

            try:
                result = subprocess.run(cmd, cwd=str(project_dir), check=False)
                if result.returncode != 0:
                    failed_submodules.append(submodule_path)
            except Exception as e:
                console.print(f"[red]❌ 检查 {submodule_path} 失败: {e}[/red]")
                failed_submodules.append(submodule_path)

        # 汇总结果
        console.print(f"\n{'=' * 60}")
        if failed_submodules:
            console.print(f"[red]❌ {len(failed_submodules)} 个 submodules 检查失败:[/red]")
            for sm in failed_submodules:
                console.print(f"  - {sm}")
            if not warn_only:
                raise typer.Exit(1)
        else:
            console.print("[green]✅ 所有 submodules 质量检查通过！[/green]")
        return

    # 主仓库检查逻辑（原有逻辑，但需要处理 submodule 排除）
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

    # 处理 submodule 包含逻辑
    if include_submodules and not submodules_only:
        console.print("⚠️  [yellow]警告: 将检查 submodules 中的文件[/yellow]")
        console.print(
            "💡 [yellow]提示: submodules 的排除规则在 pre-commit-config.yaml 中配置[/yellow]"
        )
        # 注意：如果要包含 submodules，需要临时修改 SKIP 环境变量
        # 或者创建临时配置文件，这里我们使用环境变量提示用户
        console.print(
            "📝 [cyan]如需完全控制 submodules 的检查，"
            "请临时修改 tools/pre-commit-config.yaml 中的 exclude 规则[/cyan]"
        )

    # 显示更多输出
    cmd.append("--verbose")

    # 运行 pre-commit
    console.print(f"\n🚀 执行命令: {' '.join(cmd)}\n")

    precommit_passed = True
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
            console.print("\n[green]✅ Pre-commit 检查通过！[/green]")
        elif warn_only:
            console.print("\n[yellow]⚠️ Pre-commit 发现问题，但继续执行（warn-only 模式）[/yellow]")
            precommit_passed = False
        else:
            console.print("\n[red]❌ Pre-commit 检查失败[/red]")
            precommit_passed = False

    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️ 用户中断[/yellow]")
        raise typer.Exit(130)
    except Exception as e:
        console.print(f"\n[red]❌ Pre-commit 运行失败: {e}[/red]")
        precommit_passed = False

    # 运行额外的架构和文档检查
    extra_checks_passed = True

    # 架构检查
    if architecture and not submodules_only:
        console.print("\n" + "=" * 60)
        console.print("🏗️  运行架构合规性检查...")
        console.print("=" * 60)
        try:
            from sage.tools.dev.tools.architecture_checker import ArchitectureChecker

            checker = ArchitectureChecker(root_dir=str(project_dir))
            if all_files:
                result = checker.check_all()
            else:
                result = checker.check_changed_files(diff_target="HEAD")

            if result.passed:
                console.print("[green]✅ 架构合规性检查通过[/green]")
            else:
                console.print(f"[red]❌ 发现 {len(result.violations)} 个架构违规[/red]")
                for violation in result.violations[:5]:  # 只显示前5个
                    console.print(f"   • {violation.file}: {violation.message}")
                if len(result.violations) > 5:
                    console.print(f"   ... 还有 {len(result.violations) - 5} 个问题")
                extra_checks_passed = False
        except Exception as e:
            console.print(f"[yellow]⚠️  架构检查失败: {e}[/yellow]")
            if not warn_only:
                extra_checks_passed = False

    # Dev-notes 文档检查
    if devnotes and not submodules_only:
        console.print("\n" + "=" * 60)
        console.print("📚 运行 dev-notes 文档规范检查...")
        console.print("=" * 60)
        try:
            from sage.tools.dev.tools.devnotes_checker import DevNotesChecker

            checker = DevNotesChecker(root_dir=str(project_dir))
            if all_files:
                result = checker.check_all()
            else:
                result = checker.check_changed()

            if result.get("passed", False):
                console.print("[green]✅ Dev-notes 文档规范检查通过[/green]")
            else:
                issues = result.get("issues", [])
                console.print(f"[red]❌ 发现 {len(issues)} 个文档问题[/red]")
                for issue in issues[:5]:  # 只显示前5个
                    console.print(
                        f"   • {issue.get('file', 'unknown')}: {issue.get('message', '')}"
                    )
                if len(issues) > 5:
                    console.print(f"   ... 还有 {len(issues) - 5} 个问题")
                extra_checks_passed = False
        except Exception as e:
            console.print(f"[yellow]⚠️  文档检查失败: {e}[/yellow]")
            if not warn_only:
                extra_checks_passed = False

    # README 检查（可选）
    if readme and not submodules_only:
        console.print("\n" + "=" * 60)
        console.print("📄 运行包 README 质量检查...")
        console.print("=" * 60)
        try:
            from sage.tools.dev.tools.package_readme_checker import PackageREADMEChecker

            checker = PackageREADMEChecker(workspace_root=str(project_dir))
            results = checker.check_all(fix=False)

            low_score_packages = [r for r in results if r.score < 80.0]
            if not low_score_packages:
                console.print("[green]✅ README 质量检查通过[/green]")
            else:
                console.print(
                    f"[yellow]⚠️  {len(low_score_packages)} 个包的 README 需要改进[/yellow]"
                )
                for r in low_score_packages[:5]:
                    console.print(f"   • {r.package_name}: {r.score:.1f}/100")
                if len(low_score_packages) > 5:
                    console.print(f"   ... 还有 {len(low_score_packages) - 5} 个包")
                console.print("💡 运行 `sage-dev check-readme --report` 查看详细信息")
                # README 检查不阻止提交，只是警告
        except Exception as e:
            console.print(f"[yellow]⚠️  README 检查失败: {e}[/yellow]")

    # Examples 目录结构检查（可选）
    if examples and not submodules_only:
        console.print("\n" + "=" * 60)
        console.print("📁 运行 examples 目录结构检查...")
        console.print("=" * 60)
        try:
            from pathlib import Path

            from sage.tools.dev.tools.examples_structure_checker import (
                ExamplesStructureChecker,
            )

            examples_dir = Path(project_dir) / "examples"
            if not examples_dir.exists():
                console.print(f"[yellow]⚠️  examples 目录不存在: {examples_dir}[/yellow]")
            else:
                checker = ExamplesStructureChecker(examples_dir)
                result = checker.check_structure()

                if result.passed:
                    console.print("[green]✅ Examples 目录结构检查通过[/green]")
                else:
                    console.print(f"[red]❌ 发现 {len(result.violations)} 个结构问题[/red]")
                    for violation in result.violations[:5]:
                        console.print(f"   • {violation}")
                    if len(result.violations) > 5:
                        console.print(f"   ... 还有 {len(result.violations) - 5} 个问题")

                    if result.unexpected_dirs:
                        console.print("\n[yellow]不符合规范的目录:[/yellow]")
                        for dir_name in result.unexpected_dirs:
                            console.print(f"   • {dir_name}/")

                    console.print(f"\n{checker.get_structure_guide()}")
                    extra_checks_passed = False
        except Exception as e:
            console.print(f"[yellow]⚠️  Examples 检查失败: {e}[/yellow]")
            if not warn_only:
                extra_checks_passed = False

    # 汇总结果
    console.print("\n" + "=" * 60)
    if precommit_passed and extra_checks_passed:
        console.print("[green]✅ 所有质量检查通过！[/green]")
        console.print("=" * 60)
        return
    elif warn_only:
        console.print("[yellow]⚠️  发现质量问题，但继续执行（warn-only 模式）[/yellow]")
        console.print("=" * 60)
        return
    else:
        console.print("[red]❌ 质量检查失败[/red]")
        console.print("=" * 60)
        if not all_files:
            console.print(
                "[yellow]💡 提示: 使用 --all-files 检查所有文件，或修复上述问题后重新运行[/yellow]"
            )
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
    target: str = typer.Option(
        "all",
        help="清理目标: all, all-deep, cache, build, logs, empty-dirs, cmake, temp, node-modules",
    ),
    project_root: str = typer.Option(".", help="项目根目录"),
    dry_run: bool = typer.Option(False, help="预览模式，不实际删除"),
):
    """清理项目文件

    清理各类临时文件、缓存和构建产物。根据 SAGE 架构设计，这些文件应该统一生成在 .sage/ 目录下。

    支持的清理目标:
      - all: 清理所有缓存、构建产物、日志和空目录
      - all-deep: 清理所有可清理的内容（包括 node_modules，用于彻底清理）
      - cache: Python缓存（.ruff_cache, .mypy_cache, __pycache__, *.pyc等）
      - build: 构建产物（build/, dist/, *.egg-info等）
      - logs: 日志文件（*.log等）
      - empty-dirs: 空目录
      - cmake: CMake构建产物（CMakeFiles/, cmake_build/等）
      - temp: 临时文件（.tmp, *.tmp等）
      - node-modules: 清理 node_modules（用于前端项目，如 sage-studio）
    """
    try:
        import shutil
        from pathlib import Path

        project_path = Path(project_root).resolve()

        if dry_run:
            console.print("[yellow]预览模式 - 不会实际删除文件[/yellow]\n")

        cleaned_items = []

        # 定义要清理的目录和文件模式
        # 包括根目录和递归查找的模式
        clean_targets = {
            "cache": {
                "root_dirs": [
                    ".ruff_cache",
                    ".mypy_cache",
                    ".pytest_cache",
                    ".pyre",
                    ".basedpyright",
                ],
                "root_files": [".coverage", "coverage.xml"],
                "recursive_dirs": [
                    "__pycache__",
                    "htmlcov",
                    ".pytest_cache",
                    ".mypy_cache",
                    ".ruff_cache",
                    ".pyre",
                ],
                "recursive_files": ["*.pyc", "*.pyo", ".coverage", "coverage.xml"],
            },
            "build": {
                "root_dirs": ["build", "dist", ".eggs"],
                "root_files": [],
                "recursive_dirs": ["build", "dist", ".eggs"],
                "recursive_files": ["*.egg-info"],
            },
            "logs": {
                "root_dirs": ["logs", "test_logs"],
                "root_files": ["*.log", "install.log"],
                "recursive_dirs": ["logs", "test_logs"],
                "recursive_files": ["*.log"],
            },
            "cmake": {
                "root_dirs": ["cmake_build", "CMakeFiles"],
                "root_files": ["CMakeCache.txt", "cmake_install.cmake"],
                "recursive_dirs": ["CMakeFiles"],
                "recursive_files": ["cmake_install.cmake", "CMakeCache.txt"],
            },
            "temp": {
                "root_dirs": [".tmp"],
                "root_files": ["*.tmp", "*.bak", "*.swp"],
                "recursive_dirs": [".tmp"],
                "recursive_files": ["*.tmp", "*.bak", "*.swp"],
            },
            "node-modules": {
                "root_dirs": ["node_modules"],
                "root_files": [],
                "recursive_dirs": ["node_modules"],
                "recursive_files": [],
            },
        }

        # 受保护的目录（不会被递归清理）
        PROTECTED_PATHS = {
            ".git",
            ".venv",
            "venv",
            "env",
            ".idea",
            ".vscode",
            ".sage",
        }

        # node_modules 仅在显式指定时清理
        protect_node_modules = target not in ["all-deep", "node-modules"]
        if protect_node_modules:
            PROTECTED_PATHS.add("node_modules")

        targets_to_clean = []
        if target == "all":
            targets_to_clean = list(clean_targets.keys()) + ["empty-dirs"]
            targets_to_clean.remove("node-modules")  # 默认 all 不包括 node_modules
        elif target == "all-deep":
            targets_to_clean = list(clean_targets.keys()) + ["empty-dirs"]
        elif target in clean_targets:
            targets_to_clean = [target]
        elif target == "empty-dirs":
            targets_to_clean = ["empty-dirs"]
        else:
            console.print(f"[red]不支持的清理目标: {target}[/red]")
            console.print(
                "支持的目标: all, all-deep, cache, build, logs, empty-dirs, cmake, temp, node-modules"
            )
            raise typer.Exit(1)

        # 执行清理
        for target_type in targets_to_clean:
            if target_type == "empty-dirs":
                # 特殊处理：清理空目录
                continue

            target_config = clean_targets[target_type]

            # 1. 清理根目录的特定目录
            for dir_name in target_config.get("root_dirs", []):
                dir_path = project_path / dir_name
                if dir_path.exists() and dir_path.is_dir():
                    rel = str(dir_path.relative_to(project_path))
                    try:
                        cleaned_items.append(rel + "/")
                        if not dry_run:
                            shutil.rmtree(dir_path)
                            console.print(f"[green]✓[/green] 删除: {rel}/")
                    except Exception as e:
                        console.print(f"[yellow]⚠️ 无法删除 {rel}: {e}[/yellow]")

            # 2. 清理根目录的特定文件
            for file_pattern in target_config.get("root_files", []):
                if "*" in file_pattern:
                    # 使用 glob 匹配
                    for file_path in project_path.glob(file_pattern):
                        if file_path.is_file():
                            rel = str(file_path.relative_to(project_path))
                            try:
                                cleaned_items.append(rel)
                                if not dry_run:
                                    file_path.unlink()
                                    console.print(f"[green]✓[/green] 删除: {rel}")
                            except Exception as e:
                                console.print(f"[yellow]⚠️ 无法删除 {rel}: {e}[/yellow]")
                else:
                    file_path = project_path / file_pattern
                    if file_path.exists() and file_path.is_file():
                        rel = str(file_path.relative_to(project_path))
                        try:
                            cleaned_items.append(rel)
                            if not dry_run:
                                file_path.unlink()
                                console.print(f"[green]✓[/green] 删除: {rel}")
                        except Exception as e:
                            console.print(f"[yellow]⚠️ 无法删除 {rel}: {e}[/yellow]")

            # 3. 递归清理子目录中的目录和文件
            for pattern in target_config.get("recursive_dirs", []) + target_config.get(
                "recursive_files", []
            ):
                # 特殊处理隐藏目录（以 . 开头的目录）
                # rglob 默认不匹配隐藏目录，需要手动处理
                if pattern.startswith("."):
                    # 对于隐藏目录，直接使用 glob 的 `**/<pattern>` 模式
                    try:
                        for path in project_path.glob(f"**/{pattern}"):
                            # 跳过受保护的路径
                            if any(protected in path.parts for protected in PROTECTED_PATHS):
                                continue

                            # 跳过 .sage 目录（这是有意设计的工作目录）
                            if ".sage" in path.parts:
                                continue

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
                    except Exception:
                        pass  # 忽略无法搜索的路径
                else:
                    # 对于普通目录和文件，使用 rglob
                    for path in project_path.rglob(pattern):
                        # 跳过受保护的路径
                        if any(protected in path.parts for protected in PROTECTED_PATHS):
                            continue

                        # 跳过 .sage 目录（这是有意设计的工作目录）
                        if ".sage" in path.parts:
                            continue

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

        # 最后清理空目录（自底向上）
        # 这包括在 clean 函数中总是会执行，除非明确只清理特定目标
        if "empty-dirs" in targets_to_clean or target == "all":
            empty_dirs = []
            for dirpath in sorted(
                project_path.rglob("*"), key=lambda p: len(p.parts), reverse=True
            ):
                if dirpath.is_dir() and not any(dirpath.iterdir()):
                    # 跳过受保护的目录
                    if any(protected in dirpath.parts for protected in PROTECTED_PATHS | {".sage"}):
                        continue
                    try:
                        rel = str(dirpath.relative_to(project_path))
                        if not dry_run:
                            dirpath.rmdir()
                        empty_dirs.append(rel + "/")
                    except Exception:
                        pass  # 忽略删除失败的情况

            if empty_dirs:
                cleaned_items.extend(empty_dirs)
                if not dry_run and len(empty_dirs) > 0:
                    console.print(f"[green]清理了 {len(empty_dirs)} 个空目录[/green]")

        # 报告结果
        if cleaned_items:
            console.print(
                f"\n[green]{'[预览] 将清理' if dry_run else '✅ 已清理'} {len(cleaned_items)} 个项目[/green]"
            )
            if len(cleaned_items) <= 30:
                for item in cleaned_items:
                    console.print(f"  📁 {item}")
            else:
                for item in cleaned_items[:30]:
                    console.print(f"  📁 {item}")
                console.print(f"  ... 还有 {len(cleaned_items) - 30} 个项目")
        else:
            console.print("[blue]✨ 没有找到需要清理的项目[/blue]")

        console.print("\n[green]✅ 清理完成[/green]")

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
    # 覆盖率选项
    coverage: bool = typer.Option(False, "--coverage", help="启用测试覆盖率分析"),
    coverage_report: str = typer.Option(
        "term,html,xml",
        "--coverage-report",
        help="覆盖率报告格式 (逗号分隔，可选: term, html, xml)",
    ),
    # 调试选项
    debug: bool = typer.Option(False, "--debug", help="启用调试模式，输出详细执行信息"),
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

        # 调试模式：输出时间戳
        def debug_log(message: str, stage: str = ""):
            if debug:
                timestamp = time.strftime("%H:%M:%S")
                if stage:
                    console.print(f"[dim cyan][{timestamp}] 🔍 [{stage}][/dim cyan] {message}")
                else:
                    console.print(f"[dim cyan][{timestamp}] 🔍[/dim cyan] {message}")

        debug_log("测试命令开始执行", "INIT")
        debug_log(f"参数: test_type={test_type}, packages={packages}, coverage={coverage}", "INIT")

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

        debug_log(f"项目根目录: {project_path}", "PATH")

        # 1. 代码质量检查和修复 (在测试前运行)
        debug_log(f"质量检查: skip_quality_check={skip_quality_check}", "QUALITY")
        if not skip_quality_check:
            if not quiet:
                console.print(Rule("[bold cyan]🔍 执行测试前代码质量检查...[/bold cyan]"))

            # 使用 subprocess 调用 pre-commit 进行质量检查
            import subprocess

            precommit_config = project_path / "tools" / "pre-commit-config.yaml"

            if precommit_config.exists():
                cmd = ["pre-commit", "run", "--config", str(precommit_config)]

                # 根据选项跳过某些 hooks
                skip_hooks = []
                if not quality_format:
                    skip_hooks.append("black")
                if not quality_imports:
                    skip_hooks.append("isort")
                if not quality_lint:
                    skip_hooks.append("ruff")

                if skip_hooks:
                    import os

                    os.environ["SKIP"] = ",".join(skip_hooks)

                try:
                    result = subprocess.run(cmd, cwd=str(project_path), check=False)
                    has_quality_issues = result.returncode != 0

                    if has_quality_issues and not quiet:
                        console.print("[yellow]⚠️ 发现代码质量问题，但继续运行测试[/yellow]")
                    elif not quiet:
                        console.print("[green]🎉 所有代码质量检查通过，继续运行测试[/green]")
                except Exception as e:
                    if not quiet:
                        console.print(f"[yellow]⚠️ 质量检查运行失败: {e}，继续运行测试[/yellow]")
            else:
                if not quiet:
                    console.print(
                        f"[yellow]⚠️ pre-commit 配置文件不存在: {precommit_config}，跳过质量检查[/yellow]"
                    )
        elif not quiet:
            console.print("[yellow]⚠️ 跳过代码质量检查[/yellow]")

        # 诊断模式
        if diagnose:
            debug_log("运行诊断模式", "DIAGNOSE")
            console.print(Rule("[bold cyan]🔍 运行诊断模式...[/bold cyan]"))
            run_installation_diagnostics(project_path, console=console)
            return

        debug_log("创建 EnhancedTestRunner", "RUNNER")
        runner = EnhancedTestRunner(str(project_path), enable_coverage=coverage, debug=debug)
        debug_log(f"Runner 创建成功，覆盖率: {runner.enable_coverage}", "RUNNER")

        # 解析包列表
        target_packages = []
        if packages:
            target_packages = [pkg.strip() for pkg in packages.split(",")]
            console.print(f"🎯 指定测试包: {target_packages}")
            debug_log(f"目标包: {target_packages}", "CONFIG")

        # 配置测试参数
        test_config = {
            "verbose": verbose and not quiet,
            "workers": jobs,
            "timeout": timeout,
            "continue_on_error": continue_on_error,
            "target_packages": target_packages,
            "failed_only": failed_only,
        }

        debug_log(f"测试配置: jobs={jobs}, timeout={timeout}", "CONFIG")

        if not quiet:
            console.print(Rule(f"[bold cyan]🧪 运行 {test_type} 测试...[/bold cyan]"))
            console.print(
                f"测试配置: {jobs} 线程测试,     {timeout}s 超时退出,     {'遇到错误继续执行模式' if continue_on_error else '遇错停止模式'}"
            )

        start_time = time.time()
        debug_log(f"开始执行测试，类型: {test_type}", "EXECUTE")

        # 执行测试
        if test_type == "quick":
            debug_log("执行快速测试", "EXECUTE")
            result = _run_quick_tests(runner, test_config, quiet)
        elif test_type == "all":
            debug_log("执行全部测试", "EXECUTE")
            result = _run_all_tests(runner, test_config, quiet)
        elif test_type == "unit":
            debug_log("执行单元测试", "EXECUTE")
            result = _run_unit_tests(runner, test_config, quiet)
        elif test_type == "integration":
            debug_log("执行集成测试", "EXECUTE")
            result = _run_integration_tests(runner, test_config, quiet)
        else:
            console.print(f"[red]不支持的测试类型: {test_type}[/red]")
            console.print("支持的类型: all, unit, integration, quick")
            raise typer.Exit(1)

        execution_time = time.time() - start_time
        debug_log(f"测试执行完成，耗时: {execution_time:.2f}s", "RESULT")

        # 生成覆盖率报告（如果启用）
        if coverage:
            debug_log("生成覆盖率报告", "COVERAGE")
            _generate_coverage_reports(project_path, coverage_report, quiet, debug_log)

        # 生成报告
        if report_file:
            debug_log(f"生成报告: {report_file}", "REPORT")
            _generate_test_report(result, report_file, test_type, execution_time, test_config)

        # 显示结果
        debug_log("显示测试结果", "DISPLAY")
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
                                if packages and isinstance(packages, list | dict):
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
            if isinstance(health_score, int | float):
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
                if isinstance(value, list | dict):
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


# Note: Issues Manager tests have been removed as the functionality
# is now in the separate sage-github-manager package
# Install: pip install sage-github-manager
# Use: github-manager test


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


def _generate_coverage_reports(project_path: Path, coverage_report: str, quiet: bool, debug_log):
    """生成覆盖率报告

    Args:
        project_path: 项目根目录
        coverage_report: 报告格式，逗号分隔 (term, html, xml)
        quiet: 静默模式
        debug_log: 调试日志函数
    """
    import os
    import subprocess

    from sage.common.config.output_paths import get_sage_paths

    try:
        debug_log("开始生成覆盖率报告", "COVERAGE")

        # 获取 SAGE 路径配置
        sage_paths = get_sage_paths(str(project_path))
        coverage_dir = sage_paths.coverage_dir
        coverage_file = coverage_dir / ".coverage"

        debug_log(f"Coverage 目录: {coverage_dir}", "COVERAGE")
        debug_log(f"Coverage 合并文件: {coverage_file}", "COVERAGE")

        # 查找所有coverage数据文件（包括主文件和并行测试生成的分片文件）
        coverage_files = list(coverage_dir.glob(".coverage*"))

        if not coverage_files:
            if not quiet:
                console.print("[yellow]⚠️ 未找到覆盖率数据文件[/yellow]")
                console.print(f"[yellow]   预期位置: {coverage_dir}/.coverage*[/yellow]")
            return

        debug_log(f"找到 {len(coverage_files)} 个coverage文件", "COVERAGE")

        # 合并覆盖率数据（如果有多个 .coverage.* 文件）
        # coverage combine 会自动查找所有 .coverage.* 文件并合并到 .coverage
        debug_log("合并覆盖率数据", "COVERAGE")
        combine_cmd = ["python", "-m", "coverage", "combine", "--keep"]
        result = subprocess.run(
            combine_cmd,
            cwd=str(coverage_dir),  # 在coverage目录中运行，这样它能找到所有.coverage.*文件
            env={**os.environ, "COVERAGE_FILE": str(coverage_file)},
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            debug_log(f"Coverage combine 警告: {result.stderr}", "COVERAGE")
            # 即使combine失败也继续，可能只有一个coverage文件

        # 解析报告格式
        report_formats = [fmt.strip() for fmt in coverage_report.split(",")]
        debug_log(f"报告格式: {report_formats}", "COVERAGE")

        # 生成各种格式的报告
        for fmt in report_formats:
            debug_log(f"生成 {fmt} 格式报告", "COVERAGE")

            if fmt == "term":
                # 终端输出
                if not quiet:
                    console.print("\n" + "=" * 70)
                    console.print("[bold cyan]📊 测试覆盖率报告[/bold cyan]")
                    console.print("=" * 70 + "\n")

                term_cmd = ["python", "-m", "coverage", "report", "-m"]
                result = subprocess.run(
                    term_cmd,
                    cwd=str(project_path),
                    env={**os.environ, "COVERAGE_FILE": str(coverage_file)},
                    capture_output=True,
                    text=True,
                )

                if result.returncode == 0 and not quiet:
                    console.print(result.stdout)
                else:
                    debug_log(f"Coverage report 失败: {result.stderr}", "COVERAGE")

            elif fmt == "html":
                # HTML 报告
                html_dir = coverage_dir / "htmlcov"
                html_cmd = ["python", "-m", "coverage", "html", "-d", str(html_dir)]
                result = subprocess.run(
                    html_cmd,
                    cwd=str(project_path),
                    env={**os.environ, "COVERAGE_FILE": str(coverage_file)},
                    capture_output=True,
                    text=True,
                )

                if result.returncode == 0:
                    if not quiet:
                        console.print(
                            f"[green]✅ HTML 覆盖率报告已生成: {html_dir}/index.html[/green]"
                        )
                    debug_log(f"HTML 报告生成成功: {html_dir}", "COVERAGE")
                else:
                    debug_log(f"HTML 报告生成失败: {result.stderr}", "COVERAGE")

            elif fmt == "xml":
                # XML 报告（用于 CI/CD 工具）
                xml_file = coverage_dir / "coverage.xml"
                xml_cmd = ["python", "-m", "coverage", "xml", "-o", str(xml_file)]
                result = subprocess.run(
                    xml_cmd,
                    cwd=str(project_path),
                    env={**os.environ, "COVERAGE_FILE": str(coverage_file)},
                    capture_output=True,
                    text=True,
                )

                if result.returncode == 0:
                    if not quiet:
                        console.print(f"[green]✅ XML 覆盖率报告已生成: {xml_file}[/green]")
                    debug_log(f"XML 报告生成成功: {xml_file}", "COVERAGE")
                else:
                    debug_log(f"XML 报告生成失败: {result.stderr}", "COVERAGE")

        debug_log("覆盖率报告生成完成", "COVERAGE")

    except Exception as e:
        if not quiet:
            console.print(f"[yellow]⚠️ 生成覆盖率报告时出错: {e}[/yellow]")
        debug_log(f"覆盖率报告生成异常: {e}", "COVERAGE")
        import traceback

        debug_log(traceback.format_exc(), "COVERAGE")


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


# ===================================
# 架构和文档检查命令
# ===================================


@app.command()
def architecture(
    show_dependencies: bool = typer.Option(
        True, "--dependencies/--no-dependencies", help="显示依赖关系"
    ),
    show_layers: bool = typer.Option(True, "--layers/--no-layers", help="显示层级定义"),
    package: str = typer.Option(None, "--package", help="显示特定包的信息"),
    output_format: str = typer.Option("text", "--format", help="输出格式: text, json, markdown"),
):
    """显示 SAGE 架构信息

    显示项：
    - 分层架构定义（L1-L5）
    - 包的层级归属
    - 允许的依赖关系
    - 依赖规则说明

    示例：
        sage-dev architecture                          # 显示完整架构信息
        sage-dev architecture --package sage-kernel    # 显示特定包的信息
        sage-dev architecture --format json            # JSON 格式输出
        sage-dev architecture --no-dependencies        # 只显示层级，不显示依赖
    """
    from sage.tools.dev.tools.architecture_checker import (
        ALLOWED_DEPENDENCIES,
        LAYER_DEFINITION,
        PACKAGE_TO_LAYER,
    )

    if output_format == "json":
        import json

        data = {
            "layers": LAYER_DEFINITION,
            "package_to_layer": PACKAGE_TO_LAYER,
            "dependencies": {k: list(v) for k, v in ALLOWED_DEPENDENCIES.items()},
        }

        if package:
            if package in PACKAGE_TO_LAYER:
                data = {
                    "package": package,
                    "layer": PACKAGE_TO_LAYER[package],
                    "dependencies": list(ALLOWED_DEPENDENCIES.get(package, set())),
                }
            else:
                console.print(f"[red]❌ 未找到包: {package}[/red]")
                raise typer.Exit(1)

        console.print(json.dumps(data, indent=2, ensure_ascii=False))
        return

    if output_format == "markdown":
        console.print("# SAGE 架构定义\n")

        if show_layers:
            console.print("## 层级定义\n")
            for layer in sorted(LAYER_DEFINITION.keys()):
                packages = LAYER_DEFINITION[layer]
                console.print(f"### {layer}")
                for pkg in packages:
                    console.print(f"- `{pkg}`")
                console.print()

        if show_dependencies:
            console.print("## 依赖关系\n")
            for pkg in sorted(ALLOWED_DEPENDENCIES.keys()):
                deps = ALLOWED_DEPENDENCIES[pkg]
                console.print(f"### {pkg}")
                if deps:
                    console.print(f"**允许依赖**: {', '.join(f'`{d}`' for d in sorted(deps))}")
                else:
                    console.print("**允许依赖**: 无（基础层）")
                console.print()
        return

    # Text format (default)
    console.print("\n" + "=" * 70)
    console.print("🏗️  SAGE 架构定义")
    console.print("=" * 70)

    if package:
        # 显示特定包的信息
        if package not in PACKAGE_TO_LAYER:
            console.print(f"\n[red]❌ 未找到包: {package}[/red]")
            console.print("\n可用的包：")
            for pkg in sorted(PACKAGE_TO_LAYER.keys()):
                console.print(f"  • {pkg}")
            raise typer.Exit(1)

        layer = PACKAGE_TO_LAYER[package]
        deps = ALLOWED_DEPENDENCIES.get(package, set())

        console.print(f"\n📦 包名称: [bold cyan]{package}[/bold cyan]")
        console.print(f"📊 所属层级: [bold yellow]{layer}[/bold yellow]")

        if deps:
            console.print("\n✅ 允许依赖的包:")
            for dep in sorted(deps):
                dep_layer = PACKAGE_TO_LAYER.get(dep, "unknown")
                console.print(f"  • {dep} ({dep_layer})")
        else:
            console.print("\n🔒 基础层，不依赖其他包")

        # 显示哪些包可以依赖这个包
        can_depend = [pkg for pkg, allowed in ALLOWED_DEPENDENCIES.items() if package in allowed]
        if can_depend:
            console.print("\n⬆️  可以被以下包依赖:")
            for pkg in sorted(can_depend):
                pkg_layer = PACKAGE_TO_LAYER.get(pkg, "unknown")
                console.print(f"  • {pkg} ({pkg_layer})")
    else:
        # 显示完整架构
        if show_layers:
            console.print("\n📊 层级定义:")
            console.print()

            for layer in sorted(LAYER_DEFINITION.keys()):
                packages = LAYER_DEFINITION[layer]
                layer_desc = {
                    "L1": "基础层 - 通用组件",
                    "L2": "平台层 - 基础设施",
                    "L3": "核心层 - 核心功能",
                    "L4": "中间件层 - 服务组件",
                    "L5": "接口层 - CLI与开发工具",
                }.get(layer, "")

                console.print(f"  [bold yellow]{layer}[/bold yellow] - {layer_desc}")
                for pkg in packages:
                    console.print(f"    • [cyan]{pkg}[/cyan]")
                console.print()

        if show_dependencies:
            console.print("\n🔗 依赖关系规则:")
            console.print()
            console.print("  💡 原则: 高层可以依赖低层，同层之间需要明确定义")
            console.print()

            # 按层级顺序显示（L1-L5）
            for layer in sorted(LAYER_DEFINITION.keys()):
                for pkg in LAYER_DEFINITION[layer]:
                    deps = ALLOWED_DEPENDENCIES.get(pkg, set())

                    console.print(f"  [cyan]{pkg}[/cyan] ({layer})")
                    if deps:
                        dep_list = ", ".join(sorted(deps))
                        console.print(f"    ✅ 可依赖: {dep_list}")
                    else:
                        console.print("    🔒 基础层，无依赖")
                    console.print()

    console.print("=" * 70)
    console.print("\n💡 提示:")
    console.print("  • 使用 --package <name> 查看特定包的依赖信息")
    console.print("  • 使用 --format json 获取机器可读的输出")
    console.print("  • 使用 --format markdown 获取文档格式")
    console.print("  • 运行 'sage-dev check-architecture' 检查架构合规性")
    console.print()


@app.command()
def check_architecture(
    project_root: str = typer.Option(".", help="项目根目录"),
    changed_only: bool = typer.Option(False, "--changed-only", help="仅检查变更的文件"),
    diff: str = typer.Option("HEAD", "--diff", help="git diff 比较的目标（用于 --changed-only）"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="显示详细信息"),
):
    """检查代码架构合规性

    检查项：
    - 包依赖规则（分层架构）
    - 导入路径合规性
    - 模块结构规范

    示例：
        sage-dev check-architecture                    # 检查所有文件
        sage-dev check-architecture --changed-only     # 仅检查变更文件
        sage-dev check-architecture --diff main        # 对比 main 分支
    """
    from sage.tools.dev.tools.architecture_checker import ArchitectureChecker

    project_path = Path(project_root).resolve()

    if not project_path.exists():
        console.print(f"[red]❌ 项目根目录不存在: {project_path}[/red]")
        raise typer.Exit(1)

    console.print("\n🏗️  检查 SAGE 架构合规性...")
    console.print(f"📁 项目路径: {project_path}")

    try:
        checker = ArchitectureChecker(root_dir=str(project_path))

        if changed_only:
            console.print(f"🔍 仅检查相对于 {diff} 的变更文件")
            result = checker.check_changed_files(diff_target=diff)
        else:
            console.print("🔍 检查所有文件")
            result = checker.check_all()

    except Exception as e:
        console.print(f"[red]❌ 架构检查执行失败: {e}[/red]")
        if verbose:
            import traceback

            console.print(traceback.format_exc())
        raise typer.Exit(1)

    # 显示结果
    if result.passed:
        console.print("\n[green]✅ 架构合规性检查通过！[/green]")
        if verbose and result.stats:
            console.print(f"📝 检查了 {result.stats.get('total_files', 0)} 个文件")
    else:
        console.print("\n[red]❌ 发现架构违规！[/red]")
        if result.stats:
            console.print(f"📝 检查了 {result.stats.get('total_files', 0)} 个文件")
        console.print(f"⚠️  发现 {len(result.violations)} 个问题：\n")

        for violation in result.violations:
            console.print(f"[red]❌ {violation.file}:{violation.line}[/red]")
            console.print(f"   {violation.message}")
            if violation.suggestion:
                console.print(f"   💡 建议: {violation.suggestion}")
            console.print()

        raise typer.Exit(1)


@app.command()
def check_devnotes(
    project_root: str = typer.Option(".", help="项目根目录"),
    changed_only: bool = typer.Option(False, "--changed-only", help="仅检查变更的文档"),
    check_structure: bool = typer.Option(False, "--check-structure", help="检查目录结构"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="显示详细信息"),
):
    """检查 dev-notes 文档规范

    检查项：
    - 文档分类是否正确
    - 元数据是否完整（Date, Author, Summary）
    - 文件名是否符合规范

    示例：
        sage-dev check-devnotes                    # 检查所有文档
        sage-dev check-devnotes --check-structure  # 检查目录结构
    """
    from sage.tools.dev.tools.devnotes_checker import DevNotesChecker

    project_path = Path(project_root).resolve()

    if not project_path.exists():
        console.print(f"[red]❌ 项目根目录不存在: {project_path}[/red]")
        raise typer.Exit(1)

    console.print("\n📚 检查 dev-notes 文档规范...")
    console.print(f"📁 项目路径: {project_path}")

    try:
        checker = DevNotesChecker(root_dir=str(project_path))

        if check_structure:
            console.print("🔍 检查目录结构...")
            structure_ok = checker.check_directory_structure()
            if structure_ok:
                console.print("\n[green]✅ 目录结构检查通过！[/green]")
            else:
                console.print("\n[red]❌ 目录结构检查失败！[/red]")
                raise typer.Exit(1)
            return
        elif changed_only:
            console.print("🔍 仅检查变更的文档...")
            result = checker.check_changed()
        else:
            console.print("🔍 检查所有文档...")
            result = checker.check_all()

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]❌ 文档检查执行失败: {e}[/red]")
        if verbose:
            import traceback

            console.print(traceback.format_exc())
        raise typer.Exit(1)

    # 显示结果
    if result.get("passed", False):
        console.print("\n[green]✅ 文档规范检查通过！[/green]")
        if verbose:
            console.print(f"📝 检查了 {result.get('total', 0)} 个文档")
    else:
        console.print("\n[red]❌ 发现文档规范问题！[/red]")
        issues = result.get("issues", [])
        console.print(f"⚠️  发现 {len(issues)} 个问题：\n")

        for issue in issues[:10]:  # 显示前10个
            console.print(f"[red]❌ {issue.get('file', 'unknown')}[/red]")
            console.print(f"   {issue.get('message', '')}")
            console.print()

        if len(issues) > 10:
            console.print(f"... 还有 {len(issues) - 10} 个问题")

        console.print("\n💡 参考模板: docs/dev-notes/TEMPLATE.md")
        raise typer.Exit(1)


@app.command()
def check_readme(
    package: str = typer.Argument(None, help="要检查的包名（不指定则检查所有包）"),
    project_root: str = typer.Option(".", help="项目根目录"),
    fix: bool = typer.Option(False, "--fix", help="生成缺失的章节（交互模式）"),
    report: bool = typer.Option(False, "--report", help="生成详细报告"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="显示详细信息"),
):
    """检查包 README 文档质量

    检查项：
    - README 文件是否存在
    - 必需章节是否完整
    - 文档结构是否符合模板

    示例：
        sage-dev check-readme                      # 检查所有包
        sage-dev check-readme sage-common          # 检查特定包
        sage-dev check-readme --report             # 生成详细报告
        sage-dev check-readme sage-libs --fix      # 交互式修复
    """
    from sage.tools.dev.tools.package_readme_checker import PackageREADMEChecker

    project_path = Path(project_root).resolve()

    if not project_path.exists():
        console.print(f"[red]❌ 项目根目录不存在: {project_path}[/red]")
        raise typer.Exit(1)

    console.print("\n📄 检查包 README 质量...")
    console.print(f"📁 项目路径: {project_path}")

    try:
        checker = PackageREADMEChecker(workspace_root=str(project_path))

        if package:
            console.print(f"🔍 检查包: {package}")
            result = checker.check_package(package, fix=fix)
            results = [result]
        else:
            console.print("🔍 检查所有包...")
            results = checker.check_all(fix=fix)

        # 显示结果
        all_passed = all(r.score >= 80.0 for r in results)

        if report:
            checker.generate_report(results)

        if all_passed:
            console.print("\n[green]✅ README 质量检查通过！[/green]")
            for r in results:
                console.print(f"  {r.package_name}: {r.score:.1f}/100")
        else:
            console.print("\n[yellow]⚠️  部分 README 需要改进：[/yellow]\n")
            for r in results:
                status = "✅" if r.score >= 80.0 else "⚠️"
                console.print(f"{status} {r.package_name}: {r.score:.1f}/100")
                if r.issues and verbose:
                    for issue in r.issues:
                        console.print(f"   - {issue}")

            if not all_passed:
                console.print("\n💡 运行 `sage-dev check-readme --report` 查看详细报告")
                console.print("💡 运行 `sage-dev check-readme <package> --fix` 交互式修复")

            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]❌ README 检查失败: {e}[/red]")
        if verbose:
            import traceback

            console.print(traceback.format_exc())
        raise typer.Exit(1)


@app.command()
def check_all(
    project_root: str = typer.Option(".", help="项目根目录"),
    changed_only: bool = typer.Option(False, "--changed-only", help="仅检查变更的文件"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="显示详细信息"),
    continue_on_error: bool = typer.Option(
        False, "--continue-on-error", help="出错时继续执行其他检查"
    ),
):
    """运行所有质量检查（架构 + 文档 + README）

    这是一个便捷命令，依次运行：
    1. 架构合规性检查
    2. Dev-notes 文档规范检查
    3. 包 README 质量检查

    示例：
        sage-dev check-all                      # 检查所有项目
        sage-dev check-all --changed-only       # 仅检查变更文件
        sage-dev check-all --continue-on-error  # 出错继续执行
        sage-dev check-all --verbose            # 详细输出
    """
    project_path = Path(project_root).resolve()

    if not project_path.exists():
        console.print(f"[red]❌ 项目根目录不存在: {project_path}[/red]")
        raise typer.Exit(1)

    console.print("\n" + "=" * 70)
    console.print("🔍 运行所有质量检查")
    console.print("=" * 70)
    console.print(f"📁 项目路径: {project_path}\n")

    checks_passed = []
    checks_failed = []

    # 1. 架构检查
    console.print("=" * 70)
    console.print("🏗️  [1/3] 架构合规性检查")
    console.print("=" * 70)
    try:
        from sage.tools.dev.tools.architecture_checker import ArchitectureChecker

        checker = ArchitectureChecker(root_dir=str(project_path))
        if changed_only:
            result = checker.check_changed_files(diff_target="HEAD")
        else:
            result = checker.check_all()

        if result.passed:
            console.print("[green]✅ 架构合规性检查通过[/green]\n")
            checks_passed.append("架构检查")
        else:
            console.print(f"[red]❌ 发现 {len(result.violations)} 个架构违规[/red]")
            if verbose:
                for violation in result.violations[:3]:
                    console.print(f"   • {violation.file}: {violation.message}")
                if len(result.violations) > 3:
                    console.print(f"   ... 还有 {len(result.violations) - 3} 个问题")
            console.print()
            checks_failed.append("架构检查")
            if not continue_on_error:
                raise typer.Exit(1)
    except typer.Exit:
        raise  # 重新抛出 Exit 异常
    except Exception as e:
        console.print(f"[red]❌ 架构检查执行失败: {e}[/red]\n")
        checks_failed.append("架构检查")
        if not continue_on_error:
            raise typer.Exit(1)

    # 2. Dev-notes 文档检查
    console.print("=" * 70)
    console.print("📚 [2/3] Dev-notes 文档规范检查")
    console.print("=" * 70)
    try:
        from sage.tools.dev.tools.devnotes_checker import DevNotesChecker

        checker = DevNotesChecker(root_dir=str(project_path))
        if changed_only:
            result = checker.check_changed()
        else:
            result = checker.check_all()

        if result.get("passed", False):
            console.print("[green]✅ Dev-notes 文档规范检查通过[/green]\n")
            checks_passed.append("文档检查")
        else:
            issues = result.get("issues", [])
            console.print(f"[red]❌ 发现 {len(issues)} 个文档问题[/red]")
            if verbose:
                for issue in issues[:3]:
                    console.print(
                        f"   • {issue.get('file', 'unknown')}: {issue.get('message', '')}"
                    )
                if len(issues) > 3:
                    console.print(f"   ... 还有 {len(issues) - 3} 个问题")
            console.print()
            checks_failed.append("文档检查")
            if not continue_on_error:
                raise typer.Exit(1)
    except typer.Exit:
        raise  # 重新抛出 Exit 异常
    except Exception as e:
        console.print(f"[red]❌ 文档检查执行失败: {e}[/red]\n")
        checks_failed.append("文档检查")
        if not continue_on_error:
            raise typer.Exit(1)

    # 3. README 检查
    console.print("=" * 70)
    console.print("📄 [3/3] 包 README 质量检查")
    console.print("=" * 70)
    try:
        from sage.tools.dev.tools.package_readme_checker import PackageREADMEChecker

        checker = PackageREADMEChecker(workspace_root=str(project_path))
        results = checker.check_all(fix=False)

        low_score_packages = [r for r in results if r.score < 80.0]
        if not low_score_packages:
            console.print("[green]✅ README 质量检查通过[/green]\n")
            checks_passed.append("README 检查")
        else:
            console.print(f"[yellow]⚠️  {len(low_score_packages)} 个包的 README 需要改进[/yellow]")
            if verbose:
                for r in low_score_packages[:5]:
                    console.print(f"   • {r.package_name}: {r.score:.1f}/100")
                if len(low_score_packages) > 5:
                    console.print(f"   ... 还有 {len(low_score_packages) - 5} 个包")
            console.print()
            # README 检查不阻止，只是警告
            checks_passed.append("README 检查（警告）")
    except typer.Exit:
        raise  # 重新抛出 Exit 异常
    except Exception as e:
        console.print(f"[yellow]⚠️  README 检查失败: {e}[/yellow]\n")
        # README 检查失败不算严重错误
        checks_passed.append("README 检查（跳过）")

    # 汇总结果
    console.print("=" * 70)
    console.print("📊 检查结果汇总")
    console.print("=" * 70)

    if checks_passed:
        console.print("[green]✅ 通过的检查:[/green]")
        for check in checks_passed:
            console.print(f"   • {check}")

    if checks_failed:
        console.print("\n[red]❌ 失败的检查:[/red]")
        for check in checks_failed:
            console.print(f"   • {check}")

    console.print("\n" + "=" * 70)
    if not checks_failed:
        console.print("[green]🎉 所有检查通过！[/green]")
        console.print("=" * 70)
    else:
        console.print(f"[red]❌ {len(checks_failed)} 项检查失败[/red]")
        console.print("=" * 70)
        console.print("\n💡 提示:")
        console.print("  • 使用 --verbose 查看详细错误")
        console.print("  • 使用 --continue-on-error 继续执行所有检查")
        console.print("  • 运行单独的检查命令修复问题:")
        console.print("    - sage-dev check-architecture")
        console.print("    - sage-dev check-devnotes")
        console.print("    - sage-dev check-readme")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
