#!/usr/bin/env python3
"""
SAGE安装前的构建脚本
确保C扩展库能正确编译
"""

import os
import subprocess
import sys
import platform
from pathlib import Path

def build_ring_buffer():
    """构建ring_buffer C库"""
    print("Building ring_buffer C library...")
    
    # 找到ring_buffer目录
    sage_root = Path(__file__).parent
    ring_buffer_dir = sage_root / "sage_utils" / "mmap_queue"
    
    if not ring_buffer_dir.exists():
        print(f"Error: ring_buffer directory not found: {ring_buffer_dir}")
        return False
    
    # 检查源文件是否存在
    c_source = ring_buffer_dir / "ring_buffer.c"
    h_header = ring_buffer_dir / "ring_buffer.h"
    
    if not c_source.exists():
        print(f"Error: C source file not found: {c_source}")
        return False
    
    if not h_header.exists():
        print(f"Error: Header file not found: {h_header}")
        return False
    
    # 切换到ring_buffer目录
    original_cwd = os.getcwd()
    os.chdir(ring_buffer_dir)
    
    try:
        # 方法1: 尝试使用Makefile
        if (ring_buffer_dir / "Makefile").exists():
            print("Using Makefile to build...")
            try:
                subprocess.run(["make", "clean"], check=False)  # 清理但不要求成功
                subprocess.run(["make"], check=True)
                print("✅ Built successfully using Makefile")
                return True
            except subprocess.CalledProcessError as e:
                print(f"❌ Makefile build failed: {e}")
        
        # 方法2: 尝试使用build.sh
        build_script = ring_buffer_dir / "build.sh"
        if build_script.exists():
            print("Using build.sh to build...")
            try:
                subprocess.run(["bash", str(build_script)], check=True)
                print("✅ Built successfully using build.sh")
                return True
            except subprocess.CalledProcessError as e:
                print(f"❌ build.sh failed: {e}")
        
        # 方法3: 直接使用gcc编译
        print("Using direct gcc compilation...")
        try:
            cmd = [
                "gcc",
                "-shared",
                "-fPIC",
                "-O3",
                "-o", "ring_buffer.so",
                "ring_buffer.c",
                "-lpthread"
            ]
            
            subprocess.run(cmd, check=True)
            print("✅ Built successfully using direct gcc")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Direct gcc compilation failed: {e}")
        except FileNotFoundError:
            print("❌ gcc not found. Please install gcc compiler.")
        
        return False
        
    finally:
        os.chdir(original_cwd)

def verify_build():
    """验证构建结果"""
    ring_buffer_dir = Path(__file__).parent / "sage_utils" / "mmap_queue"
    
    so_files = [
        ring_buffer_dir / "ring_buffer.so",
        ring_buffer_dir / "libring_buffer.so"
    ]
    
    found_libs = [f for f in so_files if f.exists()]
    
    if found_libs:
        print(f"✅ Found compiled libraries: {[str(f) for f in found_libs]}")
        return True
    else:
        print("❌ No compiled libraries found")
        return False

def main():
    """主函数"""
    print("=" * 60)
    print("SAGE Pre-build Script")
    print("=" * 60)
    
    print(f"Python version: {sys.version}")
    print(f"Platform: {platform.system()} {platform.machine()}")
    print()
    
    # 构建C库
    if build_ring_buffer():
        print("✅ C library build completed successfully")
    else:
        print("❌ C library build failed")
        print("\nTroubleshooting:")
        print("1. Make sure gcc is installed: sudo apt-get install gcc (Ubuntu/Debian)")
        print("2. Make sure build-essential is installed: sudo apt-get install build-essential")
        print("3. Check if pthread library is available")
        print("4. Try manual compilation:")
        print("   cd sage_utils/mmap_queue")
        print("   gcc -shared -fPIC -O3 -o ring_buffer.so ring_buffer.c -lpthread")
        return False
    
    # 验证构建结果
    if verify_build():
        print("✅ Build verification passed")
        return True
    else:
        print("❌ Build verification failed")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
