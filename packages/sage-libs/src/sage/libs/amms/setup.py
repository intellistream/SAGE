"""Setup script for isage-amms package.

This setup.py handles the building of C++ extensions for AMM algorithms.
"""

import os
import subprocess
import sys
from pathlib import Path

from setuptools import Extension, setup
from setuptools.command.build_ext import build_ext


class CMakeExtension(Extension):
    """Extension that uses CMake to build."""

    def __init__(self, name: str, sourcedir: str = "") -> None:
        super().__init__(name, sources=[])
        self.sourcedir = os.path.abspath(sourcedir)


class CMakeBuild(build_ext):
    """Custom build command that runs CMake."""

    def run(self):
        """Run CMake build."""
        try:
            subprocess.check_output(["cmake", "--version"])
        except OSError:
            raise RuntimeError(
                "CMake must be installed to build the following extensions: "
                + ", ".join(e.name for e in self.extensions)
            )

        for ext in self.extensions:
            self.build_extension(ext)

    def build_extension(self, ext):
        """Build a single extension."""
        extdir = os.path.abspath(os.path.dirname(self.get_ext_fullpath(ext.name)))
        cmake_args = [
            f"-DCMAKE_LIBRARY_OUTPUT_DIRECTORY={extdir}",
            f"-DPYTHON_EXECUTABLE={sys.executable}",
            "-DENABLE_PYBIND=ON",
            "-DENABLE_UNIT_TESTS=OFF",
        ]

        # Get PyTorch CMake prefix path
        try:
            import torch

            torch_path = torch.utils.cmake_prefix_path
            cmake_args.append(f"-DCMAKE_PREFIX_PATH={torch_path}")
        except ImportError:
            print("Warning: PyTorch not found, building without PyTorch support")

        cfg = "Debug" if self.debug else "Release"
        build_args = ["--config", cfg]

        # Platform-specific configuration
        cmake_args += [f"-DCMAKE_BUILD_TYPE={cfg}"]

        # Memory optimization flags
        if os.environ.get("AMMS_LOW_MEMORY_BUILD", "0") == "1":
            cmake_args += [
                "-DCMAKE_CXX_FLAGS=-g0 -O0 -fno-var-tracking",
                "-DCMAKE_UNITY_BUILD=ON",
                "-DCMAKE_UNITY_BUILD_BATCH_SIZE=2",
            ]

        # CUDA support
        if os.environ.get("AMMS_ENABLE_CUDA", "0") == "1":
            cmake_args.append("-DENABLE_CUDA=ON")
            cuda_path = os.environ.get("CUDA_HOME", "/usr/local/cuda")
            cmake_args.append(f"-DCUDACXX={cuda_path}/bin/nvcc")

        # Number of parallel jobs
        max_jobs = os.cpu_count() or 1
        build_args += [f"-j{max_jobs}"]

        env = os.environ.copy()
        env["CXXFLAGS"] = (
            f'{env.get("CXXFLAGS", "")} -DVERSION_INFO=\\"{self.distribution.get_version()}\\"'
        )

        if not os.path.exists(self.build_temp):
            os.makedirs(self.build_temp)

        print(f"Building in {self.build_temp}")
        print(f"CMake args: {cmake_args}")

        # Run CMake configure
        subprocess.check_call(["cmake", ext.sourcedir] + cmake_args, cwd=self.build_temp, env=env)

        # Run CMake build
        subprocess.check_call(["cmake", "--build", "."] + build_args, cwd=self.build_temp, env=env)


# Read long description from README
readme_path = Path(__file__).parent / "README.md"
long_description = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""

setup(
    long_description=long_description,
    long_description_content_type="text/markdown",
    ext_modules=[CMakeExtension("PyAMM", sourcedir="implementations")],
    cmdclass={"build_ext": CMakeBuild},
    zip_safe=False,
)
