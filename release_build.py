# conda create -n operator_test python=3.11
from setuptools import setup, find_packages, Extension
import os
import platform
import subprocess
import re

from Cython.Build import cythonize
import glob




def get_py_files():
    # 排除这些目录下所有py
    ignore_dirs = [
        "tests",
        "test",
        "example",
        "__pycache__",
        "cli",

    ]

    # 文件名或路径中出现这些关键词的也排除
    ignore_keywords = [
        "test",
        "example",
        "base",
        "abc",
        "interface",
        "protocol",
        "main",
        "job",
        "base"
    ]

    # 需要明确排除的具体文件（有报错的可手动加进来）
    ignore_files = [
        "main.py",
        # 如遇到 cythonize 报错文件可加在这里
    ]

    py_files = []
    for path in glob.glob("sage/**/*.py", recursive=True):
        norm_path = path.replace("\\", "/")
        path_parts = norm_path.split("/")

        # 跳过明确的目录
        if any(igdir in path_parts for igdir in ignore_dirs):
            continue
        # 跳过文件名/路径中有关键词的
        if any(kw in norm_path for kw in ignore_keywords):
            continue
        # 跳过明确排除文件
        if any(norm_path.endswith("/"+fname) for fname in ignore_files):
            continue
        py_files.append(path)
    return py_files



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
    ring_buffer_dir = "sage.utils/mmap_queue"

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
    c_source = os.path.join(ring_buffer_dir, "ring_buffer.c")
    if os.path.exists(c_source):
        ring_buffer_ext = Extension(
            'sage.utils.mmap_queue.ring_buffer',
            sources=[c_source],
            include_dirs=[ring_buffer_dir],
            libraries=['pthread'],  # Linux下需要pthread
            extra_compile_args=['-O3', '-fPIC'],
            extra_link_args=['-shared'] if platform.system() != 'Darwin' else []
        )
        ext_modules.append(ring_buffer_ext)

    return ext_modules

cythonized_files = get_py_files()
with open("cythonized_files.txt", "w") as f:
    for fn in cythonized_files:
        f.write(fn + "\n")
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
    ext_modules=build_c_extension() + cythonize(
        cythonized_files,
        build_dir="build",
        compiler_directives={'language_level': "3"},
    ),


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
        'sage.utils.mmap_queue': [
            '*.so', '*.c', '*.h', 'Makefile', 'build.sh',
            'README.md', 'USAGE_SUMMARY.md', 'IMPLEMENTATION_SUMMARY.md'
        ],
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

# 不稳定版本 7.26 
# # conda create -n operator_test python=3.11
# from setuptools import setup, find_packages, Extension
# import os
# import platform
# import subprocess
# import re
# from Cython.Build import cythonize
# import glob

# def get_py_files():
#     py_files = []
#     for path in glob.glob("sage/**/*.py", recursive=True):
#         if "test" not in path and "tests" not in path:
#             py_files.append(path)
#     return py_files

# def parse_requirements(filename):
#     with open(filename, encoding="utf-8") as f:
#         deps = []
#         for line in f:
#             line = line.strip()
#             if line and not line.startswith("#"):
#                 # 简单验证是否为合法依赖格式
#                 if re.match(r"^[a-zA-Z0-9_\-]+(\[.*\])?([<>=!]=?.*)?$", line):
#                     deps.append(line)
#                 else:
#                     raise ValueError(f"Invalid requirement format: {line}")
#         return deps

# # 读取README.md作为长描述
# def read_long_description():
#     try:
#         with open("README.md", encoding="utf-8") as f:
#             return f.read()
#     except FileNotFoundError:
#         return "SAGE - Stream Processing Framework"

# # 构建C扩展模块
# def build_c_extension():
#     """构建ring_buffer C扩展"""
#     ring_buffer_dir = "sage.utils/mmap_queue"
    
#     # 检查是否已有编译好的库
#     so_files = [
#         os.path.join(ring_buffer_dir, "ring_buffer.so"),
#         os.path.join(ring_buffer_dir, "libring_buffer.so")
#     ]
    
#     # 如果没有编译好的库，尝试编译
#     if not any(os.path.exists(f) for f in so_files):
#         print("Compiling ring_buffer C library...")
#         try:
#             # 尝试使用Makefile编译
#             if os.path.exists(os.path.join(ring_buffer_dir, "Makefile")):
#                 subprocess.run(["make", "-C", ring_buffer_dir], check=True)
#             # 或者使用build.sh
#             elif os.path.exists(os.path.join(ring_buffer_dir, "build.sh")):
#                 subprocess.run(["bash", os.path.join(ring_buffer_dir, "build.sh")], check=True)
#             else:
#                 print("Warning: No build system found for ring_buffer")
#         except subprocess.CalledProcessError as e:
#             print(f"Warning: Failed to compile ring_buffer: {e}")
    
#     # 定义C扩展
#     ext_modules = []
    
#     # 如果有C源文件，添加扩展模块
#     c_source = os.path.join(ring_buffer_dir, "ring_buffer.c")
#     if os.path.exists(c_source):
#         ring_buffer_ext = Extension(
#             'sage.utils.mmap_queue.ring_buffer',
#             sources=[c_source],
#             include_dirs=[ring_buffer_dir],
#             libraries=['pthread'],  # Linux下需要pthread
#             extra_compile_args=['-O3', '-fPIC'],
#             extra_link_args=['-shared'] if platform.system() != 'Darwin' else []
#         )
#         ext_modules.append(ring_buffer_ext)
    
#     return ext_modules

# setup(
#     name='sage',
#     version='0.1.1',
#     author='IntelliStream',
#     author_email="intellistream@outlook.com",
#     description="SAGE - Stream Processing Framework for python-native distributed systems with JobManager",
#     long_description=read_long_description(),
#     long_description_content_type="text/markdown",
#     packages=find_packages(
#         include=['sage', 'sage.*'],
#         exclude=[
#             'tests', 'test', 
#             '*.tests', '*.tests.*', 
#             '*test*', '*tests*'
#         ]
#     ),
#     url = "https://github.com/intellistream/SAGE",
#     install_requires=parse_requirements("installation/env_setup/requirements.txt"),
#     python_requires=">=3.11",
    
#     # C扩展模块
#         # ext_modules=build_c_extension(),
#     # from Cython.Build import cythonize
#     ext_modules = cythonize(
#         get_py_files(),
#         build_dir="build",
#         compiler_directives={'language_level': "3"},
#     ),


#     entry_points={
#             'console_scripts': [
#                 'sage=sage.cli.main:app',
#                 'sage-jm=sage.cli.job:app',  # 保持向后兼容
#             ],
#         },
#     include_package_data=True,
#     package_data={
#         'sage.core': ['config/*.yaml'],
#         'sage_deployment': ['scripts/*.sh', 'templates/*'],
#         'sage.utils.mmap_queue': [
#             '*.so', '*.c', '*.h', 'Makefile', 'build.sh',
#             'README.md', 'USAGE_SUMMARY.md', 'IMPLEMENTATION_SUMMARY.md'
#         ],
#     },
#     classifiers=[
#         "Development Status :: 3 - Alpha",
#         "Intended Audience :: Developers",
#         "License :: OSI Approved :: Apache Software License",
#         "Programming Language :: Python :: 3",
#         "Programming Language :: Python :: 3.11",
#         "Programming Language :: Python :: 3.12",
#     ],
# )