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

def check_boost():
    """检查 Boost 库是否可用"""
    print("Checking for Boost libraries...")
    
    # 检查常见的 Boost 头文件位置
    boost_paths = [
        "/usr/include/boost",
        "/usr/local/include/boost", 
        "/opt/local/include/boost",
        "/usr/include/boost169",  # CentOS 可能的路径
        "/usr/include/boost148"   # 老版本路径
    ]
    
    boost_found = False
    for path in boost_paths:
        if Path(path).exists():
            print(f"✓ Found Boost headers at: {path}")
            boost_found = True
            break
    
    if not boost_found:
        print("✗ Boost headers not found")
        print("Boost is required for sage_queue. Will attempt to install...")
        return False
    
    # 检查关键的 Boost 库文件
    import platform
    system = platform.system().lower()
    
    lib_paths = []
    if system == "linux":
        lib_paths = ["/usr/lib", "/usr/lib64", "/usr/local/lib", "/usr/lib/x86_64-linux-gnu"]
    elif system == "darwin":
        lib_paths = ["/usr/local/lib", "/opt/local/lib"]
    
    boost_libs = ["boost_system", "boost_filesystem", "boost_thread", "boost_interprocess"]
    libs_found = 0
    
    for lib_path in lib_paths:
        lib_path_obj = Path(lib_path)
        if not lib_path_obj.exists():
            continue
            
        for boost_lib in boost_libs:
            # 检查多种命名格式
            patterns = [f"lib{boost_lib}.*", f"lib{boost_lib}-mt.*"]
            for pattern in patterns:
                lib_files = list(lib_path_obj.glob(pattern))
                if lib_files:
                    libs_found += 1
                    print(f"✓ Found {boost_lib} library: {lib_files[0].name}")
                    break
            if lib_files:  # 找到了就跳出
                break
    
    # 由于boost_interprocess是header-only的，我们主要检查其他库
    if libs_found >= 2:  # 至少找到2个关键库
        print(f"✓ Found {libs_found} Boost libraries - sufficient for compilation")
        return True
    else:
        print(f"⚠ Only found {libs_found} Boost libraries")
        print("Some Boost libraries may be missing, but attempting to build anyway...")
        # 对于Ubuntu/Debian系统，如果安装了libboost-all-dev包，通常都可以编译
        # 所以我们给一个更宽容的检查
        if system == "linux" and boost_found:
            print("✓ Proceeding with build (header-only libraries may be sufficient)")
            return True
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
                "libboost-all-dev",  # Boost库开发包，sage_queue需要
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
                "boost-devel",  # Boost库开发包
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
        deps = ["cmake", "gcc", "pkg-config", "openblas", "lapack", "boost", "git"]
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
    
    # 检查并安装 Boost 相关 Python 包 (如果需要)
    try:
        import boost_python
        print("✓ boost_python found")
    except ImportError:
        print("⚠ boost_python not found, this is normal")
    
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
    
    # 找到 sage_db 目录 - 从 scripts 目录向上查找
    script_dir = Path(__file__).parent
    project_root = script_dir.parent  # 回到项目根目录
    sage_db_dir = project_root / "src" / "sage" / "extensions" / "sage_db"
    
    if not sage_db_dir.exists():
        print(f"Error: SAGE DB directory not found at {sage_db_dir}")
        return False
    
    print(f"Found SAGE DB directory at: {sage_db_dir}")
    
    # 创建构建目录，清理之前的构建
    build_dir = sage_db_dir / "build"
    if build_dir.exists():
        print("Cleaning previous build...")
        shutil.rmtree(build_dir)
    build_dir.mkdir(exist_ok=True)
    
    # 清理旧的库文件
    for pattern in ["*.so", "*.pyd", "*.dll"]:
        for old_file in sage_db_dir.glob(pattern):
            if not old_file.name.endswith(".py"):  # 保留Python文件
                print(f"Removing old library file: {old_file.name}")
                old_file.unlink()
    
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
    result = run_command(cmake_args, cwd=sage_db_dir, check=False)
    if result.returncode != 0:
        print("CMake configuration failed")
        return False
    
    # 构建
    build_args = ["cmake", "--build", ".", "--config", "Release"]
    result = run_command(build_args, cwd=sage_db_dir, check=False)
    if result.returncode != 0:
        print("Build failed")
        return False
    
    # 检查生成的库文件
    lib_files = list(sage_db_dir.glob("*sage_db*"))
    lib_files.extend(list(build_dir.glob("*sage_db*")))
    
    # 过滤出实际的库文件
    actual_lib_files = []
    for lib_file in lib_files:
        if lib_file.suffix in ['.so', '.pyd', '.dll'] and lib_file.exists():
            actual_lib_files.append(lib_file)
    
    if not actual_lib_files:
        print("No library files generated")
        print("Available files in build directory:")
        for item in build_dir.iterdir():
            print(f"  {item.name}")
        return False
    
    print(f"✓ Built library files: {[f.name for f in actual_lib_files]}")
    
    # 复制库文件到 Python 包目录（从构建目录到源目录）
    for lib_file in actual_lib_files:
        if lib_file.parent == build_dir:  # 只复制构建目录中的文件
            target_file = sage_db_dir / lib_file.name
            shutil.copy2(lib_file, target_file)
            print(f"✓ Copied {lib_file.name} to {target_file}")
    
    # 也复制到 python 子目录（如果存在）
    python_dir = sage_db_dir / "python"
    if python_dir.exists():
        for lib_file in actual_lib_files:
            if lib_file.parent == build_dir:
                target_file = python_dir / lib_file.name
                shutil.copy2(lib_file, target_file)
                print(f"✓ Also copied {lib_file.name} to {target_file}")
    
    # 验证库文件可以加载
    print("Testing library loading...")
    original_path = sys.path.copy()
    sys.path.insert(0, str(sage_db_dir))
    try:
        import _sage_db
        print("✓ C++ extension loads successfully")
        print(f"Available classes: {[x for x in dir(_sage_db) if not x.startswith('_')][:5]}...")
    except Exception as e:
        print(f"⚠ Warning: Library loading test failed: {e}")
    finally:
        sys.path = original_path
    
    return True

