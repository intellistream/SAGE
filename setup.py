#!/usr/bin/env python3
"""
SAGE 智能安装包
自动检测商业许可并安装相应功能
"""

import os
import sys
from pathlib import Path
from setuptools import setup, find_packages

def check_commercial_license():
    """检查是否有商业许可"""
    # 方法1: 检查环境变量
    if os.getenv('SAGE_LICENSE_KEY'):
        return True
    
    # 方法2: 检查许可文件
    license_file = Path.home() / '.sage' / 'license.key'
    if license_file.exists():
        return True
    
    # 方法3: 检查商业包是否可用
    commercial_pkg = Path(__file__).parent / 'packages' / 'commercial'
    if commercial_pkg.exists():
        return True
    
    return False

def get_install_requires():
    """根据许可情况决定安装哪些包"""
    # 基础包 (始终安装)
    base_requires = [
        './packages/sage-kernel',
        './packages/sage-tools/sage-dev-toolkit',
        './packages/sage-tools/sage-cli',
    ]
    
    # 检查商业许可
    if check_commercial_license():
        print("🏢 检测到商业许可，安装企业版功能...")
        commercial_requires = [
            './packages/commercial/sage-middleware',
            './packages/commercial/sage-userspace',
            './packages/commercial/sage-kernel',  # 增强版
        ]
        return base_requires + commercial_requires
    else:
        print("🌍 使用开源版本...")
        open_requires = [
            './packages/sage-middleware',
            './packages/sage-userspace',
        ]
        return base_requires + open_requires

def get_entry_points():
    """定义命令行入口点"""
    return {
        'console_scripts': [
            'sage=sage.cli:main',
            'sage-license=scripts.sage_license:main',
        ],
    }

# 读取README
readme_file = Path(__file__).parent / 'README.md'
long_description = readme_file.read_text(encoding='utf-8') if readme_file.exists() else ""

setup(
    name="sage",
    version="1.0.0",
    description="SAGE - Streaming Analytics and Graph Engine",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="SAGE Team",
    author_email="team@sage.com",
    url="https://github.com/intellistream/SAGE",
    
    # 动态依赖
    install_requires=get_install_requires(),
    
    # 可选依赖
    extras_require={
        'dev': [
            'pytest>=7.0',
            'pytest-asyncio',
            'pytest-cov',
            'black',
            'isort',
            'flake8',
            'mypy',
            'ipython',
            'jupyter',
        ],
        'docs': [
            'sphinx',
            'sphinx-rtd-theme',
        ],
    },
    
    # 命令行工具
    entry_points=get_entry_points(),
    
    # 包分类
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    
    python_requires=">=3.8",
    
    # 包发现
    packages=find_packages(),
    include_package_data=True,
    
    # 项目URLs
    project_urls={
        "Bug Reports": "https://github.com/intellistream/SAGE/issues",
        "Source": "https://github.com/intellistream/SAGE",
        "Documentation": "https://sage.readthedocs.io/",
    },
)
