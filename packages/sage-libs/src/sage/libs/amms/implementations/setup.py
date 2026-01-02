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
        # PAPI 智能检测：如果系统安装了 libpapi-dev，自动启用；否则禁用
        print(threads)

        # 智能检测 PAPI 是否可用
        def check_papi_available():
            """检查系统是否安装了 libpapi-dev"""
            import subprocess

            try:
                # 方法1: 使用 pkg-config 检测
                result = subprocess.run(
                    ["pkg-config", "--exists", "papi"], capture_output=True, timeout=5
                )
                if result.returncode == 0:
                    return True

                # 方法2: 查找库文件
                import pathlib

                papi_paths = [
                    "/usr/lib/libpapi.so",
                    "/usr/lib/x86_64-linux-gnu/libpapi.so",
                    "/usr/local/lib/libpapi.so",
                ]
                for path in papi_paths:
                    if pathlib.Path(path).exists():
                        return True

                return False
            except Exception:
                return False

        # 决定是否启用 PAPI
        env_papi = os.environ.get("ENABLE_AMMS_PAPI", "auto")

        if env_papi == "1" or env_papi.lower() == "on" or env_papi.lower() == "true":
            # 用户强制启用
            enable_papi = True
            print("✓ PAPI support enabled (forced by ENABLE_AMMS_PAPI)")
        elif env_papi == "0" or env_papi.lower() == "off" or env_papi.lower() == "false":
            # 用户强制禁用
            enable_papi = False
            print("ℹ PAPI support disabled (forced by ENABLE_AMMS_PAPI)")
        else:
            # 自动检测（默认）
            enable_papi = check_papi_available()
            if enable_papi:
                print("✓ PAPI support auto-enabled (libpapi-dev detected)")
            else:
                print("ℹ PAPI support auto-disabled (libpapi-dev not found)")
                print("  Install with: sudo apt-get install libpapi-dev")

        # 决定是否启用 CUDA
        # 检测方式：
        # 1. 环境变量 ENABLE_CUDA=1
        # 2. 检查是否安装了 cuda extra (通过检查 torch+cu 版本)
        env_cuda = os.environ.get("ENABLE_CUDA", "auto")

        def check_cuda_available():
            """检查 PyTorch 是否支持 CUDA"""
            try:
                import torch

                return torch.cuda.is_available()
            except Exception:
                return False

        if env_cuda == "1" or env_cuda.lower() == "on" or env_cuda.lower() == "true":
            enable_cuda = True
            print("✓ CUDA support enabled (forced by ENABLE_CUDA)")
        elif env_cuda == "0" or env_cuda.lower() == "off" or env_cuda.lower() == "false":
            enable_cuda = False
            print("ℹ CUDA support disabled (forced by ENABLE_CUDA)")
        else:
            # 自动检测 CUDA
            enable_cuda = check_cuda_available()
            if enable_cuda:
                print("✓ CUDA support auto-enabled (PyTorch CUDA detected)")
            else:
                print("ℹ CUDA support auto-disabled (CPU-only PyTorch or no GPU)")

        cmake_args = [
            "-DCMAKE_LIBRARY_OUTPUT_DIRECTORY=" + extdir,
            "-DPYTHON_EXECUTABLE=" + sys.executable,
            "-DCMAKE_PREFIX_PATH=" + torchCmake,
            "-DENABLE_HDF5=ON",
            "-DENABLE_PYBIND=ON",
            "-DCMAKE_INSTALL_PREFIX=/usr/local/lib",  # pragma: allowlist secret
            "-DENABLE_PAPI=ON" if enable_papi else "-DENABLE_PAPI=OFF",
        ]

        # 添加 CUDA 相关配置
        if enable_cuda:
            cmake_args.append("-DENABLE_CUDA=ON")
            # 可选：设置 CUDA 架构
            cuda_arch = os.environ.get("CUDA_ARCH", "")
            if cuda_arch:
                cmake_args.append(f"-DCMAKE_CUDA_ARCHITECTURES={cuda_arch}")
        else:
            cmake_args.append("-DENABLE_CUDA=OFF")

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
    # Optional dependencies (extras)
    extras_require={
        # CUDA support: Install PyTorch with CUDA
        # Usage: pip install isage-amms[cuda]
        "cuda": [
            # Note: User should install PyTorch with CUDA manually:
            # pip install torch --index-url https://download.pytorch.org/whl/cu121
            # We just document it here, actual CUDA detection is automatic
        ],
        # Development dependencies
        "dev": [
            "pytest>=7.0.0",
            "black>=23.0.0",
            "mypy>=1.0.0",
        ],
    },
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
