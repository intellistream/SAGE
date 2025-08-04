#!/usr/bin/env python3
"""
SAGE Framework Monorepo Setup Script

这个脚本用于在 Monorepo 工作空间中安装所有子包。
它会自动发现并安装以下包：
- packages/sage-kernel
- packages/sage-middleware  
- packages/sage-userspace
- packages/tools/sage-cli
- packages/tools/sage-frontend
- packages/commercial/* (如果存在)
- dev-toolkit
"""

import os
import subprocess
import sys
from pathlib import Path
from setuptools import setup
from setuptools.command.install import install
from setuptools.command.develop import develop


class PostInstallCommand(install):
    """安装后执行的自定义命令"""
    def run(self):
        install.run(self)
        self.install_subpackages()

    def install_subpackages(self):
        """安装所有子包"""
        print("\n=== 安装 SAGE 子包 ===")
        root_dir = Path(__file__).parent
        
        # 定义安装顺序（考虑依赖关系）
        packages_to_install = [
            root_dir / "packages" / "sage-middleware",
            root_dir / "packages" / "sage-kernel", 
            root_dir / "packages" / "sage-userspace",
            root_dir / "packages" / "tools" / "sage-cli",
            root_dir / "packages" / "tools" / "sage-frontend",
            root_dir / "dev-toolkit",
        ]
        
        # 添加商业包（如果存在）
        commercial_dir = root_dir / "packages" / "commercial"
        if commercial_dir.exists():
            packages_to_install.extend([
                commercial_dir / "sage-middleware",
                commercial_dir / "sage-kernel",
                commercial_dir / "sage-userspace",
            ])
        
        success_count = 0
        for package_path in packages_to_install:
            if package_path.exists() and (package_path / "pyproject.toml").exists():
                try:
                    print(f"安装: {package_path.name}")
                    subprocess.run([
                        sys.executable, "-m", "pip", "install", "-e", str(package_path)
                    ], check=True)
                    success_count += 1
                    print(f"✓ 成功安装: {package_path.name}")
                except subprocess.CalledProcessError as e:
                    print(f"✗ 安装失败: {package_path.name}")
        
        print(f"\n🎉 成功安装 {success_count} 个子包")


class PostDevelopCommand(develop):
    """开发模式安装后执行的自定义命令"""
    def run(self):
        develop.run(self)
        PostInstallCommand.install_subpackages(self)


# 使用 setuptools 的标准配置，但添加自定义安装命令
setup(
    cmdclass={
        'install': PostInstallCommand,
        'develop': PostDevelopCommand,
    }
)
