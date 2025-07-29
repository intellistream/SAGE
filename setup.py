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
    """构建ring_buffer C扩展"""
    # 注意：C++扩展现在通过CMake独立构建，不再依赖这个路径
    # ring_buffer_dir = "sage/utils/mmap_queue"  # 过时路径

    # 检查是否已有编译好的库
    so_files = [
        os.path.join(ring_buffer_dir, "ring_buffer.so"),
        os.path.join(ring_buffer_dir, "libring_buffer.so")
    ]

    # 如果没有编译好的库，尝试编译
    if not any(os.path.exists(f) for f in so_files):
        print("Compiling ring_buffer C library...")
        try:
            # 尝试使用Makefile编译
            if os.path.exists(os.path.join(ring_buffer_dir, "Makefile")):
                subprocess.run(["make", "-C", ring_buffer_dir], check=True)
            # 或者使用build.sh
            elif os.path.exists(os.path.join(ring_buffer_dir, "build.sh")):
                subprocess.run(["bash", os.path.join(ring_buffer_dir, "build.sh")], check=True)
            else:
                print("Warning: No build system found for ring_buffer")
        except subprocess.CalledProcessError as e:
            print(f"Warning: Failed to compile ring_buffer: {e}")

    # 定义C扩展
    ext_modules = []

    # 如果有C源文件，添加扩展模块
    # 注意：sage_ext 模块（如 sage_queue、sage_db）现在使用独立的 CMake 构建系统
    # 不再通过 setup.py 管理C++扩展

    return ext_modules



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