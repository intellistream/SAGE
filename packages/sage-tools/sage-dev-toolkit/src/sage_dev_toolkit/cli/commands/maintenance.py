"""
Maintenance commands for SAGE Development Toolkit.

Includes: clean, fix-imports, update-vscode commands.
"""

from typing import Optional

import typer
from rich.table import Table

from .common import (
    console, get_toolkit, handle_command_error, format_size,
    PROJECT_ROOT_OPTION, CONFIG_OPTION, ENVIRONMENT_OPTION, VERBOSE_OPTION
)

app = typer.Typer(name="maintenance", help="Maintenance and cleanup commands")


@app.command("fix-imports")
def fix_imports_command(
    dry_run: bool = typer.Option(False, help="Show what would be fixed without making changes"),
    project_root: Optional[str] = PROJECT_ROOT_OPTION,
    config: Optional[str] = CONFIG_OPTION,
    environment: Optional[str] = ENVIRONMENT_OPTION,
    verbose: bool = VERBOSE_OPTION
):
    """Fix import paths in SAGE packages."""
    try:
        toolkit = get_toolkit(project_root, config, environment)
        
        if verbose:
            console.print("🔧 Fixing import paths in SAGE packages...")
            
        results = toolkit.fix_import_paths(dry_run=dry_run)
        
        # Display results
        if dry_run:
            console.print("🔍 Dry run - showing what would be fixed:", style="yellow")
        else:
            console.print("✅ Import path fixing completed", style="green")
        
        console.print(f"📁 Files checked: {results.get('total_files_checked', 0)}")
        console.print(f"🔧 Fixes applied: {len(results.get('fixes_applied', []))}")
        console.print(f"❌ Fixes failed: {len(results.get('fixes_failed', []))}")
        
        if results.get('fixes_applied'):
            table = Table(title="Applied Fixes")
            table.add_column("File", style="cyan")
            table.add_column("Changes", style="green")
            
            for fix in results['fixes_applied'][:10]:  # Show first 10
                changes = len(fix.get('changes', []))
                table.add_row(fix['file'], str(changes))
            
            console.print(table)
            
            if len(results['fixes_applied']) > 10:
                console.print(f"... and {len(results['fixes_applied']) - 10} more files")
        
    except Exception as e:
        handle_command_error(e, "Import fixing", verbose)


@app.command("update-vscode")
def update_vscode_command(
    mode: str = typer.Option("enhanced", help="Update mode: basic (pyproject.toml only) or enhanced (all packages)"),
    project_root: Optional[str] = PROJECT_ROOT_OPTION,
    config: Optional[str] = CONFIG_OPTION,
    environment: Optional[str] = ENVIRONMENT_OPTION,
    verbose: bool = VERBOSE_OPTION
):
    """Update VS Code Python path configurations."""
    try:
        toolkit = get_toolkit(project_root, config, environment)
        
        if verbose:
            console.print(f"🔧 Updating VS Code paths in {mode} mode...")
            
        results = toolkit.update_vscode_paths(mode=mode)
        
        # Display results
        console.print("✅ VS Code paths updated successfully", style="green")
        console.print(f"📁 Settings file: {results.get('settings_file', 'Unknown')}")
        console.print(f"🔗 Paths added: {results.get('paths_added', 0)}")
        
        if verbose and results.get('paths'):
            table = Table(title="Added Paths")
            table.add_column("Path", style="cyan")
            
            for path in results['paths'][:15]:  # Show first 15
                table.add_row(path)
            
            console.print(table)
            
            if len(results['paths']) > 15:
                console.print(f"... and {len(results['paths']) - 15} more paths")
        
    except Exception as e:
        handle_command_error(e, "VS Code update", verbose)


