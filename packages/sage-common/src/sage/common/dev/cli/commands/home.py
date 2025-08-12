"""
SAGE home directory management commands.

Includes: home command.
"""

import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import typer

from .common import (
    console, format_size,
    PROJECT_ROOT_OPTION
)

app = typer.Typer(name="home", help="SAGE home directory management")


@app.command("home")
def home_command(
    action: str = typer.Argument(help="Action: setup, status, clean, logs"),
    project_root: Optional[str] = PROJECT_ROOT_OPTION,
    force: bool = typer.Option(False, "--force", "-f", help="Force operation without confirmation"),
    days: int = typer.Option(7, "--days", "-d", help="Clean logs older than specified days"),
    log_type: Optional[str] = typer.Option(None, "--type", "-t", help="Log type filter: test, jobmanager, toolkit, all")
):
    """🏠 Manage SAGE home directory (~/.sage/) and logs."""
    
    try:
        # 使用直接路径而不是get_toolkit避免循环导入
        if project_root:
            project_path = Path(project_root).resolve()
        else:
            # 从当前目录开始向上查找项目根目录
            current = Path.cwd()
            while current != current.parent:
                if (current / "pyproject.toml").exists() or (current / "setup.py").exists():
                    project_path = current
                    break
                current = current.parent
            else:
                project_path = Path.cwd()
        
        project_name = project_path.name
        
        # 实际的SAGE家目录在用户目录下
        real_sage_home = Path.home() / ".sage"
        # 项目中的软链接
        project_sage_link = project_path / ".sage"
        
        if action == "setup":
            with console.status("🏗️ Setting up SAGE home directory..."):
                # 1. 创建用户家目录下的.sage目录
                real_sage_home.mkdir(exist_ok=True)
                
                # 2. 创建子目录
                subdirs = ["dist", "logs", "config", "cache"]
                for subdir in subdirs:
                    (real_sage_home / subdir).mkdir(exist_ok=True)
                
                # 3. 创建项目软链接
                success = _create_symlink(project_sage_link, real_sage_home)
            
            console.print("🏠 SAGE Home Directory Setup Complete!", style="green")
            console.print(f"📁 Real SAGE home: {real_sage_home}")
            console.print(f"🔗 Project symlink: {project_sage_link}")
            
            status_icon = "✅" if success else "❌"
            console.print(f"\n🔗 Setup result:")
            console.print(f"  {status_icon} ~/.sage/ -> Real home directory")
            console.print(f"  {status_icon} .sage/ -> Symlink to ~/.sage/")
        
        elif action == "status":
            with console.status("📊 Checking SAGE home status..."):
                real_exists = real_sage_home.exists()
                link_exists = project_sage_link.exists()
                link_valid = link_exists and project_sage_link.is_symlink() and project_sage_link.resolve() == real_sage_home
            
            console.print("📊 SAGE Home Status:", style="cyan")
            console.print(f"📁 Real SAGE home: {real_sage_home}")
            console.print(f"🔗 Project symlink: {project_sage_link}")
            
            # Check real directory status
            if real_exists:
                subdirs = ["dist", "logs", "config", "cache"]
                existing_subdirs = [d for d in subdirs if (real_sage_home / d).exists()]
                console.print(f"✅ Real home exists with {len(existing_subdirs)}/{len(subdirs)} subdirectories")
            else:
                console.print("❌ Real home directory does not exist")
            
            # Check symlink status
            if link_valid:
                console.print("✅ Project symlink is valid")
            elif link_exists:
                console.print("⚠️ Project symlink exists but is invalid")
            else:
                console.print("❌ Project symlink does not exist")
        
        elif action == "clean":
            _clean_logs(real_sage_home, force, days, log_type)
        
        elif action == "logs":
            _show_logs_info(real_sage_home)
        
        else:
            console.print(f"❌ Unknown action: {action}", style="red")
            console.print("Available actions: setup, status, clean, logs")
            raise typer.Exit(1)
            
    except Exception as e:
        console.print(f"❌ SAGE home management failed: {e}", style="red")
        raise typer.Exit(1)


