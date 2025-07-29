# conda create -n operator_test python=3.11
from setuptools import setup, find_packages, Extension
import os
import platform
import subprocess
import re

import glob



def parse_requirements(filename):
    with open(filename, encoding="utf-8") as f:
        deps = []
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                # 简单验证是否为合法依赖格式
                if re.match(r"^[a-zA-Z0-9_\-]+(\[.*\])?([<>=!]=?.*)?$", line):
                    deps.append(line)
                else:
                    raise ValueError(f"Invalid requirement format: {line}")
        return deps


# 读取README.md作为长描述
def read_long_description():
    try:
        with open("README.md", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "SAGE - Stream Processing Framework"


# 构建C扩展模块
def build_c_extension():
    """
    注意：C++扩展现在通过CMake独立构建，不再通过setup.py管理
    - sage_ext/sage_queue: 通过CMake构建
    - sage_ext/sage_db: 通过CMake构建
    
    setup.py现在只负责安装Python部分
    """
    return []  # 返回空列表，不构建任何C扩展



setup(
    name='sage',
    version='0.1.2',
    author='IntelliStream',
    author_email="intellistream@outlook.com",
    description="SAGE - Stream Processing Framework for python-native distributed systems with JobManager",
    long_description=read_long_description(),
    long_description_content_type="text/markdown",
    packages=find_packages(
        include=['sage', 'sage.*'],
        exclude=[
            'tests', 'test',
            '*.tests', '*.tests.*',
            '*test*', '*tests*'
        ]
    ),
    url="https://github.com/intellistream/SAGE",
    install_requires=parse_requirements("installation/env_setup/requirements.txt"),
    python_requires=">=3.11",

    # C扩展模块

    # ext_modules=build_c_extension(),
    # from Cython.Build import cythonize
    ext_modules=build_c_extension() ,

    entry_points={
        'console_scripts': [
            'sage=sage.cli.main:app',
            'sage-jm=sage.cli.job:app',  # 保持向后兼容
        ],
    },
    include_package_data=True,
    package_data={
        'sage.core': ['config/*.yaml'],
        'sage_deployment': ['scripts/*.sh', 'templates/*'],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)