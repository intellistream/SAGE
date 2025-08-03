#!/usr/bin/env python3
"""
Simple build script for SAGE Extensions
Handles C++ compilation and Python packaging
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def run_command(cmd, cwd=None, check=True):
    """运行命令并处理错误"""
    print(f"Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, cwd=cwd, check=check, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        return result
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}")
        if e.stdout:
            print(f"STDOUT: {e.stdout}")
        if e.stderr:
            print(f"STDERR: {e.stderr}")
        if check:
            raise
        return e

def check_cmake():
    """检查 CMake 是否可用"""
    try:
        result = run_command(["cmake", "--version"])
        print("✓ CMake found")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("✗ CMake not found. Please install CMake >= 3.18")
        return False

def install_system_dependencies():
    """安装系统依赖"""
    print("Installing system dependencies...")
    
    import platform
    system = platform.system().lower()
    
    if system == "linux":
        # 检测 Linux 发行版
        try:
            with open("/etc/os-release", "r") as f:
                os_info = f.read().lower()
        except FileNotFoundError:
            os_info = ""
        
        if "ubuntu" in os_info or "debian" in os_info:
            # Ubuntu/Debian 系统
            deps = [
                "build-essential",
                "cmake", 
                "g++", 
                "gcc",
                "pkg-config",
                "libblas-dev",
                "liblapack-dev",
                "libopenblas-dev",  # 更好的 BLAS 实现
                "python3-dev",
                "git"
            ]
            
            print("Detected Ubuntu/Debian system")
            print("Installing system packages...")
            
            # 更新包列表
            try:
                run_command(["sudo", "apt-get", "update", "-y"])
            except subprocess.CalledProcessError:
                print("Warning: Could not update package list")
            
            # 安装依赖
            for dep in deps:
                try:
                    run_command(["sudo", "apt-get", "install", "-y", dep])
                    print(f"✓ {dep} installed")
                except subprocess.CalledProcessError:
                    print(f"⚠ Warning: Could not install {dep}")
                    
        elif "centos" in os_info or "rhel" in os_info or "fedora" in os_info:
            # CentOS/RHEL/Fedora 系统
            deps = [
                "gcc-c++",
                "gcc", 
                "make",
                "cmake",
                "pkgconfig",
                "blas-devel",
                "lapack-devel",
                "openblas-devel",
                "python3-devel",
                "git"
            ]
            
            print("Detected CentOS/RHEL/Fedora system")
            
            # 尝试 dnf 或 yum
            pkg_manager = "dnf" if shutil.which("dnf") else "yum"
            
            for dep in deps:
                try:
                    run_command(["sudo", pkg_manager, "install", "-y", dep])
                    print(f"✓ {dep} installed")
                except subprocess.CalledProcessError:
                    print(f"⚠ Warning: Could not install {dep}")
        else:
            print("Unknown Linux distribution, trying generic commands...")
            # 尝试通用的命令
            generic_deps = ["cmake", "gcc", "g++", "make"]
            for dep in generic_deps:
                if not shutil.which(dep):
                    print(f"⚠ Warning: {dep} not found. Please install manually.")
                else:
                    print(f"✓ {dep} found")
                    
    elif system == "darwin":  # macOS
        print("Detected macOS system")
        
        # 检查 Homebrew
        if not shutil.which("brew"):
            print("Installing Homebrew...")
            try:
                brew_install = '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
                run_command(["bash", "-c", brew_install])
            except subprocess.CalledProcessError:
                print("Failed to install Homebrew. Please install manually.")
                return False
        
        # 安装依赖
        deps = ["cmake", "gcc", "pkg-config", "openblas", "lapack", "git"]
        for dep in deps:
            try:
                run_command(["brew", "install", dep])
                print(f"✓ {dep} installed")
            except subprocess.CalledProcessError:
                print(f"⚠ Warning: Could not install {dep}")
                
    else:
        print(f"Unsupported system: {system}")
        print("Please install the following dependencies manually:")
        print("- CMake >= 3.18")
        print("- C++ compiler (GCC/Clang)")
        print("- pkg-config")
        print("- BLAS and LAPACK libraries")
        return False
    
    return True

def install_python_dependencies():
    """安装 Python 依赖"""
    print("Installing Python dependencies...")
    
    # 安装基础依赖
    deps = ["numpy", "pybind11[global]"]
    
    for dep in deps:
        try:
            run_command([sys.executable, "-m", "pip", "install", dep])
            print(f"✓ {dep} installed")
        except subprocess.CalledProcessError:
            print(f"✗ Failed to install {dep}")
            return False
    
    # 尝试安装 FAISS
    print("Installing FAISS...")
    faiss_installed = False
    
    # 首先尝试 conda
    if shutil.which("conda"):
        try:
            run_command(["conda", "install", "-y", "-c", "conda-forge", "faiss-cpu"])
            print("✓ FAISS installed via conda")
            faiss_installed = True
        except subprocess.CalledProcessError:
            print("Failed to install FAISS via conda, trying pip...")
    
    # 如果 conda 失败，尝试 pip
    if not faiss_installed:
        try:
            run_command([sys.executable, "-m", "pip", "install", "faiss-cpu"])
            print("✓ FAISS installed via pip")
            faiss_installed = True
        except subprocess.CalledProcessError:
            print("⚠ Warning: Could not install FAISS. Vector operations may be limited.")
    
    return True

def build_sage_db():
    """构建 SAGE DB 扩展"""
    print("Building SAGE DB C++ extension...")
    
    # 找到 sage_db 目录
    script_dir = Path(__file__).parent
    sage_db_dir = script_dir / "src" / "sage" / "extensions" / "sage_db"
    
    if not sage_db_dir.exists():
        print(f"Error: SAGE DB directory not found at {sage_db_dir}")
        return False
    
    # 创建构建目录
    build_dir = sage_db_dir / "build"
    build_dir.mkdir(exist_ok=True)
    
    # CMake 配置
    cmake_args = [
        "cmake",
        str(sage_db_dir),
        f"-DPYTHON_EXECUTABLE={sys.executable}",
        "-DCMAKE_BUILD_TYPE=Release",
        "-DBUILD_PYTHON_BINDINGS=ON",
        "-DBUILD_TESTS=OFF",
    ]
    
    # 检查是否有 Ninja
    if shutil.which("ninja"):
        cmake_args.extend(["-GNinja"])
    
    # 配置
    result = run_command(cmake_args, cwd=build_dir, check=False)
    if result.returncode != 0:
        print("CMake configuration failed")
        return False
    
    # 构建
    build_args = ["cmake", "--build", ".", "--config", "Release"]
    result = run_command(build_args, cwd=build_dir, check=False)
    if result.returncode != 0:
        print("Build failed")
        return False
    
    # 检查生成的库文件
    lib_files = list(build_dir.glob("*sage_db*"))
    if not lib_files:
        print("No library files generated")
        return False
    
    print(f"✓ Built library files: {[f.name for f in lib_files]}")
    
    # 复制库文件到 Python 包目录
    target_dir = sage_db_dir
    
    for lib_file in lib_files:
        if lib_file.suffix in ['.so', '.pyd', '.dll']:
            target_file = target_dir / lib_file.name
            shutil.copy2(lib_file, target_file)
            print(f"✓ Copied {lib_file.name} to {target_file}")
    
    # 也复制到 python 子目录（如果存在）
    python_dir = sage_db_dir / "python"
    if python_dir.exists():
        for lib_file in lib_files:
            if lib_file.suffix in ['.so', '.pyd', '.dll']:
                target_file = python_dir / lib_file.name
                shutil.copy2(lib_file, target_file)
                print(f"✓ Also copied {lib_file.name} to {target_file}")
    
    # 验证库文件可以加载
    print("Testing library loading...")
    import sys
    sys.path.insert(0, str(sage_db_dir))
    try:
        import _sage_db
        print("✓ C++ extension loads successfully")
        print(f"Available classes: {[x for x in dir(_sage_db) if not x.startswith('_')][:5]}...")
    except Exception as e:
        print(f"⚠ Warning: Library loading test failed: {e}")
    finally:
        sys.path.pop(0)
    
    return True

def main():
    """主构建流程"""
    print("SAGE Extensions Build Script")
    print("=" * 40)
    
    # 检查系统依赖
    if not check_cmake():
        return 1
    
    # 安装系统依赖
    if not install_system_dependencies():
        print("Failed to install system dependencies")
        return 1
    
    # 安装 Python 依赖
    if not install_python_dependencies():
        print("Failed to install Python dependencies")
        return 1
    
    # 构建 C++ 扩展
    if not build_sage_db():
        print("Failed to build C++ extensions")
        return 1
    
    print("=" * 40)
    print("✅ Build completed successfully!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
