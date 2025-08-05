"""
Optimized setup.py for SAGE with locked dependencies
This version prioritizes installation speed over flexibility
"""

from setuptools import setup, find_packages

# Read locked requirements
with open('requirements-lock.txt', 'r') as f:
    locked_requirements = [
        line.strip() 
        for line in f 
        if line.strip() and not line.startswith('#') and '==' in line
    ]

setup(
    name="sage-optimized",
    version="1.0.0",
    description="SAGE Framework (Optimized for Fast Installation)",
    long_description="SAGE Framework with locked dependencies for fastest installation experience",
    packages=find_packages(),
    install_requires=locked_requirements,
    python_requires=">=3.10",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