def _create_symlink(link_path: Path, target_path: Path) -> bool:
    """Create a symlink from link_path to target_path."""
    try:
        # Remove existing link if it exists
        if link_path.exists() or link_path.is_symlink():
            link_path.unlink()
        
        # Create the symlink
        link_path.symlink_to(target_path)
        return True
    except Exception as e:
        console.print(f"⚠️ Failed to create symlink: {e}", style="yellow")
        return False


def _clean_logs(sage_home: Path, force: bool, days: int, log_type: Optional[str] = None):
    """Clean logs from SAGE home directory."""
    logs_dir = sage_home / "logs"
    if not logs_dir.exists():
        console.print("📁 No logs directory found.", style="yellow")
        return
    
    # Calculate cutoff time
    cutoff_time = time.time() - (days * 24 * 3600)
    cutoff_date = datetime.fromtimestamp(cutoff_time)
    
    console.print(f"🗂️ Scanning logs directory: {logs_dir}")
    console.print(f"📅 Cleaning logs older than {days} days (before {cutoff_date.strftime('%Y-%m-%d %H:%M:%S')})")
    
    # Collect files to clean
    files_to_clean = []
    total_size = 0
    
    for item in logs_dir.rglob("*"):
        if item.is_file():
            # Check file age
            file_mtime = item.stat().st_mtime
            if file_mtime < cutoff_time:
                # Apply log type filter if specified
                if log_type and log_type != "all":
                    if not any(pattern in item.name for pattern in _get_log_patterns(log_type)):
                        continue
                
                file_size = item.stat().st_size
                files_to_clean.append((item, file_size))
                total_size += file_size
    
    # Also collect empty directories
    dirs_to_clean = []
    for item in logs_dir.rglob("*"):
        if item.is_dir() and not any(item.iterdir()):  # Empty directory
            dir_mtime = item.stat().st_mtime
            if dir_mtime < cutoff_time:
                dirs_to_clean.append(item)
    
    if not files_to_clean and not dirs_to_clean:
        console.print("✨ No old log files to clean.", style="green")
        return
    
    # Show summary
    console.print(f"🧹 Found {len(files_to_clean)} old log files ({format_size(total_size)}) and {len(dirs_to_clean)} empty directories")
    
    # Show files to be cleaned if not too many
    if len(files_to_clean) <= 10:
        for file_path, size in files_to_clean:
            rel_path = file_path.relative_to(logs_dir)
            age_days = (time.time() - file_path.stat().st_mtime) / (24 * 3600)
            console.print(f"  📄 {rel_path} ({format_size(size)}, {age_days:.1f} days old)")
    else:
        console.print(f"  📄 {len(files_to_clean)} files total...")
    
    # Ask for confirmation unless force is specified
    if not force:
        confirm = typer.confirm(f"🗑️ Delete {len(files_to_clean)} files and {len(dirs_to_clean)} directories?")
        if not confirm:
            console.print("❌ Operation cancelled.", style="yellow")
            return
    
    # Clean files
    cleaned_files = 0
    cleaned_size = 0
    failed_files = []
    
    with console.status("🧹 Cleaning log files..."):
        for file_path, size in files_to_clean:
            try:
                file_path.unlink()
                cleaned_files += 1
                cleaned_size += size
            except Exception as e:
                failed_files.append((file_path, str(e)))
        
        # Clean empty directories
        for dir_path in dirs_to_clean:
            try:
                dir_path.rmdir()
            except Exception as e:
                failed_files.append((dir_path, str(e)))
    
    # Report results
    console.print(f"✅ Cleaned {cleaned_files} log files ({format_size(cleaned_size)})", style="green")
    
    if failed_files:
        console.print(f"⚠️ Failed to clean {len(failed_files)} items:", style="yellow")
        for path, error in failed_files[:5]:  # Show first 5 failures
            console.print(f"  ❌ {path.name}: {error}")
        if len(failed_files) > 5:
            console.print(f"  ... and {len(failed_files) - 5} more")


