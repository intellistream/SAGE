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
        self._binary_extensions = []
        
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
        
        # 检查和保留二进制扩展文件
        self._preserve_binary_extensions()
        
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
    
    def _preserve_binary_extensions(self):
        """检查和保留二进制扩展文件"""
        # 查找所有二进制扩展文件
        extensions = []
        for ext in ["*.so", "*.pyd", "*.dylib"]:
            extensions.extend(self.compiled_path.rglob(ext))
        
        if not extensions:
            console.print("  ℹ️ 未找到二进制扩展文件", style="blue")
            return
        
        console.print(f"  🔧 找到 {len(extensions)} 个二进制扩展文件")
        
        # 记录所有扩展文件
        for ext_file in extensions:
            rel_path = ext_file.relative_to(self.compiled_path)
            size_kb = ext_file.stat().st_size / 1024
            console.print(f"    📦 保留: {rel_path} ({size_kb:.1f} KB)", style="blue")
            
        # 确保不会删除这些文件
        self._binary_extensions = extensions
    
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
        
        # 确保不会删除二进制扩展文件
        if hasattr(self, '_binary_extensions') and self._binary_extensions:
            for ext_file in self._binary_extensions:
                if ext_file.exists():
                    size_kb = ext_file.stat().st_size / 1024
                    console.print(f"    ✅ 保留二进制: {ext_file.relative_to(self.compiled_path)} ({size_kb:.1f} KB)", style="green")
        
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
            
            # 检查现有的包配置
            has_packages_list = 'packages = [' in content  # 静态包列表
            has_packages_find = "[tool.setuptools.packages.find]" in content  # 动态查找
            has_pyc_package_data = '"*.pyc"' in content and "[tool.setuptools.package-data]" in content
            has_include_package_data = "include-package-data = true" in content.lower()
            
            modified = False
            
            # 需要添加配置
            if not has_packages_list and not has_packages_find:
                content += """
[tool.setuptools.packages.find]
where = ["src"]
"""
                modified = True
                console.print("  📝 添加packages.find配置", style="green")
            
            # 确保include-package-data设置为true
            if not has_include_package_data:
                # 检查是否有[tool.setuptools]部分
                if "[tool.setuptools]" in content:
                    # 在现有部分添加
                    import re
                    pattern = r'(\[tool\.setuptools\][\s\S]*?)(?=\n\[|\n$|$)'
                    match = re.search(pattern, content)
                    if match:
                        existing_section = match.group(1)
                        if "include-package-data" not in existing_section:
                            updated_section = existing_section.rstrip() + '\ninclude-package-data = true\n'
                            content = content.replace(existing_section, updated_section)
                            modified = True
                            console.print("  📝 更新include-package-data = true", style="green")
                else:
                    # 添加新部分
                    content += """
[tool.setuptools]
include-package-data = true
"""
                    modified = True
                    console.print("  📝 添加include-package-data = true", style="green")
            
            # 添加package-data配置
            if not has_pyc_package_data:
                # 检查是否已有package-data部分
                if "[tool.setuptools.package-data]" in content:
                    # 需要更新现有的package-data配置
                    import re
                    pattern = r'(\[tool\.setuptools\.package-data\][\s\S]*?)(?=\n\[|\n$|$)'
                    match = re.search(pattern, content)
                    if match:
                        existing_data = match.group(1)
                        if '"*.pyc"' not in existing_data:
                            # 在现有配置中添加*.pyc和二进制扩展文件
                            updated_data = existing_data.rstrip() + '\n"*" = ["*.pyc", "*.pyo", "__pycache__/*", "*.so", "*.pyd", "*.dylib"]\n'
                            content = content.replace(existing_data, updated_data)
                            modified = True
                            console.print("  📝 更新package-data配置包含二进制文件", style="green")
                else:
                    # 添加新的package-data配置
                    content += """
[tool.setuptools.package-data]
"*" = ["*.pyc", "*.pyo", "__pycache__/*", "*.so", "*.pyd", "*.dylib"]
"""
                    modified = True
                    console.print("  📝 添加package-data配置包含二进制文件", style="green")
            
            # 添加MANIFEST.in文件以确保包含所有二进制文件
            manifest_file = self.compiled_path / "MANIFEST.in"
            manifest_content = """
# 包含所有编译文件和二进制扩展
recursive-include src *.pyc
recursive-include src *.pyo
recursive-include src __pycache__/*
recursive-include src *.so
recursive-include src *.pyd
recursive-include src *.dylib
"""
            manifest_file.write_text(manifest_content, encoding='utf-8')
            console.print("  📝 创建MANIFEST.in文件", style="green")
            
            # 添加setup.py文件确保包含所有文件
            setup_py_file = self.compiled_path / "setup.py"
            setup_py_content = """
from setuptools import setup

setup(
    include_package_data=True,
    package_data={
        "": ["*.pyc", "*.pyo", "__pycache__/*", "*.so", "*.pyd", "*.dylib"],
    },
)
"""
            setup_py_file.write_text(setup_py_content, encoding='utf-8')
            console.print("  📝 创建setup.py文件", style="green")
            
            if modified:
                pyproject_file.write_text(content, encoding='utf-8')
                console.print("  ✅ 更新pyproject.toml配置", style="green")
            else:
                console.print("  ✓ pyproject.toml配置已满足要求", style="green")
                
        except Exception as e:
            console.print(f"  ❌ 更新pyproject.toml失败: {e}", style="red")
    
    def build_wheel(self, compiled_path: Optional[Path] = None, upload: bool = False, dry_run: bool = True) -> Path:
        """
        构建wheel包
        
        Args:
            compiled_path: 已编译的包路径，如果未提供则使用self.compiled_path
            upload: 是否上传到PyPI
            dry_run: 是否为预演模式
            
        Returns:
            wheel文件路径
        """
        target_path = compiled_path or self.compiled_path
        
        if not target_path:
            raise SAGEDevToolkitError("Package not compiled yet. Call compile_package() first.")
        
        console.print(f"📦 构建wheel包: {target_path.name}", style="cyan")
        
        # 保存当前目录
        original_dir = Path.cwd()
        
        try:
            # 进入包目录
            os.chdir(target_path)
            
            # 清理旧构建
            for build_dir in ["dist", "build"]:
                if Path(build_dir).exists():
                    shutil.rmtree(build_dir)
                    console.print(f"  🧹 清理目录: {build_dir}")
            
            # 验证.pyc文件是否存在
            pyc_files = list(Path('.').rglob('*.pyc'))
            console.print(f"  📊 找到 {len(pyc_files)} 个.pyc文件")
            
            # 构建wheel
            console.print("  🔨 构建wheel...")
            result = subprocess.run([
                sys.executable, "-m", "build", "--wheel", "--no-isolation"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                console.print(f"  ✅ 构建成功", style="green")
                
                # 查找构建的wheel文件
                dist_files = list(Path("dist").glob("*.whl"))
                if not dist_files:
                    raise SAGEDevToolkitError("构建完成但未找到wheel文件")
                
                wheel_file = dist_files[0]  # 通常只有一个wheel文件
                file_size = wheel_file.stat().st_size / 1024 / 1024  # MB
                console.print(f"    📄 {wheel_file.name} ({file_size:.2f} MB)")
                
                # 验证wheel内容
                self._verify_wheel_contents(wheel_file)
                
                # 如果需要上传
                if upload and not dry_run:
                    self._upload_to_pypi()
                elif upload and dry_run:
                    console.print("  🔍 预演模式：跳过上传", style="yellow")
                
                # 返回绝对路径
                return wheel_file.resolve()
                
            else:
                # 构建失败，收集错误信息
                error_msg = "构建失败"
                if result.stderr.strip():
                    error_msg += f": {result.stderr.strip()}"
                if result.stdout.strip():
                    error_msg += f"\n详细信息: {result.stdout.strip()}"
                raise SAGEDevToolkitError(error_msg)
                
        except Exception as e:
            console.print(f"  💥 构建异常: {e}", style="red")
            raise
        
        finally:
            # 返回原目录
            os.chdir(original_dir)
            
    def _verify_wheel_contents(self, wheel_file: Path):
        """验证wheel包内容是否包含.pyc文件"""
        console.print("  🔍 验证wheel包内容...", style="cyan")
        
        try:
            # 创建临时目录解压wheel
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # 解压wheel
                import zipfile
                with zipfile.ZipFile(wheel_file, 'r') as zip_ref:
                    zip_ref.extractall(temp_path)
                    
                    # 列出所有文件
                    all_files = list(zip_ref.namelist())
                    
                # 计数
                pyc_count = sum(1 for f in all_files if f.endswith('.pyc'))
                py_count = sum(1 for f in all_files if f.endswith('.py'))
                binary_count = sum(1 for f in all_files if f.endswith(('.so', '.pyd', '.dylib')))
                total_count = len(all_files)
                
                console.print(f"    📊 文件总数: {total_count}")
                console.print(f"    📊 .pyc文件: {pyc_count}")
                console.print(f"    📊 .py文件: {py_count}")
                console.print(f"    📊 二进制扩展文件: {binary_count}")
                
                # 检查包是否太小
                if total_count < 10:
                    console.print("    ⚠️ 警告: wheel包文件数量过少，可能打包不完整", style="yellow")
                    
                if pyc_count == 0 and binary_count == 0:
                    console.print("    ❌ 错误: wheel包中没有.pyc或二进制扩展文件！", style="red")
                    console.print("    💡 尝试使用以下步骤修复:")
                    console.print("       1. 确保pyproject.toml中设置了include-package-data = true")
                    console.print("       2. 确保pyproject.toml中设置了package-data配置")
                    console.print("       3. 检查MANIFEST.in文件是否包含了*.pyc和*.so等")
                    
                    # 尝试输出部分文件列表以帮助诊断
                    console.print("    📁 wheel包内容示例:")
                    for f in all_files[:10]:
                        console.print(f"       - {f}")
                    if len(all_files) > 10:
                        console.print(f"       ... 还有 {len(all_files)-10} 个文件")
                else:
                    if pyc_count > 0:
                        console.print("    ✅ wheel包包含.pyc文件", style="green")
                    if binary_count > 0:
                        console.print("    ✅ wheel包包含二进制扩展文件", style="green")
                    
        except Exception as e:
            console.print(f"    ❌ 验证wheel内容失败: {e}", style="red")
    
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
