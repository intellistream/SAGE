#!/usr/bin/env python3
"""
SAGE Framework Monorepo 构建钩子

这个脚本在包构建时运行，确保所有子包被正确安装。
"""

import os
import subprocess
import sys
from pathlib import Path


def build_hook():
    """构建时的钩子函数"""
    print("=== SAGE Monorepo 构建钩子 ===")
    
    # 不在构建时安装子包，而是在后安装脚本中
    # 这里只是记录信息
    root_dir = Path(__file__).parent
    
    print("检测到以下子包:")
    subpackages = [
        root_dir / "packages" / "sage-middleware",
        root_dir / "packages" / "sage-kernel", 
        root_dir / "packages" / "sage-userspace",
        root_dir / "packages" / "tools" / "sage-cli",
        root_dir / "packages" / "tools" / "sage-frontend",
        root_dir / "dev-toolkit",
    ]
    
    for pkg in subpackages:
        if pkg.exists() and (pkg / "pyproject.toml").exists():
            print(f"  ✓ {pkg.name}")
        else:
            print(f"  ✗ {pkg.name} (不存在)")
    
    print("\n注意：子包需要手动安装。")
    print("请在安装完成后运行:")
    print("  python -c \"import setup; setup.install_subpackages()\"")
    print("  或者: ./install_packages.sh")


if __name__ == "__main__":
    build_hook()
