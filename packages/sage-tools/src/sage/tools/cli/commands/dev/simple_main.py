"""
SAGE Dev 命令组 - 简化版本

这个模块提供统一的dev命令接口，调用sage.tools.dev中的核心功能。
"""

import typer
from rich.console import Console

console = Console()
app = typer.Typer(help="SAGE 开发工具集")

# 添加Issues管理子命令
try:
    from sage.tools.dev.issues.cli import app as issues_app
    app.add_typer(issues_app, name="issues", help="🐛 Issues管理 - GitHub Issues下载、分析和管理")
except ImportError as e:
    console.print(f"[yellow]警告: Issues管理功能不可用: {e}[/yellow]")

@app.command()
def analyze(
    analysis_type: str = typer.Option("all", help="分析类型: all, health, report"),
    output_format: str = typer.Option("summary", help="输出格式: summary, json, markdown"),
    project_root: str = typer.Option(".", help="项目根目录")
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
                        console.print(f"  ⚠️ 冲突: {len(conflicts) if isinstance(conflicts, list) else 0}")
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
    dry_run: bool = typer.Option(False, help="预览模式，不实际删除")
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
                "htmlcov"
            ],
            "build": [
                "build",
                "dist", 
                "*.egg-info",
                ".eggs"
            ],
            "logs": [
                "*.log",
                "logs/*.log"
            ]
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
        
        # 执行清理
        for pattern in targets_to_clean:
            if pattern.startswith("*."):
                # 文件模式
                for file_path in project_path.rglob(pattern):
                    if file_path.is_file():
                        cleaned_items.append(str(file_path.relative_to(project_path)))
                        if not dry_run:
                            file_path.unlink()
            else:
                # 目录模式
                for dir_path in project_path.rglob(pattern):
                    if dir_path.is_dir():
                        cleaned_items.append(str(dir_path.relative_to(project_path)) + "/")
                        if not dry_run:
                            shutil.rmtree(dir_path)
        
        # 报告结果
        if cleaned_items:
            console.print(f"[green]{'预览' if dry_run else '已清理'} {len(cleaned_items)} 个项目:[/green]")
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
    check_dependencies: bool = typer.Option(False, "--deps", help="检查包依赖状态")
):
    """显示项目状态 - 集成包状态检查功能"""
    try:
        from sage.tools.dev.tools.project_status_checker import ProjectStatusChecker
        from pathlib import Path
        
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
            _show_packages_status(project_path, verbose, check_versions, check_dependencies)
            return
        
        if output_format == "json":
            # JSON格式输出
            status_data = checker.check_all(verbose=False)
            # 添加包状态信息
            status_data["packages_status"] = _get_packages_status_data(project_path)
            import json
            console.print(json.dumps(status_data, indent=2, ensure_ascii=False))
        elif output_format == "full":
            # 完整详细输出
            status_data = checker.check_all(verbose=True)
            console.print("\n" + "="*60)
            console.print(checker.generate_status_summary(status_data))
            console.print("="*60)
            # 添加包状态信息
            console.print("\n📦 包状态详情:")
            _show_packages_status(project_path, True, check_versions, check_dependencies)
        elif output_format == "markdown":
            # Markdown格式输出
            status_data = checker.check_all(verbose=verbose)
            markdown_output = _generate_status_markdown_output(status_data)
            console.print(markdown_output)
        else:
            # 简要摘要输出 (默认)
            console.print("🔍 检查项目状态...")
            status_data = checker.check_all(verbose=False)
            
            # 显示摘要
            summary = checker.generate_status_summary(status_data)
            console.print(f"\n{summary}")
            
            # 显示包状态摘要
            _show_packages_status_summary(project_path)
            
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
                name for name, test in deps_data.get("import_tests", {}).items() 
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
                name for name, check in status_data["checks"].items() 
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
    continue_on_error: bool = typer.Option(True, "--continue-on-error", help="遇到错误继续执行其他包"),
    summary_only: bool = typer.Option(False, "--summary", help="只显示摘要结果"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="静默模式"),
    report_file: str = typer.Option("", "--report", help="测试报告输出文件路径"),
    diagnose: bool = typer.Option(False, "--diagnose", help="运行诊断模式"),
    issues_manager: bool = typer.Option(False, "--issues-manager", help="包含 issues manager 测试")
):
    """运行项目测试 - 集成从 tools/ 脚本迁移的高级功能"""
    try:
        from sage.tools.dev.tools.enhanced_test_runner import EnhancedTestRunner
        from pathlib import Path
        import time
        import json
        
        # 自动检测项目根目录
        project_path = Path(project_root).resolve()
        
        # 如果当前目录不是项目根目录，尝试向上查找
        if not (project_path / "packages").exists():
            # 向上查找包含 packages 目录的根目录
            current = project_path
            found_root = False
            
            while current.parent != current:  # 没有到达文件系统根目录
                if (current / "packages").exists():
                    project_path = current
                    found_root = True
                    break
                current = current.parent
            
            if not found_root:
                # 如果还是找不到，尝试一些常见的相对路径
                possible_roots = [
                    project_path / "..",
                    project_path / "../..",
                    project_path / "../../.."
                ]
                
                for possible_root in possible_roots:
                    if (possible_root / "packages").exists():
                        project_path = possible_root.resolve()
                        found_root = True
                        break
                
                if not found_root:
                    console.print(f"[red]❌ 无法找到 SAGE 项目根目录[/red]")
                    console.print(f"当前目录: {Path.cwd()}")
                    console.print(f"指定目录: {project_root}")
                    console.print("请确保在 SAGE 项目目录中运行，或使用 --project-root 指定正确的路径")
                    raise typer.Exit(1)
        
        if not quiet:
            console.print(f"📁 项目根目录: {project_path}")
        
        # 诊断模式
        if diagnose:
            console.print("🔍 运行诊断模式...")
            _run_diagnose_mode(str(project_path))
            return
            
        # Issues Manager 测试
        if issues_manager:
            console.print("🔧 运行 Issues Manager 测试...")
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
            "jobs": jobs,
            "timeout": timeout,
            "continue_on_error": continue_on_error,
            "target_packages": target_packages,
            "failed_only": failed_only
        }
        
        if not quiet:
            console.print(f"🧪 运行 {test_type} 测试...")
            console.print(f"⚙️ 配置: {jobs}并发, {timeout}s超时, {'继续执行' if continue_on_error else '遇错停止'}")
        
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
    path: str = typer.Option("", help="SAGE_HOME路径")
):
    """管理SAGE_HOME目录"""
    try:
        from sage.tools.dev.utils.sage_home_manager import SAGEHomeManager
        manager = SAGEHomeManager()
        
        if action == "init":
            from pathlib import Path
            result = manager.setup_sage_home("." if not path else path)
            if result.get("status") == "success":
                console.print("[green]✅ SAGE_HOME 初始化完成[/green]")
            else:
                console.print(f"[yellow]⚠️ SAGE_HOME 初始化: {result.get('message', 'Unknown result')}[/yellow]")
        elif action == "clean":
            result = manager.clean_logs()
            console.print(f"[green]✅ SAGE_HOME 清理完成: 删除了 {result.get('files_removed', 0)} 个文件[/green]")
        elif action == "status":
            status = manager.check_sage_home()
            console.print("🏠 SAGE_HOME 状态:")
            console.print(f"  📁 路径: {status['sage_home_path']}")
            console.print(f"  ✅ 存在: {'是' if status['sage_home_exists'] else '否'}")
            console.print(f"  📂 日志目录: {'存在' if status['logs_dir_exists'] else '不存在'}")
            if status['logs_dir_exists']:
                console.print(f"  📊 日志大小: {status['logs_dir_size']} 字节")
                console.print(f"  📄 日志文件数: {status['log_files_count']}")
        else:
            console.print(f"[red]不支持的操作: {action}[/red]")
            console.print("支持的操作: init, clean, status")
            raise typer.Exit(1)
            
    except Exception as e:
        console.print(f"[red]SAGE_HOME操作失败: {e}[/red]")
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
            "unknown": "❓"
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
                        "unknown": "❓"
                    }.get(status, "❓")
                    
                    message = check_data.get("message", "")
                    # 清理消息中的markdown特殊字符
                    if isinstance(message, str):
                        message = message.replace("|", "\\|").replace("\n", " ")
                    else:
                        message = str(message)
                    
                    markdown_lines.append(f"| {check_name.replace('_', ' ').title()} | {status_emoji} {status} | {message} |")
            
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
                                    markdown_lines.append(f"- 已安装: {summary.get('installed', 0)}")
                                    markdown_lines.append(f"- 总计: {summary.get('total', 0)}")
                                
                                packages = data.get("packages", [])
                                if packages and isinstance(packages, (list, dict)):
                                    markdown_lines.append("")
                                    markdown_lines.append("**已安装的包**:")
                                    if isinstance(packages, list):
                                        # Safely slice the list
                                        display_packages = packages[:10] if len(packages) > 10 else packages
                                        for pkg in display_packages:
                                            markdown_lines.append(f"- {str(pkg)}")
                                        if len(packages) > 10:
                                            markdown_lines.append(f"- ... 还有 {len(packages) - 10} 个包")
                                    elif isinstance(packages, dict):
                                        count = 0
                                        for pkg_name, pkg_info in packages.items():
                                            if count >= 10:
                                                break
                                            markdown_lines.append(f"- {pkg_name}: {str(pkg_info)}")
                                            count += 1
                                        if len(packages) > 10:
                                            markdown_lines.append(f"- ... 还有 {len(packages) - 10} 个包")
                        
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
                                        markdown_lines.append(f"- {status_icon} {service}: {'运行中' if running else '未运行'}")
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
            markdown_lines.append(f"```")
            markdown_lines.append(summary)
            markdown_lines.append(f"```")
            markdown_lines.append("")
    else:
        # 处理非字典状态数据
        markdown_lines.append("## 状态数据")
        markdown_lines.append("")
        markdown_lines.append(f"```")
        markdown_lines.append(str(status_data))
        markdown_lines.append(f"```")
    
    # 添加底部信息
    markdown_lines.append("---")
    markdown_lines.append("*由 SAGE 开发工具自动生成*")
    
    return "\n".join(markdown_lines)

