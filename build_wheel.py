#!/usr/bin/env python3
"""
SAGE 闭源Wheel构建脚本

这个脚本用于构建一个闭源的SAGE wheel包，包含：
1. 编译后的Python字节码(.pyc)而不是源码(.py)
2. 所有必要的C扩展(.so文件)
3. 配置文件和文档

使用方法:
    python build_wheel.py
    python build_wheel.py --source  # 包含源码的wheel
    python build_wheel.py --clean   # 清理构建文件
"""

import os
import sys
import shutil
import subprocess
import argparse
import tempfile
from pathlib import Path
import py_compile
import compileall

def run_command(cmd, cwd=None):
    """运行命令并处理错误"""
    print(f"Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}")
        print(f"Stdout: {e.stdout}")
        print(f"Stderr: {e.stderr}")
        raise

def clean_build():
    """清理构建文件"""
    print("Cleaning build files...")
    dirs_to_remove = ['build', 'dist', 'sage.egg-info', '__pycache__']
    
    for dir_name in dirs_to_remove:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"Removed {dir_name}")
    
    # 递归删除所有__pycache__目录
    for root, dirs, files in os.walk('.'):
        if '__pycache__' in dirs:
            shutil.rmtree(os.path.join(root, '__pycache__'))
        # 删除.pyc文件
        for file in files:
            if file.endswith('.pyc'):
                os.remove(os.path.join(root, file))

def compile_c_extensions():
    """编译C扩展"""
    print("Compiling C extensions...")
    
    ring_buffer_dir = Path("sage/utils/mmap_queue")
    
    # 检查是否存在构建脚本
    if (ring_buffer_dir / "build.sh").exists():
        run_command(["bash", "build.sh"], cwd=ring_buffer_dir)
    elif (ring_buffer_dir / "Makefile").exists():
        run_command(["make"], cwd=ring_buffer_dir)
    else:
        print("Warning: No build system found for ring_buffer")
    
    # 验证.so文件是否存在
    so_files = list(ring_buffer_dir.glob("*.so"))
    if so_files:
        print(f"Found compiled libraries: {[f.name for f in so_files]}")
    else:
        print("Warning: No .so files found after compilation")

def compile_python_source(source_only=False):
    """编译Python源码为字节码"""
    if source_only:
        print("Skipping Python compilation (source-only mode)")
        return
    
    print("Compiling Python source code...")
    
    # 编译sage目录下的所有Python文件
    sage_dir = Path("sage")
    if sage_dir.exists():
        compileall.compile_dir(str(sage_dir), force=True, quiet=1)
        print("Python source code compiled successfully")
    else:
        print("Warning: sage directory not found")

def create_bytecode_only_structure(temp_dir, source_only=False):
    """创建只包含字节码的目录结构"""
    if source_only:
        print("Creating source-only structure...")
        # 直接复制源码
        shutil.copytree("sage", os.path.join(temp_dir, "sage"))
        return
    
    print("Creating bytecode-only structure...")
    
    sage_source = Path("sage")
    sage_dest = Path(temp_dir) / "sage"
    
    # 创建目标目录
    sage_dest.mkdir(parents=True, exist_ok=True)
    
    for root, dirs, files in os.walk(sage_source):
        # 计算相对路径
        rel_path = Path(root).relative_to(sage_source)
        dest_dir = sage_dest / rel_path
        dest_dir.mkdir(parents=True, exist_ok=True)
        
        for file in files:
            src_file = Path(root) / file
            
            if file.endswith('.py'):
                # 对于Python文件，只复制字节码
                pyc_file = None
                
                # 查找对应的.pyc文件
                pycache_dir = Path(root) / '__pycache__'
                if pycache_dir.exists():
                    for pyc in pycache_dir.glob(f"{file[:-3]}.*.pyc"):
                        pyc_file = pyc
                        break
                
                if pyc_file and pyc_file.exists():
                    # 复制.pyc文件并重命名为.py（保持导入兼容性）
                    dest_file = dest_dir / file
                    shutil.copy2(pyc_file, dest_file)
                    print(f"Copied bytecode: {src_file} -> {dest_file}")
                else:
                    # 如果没有找到.pyc文件，编译并复制
                    try:
                        compiled = py_compile.compile(src_file, doraise=True)
                        dest_file = dest_dir / file
                        shutil.copy2(compiled, dest_file)
                        print(f"Compiled and copied: {src_file} -> {dest_file}")
                    except py_compile.PyCompileError:
                        # 如果编译失败，直接复制源文件
                        dest_file = dest_dir / file
                        shutil.copy2(src_file, dest_file)
                        print(f"Compilation failed, copied source: {src_file} -> {dest_file}")
            
            elif file.endswith(('.so', '.c', '.h', '.yaml', '.yml', '.md', '.txt', '.sh')):
                # 复制二进制文件、配置文件和文档
                dest_file = dest_dir / file
                shutil.copy2(src_file, dest_file)
                print(f"Copied file: {src_file} -> {dest_file}")

