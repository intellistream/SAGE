# conda create -n operator_test python=3.11
from setuptools import setup, find_packages

def parse_requirements(filename):
    with open(filename, encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]
    
setup(
    name='sage',
    version='0.1.0',
    author='IntelliStream',
    author_email="intellistream@outlook.com",
    packages=find_packages(),
    url = "https://github.com/intellistream/SAGE",
    install_requires=parse_requirements("requirements.txt"),
    python_requires=">=3.11",
)