def _generate_markdown_output(result, analysis_type):
    """生成Markdown格式的分析输出"""
    import datetime
    
    markdown_lines = []
    
    # 添加标题和时间戳
    markdown_lines.append(f"# SAGE 项目依赖分析报告")
    markdown_lines.append(f"")
    markdown_lines.append(f"**分析类型**: {analysis_type}")
    markdown_lines.append(f"**生成时间**: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    markdown_lines.append(f"")
    
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
                            markdown_lines.append(f"   - 冲突类型: {conflict.get('type', 'Unknown')}")
                            markdown_lines.append(f"   - 描述: {conflict.get('description', 'No description')}")
                        else:
                            markdown_lines.append(f"{i}. {str(conflict)}")
            
            markdown_lines.append("")
        
        # 处理健康评分结果
        if "health_score" in result:
            markdown_lines.append("## 💯 项目健康评分")
            markdown_lines.append("")
            health_score = result.get('health_score', 'N/A')
            grade = result.get('grade', 'N/A')
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
                        version = info.get('version', 'Unknown')
                        status = info.get('status', 'Unknown')
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
            if key not in ["summary", "health_score", "grade", "dependencies", "packages"]:
                markdown_lines.append(f"## {key.replace('_', ' ').title()}")
                markdown_lines.append("")
                if isinstance(value, (list, dict)):
                    markdown_lines.append(f"```json")
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
                        markdown_lines.append(json.dumps(serializable_value, indent=2, ensure_ascii=False))
                    except Exception:
                        markdown_lines.append(str(value))
                    markdown_lines.append(f"```")
                else:
                    markdown_lines.append(f"{value}")
                markdown_lines.append("")
    else:
        # 处理非字典结果
        markdown_lines.append("## 分析结果")
        markdown_lines.append("")
        markdown_lines.append(f"```")
        markdown_lines.append(str(result))
        markdown_lines.append(f"```")
    
    # 添加底部信息
    markdown_lines.append("---")
    markdown_lines.append("*由 SAGE 开发工具自动生成*")
    
    return "\n".join(markdown_lines)

# ===================================
# 测试功能辅助函数 (从 tools/ 脚本迁移)
# ===================================

def _run_diagnose_mode(project_root: str):
    """运行诊断模式，检查 SAGE 安装状态 - 集成 diagnose_sage.py 功能"""
    try:
        import subprocess
        import sys
        import importlib
        import pkgutil
        from pathlib import Path
        
        console.print("🔍 SAGE 完整安装诊断")
        console.print("=" * 50)
        
        # 1. 基础导入测试
        console.print("📦 基础导入测试...")
        imports_to_test = [
            "sage",
            "sage.common", 
            "sage.kernel",
            "sage.libs",
            "sage.middleware"
        ]
        
        import_results = {}
        for module in imports_to_test:
            try:
                imported_module = importlib.import_module(module)
                version = getattr(imported_module, '__version__', 'Unknown')
                path = getattr(imported_module, '__file__', getattr(imported_module, '__path__', 'Unknown'))
                import_results[module] = {
                    "status": "success",
                    "version": version,
                    "path": str(path) if path != 'Unknown' else path
                }
                console.print(f"  ✅ {module} (版本: {version})")
            except ImportError as e:
                import_results[module] = {
                    "status": "failed", 
                    "error": str(e)
                }
                console.print(f"  ❌ {module}: {str(e)}")
            except Exception as e:
                import_results[module] = {
                    "status": "error",
                    "error": str(e)
                }
                console.print(f"  ❌ {module}: {str(e)}")
        
        # 2. 命名空间包检查
        console.print("\n🔗 命名空间包检查...")
        try:
            import sage
            if hasattr(sage, '__path__'):
                console.print(f"  ✅ sage 命名空间路径: {sage.__path__}")
                
                # 检查子包
                for finder, name, ispkg in pkgutil.iter_modules(sage.__path__, sage.__name__ + "."):
                    if name.split('.')[-1] in ['common', 'kernel', 'libs', 'middleware', 'tools']:
                        console.print(f"    📦 发现子包: {name}")
            else:
                console.print("  ⚠️  sage 不是命名空间包")
        except Exception as e:
            console.print(f"  ❌ 命名空间检查失败: {e}")
        
        # 3. 包结构检查
        console.print("\n🏗️ 包结构检查...")
        packages_dir = Path(project_root) / "packages"
        if packages_dir.exists():
            structure_status = {}
            for package_dir in packages_dir.iterdir():
                if package_dir.is_dir() and package_dir.name.startswith("sage-"):
                    package_name = package_dir.name
                    structure_info = {
                        "pyproject": (package_dir / "pyproject.toml").exists(),
                        "setup": (package_dir / "setup.py").exists(), 
                        "src": (package_dir / "src").exists(),
                        "tests": (package_dir / "tests").exists()
                    }
                    structure_status[package_name] = structure_info
                    
                    console.print(f"  📦 {package_name}")
                    console.print(f"    ✅ pyproject.toml" if structure_info["pyproject"] else "    ❌ pyproject.toml 缺失")
                    if structure_info["src"]:
                        console.print(f"    ✅ src/ 目录")
                    if structure_info["tests"]:
                        console.print(f"    ✅ tests/ 目录")
                    else:
                        console.print(f"    ⚠️  tests/ 目录缺失")
        else:
            console.print("  ❌ packages 目录不存在")
        
        # 4. 环境变量检查
        console.print("\n🌍 环境变量检查...")
        import os
        env_vars = ["SAGE_HOME", "PYTHONPATH", "PATH"]
        for var in env_vars:
            value = os.environ.get(var)
            if value:
                console.print(f"  ✅ {var}: {value[:100]}{'...' if len(value) > 100 else ''}")
            else:
                console.print(f"  ⚠️  {var}: 未设置")
        
        # 5. CLI 工具检查
        console.print("\n🖥️ CLI 工具检查...")
        cli_commands = ["sage", "sage-dev"]
        for cmd in cli_commands:
            try:
                result = subprocess.run([cmd, "--help"], capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    console.print(f"  ✅ {cmd} 可用")
                else:
                    console.print(f"  ❌ {cmd} 返回错误码: {result.returncode}")
            except subprocess.TimeoutExpired:
                console.print(f"  ⚠️  {cmd} 超时")
            except FileNotFoundError:
                console.print(f"  ❌ {cmd} 未找到")
            except Exception as e:
                console.print(f"  ❌ {cmd} 检查失败: {e}")
        
        # 6. 依赖包检查
        console.print("\n📚 关键依赖检查...")
        key_dependencies = [
            "typer", "rich", "pydantic", "fastapi", 
            "pytest", "numpy", "pandas"
        ]
        
        for dep in key_dependencies:
            try:
                imported = importlib.import_module(dep)
                version = getattr(imported, '__version__', 'Unknown')
                console.print(f"  ✅ {dep} (版本: {version})")
            except ImportError:
                console.print(f"  ⚠️  {dep} 未安装")
            except Exception as e:
                console.print(f"  ❌ {dep} 检查失败: {e}")
        
        # 7. 生成总结
        console.print("\n📋 诊断总结:")
        successful_imports = sum(1 for result in import_results.values() if result["status"] == "success")
        total_imports = len(import_results)
        
        console.print(f"  📊 导入成功率: {successful_imports}/{total_imports}")
        
        if successful_imports == total_imports:
            console.print("  🎉 SAGE 安装完整，所有模块可正常导入")
        elif successful_imports > 0:
            console.print("  ⚠️  SAGE 部分安装，部分模块存在问题")
        else:
            console.print("  ❌ SAGE 安装存在严重问题，无法导入核心模块")
        
        console.print("\n✅ 完整诊断完成")
        
    except Exception as e:
        console.print(f"[red]诊断失败: {e}[/red]")
        import traceback
        console.print(f"[red]详细错误:\n{traceback.format_exc()}[/red]")

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
    quick_packages = ["sage-common", "sage-tools", "sage-kernel", "sage-libs", "sage-middleware"]
    
    if not quiet:
        console.print(f"🚀 快速测试模式 - 测试包: {quick_packages}")
    
    # 重写配置为快速模式
    quick_config = config.copy()
    quick_config.update({
        "timeout": 120,  # 2分钟超时
        "jobs": 3,       # 3并发
        "target_packages": quick_packages
    })
    
    return runner.run_tests(mode="all", **quick_config)

def _run_all_tests(runner, config: dict, quiet: bool):
    """运行全部测试"""
    if not quiet:
        console.print("🧪 全面测试模式")
    
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

def _generate_test_report(result: dict, report_file: str, test_type: str, execution_time: float, config: dict):
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
                "errors": result.get("errors", 0)
            }
        }
        
        report_path = Path(report_file)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        
        if report_file.endswith('.json'):
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)
        else:
            # 生成 Markdown 格式报告
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(f"# SAGE 测试报告\n\n")
                f.write(f"**测试类型**: {test_type}\n")
                f.write(f"**生成时间**: {report_data['timestamp']}\n")
                f.write(f"**执行时间**: {execution_time:.2f}秒\n\n")
                f.write(f"## 测试结果\n\n")
                f.write(f"- 状态: {result.get('status', '未知')}\n")
                f.write(f"- 总测试数: {result.get('total', 0)}\n")
                f.write(f"- 通过: {result.get('passed', 0)}\n")
                f.write(f"- 失败: {result.get('failed', 0)}\n")
                f.write(f"- 错误: {result.get('errors', 0)}\n\n")
                
                if result.get('failed_tests'):
                    f.write(f"## 失败的测试\n\n")
                    for test in result['failed_tests']:
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
        summary = result.get('summary', result)
        console.print(f"📊 总测试数: {summary.get('total', 0)}")
        console.print(f"✅ 通过: {summary.get('passed', 0)}")
        console.print(f"❌ 失败: {summary.get('failed', 0)}")
        console.print(f"💥 错误: {summary.get('errors', 0)}")
        
        if not summary_only and result.get('failed_tests'):
            console.print("\n❌ 失败的测试:")
            for test in result['failed_tests']:
                console.print(f"  - {test}")
    else:
        console.print("❓ 无法获取测试结果")

