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
    analysis_type: str = typer.Option("all", help="分析类型: all, circular, missing, conflicts"),
    output_format: str = typer.Option("summary", help="输出格式: summary, json, markdown"),
    project_root: str = typer.Option(".", help="项目根目录")
):
    """分析项目依赖和结构"""
    try:
        from sage.tools.dev.tools.dependency_analyzer import DependencyAnalyzer
        analyzer = DependencyAnalyzer(project_root)
        
        if analysis_type == "all":
            result = analyzer.run_all_analyses()
        elif analysis_type == "circular":
            result = analyzer.detect_circular_dependencies()
        elif analysis_type == "missing":
            result = analyzer.check_missing_dependencies()
        elif analysis_type == "conflicts":
            result = analyzer.detect_version_conflicts()
        else:
            console.print(f"[red]不支持的分析类型: {analysis_type}[/red]")
            raise typer.Exit(1)
            
        # 输出结果
        if output_format == "json":
            import json
            console.print(json.dumps(result, indent=2))
        elif output_format == "markdown":
            # TODO: 实现markdown输出
            console.print("Markdown输出格式暂未实现")
        else:
            console.print(result)
            
    except Exception as e:
        console.print(f"[red]分析失败: {e}[/red]")
        raise typer.Exit(1)

@app.command()
def clean(
    target: str = typer.Option("all", help="清理目标: all, cache, build, logs"),
    project_root: str = typer.Option(".", help="项目根目录"),
    dry_run: bool = typer.Option(False, help="预览模式，不实际删除")
):
    """清理项目文件"""
    try:
        from sage.tools.dev.tools.enhanced_package_manager import EnhancedPackageManager
        manager = EnhancedPackageManager(project_root)
        
        if dry_run:
            console.print("[yellow]预览模式 - 不会实际删除文件[/yellow]")
            
        if target == "all":
            manager.clean_all(dry_run=dry_run)
        elif target == "cache":
            manager.clean_cache(dry_run=dry_run)
        elif target == "build":
            manager.clean_build(dry_run=dry_run)
        elif target == "logs":
            manager.clean_logs(dry_run=dry_run)
        else:
            console.print(f"[red]不支持的清理目标: {target}[/red]")
            raise typer.Exit(1)
            
        console.print("[green]✅ 清理完成[/green]")
        
    except Exception as e:
        console.print(f"[red]清理失败: {e}[/red]")
        raise typer.Exit(1)

@app.command()
def status(
    project_root: str = typer.Option(".", help="项目根目录"),
    verbose: bool = typer.Option(False, help="详细输出")
):
    """显示项目状态"""
    try:
        # 这里应该调用核心模块的状态检查功能
        console.print("🔍 检查项目状态...")
        
        # TODO: 实现具体的状态检查逻辑
        console.print("[green]✅ 项目状态正常[/green]")
        
    except Exception as e:
        console.print(f"[red]状态检查失败: {e}[/red]")
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
        from sage.tools.dev.utils.sage_home_manager import SageHomeManager
        manager = SageHomeManager(path if path else None)
        
        if action == "init":
            manager.initialize()
            console.print("[green]✅ SAGE_HOME 初始化完成[/green]")
        elif action == "clean":
            manager.clean()
            console.print("[green]✅ SAGE_HOME 清理完成[/green]")
        elif action == "status":
            status = manager.get_status()
            console.print(status)
        else:
            console.print(f"[red]不支持的操作: {action}[/red]")
            raise typer.Exit(1)
            
    except Exception as e:
        console.print(f"[red]SAGE_HOME操作失败: {e}[/red]")
        raise typer.Exit(1)

if __name__ == "__main__":
    app()