def build_sage_queue():
    """构建 SAGE Queue 扩展"""
    print("Building SAGE Queue C++ extension...")
    
    # 找到 sage_queue 目录
    script_dir = Path(__file__).parent
    project_root = script_dir.parent  # 回到项目根目录
    sage_queue_dir = project_root / "src" / "sage" / "extensions" / "sage_queue"
    
    if not sage_queue_dir.exists():
        print(f"Error: SAGE Queue directory not found at {sage_queue_dir}")
        return False
    
    print(f"Found SAGE Queue directory at: {sage_queue_dir}")
    
    # 创建构建目录，清理之前的构建
    build_dir = sage_queue_dir / "build"
    if build_dir.exists():
        print("Cleaning previous build...")
        shutil.rmtree(build_dir)
    build_dir.mkdir(exist_ok=True)
    
    # 清理旧的库文件
    for pattern in ["*.so", "*.pyd", "*.dll"]:
        for old_file in sage_queue_dir.glob(pattern):
            if not old_file.name.endswith(".py"):  # 保留Python文件
                print(f"Removing old library file: {old_file.name}")
                old_file.unlink()
    
    # CMake 配置
    cmake_args = [
        "cmake",
        str(sage_queue_dir),
        f"-DPYTHON_EXECUTABLE={sys.executable}",
        "-DCMAKE_BUILD_TYPE=Release",
        "-DBUILD_PYTHON_BINDINGS=ON",
        "-DBUILD_TESTS=OFF",
        "-DUSE_OPENMP=ON"
    ]
    
    # 检查是否有 Ninja
    if shutil.which("ninja"):
        cmake_args.extend(["-GNinja"])
    
    # 配置
    result = run_command(cmake_args, cwd=sage_queue_dir, check=False)
    if result.returncode != 0:
        print("CMake configuration failed")
        print("This might be due to missing Boost libraries")
        return False
    
    # 构建
    build_args = ["cmake", "--build", ".", "--config", "Release"]
    result = run_command(build_args, cwd=sage_queue_dir, check=False)
    if result.returncode != 0:
        print("Build failed")
        return False
    
    # 查找生成的库文件（在build目录和源目录中）
    lib_files = []
    lib_extensions = ['.so', '.pyd', '.dll']
    
    # 在build目录中查找
    for ext in lib_extensions:
        lib_files.extend(build_dir.glob(f"*{ext}"))
        lib_files.extend(build_dir.glob(f"*sage_queue*{ext}"))
        lib_files.extend(build_dir.glob(f"*ring_buffer*{ext}"))
    
    # 在源目录中查找（CMake可能直接输出到源目录）
    for ext in lib_extensions:
        lib_files.extend(sage_queue_dir.glob(f"*{ext}"))
        lib_files.extend(sage_queue_dir.glob(f"*sage_queue*{ext}"))
        lib_files.extend(sage_queue_dir.glob(f"*ring_buffer*{ext}"))
    
    # 过滤出实际存在的文件，去重
    actual_lib_files = []
    seen_names = set()
    for f in lib_files:
        if f.exists() and f.name not in seen_names:
            actual_lib_files.append(f)
            seen_names.add(f.name)
    
    if not actual_lib_files:
        print("No library files generated")
        print("Checking build directory contents:")
        for item in build_dir.iterdir():
            print(f"  {item.name}")
        return False
    
    print(f"✓ Built library files: {[f.name for f in actual_lib_files]}")
    
    # 复制库文件到 Python 包目录（如果需要的话）
    for lib_file in actual_lib_files:
        # 如果文件已经在源目录中，不需要复制
        if lib_file.parent == sage_queue_dir:
            print(f"✓ {lib_file.name} is already in correct location")
        else:
            # 从build目录复制到源目录
            target_file = sage_queue_dir / lib_file.name
            shutil.copy2(lib_file, target_file)
            print(f"✓ Copied {lib_file.name} to {target_file}")
    
    # 修复符号链接（避免循环引用）
    sage_queue_lib_1 = sage_queue_dir / "libsage_queue.so.1"
    sage_queue_lib_100 = sage_queue_dir / "libsage_queue.so.1.0.0"
    if sage_queue_lib_1.exists() and sage_queue_lib_100.exists():
        if sage_queue_lib_1.is_symlink():
            sage_queue_lib_1.unlink()
        sage_queue_lib_1.symlink_to("libsage_queue.so.1.0.0")
        print("✓ Fixed libsage_queue.so.1 symlink")
    
    # 也复制到 python 子目录（如果存在）
    python_dir = sage_queue_dir / "python"
    if python_dir.exists():
        for lib_file in actual_lib_files:
            target_file = python_dir / lib_file.name
            if lib_file.parent != python_dir:  # 避免复制到自己
                shutil.copy2(lib_file, target_file)
                print(f"✓ Also copied {lib_file.name} to {target_file}")
    
    # 验证库文件可以加载
    print("Testing library loading...")
    original_path = sys.path.copy()
    sys.path.insert(0, str(sage_queue_dir))
    try:
        # 尝试加载Python绑定
        if (sage_queue_dir / "sage_queue_bindings.so").exists():
            import sage_queue_bindings
            print("✓ sage_queue_bindings extension loads successfully")
            print(f"Available functions: {[x for x in dir(sage_queue_bindings) if not x.startswith('_')][:5]}...")
        else:
            print("⚠ sage_queue_bindings.so not found, checking for other libraries...")
            # 检查是否有其他库文件
            for lib_file in actual_lib_files:
                print(f"  Found: {lib_file.name}")
    except Exception as e:
        print(f"⚠ Warning: Library loading test failed: {e}")
    finally:
        sys.path = original_path
    
    return True

