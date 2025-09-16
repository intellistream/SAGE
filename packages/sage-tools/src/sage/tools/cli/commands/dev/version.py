"""
SAGE Dev Version Management Command

This module provides commands to manage version.py files across all SAGE subpackages.
"""

import re
import typer
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()
app = typer.Typer(help="🏷️ 版本管理 - 管理各个子包的版本信息")


def find_version_files(root_path: Path) -> Dict[str, Path]:
    """查找所有的_version.py文件"""
    version_files = {}
    packages_dir = root_path / "packages"
    
    if not packages_dir.exists():
        console.print(f"[red]❌ packages目录不存在: {packages_dir}[/red]")
        return version_files
    
    for package_dir in packages_dir.iterdir():
        if package_dir.is_dir() and not package_dir.name.startswith('.'):
            # 查找_version.py文件
            version_file_patterns = [
                package_dir / "src" / "sage" / "_version.py",
                package_dir / "src" / "sage" / package_dir.name.replace('-', '/') / "_version.py",
            ]
            
            # 为sage-kernel特殊处理
            if package_dir.name == "sage-kernel":
                version_file_patterns.append(package_dir / "src" / "sage" / "kernel" / "_version.py")
            elif package_dir.name == "sage-common":
                version_file_patterns.append(package_dir / "src" / "sage" / "common" / "_version.py")
            elif package_dir.name == "sage-libs":
                version_file_patterns.append(package_dir / "src" / "sage" / "libs" / "_version.py")
            elif package_dir.name == "sage-middleware":
                version_file_patterns.append(package_dir / "src" / "sage" / "middleware" / "_version.py")
            elif package_dir.name == "sage-tools":
                version_file_patterns.append(package_dir / "src" / "sage" / "tools" / "_version.py")
            
            for version_file in version_file_patterns:
                if version_file.exists():
                    version_files[package_dir.name] = version_file
                    break
    
    return version_files


def read_version_info(version_file: Path) -> Dict[str, str]:
    """从_version.py文件中读取版本信息"""
    try:
        content = version_file.read_text(encoding='utf-8')
        
        version_match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
        author_match = re.search(r'__author__\s*=\s*["\']([^"\']+)["\']', content)
        email_match = re.search(r'__email__\s*=\s*["\']([^"\']+)["\']', content)
        
        return {
            'version': version_match.group(1) if version_match else 'unknown',
            'author': author_match.group(1) if author_match else 'unknown',
            'email': email_match.group(1) if email_match else 'unknown'
        }
    except Exception as e:
        console.print(f"[red]❌ 读取版本文件失败 {version_file}: {e}[/red]")
        return {'version': 'error', 'author': 'error', 'email': 'error'}


def update_version_file(version_file: Path, new_version: str, author: str = None, email: str = None) -> bool:
    """更新_version.py文件中的版本信息"""
    try:
        content = version_file.read_text(encoding='utf-8')
        
        # 更新版本号
        content = re.sub(r'(__version__\s*=\s*["\'])([^"\']+)(["\'])', 
                        rf'\g<1>{new_version}\g<3>', content)
        
        # 如果提供了作者信息，也更新
        if author:
            content = re.sub(r'(__author__\s*=\s*["\'])([^"\']+)(["\'])', 
                            rf'\g<1>{author}\g<3>', content)
        
        # 如果提供了邮箱信息，也更新
        if email:
            content = re.sub(r'(__email__\s*=\s*["\'])([^"\']+)(["\'])', 
                            rf'\g<1>{email}\g<3>', content)
        
        version_file.write_text(content, encoding='utf-8')
        return True
    except Exception as e:
        console.print(f"[red]❌ 更新版本文件失败 {version_file}: {e}[/red]")
        return False


def parse_version(version_str: str) -> Tuple[int, int, int, str]:
    """解析版本号为(major, minor, patch, suffix)"""
    # 匹配形如 "0.1.3.1" 或 "0.1.3-alpha.1" 的版本号
    match = re.match(r'(\d+)\.(\d+)\.(\d+)(?:\.(\d+)|[\-\.]?(.*))?', version_str)
    if match:
        major, minor, patch, build, suffix = match.groups()
        if build:
            # 如果有第四位数字，将其作为patch的扩展
            patch_full = f"{patch}.{build}"
            return int(major), int(minor), patch_full, suffix or ""
        else:
            return int(major), int(minor), int(patch), suffix or ""
    else:
        # 如果解析失败，返回默认值
        return 0, 1, 0, ""