# ===================================
# 包状态检查辅助函数 (从 check_packages_status.sh 迁移)
# ===================================

def _get_packages_status_data(project_path) -> dict:
    """获取包状态数据"""
    try:
        from pathlib import Path
        if isinstance(project_path, str):
            project_path = Path(project_path)
            
        packages_dir = project_path / "packages"
        if not packages_dir.exists():
            return {"error": "packages directory not found"}
        
        packages_status = {}
        
        for package_dir in packages_dir.iterdir():
            if package_dir.is_dir() and package_dir.name.startswith("sage-"):
                package_name = package_dir.name
                status_info = {
                    "name": package_name,
                    "path": str(package_dir),
                    "has_pyproject": (package_dir / "pyproject.toml").exists(),
                    "has_setup": (package_dir / "setup.py").exists(),
                    "has_tests": (package_dir / "tests").exists(),
                    "version": "unknown"
                }
                
                # 尝试获取版本信息
                try:
                    import subprocess
                    result = subprocess.run([
                        "python", "-c", 
                        f"import {package_name.replace('-', '.')}; print(getattr({package_name.replace('-', '.')}, '__version__', 'unknown'))"
                    ], capture_output=True, text=True, timeout=5)
                    
                    if result.returncode == 0:
                        status_info["version"] = result.stdout.strip()
                        status_info["import_status"] = "success"
                    else:
                        status_info["import_status"] = "failed"
                        status_info["import_error"] = result.stderr.strip()
                except Exception as e:
                    status_info["import_status"] = "error"
                    status_info["import_error"] = str(e)
                
                packages_status[package_name] = status_info
        
        return {
            "total_packages": len(packages_status),
            "packages": packages_status
        }
    
    except Exception as e:
        return {"error": str(e)}

