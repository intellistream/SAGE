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
    output_format: str = typer.Option("summary", help="输出格式: summary, json, full, markdown")
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
                    message = message.replace("|", "\\|").replace("\n", " ")
                    
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
                                    markdown_lines.append(f"- **{key}**: {value}")
                        
                        elif check_name == "packages":
                            if isinstance(data, dict):
                                summary = data.get("summary", {})
                                if summary:
                                    markdown_lines.append("**包安装摘要**:")
                                    markdown_lines.append(f"- 已安装: {summary.get('installed', 0)}")
                                    markdown_lines.append(f"- 总计: {summary.get('total', 0)}")
                                
                                packages = data.get("packages", [])
                                if packages:
                                    markdown_lines.append("")
                                    markdown_lines.append("**已安装的包**:")
                                    for pkg in packages[:10]:  # 限制显示数量
                                        markdown_lines.append(f"- {pkg}")
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
                            if isinstance(data, dict):
                                for key, value in data.items():
                                    markdown_lines.append(f"- **{key}**: {value}")
                            elif isinstance(data, list):
                                for item in data[:5]:  # 限制显示数量
                                    markdown_lines.append(f"- {item}")
                                if len(data) > 5:
                                    markdown_lines.append(f"- ... 还有 {len(data) - 5} 项")
                            else:
                                markdown_lines.append(f"数据: {data}")
                        
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

if __name__ == "__main__":
    app()