def increment_version(version_str: str, increment_type: str) -> str:
    """增加版本号"""
    if '.' in version_str and len(version_str.split('.')) >= 4:
        # 处理四位版本号，如 "0.1.3.1"
        parts = version_str.split('.')
        major, minor, patch, build = int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3])
        
        if increment_type == "major":
            return f"{major + 1}.0.0.0"
        elif increment_type == "minor":
            return f"{major}.{minor + 1}.0.0"
        elif increment_type == "patch":
            return f"{major}.{minor}.{patch + 1}.0"
        elif increment_type == "build":
            return f"{major}.{minor}.{patch}.{build + 1}"
        else:
            return version_str
    else:
        # 处理三位版本号
        major, minor, patch, suffix = parse_version(version_str)
        
        if increment_type == "major":
            return f"{major + 1}.0.0{('.' + suffix) if suffix else ''}"
        elif increment_type == "minor":
            return f"{major}.{minor + 1}.0{('.' + suffix) if suffix else ''}"
        elif increment_type == "patch":
            return f"{major}.{minor}.{patch + 1}{('.' + suffix) if suffix else ''}"
        else:
            return version_str


@app.command("list")
def list_versions(
    root: str = typer.Option(".", "--root", "-r", help="项目根目录路径")
):
    """📋 列出所有包的版本信息"""
    root_path = Path(root).resolve()
    
    console.print(Panel.fit(
        f"🔍 扫描项目版本信息\n📁 项目路径: {root_path}",
        title="Version Scanner",
        border_style="blue"
    ))
    
    version_files = find_version_files(root_path)
    
    if not version_files:
        console.print("[yellow]⚠️  未找到任何版本文件[/yellow]")
        return
    
    table = Table(title="📦 SAGE 包版本信息", show_header=True, header_style="bold magenta")
    table.add_column("包名", style="cyan", no_wrap=True)
    table.add_column("版本", style="green")
    table.add_column("作者", style="blue")
    table.add_column("邮箱", style="yellow")
    table.add_column("文件路径", style="dim")
    
    for package_name, version_file in sorted(version_files.items()):
        version_info = read_version_info(version_file)
        table.add_row(
            package_name,
            version_info['version'],
            version_info['author'],
            version_info['email'],
            str(version_file.relative_to(root_path))
        )
    
    console.print(table)


@app.command("set")
def set_version(
    new_version: str = typer.Argument(..., help="新的版本号"),
    packages: Optional[List[str]] = typer.Option(None, "--package", "-p", help="指定要更新的包名（可多次使用）"),
    root: str = typer.Option(".", "--root", "-r", help="项目根目录路径"),
    dry_run: bool = typer.Option(False, "--dry-run", help="预览模式，不实际修改文件"),
):
    """🏷️ 设置指定包的版本号"""
    root_path = Path(root).resolve()
    
    console.print(Panel.fit(
        f"🏷️ 设置版本号: {new_version}\n📁 项目路径: {root_path}",
        title="Set Version",
        border_style="green"
    ))
    
    version_files = find_version_files(root_path)
    
    if not version_files:
        console.print("[yellow]⚠️  未找到任何版本文件[/yellow]")
        return
    
    # 如果指定了包名，只更新指定的包
    if packages:
        filtered_files = {name: path for name, path in version_files.items() if name in packages}
        if not filtered_files:
            console.print(f"[red]❌ 未找到指定的包: {', '.join(packages)}[/red]")
            console.print(f"可用的包: {', '.join(version_files.keys())}")
            return
        version_files = filtered_files
    
    updated_count = 0
    for package_name, version_file in version_files.items():
        current_info = read_version_info(version_file)
        
        if dry_run:
            console.print(f"[blue]🔍 预览[/blue] {package_name}: {current_info['version']} -> {new_version}")
        else:
            if update_version_file(version_file, new_version):
                console.print(f"[green]✅ 更新[/green] {package_name}: {current_info['version']} -> {new_version}")
                updated_count += 1
            else:
                console.print(f"[red]❌ 失败[/red] {package_name}: 无法更新版本文件")
    
    if not dry_run:
        console.print(f"\n🎉 成功更新 {updated_count} 个包的版本")


