# conda create -n operator_test python=3.11
from setuptools import setup, find_packages
import os

import re

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

setup(
    name='sage',
    version='0.1.1',
    author='IntelliStream',
    author_email="intellistream@outlook.com",
    description="SAGE - Stream Processing Framework with JobManager",
    long_description=read_long_description(),
    long_description_content_type="text/markdown",
    packages=find_packages(),
    url = "https://github.com/intellistream/SAGE",
    install_requires=parse_requirements("installation/env_setup/requirements.txt"),
    python_requires=">=3.11",
    entry_points={
        'console_scripts': [
            'sage-deploy=deployment.app.cli.sage_deploy:app',
            'sage=deployment.app.cli.sage:app',
        ],
    },
    include_package_data=True,
    package_data={
        'sage_core': ['config/*.yaml'],
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