def _show_logs_info(sage_home: Path):
    """Show information about logs in SAGE home directory."""
    logs_dir = sage_home / "logs"
    if not logs_dir.exists():
        console.print("📁 No logs directory found.", style="yellow")
        return
    
    console.print("📊 SAGE Logs Information", style="cyan")
    console.print(f"📁 Logs directory: {logs_dir}")
    
    # Categorize log files
    categories = {
        'test': {'files': [], 'size': 0},
        'jobmanager': {'files': [], 'size': 0},
        'toolkit': {'files': [], 'size': 0},
        'other': {'files': [], 'size': 0}
    }
    
    total_files = 0
    total_size = 0
    oldest_file = None
    newest_file = None
    
    # Scan all files
    for item in logs_dir.rglob("*"):
        if item.is_file():
            file_size = item.stat().st_size
            file_mtime = item.stat().st_mtime
            
            total_files += 1
            total_size += file_size
            
            # Track oldest and newest
            if oldest_file is None or file_mtime < oldest_file[1]:
                oldest_file = (item, file_mtime)
            if newest_file is None or file_mtime > newest_file[1]:
                newest_file = (item, file_mtime)
            
            # Categorize
            if any(pattern in item.name for pattern in ["test_", "_test", "packages_"]):
                categories['test']['files'].append(item)
                categories['test']['size'] += file_size
            elif "jobmanager" in str(item.parent) or "jobmanager" in item.name:
                categories['jobmanager']['files'].append(item)
                categories['jobmanager']['size'] += file_size
            elif "sage_common" in item.name:
                categories['toolkit']['files'].append(item)
                categories['toolkit']['size'] += file_size
            else:
                categories['other']['files'].append(item)
                categories['other']['size'] += file_size
    
    # Show summary
    console.print(f"\n📈 Summary:")
    console.print(f"  📄 Total files: {total_files}")
    console.print(f"  💾 Total size: {format_size(total_size)}")
    
    if oldest_file and newest_file:
        oldest_date = datetime.fromtimestamp(oldest_file[1])
        newest_date = datetime.fromtimestamp(newest_file[1])
        age_days = (newest_file[1] - oldest_file[1]) / (24 * 3600)
        console.print(f"  📅 Date range: {oldest_date.strftime('%Y-%m-%d')} to {newest_date.strftime('%Y-%m-%d')} ({age_days:.1f} days)")
    
    # Show categories
    console.print(f"\n📊 By Category:")
    for category, data in categories.items():
        if data['files']:
            icon = {"test": "🧪", "jobmanager": "📋", "toolkit": "🔧", "other": "📄"}[category]
            console.print(f"  {icon} {category.title()}: {len(data['files'])} files ({format_size(data['size'])})")
    
    # Show recent files (last 5)
    recent_files = sorted(
        [item for item in logs_dir.rglob("*") if item.is_file()],
        key=lambda x: x.stat().st_mtime,
        reverse=True
    )[:5]
    
    if recent_files:
        console.print(f"\n🕐 Recent files:")
        for item in recent_files:
            rel_path = item.relative_to(logs_dir)
            file_time = datetime.fromtimestamp(item.stat().st_mtime)
            file_size = format_size(item.stat().st_size)
            console.print(f"  📄 {rel_path} ({file_size}, {file_time.strftime('%Y-%m-%d %H:%M')})")


def _get_log_patterns(log_type: str):
    """Get file name patterns for different log types."""
    patterns = {
        'test': ["test_", "_test", "packages_"],
        'jobmanager': ["jobmanager"],
        'toolkit': ["sage_common"],
    }
    return patterns.get(log_type, [])
