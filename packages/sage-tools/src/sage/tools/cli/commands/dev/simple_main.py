"""
SAGE Dev 命令组 - 简化版本

这个模块提供统一的dev命令接口，调用sage.tools.dev中的核心功能。
"""

import typer
from rich.console import Console

console = Console()
app = typer.Typer(help="SAGE 开发工具集")

@app.command()
def analyze(
    analysis_type: str = typer.Option("all", help="分析类型: all, health, report"),
    output_format: str = typer.Option("summary", help="输出格式: summary, json"),
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
    output_format: str = typer.Option("summary", help="输出格式: summary, json, full")
):
    """显示项目状态"""
    try:
        from sage.tools.dev.tools.project_status_checker import ProjectStatusChecker
        
        checker = ProjectStatusChecker(project_root)
        
        if output_format == "json":
            # JSON格式输出
            status_data = checker.check_all(verbose=False)
            import json
            console.print(json.dumps(status_data, indent=2, ensure_ascii=False))
        elif output_format == "full":
            # 完整详细输出
            status_data = checker.check_all(verbose=True)
            console.print("\n" + "="*60)
            console.print(checker.generate_status_summary(status_data))
            console.print("="*60)
        else:
            # 简要摘要输出 (默认)
            console.print("🔍 检查项目状态...")
            status_data = checker.check_all(verbose=False)
            
            # 显示摘要
            summary = checker.generate_status_summary(status_data)
            console.print(f"\n{summary}")
            
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
    test_type: str = typer.Option("all", help="测试类型: all, unit, integration"),
    project_root: str = typer.Option(".", help="项目根目录"),
    verbose: bool = typer.Option(False, help="详细输出")
):
    """运行项目测试"""
    try:
        from sage.tools.dev.tools.enhanced_test_runner import EnhancedTestRunner
        runner = EnhancedTestRunner(project_root)
        
        console.print(f"🧪 运行{test_type}测试...")
        
        if test_type == "all":
            result = runner.run_all_tests(verbose=verbose)
        elif test_type == "unit":
            result = runner.run_unit_tests(verbose=verbose)
        elif test_type == "integration":
            result = runner.run_integration_tests(verbose=verbose)
        else:
            console.print(f"[red]不支持的测试类型: {test_type}[/red]")
            raise typer.Exit(1)
            
        if result:
            console.print("[green]✅ 所有测试通过[/green]")
        else:
            console.print("[red]❌ 测试失败[/red]")
            raise typer.Exit(1)
            
    except Exception as e:
        console.print(f"[red]测试运行失败: {e}[/red]")
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

if __name__ == "__main__":
    app()
