#!/usr/bin/env python3
"""
SAGE Extensions - Setup script for C++ extensions
"""

import os
import sys
import subprocess
from pathlib import Path
from setuptools import setup, Extension
from setuptools.command.build_ext import build_ext as _build_ext


class BuildExtCommand(_build_ext):
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
            print("\n或者运行: ./install.sh")
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


def main():
    """主安装函数"""
    
    # 读取版本和其他元数据从 pyproject.toml
    # （这将通过 setuptools 自动处理）
    
    setup(
        # 大部分配置在 pyproject.toml 中
        cmdclass={
            'build_ext': BuildExtCommand,
        },
        # 这里不定义 ext_modules，因为我们使用自定义构建
    )


if __name__ == "__main__":
    main()
