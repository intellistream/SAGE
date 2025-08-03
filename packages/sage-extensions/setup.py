#!/usr/bin/env python3
"""
SAGE Extensions - Setup script for C++ extensions
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
from setuptools import setup, Extension
from setuptools.command.build_ext import build_ext as _build_ext
from setuptools.command.install import install as _install


class CustomInstallCommand(_install):
    """自定义安装命令，确保 .so 文件被正确安装"""
    
    def run(self):
        # 确保在安装前构建扩展
        self.run_command('build_ext')
        
        # 运行标准安装
        _install.run(self)
        
        # 确保 .so 文件在正确位置
        self._ensure_extension_files()
    
    def _ensure_extension_files(self):
        """确保扩展文件在安装位置"""
        import site
        
        # 查找已安装的包位置
        installed_paths = [
            os.path.join(self.install_lib, 'sage', 'extensions', 'sage_db'),
            os.path.join(site.getsitepackages()[0], 'sage', 'extensions', 'sage_db') if site.getsitepackages() else None
        ]
        
        # 源文件位置
        source_dir = Path('src/sage/extensions/sage_db')
        so_files = list(source_dir.glob('*.so')) + list(source_dir.glob('*.pyd'))
        
        for install_path in installed_paths:
            if install_path and os.path.exists(install_path):
                for so_file in so_files:
                    dest = os.path.join(install_path, so_file.name)
                    if os.path.exists(str(so_file)):
                        shutil.copy2(str(so_file), dest)
                        print(f"Copied {so_file.name} to {dest}")


class BuildExtCommand(_build_ext):
    """自定义构建命令"""
    
    def run(self):
        """运行构建过程"""
    """自定义构建命令"""
    
    def run(self):
        """运行构建过程"""
        # 检查系统依赖
        if not self._check_system_deps():
            raise RuntimeError("System dependencies not satisfied")
        
        # 运行我们的构建脚本
        build_script = Path(__file__).parent / "scripts" / "build.py"
        if build_script.exists():
            print("Running custom build script...")
            result = subprocess.run([sys.executable, str(build_script)], 
                                  capture_output=False)
            if result.returncode != 0:
                raise RuntimeError("Build failed")
        
        # 调用父类的构建方法（但我们没有标准的扩展）
        # super().run()
    
    def _check_system_deps(self):
        """检查系统依赖"""
        print("Checking system dependencies...")
        
        # 检查关键工具
        required_tools = ["cmake", "gcc", "pkg-config"]
        missing_tools = []
        
        for tool in required_tools:
            if not self._which(tool):
                missing_tools.append(tool)
        
        if missing_tools:
            print(f"❌ Missing required tools: {', '.join(missing_tools)}")
            print("\n请安装缺失的系统依赖:")
            print("Ubuntu/Debian: sudo apt-get install build-essential cmake pkg-config libblas-dev liblapack-dev")
            print("CentOS/RHEL: sudo yum install gcc-c++ cmake pkgconfig blas-devel lapack-devel")
            print("macOS: brew install cmake gcc pkg-config openblas lapack")
            print("\n或者运行: ./scripts/install.sh")
            return False
        
        # 检查 Python 开发头文件
        try:
            import pybind11
            print("✅ pybind11 available")
        except ImportError:
            print("❌ pybind11 not found, installing...")
            subprocess.run([sys.executable, "-m", "pip", "install", "pybind11[global]"])
        
        return True
    
    def _which(self, program):
        """检查程序是否在 PATH 中"""
        import shutil
        return shutil.which(program) is not None


class InstallCommand(_install):
    """自定义安装命令"""
    
    def run(self):
        """运行安装过程"""
        # 先执行标准安装
        super().run()
        
        # 然后复制编译好的 .so 文件
        self._copy_so_files()
    
    def _copy_so_files(self):
        """复制编译好的 .so 文件到安装目录"""
        print("Copying compiled .so files...")
        
        # 安装目录
        install_lib = Path(self.install_lib)
        
        # 处理 sage_db
        self._copy_extension_files("sage_db", install_lib)
        
        # 处理 sage_queue 
        self._copy_extension_files("sage_queue", install_lib)
    
    def _copy_extension_files(self, extension_name, install_lib):
        """复制特定扩展的文件"""
        print(f"Copying {extension_name} files...")
        
        # 源目录：构建目录和源目录
        project_root = Path(__file__).parent
        extension_dir = project_root / "src" / "sage" / "extensions" / extension_name
        build_dir = extension_dir / "build"
        
        # 目标目录：安装后的包目录
        target_dir = install_lib / "sage" / "extensions" / extension_name
        
        if not target_dir.exists():
            print(f"Warning: Target directory does not exist: {target_dir}")
            return
        
        # 查找并复制 .so 文件
        so_files = []
        
        # 从构建目录查找
        if build_dir.exists():
            so_files.extend(build_dir.glob("*.so"))
            so_files.extend(build_dir.glob("*.pyd"))
            so_files.extend(build_dir.glob("*.dll"))
        
        # 从源目录查找
        so_files.extend(extension_dir.glob("*.so"))
        so_files.extend(extension_dir.glob("*.pyd"))
        so_files.extend(extension_dir.glob("*.dll"))
        
        copied_files = []
        for so_file in so_files:
            if so_file.exists():
                target_file = target_dir / so_file.name
                shutil.copy2(so_file, target_file)
                print(f"✓ Copied {so_file.name} to {target_file}")
                copied_files.append(target_file)
                
                # 设置执行权限
                os.chmod(target_file, 0o755)
        
        if copied_files:
            print(f"✅ Successfully copied {len(copied_files)} {extension_name} library files")
        else:
            print(f"⚠ Warning: No .so files found for {extension_name}")
            print("You may need to run the build script manually:")
            print("  python scripts/build.py")


def main():
    """主安装函数"""
    
    # 读取版本和其他元数据从 pyproject.toml
    # （这将通过 setuptools 自动处理）
    
    setup(
        # 大部分配置在 pyproject.toml 中
        cmdclass={
            'build_ext': BuildExtCommand,
            'install': CustomInstallCommand,
        },
        # 这里不定义 ext_modules，因为我们使用自定义构建
    )


if __name__ == "__main__":
    main()
