"""
Package publishing commands - simplified interface for publishing packages.
支持任意包路径，不依赖特定项目结构。
"""

import typer
from typing import Optional
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.prompt import Confirm
import os

from ..core.common import handle_command_error
from ..core.base import BaseCommand


console = Console()


class PublishCommand(BaseCommand):
    """包发布命令 - 支持任意包路径"""
    
    def __init__(self):
        self.app = typer.Typer(name="publish", help="📤 发布包到 PyPI")
        self._setup_commands()
    
    def _setup_commands(self):
        self.app.command(name="opensource")(self.opensource)
        self.app.command(name="proprietary")(self.proprietary)
        self.app.command(name="info")(self.info)
    
    def opensource(
        self,
        package_path: str = typer.Argument(..., help="包路径（包含 pyproject.toml 的目录）"),
        dry_run: bool = typer.Option(True, "--dry-run/--no-dry-run", help="是否为预演模式"),
        force: bool = typer.Option(False, "--force", help="强制发布，跳过确认"),
    ):
        """📦 发布开源包 (保留源码)"""
        try:
            package_path = Path(package_path).resolve()
            
            # 验证包路径
            if not self._validate_package_path(package_path):
                raise typer.Exit(1)
            
            package_name = self._get_package_name(package_path)
            
            # 确认发布
            if not force and not dry_run:
                if not Confirm.ask(f"确认发布开源包 [bold]{package_name}[/bold] 到 PyPI?"):
                    console.print("取消发布", style="yellow")
                    raise typer.Exit(0)
            
            # 构建包（保留源码）
            result = self._build_opensource_package(package_path, package_name)
            
            if not result['success']:
                console.print(f"❌ {package_name}: 构建失败", style="red")
                raise typer.Exit(1)
            
            # 上传到 PyPI (如果不是预演模式)
            if not dry_run:
                self._upload_to_pypi(result['build_path'])
            else:
                console.print("🔍 [预演模式] 跳过上传到 PyPI", style="yellow")
            
            console.print(f"✅ {package_name}: 开源包发布完成", style="green")
        
        except Exception as e:
            handle_command_error(e, f"发布开源包失败")
    
    def proprietary(
        self,
        package_path: str = typer.Argument(..., help="包路径（包含 pyproject.toml 的目录）"),
        dry_run: bool = typer.Option(True, "--dry-run/--no-dry-run", help="是否为预演模式"),
        force: bool = typer.Option(False, "--force", help="强制发布，跳过确认"),
        output_dir: Optional[str] = typer.Option(None, "--output", help="编译输出目录"),
    ):
        """🔒 发布闭源包 (编译为字节码)"""
        try:
            package_path = Path(package_path).resolve()
            
            # 验证包路径
            if not self._validate_package_path(package_path):
                raise typer.Exit(1)
            
            package_name = self._get_package_name(package_path)
            
            # 确认发布
            if not force and not dry_run:
                if not Confirm.ask(f"确认发布闭源包 [bold]{package_name}[/bold] 到 PyPI?"):
                    console.print("取消发布", style="yellow")
                    raise typer.Exit(0)
            
            # 编译和构建包
            output_path = Path(output_dir) if output_dir else None
            result = self._build_proprietary_package(package_path, package_name, output_path)
            
            if not result['success']:
                console.print(f"❌ {package_name}: 构建失败", style="red")
                raise typer.Exit(1)
            
            # 上传到 PyPI (如果不是预演模式)
            if not dry_run:
                wheel_path = result['wheel_path']
                self._upload_wheel_file(wheel_path)
            else:
                console.print("🔍 [预演模式] 跳过上传到 PyPI", style="yellow")
            
            console.print(f"✅ {package_name}: 闭源包发布完成", style="green")
        
        except Exception as e:
            handle_command_error(e, f"发布闭源包失败")
    
    def info(self, package_path: str = typer.Argument(..., help="包路径")):
        """📊 显示包信息"""
        try:
            package_path = Path(package_path).resolve()
            
            if not self._validate_package_path(package_path):
                raise typer.Exit(1)
            
            self._show_package_info(package_path)
        
        except Exception as e:
            handle_command_error(e, "显示包信息失败")
    
    def _validate_package_path(self, package_path: Path) -> bool:
        """验证包路径"""
        if not package_path.exists():
            console.print(f"❌ 包路径不存在: {package_path}", style="red")
            return False
        
        if not package_path.is_dir():
            console.print(f"❌ 路径不是目录: {package_path}", style="red")
            return False
        
        # 检查必要文件
        pyproject_file = package_path / "pyproject.toml"
        setup_file = package_path / "setup.py"
        
        if not pyproject_file.exists() and not setup_file.exists():
            console.print(f"❌ 未找到 pyproject.toml 或 setup.py: {package_path}", style="red")
            return False
        
        # 检查源码目录
        src_dir = package_path / "src"
        if not src_dir.exists():
            console.print(f"❌ 未找到 src/ 目录: {package_path}", style="red")
            return False
        
        console.print(f"✅ 包路径验证通过: {package_path}", style="green")
        return True
    
    def _get_package_name(self, package_path: Path) -> str:
        """获取包名"""
        pyproject_file = package_path / "pyproject.toml"
        
        if pyproject_file.exists():
            try:
                import tomli
                with open(pyproject_file, 'rb') as f:
                    data = tomli.load(f)
                
                project = data.get('project', {})
                name = project.get('name')
                if name:
                    return name
            except Exception:
                pass
        
        # 如果无法从配置文件读取，使用目录名
        return package_path.name
    
    def _build_opensource_package(self, package_path: Path, package_name: str) -> dict:
        """构建开源包（保留源码）"""
        console.print(f"📦 构建开源包: {package_name}", style="green")
        console.print(f"  路径: {package_path}")
        
        # 保存当前目录
        original_cwd = Path.cwd()
        
        try:
            # 进入包目录
            os.chdir(package_path)
            
            # 清理旧构建
            self._clean_build_dirs(package_path)
            
            # 构建 wheel
            console.print("  🔨 构建wheel包...")
            import subprocess
            import sys
            
            result = subprocess.run([
                sys.executable, "-m", "build", "--wheel"
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                console.print(f"  ❌ 构建失败: {result.stderr}", style="red")
                return {'success': False}
            
            console.print("  ✅ 构建成功", style="green")
            
            # 显示构建结果
            dist_dir = package_path / "dist"
            wheel_files = list(dist_dir.glob("*.whl"))
            
            if wheel_files:
                wheel_file = wheel_files[0]
                file_size = wheel_file.stat().st_size / 1024 / 1024
                console.print(f"    📄 {wheel_file.name} ({file_size:.2f} MB)")
            
            return {
                'success': True,
                'type': 'opensource',
                'package_name': package_name,
                'package_path': package_path,
                'build_path': dist_dir
            }
        
        except Exception as e:
            console.print(f"  💥 构建异常: {e}", style="red")
            return {'success': False}
        
        finally:
            os.chdir(original_cwd)
    
    def _build_proprietary_package(
        self, 
        package_path: Path, 
        package_name: str,
        output_dir: Optional[Path] = None
    ) -> dict:
        """构建闭源包（编译为字节码）"""
        from ...core.bytecode_compiler import BytecodeCompiler
        
        console.print(f"🔒 构建闭源包: {package_name}", style="yellow")
        console.print(f"  源路径: {package_path}")
        
        try:
            # 编译包
            compiler = BytecodeCompiler(package_path)
            compiled_path = compiler.compile_package(output_dir, use_sage_home=False)
            
            console.print(f"  📁 编译路径: {compiled_path}")
            
            # 构建 wheel
            wheel_path = compiler.build_wheel(compiled_path)
            
            console.print(f"  ✅ 闭源包构建完成", style="green")
            
            return {
                'success': True,
                'type': 'proprietary', 
                'package_name': package_name,
                'package_path': package_path,
                'compiled_path': compiled_path,
                'wheel_path': wheel_path
            }
            
        except Exception as e:
            # 显示详细的错误信息
            error_msg = str(e)
            console.print(f"  💥 构建异常: {error_msg}", style="red")
            
            # 如果是构建错误，尝试显示更多调试信息
            if "构建失败" in error_msg or "parse" in error_msg.lower():
                console.print("  🔍 调试提示:", style="yellow")
                console.print(f"    - 包路径: {package_path}", style="dim")
                
                # 检查是否是编译阶段的问题
                if 'compiled_path' in locals():
                    console.print(f"    - 编译路径: {compiled_path}", style="dim")
                    
                    # 检查编译后的pyproject.toml
                    compiled_pyproject = compiled_path / "pyproject.toml"
                    if compiled_pyproject.exists():
                        console.print("    - 编译后的pyproject.toml存在", style="dim")
                        # 检查是否有语法错误提示
                        if "parse" in error_msg.lower() or "declare" in error_msg.lower():
                            console.print("    - 💡 可能是pyproject.toml配置重复或语法错误", style="yellow")
                    else:
                        console.print("    - ⚠️ 编译后的pyproject.toml不存在", style="yellow")
                else:
                    console.print("    - 编译路径: 编译未完成", style="dim")
            
            return {'success': False, 'error': error_msg}
    
    def _clean_build_dirs(self, package_path: Path):
        """清理构建目录"""
        import shutil
        
        build_dirs = ["dist", "build", "*.egg-info"]
        
        for pattern in build_dirs:
            if "*" in pattern:
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
    
    def _show_package_info(self, package_path: Path):
        """显示包信息"""
        package_name = self._get_package_name(package_path)
        
        console.print(f"📦 包信息: [bold]{package_name}[/bold]")
        console.print(f"  路径: {package_path}")
        
        # 显示 pyproject.toml 信息
        pyproject_file = package_path / "pyproject.toml"
        if pyproject_file.exists():
            try:
                import tomli
                with open(pyproject_file, 'rb') as f:
                    data = tomli.load(f)
                
                project = data.get('project', {})
                console.print(f"  名称: {project.get('name', '未知')}")
                console.print(f"  版本: {project.get('version', '未知')}")
                console.print(f"  描述: {project.get('description', '无')}")
                
                dependencies = project.get('dependencies', [])
                console.print(f"  依赖: {len(dependencies)} 个")
                
            except Exception as e:
                console.print(f"  ⚠️ 无法读取 pyproject.toml: {e}", style="yellow")
        
        # 显示目录结构
        src_dir = package_path / "src"
        if src_dir.exists():
            python_files = list(src_dir.rglob("*.py"))
            console.print(f"  Python文件: {len(python_files)} 个")
        
        # 显示构建状态
        dist_dir = package_path / "dist"
        if dist_dir.exists():
            files = list(dist_dir.iterdir())
            build_count = len([f for f in files if f.is_file()])
            console.print(f"  构建文件: {build_count} 个")
        else:
            console.print(f"  构建文件: 0 个")
    
    def _upload_to_pypi(self, build_path: Path):
        """上传到PyPI"""
        import subprocess
        
        console.print("🚀 上传到 PyPI...")
        
        try:
            # 查找wheel文件
            wheel_files = list(build_path.glob("*.whl"))
            if not wheel_files:
                raise RuntimeError("未找到wheel文件")
            
            # 上传
            for wheel_file in wheel_files:
                result = subprocess.run([
                    "twine", "upload", str(wheel_file)
                ], capture_output=True, text=True)
                
                if result.returncode == 0:
                    console.print(f"  ✅ {wheel_file.name} 上传成功", style="green")
                else:
                    error_msg = result.stderr or result.stdout or "未知错误"
                    console.print(f"  ❌ {wheel_file.name} 上传失败: {error_msg}", style="red")
                    raise RuntimeError(f"上传失败: {error_msg}")
        
        except FileNotFoundError:
            console.print("❌ 未找到twine工具，请先安装: pip install twine", style="red")
            raise
        except Exception as e:
            console.print(f"💥 上传异常: {e}", style="red")
            raise
    
    def _upload_wheel_file(self, wheel_path: Path):
        """上传单个wheel文件"""
        import subprocess
        
        console.print(f"🚀 上传 wheel 文件: {wheel_path.name}")
        
        try:
            result = subprocess.run([
                "twine", "upload", str(wheel_path)
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                console.print(f"  ✅ {wheel_path.name} 上传成功", style="green")
            else:
                error_msg = result.stderr or result.stdout or "未知错误"
                console.print(f"  ❌ {wheel_path.name} 上传失败: {error_msg}", style="red")
                raise RuntimeError(f"上传失败: {error_msg}")
        
        except FileNotFoundError:
            console.print("❌ 未找到twine工具，请先安装: pip install twine", style="red")
            raise
        except Exception as e:
            console.print(f"💥 上传异常: {e}", style="red")
            raise


# 导出命令实例
command = PublishCommand()
