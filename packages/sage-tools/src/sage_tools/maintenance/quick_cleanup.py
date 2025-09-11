# Converted from quick_cleanup.sh
# SAGE项目快速清理脚本
# 清理Python缓存文件和构建文件

import os
import sys
import shutil
from pathlib import Path
from typing import List

REPO_ROOT = Path(".")

def count_and_remove(patterns: List[str], message: str) -> int:
    """计数并删除匹配的文件或目录"""
    count = 0
    for pattern in patterns:
        for item in REPO_ROOT.rglob(pattern):
            if item.is_dir():
                shutil.rmtree(item, ignore_errors=True)
            else:
                item.unlink(missing_ok=True)
            count += 1
    if count > 0:
        print(f"✅ 删除了 {count} 个 {message}")
    return count

def main():
    print("🧹 清理 SAGE 项目缓存和临时文件...")
    
    removed_count = 0
    
    # 清理 __pycache__ 目录
    print("清理 __pycache__ 目录...")
    pycache_count = count_and_remove(["__pycache__"], "__pycache__ 目录")
    removed_count += pycache_count
    
    # 清理 .pyc 和 .pyo 文件
    print("清理 .pyc/.pyo 文件...")
    pyc_count = count_and_remove(["*.pyc", "*.pyo"], ".pyc/.pyo 文件")
    removed_count += pyc_count
    
    # 清理构建文件
    print("清理构建文件...")
    build_dirs = ["build", "dist"]
    for dir_name in build_dirs:
        dir_path = REPO_ROOT / dir_name
        if dir_path.exists():
            shutil.rmtree(dir_path, ignore_errors=True)
            print(f"✅ 删除了 {dir_name}/ 目录")
            removed_count += 1
    
    # 清理 .egg-info 目录
    print("清理 .egg-info 目录...")
    egg_info_count = count_and_remove(["*.egg-info"], ".egg-info 目录")
    removed_count += egg_info_count
    
    # 清理子模块中的构建文件
    if (REPO_ROOT / "sage_ext").exists():
        sage_ext_build_count = count_and_remove(["build"], "sage_ext 子模块的构建文件", root=(REPO_ROOT / "sage_ext"))
        if sage_ext_build_count > 0:
            print("✅ 清理了 sage_ext 子模块的构建文件")
    
    # 清理空目录 (排除.git和docs-public)
    print("清理空目录...")
    empty_dirs = []
    for p in REPO_ROOT.rglob("*"):
        if p.is_dir() and not any(ex in p.parts for ex in [".git", "docs-public"]) and not any(p.rglob("*")):
            p.rmdir()
            empty_dirs.append(p)
    empty_dirs_count = len(empty_dirs)
    if empty_dirs_count > 0:
        print(f"✅ 删除了 {empty_dirs_count} 个空目录")
        removed_count += empty_dirs_count
    
    print("")
    print(f"🎉 清理完成！总共清理了 {removed_count} 个文件/目录")
    
    # 显示项目大小
    print("")
    print("当前项目大小:")
    total_size = sum(f.stat().st_size for f in REPO_ROOT.rglob("*") if f.is_file())
    print(f"{total_size / (1024*1024*1024):.2f} GB" if total_size > 1024*1024*1024 else f"{total_size / (1024*1024):.2f} MB")

if __name__ == "__main__":
    main()