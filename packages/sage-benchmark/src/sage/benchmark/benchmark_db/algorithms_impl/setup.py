"""
Setup script for PyCANDYAlgo package
"""

import glob
import sys

from setuptools import Extension, setup
from setuptools.dist import Distribution


class BinaryDistribution(Distribution):
    """Distribution which always forces a binary package with platform name"""

    def has_ext_modules(self):
        return True


# 查找所有编译好的 .so 文件
so_files = glob.glob("PyCANDYAlgo*.so")

# 如果 .so 文件存在，直接使用预编译的二进制文件
if so_files:
    setup(
        name="PyCANDYAlgo",
        version="0.1.0",
        description="CANDY Algorithm implementations with Python bindings",
        author="IntelliStream",
        # 使用 py_modules 而不是 packages，因为这是一个单独的扩展模块
        py_modules=[],
        # 直接指定扩展模块的位置
        ext_modules=[
            Extension(
                name="PyCANDYAlgo",
                sources=[],  # 已经编译好，不需要源文件
            ),
        ],
        package_data={
            "": ["*.so"],
        },
        data_files=[
            ("", so_files),  # 将 .so 文件安装到 site-packages 根目录
        ],
        distclass=BinaryDistribution,
        zip_safe=False,
        python_requires=">=3.8",
        install_requires=[
            "numpy",
            "torch",
        ],
    )
else:
    print("Error: No PyCANDYAlgo*.so file found. Please run ./build.sh first.", file=sys.stderr)
    sys.exit(1)
