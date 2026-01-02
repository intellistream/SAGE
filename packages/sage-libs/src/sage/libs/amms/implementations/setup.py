import glob
import os
import shutil
import subprocess
import sys

from setuptools import Extension, setup
from setuptools.command.build_ext import build_ext


class CMakeExtension(Extension):
    def __init__(self, name, sourcedir=""):
        Extension.__init__(self, name, sources=[])
        self.sourcedir = os.path.abspath(sourcedir)


class CMakeBuild(build_ext):
    def run(self):
        # Check if CMake is installed
        try:
            subprocess.check_output(["cmake", "--version"])
        except OSError:
            raise RuntimeError(
                "CMake must be installed to build the following extensions: "
                + ", ".join(e.name for e in self.extensions)
            )

        # Set environment variables
        os.environ["CUDACXX"] = "/usr/local/cuda/bin/nvcc"
        if sys.platform == "linux":
            os.environ["LD_LIBRARY_PATH"] = "/path/to/custom/libs:" + os.environ.get(
                "LD_LIBRARY_PATH", ""
            )

        for ext in self.extensions:
            self.build_extension(ext)

    def build_extension(self, ext):
        extdir = os.path.abspath(os.path.dirname(self.get_ext_fullpath(ext.name)))
        os.system("python3 -c 'import torch;print(torch.utils.cmake_prefix_path)' >> 1.txt")
        with open("1.txt") as file:
            torchCmake = file.read().rstrip("\n")
        os.system("rm 1.txt")
        os.system("nproc >> 1.txt")
        with open("1.txt") as file:
            threads = file.read().rstrip("\n")
        os.system("rm 1.txt")
        os.system("cd thirdparty&&./makeClean.sh&&./installPAPI.sh")
        print(threads)
        cmake_args = [
            "-DCMAKE_LIBRARY_OUTPUT_DIRECTORY=" + extdir,
            "-DPYTHON_EXECUTABLE=" + sys.executable,
            "-DCMAKE_PREFIX_PATH=" + torchCmake,
            "-DENABLE_HDF5=ON",
            "-DENABLE_PYBIND=ON",
            "-DCMAKE_INSTALL_PREFIX=/usr/local/lib",  # pragma: allowlist secret
            "-DENABLE_PAPI=ON",
        ]

        cfg = "Debug" if self.debug else "Release"
        cmake_args += ["-DCMAKE_BUILD_TYPE=" + cfg]

        build_args = ["--config", cfg]
        build_args += ["--", "-j" + threads]
        if not os.path.exists(self.build_temp):
            os.makedirs(self.build_temp)
        subprocess.run(["cmake", ext.sourcedir] + cmake_args, cwd=self.build_temp, check=True)
        subprocess.run(["cmake", "--build", "."] + build_args, cwd=self.build_temp, check=True)
        # Now copy all *.so files from the build directory to the final installation directory
        so_files = glob.glob(os.path.join(self.build_temp, "*.so"))
        for file in so_files:
            shutil.copy(file, extdir)


setup(
    name="PyAMM",
    version="0.1.1",
    author="IntelliStream Team",
    author_email="shuhao_zhang@hust.edu.cn",
    description="LibAMM: Approximate Matrix Multiplication Library with NumPy interface",
    long_description="A high-performance library for approximate matrix multiplication algorithms, "
    "providing a NumPy-based Python interface while internally using PyTorch for computation.",
    long_description_content_type="text/plain",
    url="https://github.com/intellistream/LibAMM",
    ext_modules=[CMakeExtension(".")],
    cmdclass={
        "build_ext": CMakeBuild,
    },
    # Runtime dependencies
    install_requires=[
        "numpy>=1.20.0",  # NumPy interface for Python users
        "torch>=2.0.0",  # Required by LibAMM internally (DO NOT REMOVE)
        "pybind11>=2.10.0",  # Python bindings
    ],
    python_requires=">=3.8",
    zip_safe=False,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Mathematics",
        "Programming Language :: C++",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
