# conda create -n operator_test python=3.11
from setuptools import setup, find_packages

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
    
setup(
    name='sage',
    version='0.1.0',
    author='IntelliStream',
    author_email="intellistream@outlook.com",
    packages=find_packages(),
    url = "https://github.com/intellistream/SAGE",
    install_requires=parse_requirements("requirements.txt"),
    python_requires=">=3.11"
)