def _show_packages_status_summary(project_path):
    """显示包状态摘要"""
    console.print("\n📦 包状态摘要:")
    
    data = _get_packages_status_data(project_path)
    if "error" in data:
        console.print(f"[red]❌ {data['error']}[/red]")
        return
    
    total = data["total_packages"]
    packages = data["packages"]
    
    importable = sum(1 for pkg in packages.values() if pkg.get("import_status") == "success")
    has_tests = sum(1 for pkg in packages.values() if pkg.get("has_tests", False))
    
    console.print(f"  📊 总包数: {total}")
    console.print(f"  ✅ 可导入: {importable}/{total}")
    console.print(f"  🧪 有测试: {has_tests}/{total}")

def _show_packages_status(project_path, verbose: bool, check_versions: bool, check_dependencies: bool):
    """显示详细包状态"""
    console.print("📦 SAGE Framework 包状态详情")
    console.print("=" * 50)
    
    data = _get_packages_status_data(project_path)
    if "error" in data:
        console.print(f"[red]❌ {data['error']}[/red]")
        return
    
    packages = data["packages"]
    
    for package_name, info in packages.items():
        console.print(f"\n📦 {package_name}")
        
        # 基础信息
        if info.get("has_pyproject"):
            console.print("  ✅ pyproject.toml")
        else:
            console.print("  ❌ pyproject.toml 缺失")
        
        if info.get("has_tests"):
            console.print("  ✅ tests 目录")
        else:
            console.print("  ⚠️  tests 目录缺失")
        
        # 导入状态
        if info.get("import_status") == "success":
            version = info.get("version", "unknown")
            console.print(f"  ✅ 导入成功 (版本: {version})")
        else:
            console.print(f"  ❌ 导入失败")
            if verbose and info.get("import_error"):
                console.print(f"     错误: {info['import_error']}")
        
        # 详细版本信息
        if check_versions and verbose:
            console.print(f"  📍 路径: {info.get('path', 'unknown')}")
        
        # 依赖检查
        if check_dependencies:
            _check_package_dependencies(package_name, verbose)

