#!/usr/bin/env python3
"""
SAGE Framework Monorepo Setup Script

这个脚本用于在 Monorepo 工作空间中安装所有子包。
当运行 pip install . 时会自动安装所有子包。
"""

import os
import subprocess
import sys
from pathlib import Path
from setuptools import setup, find_packages
from setuptools.command.install import install
from setuptools.command.develop import develop


def install_subpackages():
    """安装所有子包"""
    print("\n=== 正在安装 SAGE 子包 ===")
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
    failed_packages = []
    
    for package_path in packages_to_install:
        if package_path.exists() and (package_path / "pyproject.toml").exists():
            try:
                print(f"正在安装: {package_path.name}")
                result = subprocess.run([
                    sys.executable, "-m", "pip", "install", "-e", str(package_path)
                ], check=True, capture_output=True, text=True)
                success_count += 1
                print(f"✓ 成功安装: {package_path.name}")
            except subprocess.CalledProcessError as e:
                failed_packages.append(package_path.name)
                print(f"✗ 安装失败: {package_path.name}")
                print(f"  错误: {e.stderr}")
    
    print(f"\n=== 安装完成 ===")
    print(f"成功安装: {success_count} 个子包")
    if failed_packages:
        print(f"安装失败: {', '.join(failed_packages)}")
        print("\n建议手动运行: ./install_packages.sh")
    else:
        print("🎉 所有子包安装成功！")


class PostInstallCommand(install):
    """安装后执行的自定义命令"""
    def run(self):
        install.run(self)
        install_subpackages()


class PostDevelopCommand(develop):
    """开发模式安装后执行的自定义命令"""
    def run(self):
        develop.run(self)
        install_subpackages()


# 如果直接运行此脚本，执行安装
if __name__ == "__main__":
    if len(sys.argv) == 1:
        # 直接运行脚本时执行安装
        install_subpackages()
    else:
        # 通过 pip 调用时使用标准 setup
        setup(
            name="sage-workspace",
            version="1.0.0", 
            description="SAGE Framework Monorepo Workspace",
            py_modules=[],  # 空的，因为这是一个元包
            cmdclass={
                'install': PostInstallCommand,
                'develop': PostDevelopCommand,
            }
        )
else:
    # 被导入时也提供 setup 配置
    setup(
        name="sage-workspace",
        version="1.0.0",
        description="SAGE Framework Monorepo Workspace", 
        py_modules=[],
        cmdclass={
            'install': PostInstallCommand,
            'develop': PostDevelopCommand,
        }
    )
