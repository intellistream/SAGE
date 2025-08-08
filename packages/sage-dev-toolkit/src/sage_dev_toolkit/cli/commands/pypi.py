"""
PyPI management commands for SAGE Development Toolkit.

Includes: upload to PyPI, build and publish packages, version management.
"""

import subprocess
import tomli
from pathlib import Path
from typing import Optional, List, Dict, Any
import shutil
import os

import typer
from rich.table import Table

from .common import (
    console, get_toolkit, handle_command_error,
    PROJECT_ROOT_OPTION, CONFIG_OPTION, ENVIRONMENT_OPTION, VERBOSE_OPTION
)

app = typer.Typer(name="pypi", help="PyPI package management and upload commands")


class PyPIUploader:
    """PyPI上传管理器"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.packages_dir = project_root / "packages"
        self.config = self._load_project_config()
        
        # 定义开源包列表和映射
        self.opensource_packages = self._get_opensource_packages()
    
    def _load_project_config(self) -> dict:
        """加载项目配置文件"""
        config_path = self.project_root / "project_config.toml"
        if not config_path.exists():
            raise FileNotFoundError(f"项目配置文件不存在: {config_path}")
        
        with open(config_path, 'rb') as f:
            return tomli.load(f)
    
    def _get_opensource_packages(self) -> Dict[str, Path]:
        """获取开源包列表和路径映射"""
        packages = {}
        config_packages = self.config.get('packages', {})
        
        # 从配置文件获取开源包
        # 这里可以配置哪些包是开源的
        opensource_names = [
            "intellistream-sage-kernel",
            "intellistream-sage-middleware", 
            "intellistream-sage",
        ]
        
        for package_name in opensource_names:
            if package_name in config_packages:
                package_path = self.project_root / config_packages[package_name]
                if package_path.exists():
                    packages[package_name] = package_path
        
        return packages
    
    def check_requirements(self) -> bool:
        """检查必要工具"""
        console.print("🔍 检查必要工具...", style="blue")
        
        missing_tools = []
        
        # 检查 Python
        if not shutil.which("python3"):
            missing_tools.append("python3")
        
        # 检查构建工具
        try:
            import build
        except ImportError:
            console.print("⚠️ 缺少 build 包，正在安装...", style="yellow")
            subprocess.run(["python3", "-m", "pip", "install", "--upgrade", "build"], check=True)
        
        # 检查上传工具
        try:
            import twine
        except ImportError:
            console.print("⚠️ 缺少 twine 包，正在安装...", style="yellow")
            subprocess.run(["python3", "-m", "pip", "install", "--upgrade", "twine"], check=True)
        
        if missing_tools:
            console.print(f"❌ 缺少必要工具: {', '.join(missing_tools)}", style="red")
            return False
        
        console.print("✅ 工具检查完成", style="green")
        return True
    
    def check_package_config(self, package_path: Path, package_name: str) -> bool:
        """检查包配置"""
        console.print(f"🔍 检查包配置: {package_name}", style="blue")
        
        # 检查 pyproject.toml
        pyproject_path = package_path / "pyproject.toml"
        if not pyproject_path.exists():
            console.print(f"❌ {package_name}: 缺少 pyproject.toml 文件", style="red")
            return False
        
        # 检查版本信息
        try:
            with open(pyproject_path, 'rb') as f:
                data = tomli.load(f)
                version = data.get('project', {}).get('version', 'unknown')
            
            if version == "unknown":
                console.print(f"❌ {package_name}: 无法读取版本信息", style="red")
                return False
            
            console.print(f"📦 {package_name}: 版本 {version}", style="green")
        except Exception as e:
            console.print(f"❌ {package_name}: 读取配置失败 - {e}", style="red")
            return False
        
        # 检查 README
        readme_path = package_path / "README.md"
        if not readme_path.exists():
            console.print(f"⚠️ {package_name}: 缺少 README.md 文件", style="yellow")
        
        return True
    
    def build_package(self, package_path: Path, package_name: str, force_build: bool = False, verbose: bool = False) -> bool:
        """构建包"""
        console.print(f"🏗️ 构建包: {package_name}", style="blue")
        
        original_cwd = Path.cwd()
        try:
            os.chdir(package_path)
            
            # 清理旧的构建文件
            if force_build:
                console.print("🧹 清理旧的构建文件...", style="blue")
                for dir_to_remove in ["build", "dist", "*.egg-info", "src/*.egg-info"]:
                    for path in package_path.glob(dir_to_remove):
                        if path.is_dir():
                            shutil.rmtree(path)
                        elif path.is_file():
                            path.unlink()
            
            # 检查是否已经有构建产物
            dist_dir = package_path / "dist"
            if dist_dir.exists() and not force_build:
                wheel_files = list(dist_dir.glob("*.whl"))
                if wheel_files:
                    console.print(f"📦 {package_name}: 发现现有构建产物，跳过构建", style="green")
                    return True
            
            # 构建包
            console.print(f"🔨 {package_name}: 使用标准构建...", style="blue")
            
            cmd = ["python3", "-m", "build"]
            if verbose:
                result = subprocess.run(cmd, capture_output=False)
            else:
                result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                console.print(f"❌ {package_name}: 构建失败", style="red")
                if not verbose and result.stderr:
                    console.print(f"错误信息: {result.stderr}", style="red")
                return False
            
            # 验证构建结果
            if not dist_dir.exists():
                console.print(f"❌ {package_name}: 构建失败，未找到 dist 目录", style="red")
                return False
            
            wheel_files = list(dist_dir.glob("*.whl"))
            if not wheel_files:
                console.print(f"❌ {package_name}: 构建失败，未找到 wheel 文件", style="red")
                return False
            
            console.print(f"✅ {package_name}: 构建完成", style="green")
            return True
            
        finally:
            os.chdir(original_cwd)
    
    def validate_package(self, package_path: Path, package_name: str, verbose: bool = False) -> bool:
        """验证包"""
        console.print(f"🔍 验证包: {package_name}", style="blue")
        
        original_cwd = Path.cwd()
        try:
            os.chdir(package_path)
            
            cmd = ["python3", "-m", "twine", "check", "dist/*"]
            if verbose:
                result = subprocess.run(cmd, capture_output=False)
            else:
                result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                console.print(f"❌ {package_name}: 包验证失败", style="red")
                if not verbose and result.stderr:
                    console.print(f"错误信息: {result.stderr}", style="red")
                return False
            
            console.print(f"✅ {package_name}: 包验证通过", style="green")
            return True
            
        finally:
            os.chdir(original_cwd)
    
    def upload_package(self, package_path: Path, package_name: str, test_pypi: bool = False, 
                      dry_run: bool = False, verbose: bool = False) -> bool:
        """上传包"""
        original_cwd = Path.cwd()
        try:
            os.chdir(package_path)
            
            if dry_run:
                console.print(f"🔄 [预演] 上传包: {package_name}", style="yellow")
                console.print("📋 [预演] 文件列表:", style="yellow")
                
                dist_files = list(Path("dist").glob("*"))
                for file in dist_files:
                    console.print(f"  • {file.name}", style="cyan")
                return True
            
            target = "TestPyPI" if test_pypi else "PyPI"
            console.print(f"📤 上传包到 {target}: {package_name}", style="blue")
            
            cmd = ["python3", "-m", "twine", "upload"]
            if test_pypi:
                cmd.extend(["--repository", "testpypi"])
            cmd.append("dist/*")
            
            if verbose:
                result = subprocess.run(cmd, capture_output=False)
            else:
                result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                console.print(f"✅ {package_name}: 上传完成", style="green")
                return True
            else:
                console.print(f"❌ {package_name}: 上传失败", style="red")
                if not verbose and result.stderr:
                    console.print(f"错误信息: {result.stderr}", style="red")
                return False
                
        finally:
            os.chdir(original_cwd)


@app.command("upload")
def upload_command(
    packages: Optional[str] = typer.Argument(None, help="要上传的包名（逗号分隔），如果不指定则上传所有开源包"),
    dry_run: bool = typer.Option(True, "--dry-run", help="预演模式，不实际上传（默认启用，使用 --no-dry-run 禁用）"),
    test_pypi: bool = typer.Option(False, "--test", "-t", help="上传到 TestPyPI 而不是正式 PyPI"),
    force_build: bool = typer.Option(False, "--force", "-f", help="强制重新构建包"),
    skip_checks: bool = typer.Option(False, "--skip-checks", help="跳过预检查"),
    skip_build: bool = typer.Option(False, "--skip-build", help="跳过构建步骤，直接上传现有的包"),
    project_root: Optional[str] = PROJECT_ROOT_OPTION,
    verbose: bool = VERBOSE_OPTION
):
    """📤 上传 SAGE 包到 PyPI 或 TestPyPI"""
    
    try:
        # 确定项目根目录
        if project_root:
            project_root_path = Path(project_root)
        else:
            project_root_path = Path.cwd()
            
        uploader = PyPIUploader(project_root_path)
        
        console.print("🚀 SAGE PyPI 上传工具启动", style="bold blue")
        console.print(f"📂 工作目录: {project_root_path}", style="blue")
        
        if dry_run:
            console.print("⚠️ 预演模式：不会实际上传包", style="yellow")
        
        target = "TestPyPI" if test_pypi else "PyPI"
        console.print(f"🎯 上传目标: {target}", style="blue")
        
        # 确定要上传的包
        if packages:
            package_names = [pkg.strip() for pkg in packages.split(",")]
            # 验证包名
            invalid_packages = []
            for pkg in package_names:
                if pkg not in uploader.opensource_packages:
                    invalid_packages.append(pkg)
            
            if invalid_packages:
                console.print(f"❌ 未知的包名: {', '.join(invalid_packages)}", style="red")
                console.print(f"可用的包: {', '.join(uploader.opensource_packages.keys())}", style="blue")
                raise typer.Exit(1)
        else:
            package_names = list(uploader.opensource_packages.keys())
            console.print(f"📦 将上传所有开源包: {', '.join(package_names)}", style="blue")
        
        # 检查必要工具
        if not skip_checks:
            if not uploader.check_requirements():
                raise typer.Exit(1)
        
        # 处理每个包
        failed_packages = []
        success_packages = []
        
        for package_name in package_names:
            package_path = uploader.opensource_packages[package_name]
            
            console.print(f"\n📦 处理包: {package_name} ({package_path})", style="bold cyan")
            
            # 检查包路径是否存在
            if not package_path.exists():
                console.print(f"❌ {package_name}: 路径不存在 {package_path}", style="red")
                failed_packages.append(package_name)
                continue
            
            # 检查包配置
            if not skip_checks:
                if not uploader.check_package_config(package_path, package_name):
                    failed_packages.append(package_name)
                    continue
            
            # 构建包
            if not skip_build:
                if not uploader.build_package(package_path, package_name, force_build, verbose):
                    failed_packages.append(package_name)
                    continue
            
            # 验证包
            if not skip_checks:
                if not uploader.validate_package(package_path, package_name, verbose):
                    failed_packages.append(package_name)
                    continue
            
            # 上传包
            if not uploader.upload_package(package_path, package_name, test_pypi, dry_run, verbose):
                failed_packages.append(package_name)
                continue
            
            success_packages.append(package_name)
        
        # 显示总结
        console.print("\n📊 上传总结:", style="bold blue")
        
        if success_packages:
            console.print(f"✅ 成功处理 {len(success_packages)} 个包:", style="green")
            for package in success_packages:
                console.print(f"  ✓ {package}", style="green")
        
        if failed_packages:
            console.print(f"❌ 失败 {len(failed_packages)} 个包:", style="red")
            for package in failed_packages:
                console.print(f"  ✗ {package}", style="red")
            raise typer.Exit(1)
        
        if dry_run:
            console.print("🎭 预演完成！", style="bold yellow")
            console.print("💡 使用 --no-dry-run 进行实际上传", style="yellow")
        else:
            console.print("🎉 所有包上传完成！", style="bold green")
        
    except Exception as e:
        handle_command_error(e, "PyPI上传", verbose)


@app.command("list")
def list_packages_command(
    project_root: Optional[str] = PROJECT_ROOT_OPTION
):
    """📋 列出所有可上传的开源包"""
    
    try:
        # 确定项目根目录
        if project_root:
            project_root_path = Path(project_root)
        else:
            project_root_path = Path.cwd()
            
        uploader = PyPIUploader(project_root_path)
        
        table = Table(title="SAGE 开源包列表")
        table.add_column("包名", style="cyan", width=35)
        table.add_column("路径", style="white", width=40)
        table.add_column("状态", style="green", width=15)
        
        for package_name, package_path in uploader.opensource_packages.items():
            status = "✅ 存在" if package_path.exists() else "❌ 不存在"
            table.add_row(package_name, str(package_path.relative_to(project_root_path)), status)
        
        console.print(table)
        console.print(f"\n📊 总共 {len(uploader.opensource_packages)} 个开源包", style="blue")
        
    except Exception as e:
        handle_command_error(e, "列出包", verbose=False)


@app.command("build")
def build_command(
    packages: Optional[str] = typer.Argument(None, help="要构建的包名（逗号分隔），如果不指定则构建所有开源包"),
    force: bool = typer.Option(False, "--force", "-f", help="强制重新构建包"),
    project_root: Optional[str] = PROJECT_ROOT_OPTION,
    verbose: bool = VERBOSE_OPTION
):
    """🏗️ 构建 SAGE 包（生成 wheel 和 sdist）"""
    
    try:
        # 确定项目根目录
        if project_root:
            project_root_path = Path(project_root)
        else:
            project_root_path = Path.cwd()
            
        uploader = PyPIUploader(project_root_path)
        
        # 确定要构建的包
        if packages:
            package_names = [pkg.strip() for pkg in packages.split(",")]
            # 验证包名
            invalid_packages = []
            for pkg in package_names:
                if pkg not in uploader.opensource_packages:
                    invalid_packages.append(pkg)
            
            if invalid_packages:
                console.print(f"❌ 未知的包名: {', '.join(invalid_packages)}", style="red")
                console.print(f"可用的包: {', '.join(uploader.opensource_packages.keys())}", style="blue")
                raise typer.Exit(1)
        else:
            package_names = list(uploader.opensource_packages.keys())
        
        console.print("🏗️ SAGE 包构建工具", style="bold blue")
        console.print(f"📦 将构建 {len(package_names)} 个包", style="blue")
        
        # 检查必要工具
        if not uploader.check_requirements():
            raise typer.Exit(1)
        
        # 构建每个包
        failed_packages = []
        success_packages = []
        
        for package_name in package_names:
            package_path = uploader.opensource_packages[package_name]
            
            console.print(f"\n🔨 构建包: {package_name}", style="bold cyan")
            
            if not package_path.exists():
                console.print(f"❌ {package_name}: 路径不存在 {package_path}", style="red")
                failed_packages.append(package_name)
                continue
            
            if uploader.build_package(package_path, package_name, force, verbose):
                success_packages.append(package_name)
            else:
                failed_packages.append(package_name)
        
        # 显示总结
        console.print("\n📊 构建总结:", style="bold blue")
        
        if success_packages:
            console.print(f"✅ 成功构建 {len(success_packages)} 个包:", style="green")
            for package in success_packages:
                console.print(f"  ✓ {package}", style="green")
        
        if failed_packages:
            console.print(f"❌ 构建失败 {len(failed_packages)} 个包:", style="red")
            for package in failed_packages:
                console.print(f"  ✗ {package}", style="red")
            raise typer.Exit(1)
        
        console.print("🎉 所有包构建完成！", style="bold green")
        
    except Exception as e:
        handle_command_error(e, "包构建", verbose)


@app.command("check")
def check_command(
    packages: Optional[str] = typer.Argument(None, help="要检查的包名（逗号分隔），如果不指定则检查所有开源包"),
    project_root: Optional[str] = PROJECT_ROOT_OPTION,
    verbose: bool = VERBOSE_OPTION
):
    """🔍 检查包配置和构建产物"""
    
    try:
        # 确定项目根目录
        if project_root:
            project_root_path = Path(project_root)
        else:
            project_root_path = Path.cwd()
            
        uploader = PyPIUploader(project_root_path)
        
        # 确定要检查的包
        if packages:
            package_names = [pkg.strip() for pkg in packages.split(",")]
        else:
            package_names = list(uploader.opensource_packages.keys())
        
        console.print("🔍 SAGE 包检查工具", style="bold blue")
        
        # 检查每个包
        for package_name in package_names:
            package_path = uploader.opensource_packages[package_name]
            
            console.print(f"\n📦 检查包: {package_name}", style="bold cyan")
            
            if not package_path.exists():
                console.print(f"❌ 路径不存在: {package_path}", style="red")
                continue
            
            # 检查配置
            config_ok = uploader.check_package_config(package_path, package_name)
            
            # 检查构建产物
            dist_dir = package_path / "dist"
            if dist_dir.exists():
                wheel_files = list(dist_dir.glob("*.whl"))
                sdist_files = list(dist_dir.glob("*.tar.gz"))
                
                console.print(f"📦 构建产物:", style="blue")
                console.print(f"  • Wheel 文件: {len(wheel_files)}", style="cyan")
                console.print(f"  • Source 文件: {len(sdist_files)}", style="cyan")
                
                if wheel_files or sdist_files:
                    # 验证构建产物
                    uploader.validate_package(package_path, package_name, verbose)
            else:
                console.print("⚠️ 没有构建产物", style="yellow")
        
        console.print("\n✅ 检查完成", style="green")
        
    except Exception as e:
        handle_command_error(e, "包检查", verbose)