def build_wheel(source_only=False, output_dir="dist"):
    """构建wheel包"""
    print(f"Building {'source' if source_only else 'bytecode-only'} wheel...")
    
    # 确保输出目录存在
    Path(output_dir).mkdir(exist_ok=True)
    
    if source_only:
        # 直接构建源码wheel
        run_command([sys.executable, "setup.py", "bdist_wheel"])
    else:
        # 创建临时目录
        with tempfile.TemporaryDirectory() as temp_dir:
            print(f"Using temporary directory: {temp_dir}")
            
            # 复制setup.py和其他必要文件
            files_to_copy = [
                "setup.py", "README.md", "LICENSE", "MANIFEST.in",
                "requirements.txt"
            ]
            
            for file in files_to_copy:
                if Path(file).exists():
                    shutil.copy2(file, temp_dir)
            
            # 复制installation目录（如果存在）
            if Path("installation").exists():
                shutil.copytree("installation", os.path.join(temp_dir, "installation"))
            
            # 创建字节码结构
            create_bytecode_only_structure(temp_dir, source_only)
            
            # 在临时目录中构建wheel
            run_command([sys.executable, "setup.py", "bdist_wheel"], cwd=temp_dir)
            
            # 复制生成的wheel到目标目录
            temp_dist = Path(temp_dir) / "dist"
            if temp_dist.exists():
                for wheel_file in temp_dist.glob("*.whl"):
                    dest_wheel = Path(output_dir) / wheel_file.name
                    shutil.copy2(wheel_file, dest_wheel)
                    print(f"Wheel created: {dest_wheel}")
                    
                    # 重命名以标识为闭源版本
                    if not source_only:
                        new_name = wheel_file.name.replace(".whl", "_bytecode.whl")
                        new_dest = Path(output_dir) / new_name
                        dest_wheel.rename(new_dest)
                        print(f"Renamed to: {new_dest}")

def main():
    parser = argparse.ArgumentParser(description="Build SAGE wheel package")
    parser.add_argument("--source", action="store_true", 
                       help="Build source wheel (default is bytecode-only)")
    parser.add_argument("--clean", action="store_true",
                       help="Clean build files before building")
    parser.add_argument("--output-dir", default="dist",
                       help="Output directory for wheel files")
    
    args = parser.parse_args()
    
    try:
        if args.clean:
            clean_build()
        
        # 编译C扩展
        compile_c_extensions()
        
        # 编译Python源码
        compile_python_source(args.source)
        
        # 构建wheel
        build_wheel(args.source, args.output_dir)
        
        print("\n" + "="*50)
        print("Build completed successfully!")
        print(f"Check the {args.output_dir} directory for wheel files.")
        print("="*50)
        
    except Exception as e:
        print(f"\nBuild failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