@app.command("clean")
def clean_command(
    categories: Optional[str] = typer.Option(None, help="Categories to clean (comma-separated): egg_info,dist,build,pycache,coverage,pytest,mypy,temp,logs,all"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be cleaned without actually deleting"),
    force: bool = typer.Option(False, "--force", "-f", help="Force cleanup without confirmation"),
    older_than_days: Optional[int] = typer.Option(None, "--older-than-days", help="Only clean files older than specified days"),
    create_script: bool = typer.Option(False, "--create-script", help="Generate cleanup script"),
    update_gitignore: bool = typer.Option(False, "--update-gitignore", help="Update .gitignore with build artifact rules"),
    project_root: Optional[str] = PROJECT_ROOT_OPTION,
    verbose: bool = VERBOSE_OPTION
):
    """🧹 Clean build artifacts and pip install intermediates."""
    try:
        from ...tools.build_artifacts_manager import BuildArtifactsManager
        
        toolkit = get_toolkit(project_root=project_root)
        manager = BuildArtifactsManager(str(toolkit.config.project_root))
        
        # 处理类别参数
        category_list = None
        if categories:
            if categories.lower() == "all":
                category_list = None  # None means all categories
            else:
                category_list = [cat.strip() for cat in categories.split(",")]
                # 验证类别
                valid_categories = set(manager.DEFAULT_PATTERNS.keys())
                invalid_categories = set(category_list) - valid_categories
                if invalid_categories:
                    console.print(f"❌ Invalid categories: {', '.join(invalid_categories)}", style="red")
                    console.print(f"Valid categories: {', '.join(sorted(valid_categories))}")
                    raise typer.Exit(1)
        
        # 更新gitignore
        if update_gitignore:
            with console.status("📝 Updating .gitignore..."):
                gitignore_result = manager.setup_gitignore_rules()
            
            console.print("📝 .gitignore Update Results:", style="cyan")
            console.print(f"  📄 File: {gitignore_result['gitignore_path']}")
            console.print(f"  ➕ Rules added: {gitignore_result['rules_added']}")
            if gitignore_result['new_rules']:
                console.print("  📋 New rules:", style="yellow")
                for rule in gitignore_result['new_rules'][:5]:
                    console.print(f"    • {rule}")
                if len(gitignore_result['new_rules']) > 5:
                    console.print(f"    ... and {len(gitignore_result['new_rules']) - 5} more")
        
        # 创建清理脚本
        if create_script:
            with console.status("📜 Creating cleanup script..."):
                script_path = manager.create_cleanup_script()
            
            console.print(f"📜 Cleanup script created: {script_path}", style="green")
            console.print("   Run with: bash scripts/cleanup_build_artifacts.sh")
            return
        
        # 扫描构建产物
        with console.status("🔍 Scanning build artifacts..."):
            artifacts = manager.scan_artifacts()
            summary = manager.get_artifacts_summary(artifacts)
        
        # 显示扫描结果
        console.print("🔍 Build Artifacts Scan Results:", style="cyan")
        
        # 创建汇总表格
        table = Table(title="Build Artifacts Summary")
        table.add_column("Category", style="cyan")
        table.add_column("Count", style="yellow")
        table.add_column("Size", style="green")
        table.add_column("Sample Paths", style="white")
        
        total_count = 0
        total_size = 0
        
        for category, info in summary.items():
            if info['count'] > 0:
                total_count += info['count']
                total_size += info['total_size']
                
                # 只有在详细模式或该类别将被清理时才显示路径样本
                sample_paths = ""
                if verbose or (category_list is None or category in (category_list or [])):
                    sample_files = info.get('sample_files', [])[:2]
                    sample_paths = ', '.join([f.name for f in sample_files])
                
                table.add_row(
                    category.replace('_', ' ').title(),
                    str(info['count']),
                    info['size_formatted'],
                    sample_paths
                )
        
        console.print(table)
        console.print(f"\n📊 Total: {total_count} items ({format_size(total_size)})")
        
        # 应用时间过滤提示
        if older_than_days:
            console.print(f"⏰ Filtering: Only items older than {older_than_days} days", style="yellow")
        
        # 如果没有找到任何构建产物
        if total_count == 0:
            console.print("✨ No build artifacts found to clean!", style="green")
            return
        
        # 执行清理
        if not dry_run:
            # 确认操作（除非强制模式）
            if not force:
                action_desc = f"clean {category_list if category_list else 'all'} categories"
                if older_than_days:
                    action_desc += f" (older than {older_than_days} days)"
                
                confirm = typer.confirm(f"🗑️ Proceed to {action_desc}?")
                if not confirm:
                    console.print("❌ Operation cancelled.", style="yellow")
                    return
        
        # 执行清理
        action_desc = "preview" if dry_run else "clean"
        with console.status(f"🧹 Starting {action_desc} operation..."):
            results = manager.clean_artifacts(
                categories=category_list,
                dry_run=dry_run,
                force=force,
                older_than_days=older_than_days
            )
        
        # 显示结果
        mode_text = "Preview" if dry_run else "Cleanup"
        console.print(f"🧹 {mode_text} Results:", style="green")
        
        if results['total_files_removed'] > 0 or results['total_dirs_removed'] > 0:
            console.print(f"  📄 Files: {results['total_files_removed']}")
            console.print(f"  📁 Directories: {results['total_dirs_removed']}")
            console.print(f"  💾 Space freed: {format_size(results['total_size_freed'])}")
            
            if verbose and results['cleaned_categories']:
                detail_table = Table(title="Detailed Results")
                detail_table.add_column("Category", style="cyan")
                detail_table.add_column("Files", style="yellow")
                detail_table.add_column("Dirs", style="yellow") 
                detail_table.add_column("Size", style="green")
                
                for category, stats in results['cleaned_categories'].items():
                    detail_table.add_row(
                        category,
                        str(stats.get('files_removed', 0)),
                        str(stats.get('dirs_removed', 0)),
                        format_size(stats.get('size_freed', 0))
                    )
                
                console.print(detail_table)
        
        # 显示错误
        if results['errors']:
            console.print(f"\n⚠️ Errors occurred:", style="yellow")
            for error in results['errors'][:5]:  # Show first 5 errors
                console.print(f"  ❌ {error}", style="red")
            if len(results['errors']) > 5:
                console.print(f"  ... and {len(results['errors']) - 5} more errors")
        
        # 提供额外建议
        if not dry_run and results['total_files_removed'] > 0:
            console.print("\n💡 Tips:", style="blue")
            console.print("  • Use --dry-run to preview before cleaning")
            console.print("  • Use --update-gitignore to prevent future artifacts")
            console.print("  • Use --create-script to generate automated cleanup")
        
    except Exception as e:
        handle_command_error(e, "Build artifacts cleanup", verbose)