def main():
    """主构建流程"""
    print("SAGE Extensions Build Script")
    print("=" * 40)
    
    # 检查系统依赖
    if not check_cmake():
        return 1
    
    # 检查 Boost（sage_queue 需要）
    boost_available = check_boost()
    
    # 安装系统依赖
    if not install_system_dependencies():
        print("Failed to install system dependencies")
        return 1
    
    # 如果之前没有 Boost，再检查一次
    if not boost_available:
        print("Re-checking Boost after dependency installation...")
        boost_available = check_boost()
    
    # 安装 Python 依赖
    if not install_python_dependencies():
        print("Failed to install Python dependencies")
        return 1
    
    # 构建 C++ 扩展
    success = True
    
    if not build_sage_db():
        print("Failed to build SAGE DB extension")
        success = False
    
    if boost_available:
        if not build_sage_queue():
            print("Failed to build SAGE Queue extension")
            success = False
    else:
        print("⚠ Skipping SAGE Queue build due to missing Boost libraries")
        print("  Install boost development packages and run again:")
        print("  Ubuntu/Debian: sudo apt-get install libboost-all-dev")
        print("  CentOS/RHEL: sudo yum install boost-devel")
        print("  macOS: brew install boost")
    
    if not success:
        print("Some extensions failed to build")
        return 1
    
    print("=" * 40)
    print("✅ Build completed successfully!")
    if boost_available:
        print("Both SAGE DB and SAGE Queue extensions are ready!")
    else:
        print("SAGE DB extension is ready. Install Boost for SAGE Queue support.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
