"""
SAGE Bytecode Compiler
编译Python源码为.pyc文件，隐藏企业版源代码
"""

import os
import sys
import shutil
import py_compile
import tempfile
import subprocess
from pathlib import Path
from typing import List, Dict, Optional
from rich.console import Console
from rich.progress import Progress, TaskID

from .exceptions import SAGEDevToolkitError

console = Console()


class BytecodeCompiler:
    """字节码编译器 - 集成到SAGE开发工具包"""
    
    def __init__(self, package_path: Path, temp_dir: Optional[Path] = None):
        """
        初始化字节码编译器
        
        Args:
            package_path: 要编译的包路径
            temp_dir: 临时目录，如果为None则自动创建
        """
        self.package_path = Path(package_path)
        self.temp_dir = temp_dir
        self.compiled_path = None
        
        if not self.package_path.exists():
            raise SAGEDevToolkitError(f"Package path does not exist: {package_path}")
        
        if not self.package_path.is_dir():
            raise SAGEDevToolkitError(f"Package path is not a directory: {package_path}")
        
    def compile_package(self, output_dir: Optional[Path] = None, use_sage_home: bool = True) -> Path:
        """
        编译包为字节码
        
        Args:
            output_dir: 输出目录，如果为None则使用SAGE home目录或临时目录
            use_sage_home: 是否使用SAGE home目录作为默认输出
            
        Returns:
            编译后的包路径
        """
        console.print(f"🔧 编译包: {self.package_path.name}", style="cyan")
        
        # 确定输出目录
        if output_dir:
            self.temp_dir = Path(output_dir)
            self.temp_dir.mkdir(parents=True, exist_ok=True)
        elif use_sage_home:
            # 使用SAGE home目录
            sage_home = Path.home() / ".sage"
            self.temp_dir = sage_home / "dist"
            self.temp_dir.mkdir(parents=True, exist_ok=True)
            console.print(f"📁 使用SAGE home目录: {self.temp_dir}", style="blue")
        else:
            self.temp_dir = Path(tempfile.mkdtemp(
                prefix=f"sage_bytecode_{self.package_path.name}_"
            ))
        
        # 复制项目结构
        self.compiled_path = self.temp_dir / self.package_path.name
        console.print(f"📁 复制项目结构到: {self.compiled_path}")
        shutil.copytree(self.package_path, self.compiled_path)
        
        # 编译Python文件
        self._compile_python_files()
        
        # 删除.py源文件
        self._remove_source_files()
        
        # 更新pyproject.toml排除源文件
        self._update_pyproject()
        
        console.print(f"✅ 包编译完成: {self.package_path.name}", style="green")
        return self.compiled_path
    
    def _compile_python_files(self):
        """编译所有Python文件"""
        python_files = list(self.compiled_path.rglob("*.py"))
        
        # 过滤要跳过的文件
        files_to_compile = []
        for py_file in python_files:
            if self._should_skip_file(py_file):
                console.print(f"  ⏭️ 跳过: {py_file.relative_to(self.compiled_path)}", style="yellow")
                continue
            files_to_compile.append(py_file)
        
        if not files_to_compile:
            console.print("  ⚠️ 没有找到需要编译的Python文件", style="yellow")
            return
        
        console.print(f"  📝 找到 {len(files_to_compile)} 个Python文件需要编译")
        
        # 使用进度条显示编译进度
        with Progress() as progress:
            task = progress.add_task("编译Python文件", total=len(files_to_compile))
            
            compiled_count = 0
            failed_count = 0
            
            for py_file in files_to_compile:
                try:
                    # 编译为.pyc
                    pyc_file = py_file.with_suffix('.pyc')
                    py_compile.compile(py_file, pyc_file, doraise=True)
                    compiled_count += 1
                    progress.console.print(
                        f"    ✓ 编译: {py_file.relative_to(self.compiled_path)} → {pyc_file.name}",
                        style="green"
                    )
                    
                except py_compile.PyCompileError as e:
                    failed_count += 1
                    progress.console.print(
                        f"    ❌ 编译失败: {py_file.relative_to(self.compiled_path)}: {e}",
                        style="red"
                    )
                except Exception as e:
                    failed_count += 1
                    progress.console.print(
                        f"    💥 未知错误: {py_file.relative_to(self.compiled_path)}: {e}",
                        style="red"
                    )
                
                progress.update(task, advance=1)
        
        console.print(f"  📊 编译统计: 成功 {compiled_count}, 失败 {failed_count}")
    
    def _should_skip_file(self, py_file: Path) -> bool:
        """判断是否应该跳过文件"""
        # 跳过setup.py等特殊文件
        skip_files = ['setup.py', 'conftest.py']
        
        if py_file.name in skip_files:
            return True
        
        # 跳过测试文件 - 更精确的模式匹配
        file_str = str(py_file)
        
        # 检查是否在tests目录中
        if '/tests/' in file_str or file_str.endswith('/tests'):
            return True
        
        # 检查文件名是否以test_开头或以_test.py结尾
        if py_file.name.startswith('test_') or py_file.name.endswith('_test.py'):
            return True
        
        return False
    
    def _remove_source_files(self):
        """删除源文件，只保留字节码"""
        python_files = list(self.compiled_path.rglob("*.py"))
        
        removed_count = 0
        kept_count = 0
        
        console.print("  🗑️ 清理源文件...")
        
        for py_file in python_files:
            # 保留必要的文件
            if self._should_keep_source(py_file):
                kept_count += 1
                console.print(f"    📌 保留: {py_file.relative_to(self.compiled_path)}", style="blue")
                continue
                
            # 对于__init__.py和其他.py文件，如果有对应的.pyc，则删除.py
            pyc_file = py_file.with_suffix('.pyc')
            if pyc_file.exists():
                py_file.unlink()
                removed_count += 1
                console.print(f"    🗑️ 删除: {py_file.relative_to(self.compiled_path)}", style="dim")
            else:
                # 如果没有编译成功，保留源文件避免包损坏
                kept_count += 1
                console.print(f"    ⚠️ 保留(无.pyc): {py_file.relative_to(self.compiled_path)}", style="yellow")
        
        console.print(f"  📊 清理统计: 删除 {removed_count}, 保留 {kept_count}")
    
    def _should_keep_source(self, py_file: Path) -> bool:
        """判断是否应该保留源文件"""
        # 必须保留的文件
        keep_files = ['setup.py']
        
        if py_file.name in keep_files:
            return True
        
        return False
    
    def _update_pyproject(self):
        """更新pyproject.toml包含.pyc文件"""
        pyproject_file = self.compiled_path / "pyproject.toml"
        
        if not pyproject_file.exists():
            console.print("  ⚠️ 未找到pyproject.toml文件", style="yellow")
            return
        
        try:
            content = pyproject_file.read_text(encoding='utf-8')
            
            # 检查是否已经有setuptools配置
            if "[tool.setuptools.packages.find]" not in content:
                # 添加包含.pyc的配置
                setuptools_config = """

[tool.setuptools.packages.find]
where = ["src"]

[tool.setuptools.package-data]
"*" = ["*.pyc"]

"""
                content += setuptools_config
                pyproject_file.write_text(content, encoding='utf-8')
                console.print("  📝 更新pyproject.toml包含.pyc文件", style="green")
            else:
                console.print("  ✓ pyproject.toml已包含setuptools配置", style="green")
                
        except Exception as e:
            console.print(f"  ❌ 更新pyproject.toml失败: {e}", style="red")
    
    def build_wheel(self, upload: bool = False, dry_run: bool = True) -> bool:
        """
        构建wheel包
        
        Args:
            upload: 是否上传到PyPI
            dry_run: 是否为预演模式
            
        Returns:
            是否成功
        """
        if not self.compiled_path:
            raise SAGEDevToolkitError("Package not compiled yet. Call compile_package() first.")
        
        console.print(f"📦 构建wheel包: {self.compiled_path.name}", style="cyan")
        
        # 保存当前目录
        original_dir = Path.cwd()
        
        try:
            # 进入包目录
            os.chdir(self.compiled_path)
            
            # 清理旧构建
            for build_dir in ["dist", "build"]:
                if Path(build_dir).exists():
                    shutil.rmtree(build_dir)
                    console.print(f"  🧹 清理目录: {build_dir}")
            
            # 构建wheel
            console.print("  🔨 构建wheel...")
            result = subprocess.run([
                sys.executable, "-m", "build", "--wheel"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                console.print(f"  ✅ 构建成功", style="green")
                
                # 显示构建的文件
                dist_files = list(Path("dist").glob("*.whl"))
                for dist_file in dist_files:
                    file_size = dist_file.stat().st_size / 1024 / 1024  # MB
                    console.print(f"    📄 {dist_file.name} ({file_size:.2f} MB)")
                
                # 上传到PyPI
                if upload and not dry_run:
                    return self._upload_to_pypi()
                elif upload and dry_run:
                    console.print("  🔍 [预演模式] 跳过上传", style="yellow")
                
                return True
                
            else:
                console.print(f"  ❌ 构建失败: {result.stderr}", style="red")
                return False
                
        except Exception as e:
            console.print(f"  💥 构建异常: {e}", style="red")
            return False
        
        finally:
            # 返回原目录
            os.chdir(original_dir)
    
    def _upload_to_pypi(self) -> bool:
        """上传到PyPI"""
        console.print("  🚀 上传到PyPI...")
        
        try:
            upload_result = subprocess.run([
                "twine", "upload", "dist/*"
            ], capture_output=True, text=True)
            
            if upload_result.returncode == 0:
                console.print("  ✅ 上传成功", style="green")
                return True
            else:
                console.print(f"  ❌ 上传失败: {upload_result.stderr}", style="red")
                return False
                
        except FileNotFoundError:
            console.print("  ❌ 未找到twine工具，请先安装: pip install twine", style="red")
            return False
        except Exception as e:
            console.print(f"  💥 上传异常: {e}", style="red")
            return False
    
    def cleanup_temp_dir(self):
        """清理临时目录"""
        if self.temp_dir and self.temp_dir.exists():
            try:
                shutil.rmtree(self.temp_dir)
                console.print(f"🧹 清理临时目录: {self.temp_dir}", style="dim")
            except Exception as e:
                console.print(f"⚠️ 清理临时目录失败: {e}", style="yellow")


def compile_multiple_packages(
    package_paths: List[Path], 
    output_dir: Optional[Path] = None,
    build_wheels: bool = False,
    upload: bool = False,
    dry_run: bool = True,
    use_sage_home: bool = True,
    create_symlink: bool = True
) -> Dict[str, bool]:
    """
    编译多个包
    
    Args:
        package_paths: 包路径列表
        output_dir: 输出目录
        build_wheels: 是否构建wheel包
        upload: 是否上传到PyPI
        dry_run: 是否为预演模式
        use_sage_home: 是否使用SAGE home目录
        create_symlink: 是否创建软链接
        
    Returns:
        编译结果字典 {package_name: success}
    """
    results = {}
    
    console.print(f"🎯 批量编译 {len(package_paths)} 个包", style="bold cyan")
    console.print("=" * 60)
    
    # 创建SAGE home目录软链接（如果需要）
    sage_home_link = None
    if use_sage_home and create_symlink:
        sage_home_link = _create_sage_home_symlink()
    
    for i, package_path in enumerate(package_paths, 1):
        console.print(f"\n[{i}/{len(package_paths)}] 处理包: {package_path.name}", style="bold")
        
        try:
            # 编译包
            compiler = BytecodeCompiler(package_path)
            compiled_path = compiler.compile_package(output_dir, use_sage_home)
            
            # 构建wheel（如果需要）
            if build_wheels:
                success = compiler.build_wheel(upload=upload, dry_run=dry_run)
                results[package_path.name] = success
            else:
                results[package_path.name] = True
            
            # 不清理临时目录，让用户可以检查结果
            # compiler.cleanup_temp_dir()
            
        except Exception as e:
            console.print(f"❌ 处理包失败 {package_path.name}: {e}", style="red")
            results[package_path.name] = False
    
    # 显示汇总结果
    console.print("\n" + "=" * 60)
    console.print("📊 编译结果汇总:", style="bold")
    
    success_count = sum(1 for success in results.values() if success)
    total_count = len(results)
    
    for package_name, success in results.items():
        status = "✅" if success else "❌"
        style = "green" if success else "red"
        console.print(f"  {status} {package_name}", style=style)
    
    console.print(f"\n🎉 成功: {success_count}/{total_count}", style="bold green")
    
    # 显示软链接信息
    if sage_home_link:
        console.print(f"\n🔗 软链接已创建: {sage_home_link} -> ~/.sage", style="blue")
    
    return results


def _create_sage_home_symlink() -> Optional[Path]:
    """
    在当前目录创建指向SAGE home的软链接
    
    Returns:
        软链接路径，如果创建失败则返回None
    """
    import os
    
    current_dir = Path.cwd()
    sage_home = Path.home() / ".sage"
    symlink_path = current_dir / ".sage"
    
    try:
        # 如果软链接已存在，先检查是否指向正确的目标
        if symlink_path.exists() or symlink_path.is_symlink():
            if symlink_path.is_symlink():
                existing_target = symlink_path.readlink()
                if existing_target == sage_home:
                    console.print(f"✓ 软链接已存在: {symlink_path}", style="green")
                    return symlink_path
                else:
                    console.print(f"⚠️ 软链接指向错误目标，重新创建: {existing_target} -> {sage_home}", style="yellow")
                    symlink_path.unlink()
            else:
                console.print(f"⚠️ 路径已存在且不是软链接: {symlink_path}", style="yellow")
                return None
        
        # 确保SAGE home目录存在
        sage_home.mkdir(parents=True, exist_ok=True)
        
        # 创建软链接
        symlink_path.symlink_to(sage_home)
        console.print(f"🔗 创建软链接: {symlink_path} -> {sage_home}", style="green")
        
        return symlink_path
        
    except Exception as e:
        console.print(f"❌ 创建软链接失败: {e}", style="red")
        return None


def _get_sage_home_info():
    """显示SAGE home目录信息"""
    sage_home = Path.home() / ".sage"
    dist_dir = sage_home / "dist"
    
    console.print("📂 SAGE Home 目录信息:", style="bold blue")
    console.print(f"  🏠 Home: {sage_home}")
    console.print(f"  📦 Dist: {dist_dir}")
    
    if dist_dir.exists():
        compiled_packages = list(dist_dir.iterdir())
        console.print(f"  📊 已编译包: {len(compiled_packages)}")
        
        for pkg in compiled_packages[:5]:  # 显示前5个
            if pkg.is_dir():
                console.print(f"    📁 {pkg.name}")
        
        if len(compiled_packages) > 5:
            console.print(f"    ... 和其他 {len(compiled_packages) - 5} 个包")
    else:
        console.print("  📊 已编译包: 0 (目录不存在)")
    
    # 检查当前目录的软链接
    current_symlink = Path.cwd() / ".sage"
    if current_symlink.exists() and current_symlink.is_symlink():
        target = current_symlink.readlink()
        console.print(f"  🔗 当前软链接: {current_symlink} -> {target}")
    else:
        console.print("  🔗 当前软链接: 不存在")