def _check_package_dependencies(package_name: str, verbose: bool):
    """检查单个包的依赖"""
    try:
        import subprocess
        from pathlib import Path
        
        # 尝试读取 pyproject.toml 依赖
        console.print(f"    🔗 检查 {package_name} 依赖...")
        
        # 这里可以添加更详细的依赖检查逻辑
        # 暂时简化处理
        console.print(f"    ℹ️  依赖检查功能待完善")
        
    except Exception as e:
        if verbose:
            console.print(f"    ❌ 依赖检查失败: {e}")


@app.command()
def tools(
    command: str = typer.Argument(..., help="工具命令: test, diagnose, status, help"),
    test_type: str = typer.Option("quick", "--type", help="测试类型: quick, all, diagnose"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="详细输出"),
    packages: str = typer.Option("", "--packages", "-p", help="指定包，逗号分隔")
):
    """开发工具集合 - 替代 tools/tests/test 脚本"""
    
    if command == "help":
        _show_tools_help()
        return
    elif command == "test":
        _run_tools_test(test_type, verbose, packages)
    elif command == "diagnose":
        _run_diagnose_mode(None, verbose)
    elif command == "status":
        _show_packages_status(verbose)
    else:
        console.print(f"[red]未知命令: {command}[/red]")
        _show_tools_help()

