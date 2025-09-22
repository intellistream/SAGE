"""
PyPI management commands - basic PyPI operations and package management.
"""

import typer
from typing import Optional
from pathlib import Path
from rich.console import Console
from rich.table import Table

from ..core.common import get_toolkit, handle_command_error
from ..core.base import BaseCommand


console = Console()


class PyPICommand(BaseCommand):
    """PyPI 基础管理命令"""
    
    def __init__(self):
        self.app = typer.Typer(name="pypi", help="🐍 PyPI 包管理基础工具")
        self._setup_commands()
    
    def _setup_commands(self):
        self.app.command(name="check")(self.check)
        self.app.command(name="build")(self.build)
        self.app.command(name="info")(self.info)
        self.app.command(name="clean")(self.clean)
    
    def check(self, package: Optional[str] = typer.Argument(None, help="要检查的包名")):
        """🔍 检查包配置和状态"""
        try:
            toolkit = get_toolkit()
            
            if package:
                # 检查指定包
                self._check_package_config(toolkit, package)
            else:
                # 检查所有包
                self._check_all_packages(toolkit)
        
        except Exception as e:
            handle_command_error(e, "检查包配置失败")
    
    def build(
        self,
        package: str = typer.Argument(..., help="要构建的包名"),
        wheel_only: bool = typer.Option(False, "--wheel-only", help="只构建wheel包"),
        clean: bool = typer.Option(True, "--clean/--no-clean", help="构建前清理")
    ):
        """🔨 构建包 (不编译源码)"""
        try:
            toolkit = get_toolkit()
            package_path = self._get_package_path(toolkit, package)
            
            console.print(f"🔨 构建包: [bold]{package}[/bold]")
            console.print(f"  路径: {package_path}")
            
            # 保存当前目录
            import os
            original_dir = Path.cwd()
            
            try:
                os.chdir(package_path)
                
                # 清理旧构建 (如果需要)
                if clean:
                    self._clean_build_dirs(package_path)
                
                # 构建包
                self._build_package(wheel_only)
                
                # 显示构建结果
                self._show_build_results(package_path)
                
                console.print(f"✅ {package}: 构建完成", style="green")
            
            finally:
                os.chdir(original_dir)
        
        except Exception as e:
            handle_command_error(e, f"构建包 {package} 失败")
    
    def info(self, package: Optional[str] = typer.Argument(None, help="显示指定包信息")):
        """📊 显示包信息"""
        try:
            toolkit = get_toolkit()
            
            if package:
                self._show_package_info(toolkit, package)
            else:
                self._show_all_packages_info(toolkit)
        
        except Exception as e:
            handle_command_error(e, "显示包信息失败")
    
    def clean(
        self,
        package: Optional[str] = typer.Argument(None, help="要清理的包名"),
        all_packages: bool = typer.Option(False, "--all", help="清理所有包")
    ):
        """🧹 清理构建文件"""
        try:
            toolkit = get_toolkit()
            
            if all_packages:
                self._clean_all_packages(toolkit)
            elif package:
                self._clean_single_package(toolkit, package)
            else:
                console.print("请指定包名或使用 --all 清理所有包", style="yellow")
        
        except Exception as e:
            handle_command_error(e, "清理构建文件失败")
    
    def _check_package_config(self, toolkit, package_name: str):
        """检查单个包的配置"""
        packages = toolkit.config.get('packages', {})
        
        if package_name not in packages:
            console.print(f"❌ 未找到包: {package_name}", style="red")
            console.print("可用的包:")
            for name in packages:
                console.print(f"  - {name}")
            return
        
        package_path = toolkit.project_root / packages[package_name]
        
        console.print(f"📦 包配置检查: [bold]{package_name}[/bold]")
        console.print(f"  路径: {package_path}")
        console.print(f"  存在: {'✅' if package_path.exists() else '❌'}")
        
        # 检查关键文件
        key_files = ['pyproject.toml', 'setup.py', 'setup.cfg']
        for file in key_files:
            file_path = package_path / file
            if file_path.exists():
                console.print(f"  {file}: ✅")
                
                # 显示pyproject.toml的基本信息
                if file == 'pyproject.toml':
                    self._show_pyproject_info(file_path)
            else:
                console.print(f"  {file}: ❌")
        
        # 检查src目录
        src_dir = package_path / "src"
        if src_dir.exists():
            console.print(f"  src/: ✅")
            python_files = list(src_dir.rglob("*.py"))
            console.print(f"  Python文件: {len(python_files)}")
        else:
            console.print(f"  src/: ❌")
    
    def _check_all_packages(self, toolkit):
        """检查所有包的配置"""
        packages = toolkit.config.get('packages', {})
        
        if not packages:
            console.print("未找到任何包配置", style="yellow")
            return
        
        # 创建检查结果表格
        table = Table(title="📋 包配置检查结果")
        table.add_column("包名", style="cyan")
        table.add_column("路径存在", style="green")
        table.add_column("配置文件", style="blue")
        table.add_column("源码目录", style="yellow")
        
        for name, rel_path in packages.items():
            package_path = toolkit.project_root / rel_path
            exists = "✅" if package_path.exists() else "❌"
            
            # 检查配置文件
            config_files = []
            for file in ['pyproject.toml', 'setup.py']:
                if (package_path / file).exists():
                    config_files.append(file)
            config_status = ", ".join(config_files) if config_files else "无"
            
            # 检查src目录
            src_status = "✅" if (package_path / "src").exists() else "❌"
            
            table.add_row(name, exists, config_status, src_status)
        
        console.print(table)
    
    def _get_package_path(self, toolkit, package_name: str) -> Path:
        """获取包路径"""
        packages = toolkit.config.get('packages', {})
        
        if package_name not in packages:
            raise ValueError(f"未知的包名: {package_name}")
        
        return toolkit.project_root / packages[package_name]
    
    def _clean_build_dirs(self, package_path: Path):
        """清理构建目录"""
        import shutil
        
        build_dirs = ["dist", "build", "*.egg-info"]
        
        for pattern in build_dirs:
            if "*" in pattern:
                # 处理通配符模式
                import glob
                matches = glob.glob(str(package_path / pattern))
                for match in matches:
                    match_path = Path(match)
                    if match_path.is_dir():
                        console.print(f"  🧹 清理目录: {match_path.name}")
                        shutil.rmtree(match_path)
            else:
                dir_path = package_path / pattern
                if dir_path.exists():
                    console.print(f"  🧹 清理目录: {pattern}")
                    shutil.rmtree(dir_path)
    
    def _build_package(self, wheel_only: bool = False):
        """构建包"""
        import subprocess
        import sys
        
        if wheel_only:
            console.print("  🔨 构建wheel包...")
            cmd = [sys.executable, "-m", "build", "--wheel"]
        else:
            console.print("  🔨 构建源码包和wheel包...")
            cmd = [sys.executable, "-m", "build"]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise RuntimeError(f"构建失败: {result.stderr}")
        
        console.print("  ✅ 构建成功", style="green")
    
    def _show_build_results(self, package_path: Path):
        """显示构建结果"""
        dist_dir = package_path / "dist"
        
        if not dist_dir.exists():
            console.print("  📦 构建目录不存在", style="yellow")
            return
        
        # 列出所有构建文件
        files = list(dist_dir.iterdir())
        if not files:
            console.print("  📦 构建目录为空", style="yellow")
            return
        
        console.print(f"  📦 构建文件 ({len(files)}):")
        for file in sorted(files):
            if file.is_file():
                size_mb = file.stat().st_size / 1024 / 1024
                console.print(f"    📄 {file.name} ({size_mb:.2f} MB)")
    
    def _show_package_info(self, toolkit, package_name: str):
        """显示单个包的详细信息"""
        try:
            package_path = self._get_package_path(toolkit, package_name)
            
            console.print(f"📦 包信息: [bold]{package_name}[/bold]")
            console.print(f"  路径: {package_path}")
            
            # 显示pyproject.toml信息
            pyproject_path = package_path / "pyproject.toml"
            if pyproject_path.exists():
                self._show_pyproject_info(pyproject_path)
            
            # 显示构建信息
            dist_dir = package_path / "dist"
            if dist_dir.exists():
                files = list(dist_dir.iterdir())
                console.print(f"  构建文件: {len(files)}")
                for file in sorted(files)[-3:]:  # 显示最新的3个文件
                    if file.is_file():
                        console.print(f"    📄 {file.name}")
            else:
                console.print("  构建文件: 0")
        
        except ValueError as e:
            console.print(f"❌ {e}", style="red")
    
    def _show_all_packages_info(self, toolkit):
        """显示所有包的信息"""
        packages = toolkit.config.get('packages', {})
        
        if not packages:
            console.print("未找到任何包", style="yellow")
            return
        
        # 创建信息表格
        table = Table(title="📊 所有包信息")
        table.add_column("包名", style="cyan")
        table.add_column("路径", style="blue")
        table.add_column("构建文件", style="green")
        table.add_column("大小", style="yellow")
        
        for name, rel_path in packages.items():
            package_path = toolkit.project_root / rel_path
            
            # 统计构建文件
            dist_dir = package_path / "dist"
            if dist_dir.exists():
                files = list(dist_dir.iterdir())
                file_count = len([f for f in files if f.is_file()])
                
                # 计算总大小
                total_size = sum(f.stat().st_size for f in files if f.is_file())
                size_mb = total_size / 1024 / 1024 if total_size > 0 else 0
                size_str = f"{size_mb:.1f} MB" if size_mb > 0 else "0"
            else:
                file_count = 0
                size_str = "0"
            
            table.add_row(
                name,
                str(package_path.relative_to(toolkit.project_root)),
                str(file_count),
                size_str
            )
        
        console.print(table)
    
    def _show_pyproject_info(self, pyproject_path: Path):
        """显示pyproject.toml的基本信息"""
        try:
            import tomli
            
            with open(pyproject_path, 'rb') as f:
                data = tomli.load(f)
            
            # 显示项目信息
            project = data.get('project', {})
            if project:
                name = project.get('name', '未知')
                version = project.get('version', '未知')
                console.print(f"    名称: {name}")
                console.print(f"    版本: {version}")
        
        except Exception:
            console.print("    ⚠️ 无法读取pyproject.toml")
    
    def _clean_single_package(self, toolkit, package_name: str):
        """清理单个包的构建文件"""
        try:
            package_path = self._get_package_path(toolkit, package_name)
            console.print(f"🧹 清理包: [bold]{package_name}[/bold]")
            self._clean_build_dirs(package_path)
            console.print(f"✅ {package_name}: 清理完成", style="green")
        except ValueError as e:
            console.print(f"❌ {e}", style="red")
    
    def _clean_all_packages(self, toolkit):
        """清理所有包的构建文件"""
        packages = toolkit.config.get('packages', {})
        
        if not packages:
            console.print("未找到任何包", style="yellow")
            return
        
        console.print(f"🧹 清理所有包构建文件...")
        
        cleaned_count = 0
        for name, rel_path in packages.items():
            package_path = toolkit.project_root / rel_path
            if package_path.exists():
                console.print(f"  清理: {name}")
                self._clean_build_dirs(package_path)
                cleaned_count += 1
        
        console.print(f"✅ 已清理 {cleaned_count} 个包", style="green")


# 导出命令实例
command = PyPICommand()
