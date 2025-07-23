"""
SAGE Flow Framework Setup Script

This setup script builds and installs the SAGE Flow C++ library with Python bindings.
Follows Google C++ Style Guide and integrates with the SAGE ecosystem.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

from pybind11.setup_helpers import Pybind11Extension, build_ext
from setuptools import setup, Extension, find_packages

# Package information
__version__ = "0.1.1"

# SAGE Flow project root
SAGE_FLOW_ROOT = Path(__file__).parent

# Define the extension module
ext_modules = [
    Pybind11Extension(
        "sage_flow_py",
        [
            "src/message/vector_data.cpp",
            "src/message/retrieval_context.cpp",
            "src/message/multimodal_message_core.cpp",
            "src/operator/operator.cpp", 
            "src/function/text_processing.cpp",
            "src/index/index_operators.cpp",
            "src/python/bindings.cpp",
        ],
        include_dirs=[
            str(SAGE_FLOW_ROOT / "include"),
        ],
        language="c++",
        cxx_std="17",  # C++17 standard as required
    ),
]

def build_cmake_library():
    """Build the C++ library using CMake."""
    print("Building SAGE Flow C++ library...")
    
    build_dir = SAGE_FLOW_ROOT / "build"
    if build_dir.exists():
        shutil.rmtree(build_dir)
    
    build_dir.mkdir()
    
    # Run CMake configuration
    cmake_cmd = [
        "cmake", 
        str(SAGE_FLOW_ROOT),
        "-DCMAKE_BUILD_TYPE=Release",
        "-DCMAKE_CXX_STANDARD=17",
        "-DCMAKE_CXX_STANDARD_REQUIRED=ON",
    ]
    
    try:
        subprocess.run(cmake_cmd, cwd=build_dir, check=True)
        
        # Build the library
        build_cmd = ["make", "-j4"]
        subprocess.run(build_cmd, cwd=build_dir, check=True)
        
        print("✅ C++ library built successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ CMake build failed: {e}")
        return False

class CustomBuildExt(build_ext):
    """Custom build extension that runs CMake first."""
    
    def build_extensions(self):
        # Build C++ library with CMake first
        if not build_cmake_library():
            print("Failed to build C++ library. Attempting pybind11 build...")
        
        # Continue with pybind11 build
        super().build_extensions()

def read_readme():
    """Read the README file for the long description."""
    readme_file = SAGE_FLOW_ROOT / "README.md"
    if readme_file.exists():
        return readme_file.read_text(encoding="utf-8")
    return "SAGE Flow Framework - High-performance data processing for AI applications"

def get_requirements():
    """Get package requirements."""
    return [
        "numpy>=1.19.0",
        "pybind11>=2.6.0",
    ]

def get_extra_requirements():
    """Get optional requirements for development and testing."""
    return {
        "dev": [
            "pytest>=6.0.0",
            "pytest-cov>=2.10.0",
            "black>=21.0.0",
            "mypy>=0.900",
        ],
        "test": [
            "pytest>=6.0.0",
            "pytest-benchmark>=3.4.0",
        ],
    }

# Setup configuration
setup(
    name="sage-flow",
    version=__version__,
    author="SAGE Development Team",
    author_email="sage-dev@example.com",
    description="High-performance data processing framework for SAGE AI ecosystem",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/leixy2004/SAGE",
    project_urls={
        "Documentation": "https://sage-docs.example.com",
        "Source": "https://github.com/leixy2004/SAGE",
        "Tracker": "https://github.com/leixy2004/SAGE/issues",
    },
    
    # Package discovery
    packages=find_packages(where="python"),
    package_dir={"": "python"},
    
    # Extension modules
    ext_modules=ext_modules,
    cmdclass={"build_ext": CustomBuildExt},
    
    # Requirements
    python_requires=">=3.8",
    install_requires=get_requirements(),
    extras_require=get_extra_requirements(),
    
    # Package metadata
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: C++",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    
    # Entry points
    entry_points={
        "console_scripts": [
            "sage-flow=sage_flow.cli:main",
        ],
    },
    
    # Include additional files
    include_package_data=True,
    package_data={
        "sage_flow": [
            "*.so",
            "*.dll", 
            "*.dylib",
        ],
    },
    
    # Build options
    zip_safe=False,
    
    # Keywords for PyPI
    keywords=[
        "sage", "flow", "data-processing", "machine-learning", 
        "vector-processing", "cpp", "high-performance"
    ],
)