def _show_tools_help():
    """显示工具帮助信息"""
    console.print("🧪 [bold blue]SAGE Framework 开发工具[/bold blue]")
    console.print()
    console.print("[bold]使用方法:[/bold]")
    console.print("  sage dev tools <command> [options]")
    console.print()
    console.print("[bold]命令:[/bold]")
    console.print("  [green]test[/green]      运行测试 (quick|all|diagnose)")
    console.print("  [green]diagnose[/green]  运行诊断和状态检查")
    console.print("  [green]status[/green]    显示包状态")
    console.print("  [green]help[/green]      显示此帮助")
    console.print()
    console.print("[bold]快速命令:[/bold]")
    console.print("  sage dev tools test --type quick              # 快速测试")
    console.print("  sage dev tools test --type all --verbose      # 测试所有包")
    console.print("  sage dev tools diagnose                       # 运行诊断")
    console.print("  sage dev tools test --packages sage-libs      # 测试指定包")
    console.print()
    console.print("[bold]详细用法:[/bold]")
    console.print("  sage dev test --help                   # 查看完整测试选项")
    console.print("  sage dev status --help                 # 查看状态选项")

def _run_tools_test(test_type: str, verbose: bool, packages: str):
    """运行工具测试"""
    from pathlib import Path
    
    project_root = str(Path(".").resolve())
    
    if test_type == "diagnose":
        _run_diagnose_mode(project_root, verbose)
    else:
        # 直接调用内部测试逻辑，而不是通过 test 函数
        try:
            from sage.tools.dev.tools.enhanced_test_runner import EnhancedTestRunner
            import time
            
            runner = EnhancedTestRunner(project_root)
            
            # 解析包列表
            target_packages = []
            if packages:
                target_packages = [pkg.strip() for pkg in packages.split(",")]
                console.print(f"🎯 指定测试包: {target_packages}")
            
            # 配置测试参数
            test_config = {
                "verbose": verbose,
                "jobs": 4,
                "timeout": 300,
                "continue_on_error": True,
                "target_packages": target_packages,
                "failed_only": False
            }
            
            console.print(f"🧪 运行 {test_type} 测试...")
            
            start_time = time.time()
            
            # 执行测试
            if test_type == "quick":
                results = _run_quick_tests(runner, test_config, False)
            elif test_type == "all":
                results = runner.run_all_tests(**test_config)
            else:
                console.print(f"[red]未知测试类型: {test_type}[/red]")
                return
            
            duration = time.time() - start_time
            
            # 显示结果
            _display_test_results(results, duration, False)
            
        except Exception as e:
            console.print(f"[red]测试运行失败: {e}[/red]")


if __name__ == "__main__":
    app()