@app.command("bump")
def bump_version(
    increment_type: str = typer.Argument(..., help="版本增量类型: major, minor, patch, build"),
    packages: Optional[List[str]] = typer.Option(None, "--package", "-p", help="指定要更新的包名（可多次使用）"),
    root: str = typer.Option(".", "--root", "-r", help="项目根目录路径"),
    dry_run: bool = typer.Option(False, "--dry-run", help="预览模式，不实际修改文件"),
):
    """⬆️ 增加版本号（major, minor, patch, build）"""
    if increment_type not in ["major", "minor", "patch", "build"]:
        console.print("[red]❌ 无效的增量类型，支持: major, minor, patch, build[/red]")
        raise typer.Exit(1)
    
    root_path = Path(root).resolve()
    
    console.print(Panel.fit(
        f"⬆️ 增加版本号: {increment_type}\n📁 项目路径: {root_path}",
        title="Bump Version",
        border_style="yellow"
    ))
    
    version_files = find_version_files(root_path)
    
    if not version_files:
        console.print("[yellow]⚠️  未找到任何版本文件[/yellow]")
        return
    
    # 如果指定了包名，只更新指定的包
    if packages:
        filtered_files = {name: path for name, path in version_files.items() if name in packages}
        if not filtered_files:
            console.print(f"[red]❌ 未找到指定的包: {', '.join(packages)}[/red]")
            console.print(f"可用的包: {', '.join(version_files.keys())}")
            return
        version_files = filtered_files
    
    updated_count = 0
    for package_name, version_file in version_files.items():
        current_info = read_version_info(version_file)
        current_version = current_info['version']
        new_version = increment_version(current_version, increment_type)
        
        if dry_run:
            console.print(f"[blue]🔍 预览[/blue] {package_name}: {current_version} -> {new_version}")
        else:
            if update_version_file(version_file, new_version):
                console.print(f"[green]✅ 更新[/green] {package_name}: {current_version} -> {new_version}")
                updated_count += 1
            else:
                console.print(f"[red]❌ 失败[/red] {package_name}: 无法更新版本文件")
    
    if not dry_run:
        console.print(f"\n🎉 成功更新 {updated_count} 个包的版本")


@app.command("sync")
def sync_versions(
    source_package: str = typer.Option("sage", "--source", "-s", help="源包名（作为版本参考）"),
    root: str = typer.Option(".", "--root", "-r", help="项目根目录路径"),
    dry_run: bool = typer.Option(False, "--dry-run", help="预览模式，不实际修改文件"),
):
    """🔄 同步所有包的版本到指定包的版本"""
    root_path = Path(root).resolve()
    
    console.print(Panel.fit(
        f"🔄 同步版本到 {source_package}\n📁 项目路径: {root_path}",
        title="Sync Versions",
        border_style="cyan"
    ))
    
    version_files = find_version_files(root_path)
    
    if not version_files:
        console.print("[yellow]⚠️  未找到任何版本文件[/yellow]")
        return
    
    # 获取源包的版本
    if source_package not in version_files:
        console.print(f"[red]❌ 未找到源包: {source_package}[/red]")
        console.print(f"可用的包: {', '.join(version_files.keys())}")
        return
    
    source_version_info = read_version_info(version_files[source_package])
    source_version = source_version_info['version']
    
    console.print(f"📌 源版本: {source_package} = {source_version}")
    
    updated_count = 0
    for package_name, version_file in version_files.items():
        if package_name == source_package:
            continue  # 跳过源包自身
            
        current_info = read_version_info(version_file)
        current_version = current_info['version']
        
        if current_version == source_version:
            console.print(f"[dim]⏭️  跳过[/dim] {package_name}: 版本已一致 ({current_version})")
            continue
        
        if dry_run:
            console.print(f"[blue]🔍 预览[/blue] {package_name}: {current_version} -> {source_version}")
        else:
            if update_version_file(version_file, source_version):
                console.print(f"[green]✅ 同步[/green] {package_name}: {current_version} -> {source_version}")
                updated_count += 1
            else:
                console.print(f"[red]❌ 失败[/red] {package_name}: 无法更新版本文件")
    
    if not dry_run:
        console.print(f"\n🎉 成功同步 {updated_count} 个包的版本")


if __name__ == "__main__":
    app()