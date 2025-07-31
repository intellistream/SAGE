# conda create -n operator_test python=3.11
from setuptools import setup, find_packages, Extension
import os
import platform
import subprocess
import re
import shutil
import sys

from Cython.Build import cythonize
import glob
from pybind11.setup_helpers import Pybind11Extension, build_ext
from pybind11 import get_cmake_dir
import pybind11




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
        "source.py",  # 临时排除，因为有 sleep 导入问题
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


# 构建C/C++扩展模块
def build_sage_ext_modules():
    """自动发现并构建sage_ext目录下的所有C/C++扩展模块"""
    ext_modules = []
    
    # sage_ext目录
    sage_ext_dir = "sage_ext"
    
    if not os.path.exists(sage_ext_dir):
        print("Warning: sage_ext directory not found")
        return ext_modules
    
    # 先构建所有模块 (这会生成.so文件)
    build_sage_ext_libraries()
    
    # 检查已经构建好的.so文件，而不是重新编译绑定
    for root, dirs, files in os.walk(sage_ext_dir):
        # 查找已构建的Python扩展模块
        for file in files:
            if file.endswith('.so') and ('_sage' in file or 'bindings' in file):
                so_path = os.path.join(root, file)
                module_info = parse_existing_so_module(so_path, sage_ext_dir)
                if module_info:
                    print(f"✓ Found pre-built extension: {module_info['module_name']} at {so_path}")
                    # 注意：这里不需要创建Extension，因为.so文件已经存在
                    # 我们只需要确保它们被正确打包
    
    # 对于没有预构建.so的绑定文件，仍然尝试用pybind11构建
    binding_files = glob.glob(os.path.join(sage_ext_dir, "**", "*bindings*.cpp"), recursive=True)
    
    for binding_file in binding_files:
        # 检查是否已经有对应的.so文件
        if has_corresponding_so_file(binding_file):
            continue  # 跳过已有.so文件的绑定
            
        try:
            # 解析模块信息
            module_info = parse_binding_module(binding_file, sage_ext_dir)
            if module_info:
                ext = create_pybind_extension(module_info)
                if ext:
                    ext_modules.append(ext)
                    print(f"✓ Added extension: {module_info['module_name']} with {len(module_info['sources'])} source files")
        except Exception as e:
            print(f"Warning: Failed to create extension for {binding_file}: {e}")
    
    return ext_modules


def has_corresponding_so_file(binding_file):
    """检查绑定文件是否已有对应的.so文件"""
    base_dir = os.path.dirname(binding_file)
    # 在绑定文件的目录及其父目录中查找.so文件
    for search_dir in [base_dir, os.path.dirname(base_dir)]:
        for file in os.listdir(search_dir):
            if file.endswith('.so') and ('_sage' in file or 'bindings' in file):
                return True
    return False


def parse_existing_so_module(so_path, sage_ext_dir):
    """解析已存在的.so模块信息"""
    so_path = os.path.normpath(so_path)
    sage_ext_dir = os.path.normpath(sage_ext_dir)
    
    # 获取相对于sage_ext的路径
    rel_path = os.path.relpath(so_path, sage_ext_dir)
    path_parts = rel_path.split(os.sep)
    
    if len(path_parts) < 2:
        return None
    
    # 模块目录 (如 sage_db, sage_queue)
    module_dir_name = path_parts[0]
    
    # 模块名 (从.so文件名推导)
    so_name = os.path.splitext(os.path.basename(so_path))[0]
    
    return {
        'module_name': f"sage_ext.{module_dir_name}.{so_name}",
        'so_path': so_path,
        'module_dir_name': module_dir_name,
        'relative_path': rel_path
    }


def parse_binding_module(binding_file, sage_ext_dir):
    """解析绑定文件，提取模块信息"""
    binding_file = os.path.normpath(binding_file)
    sage_ext_dir = os.path.normpath(sage_ext_dir)
    
    # 获取相对于sage_ext的路径
    rel_path = os.path.relpath(binding_file, sage_ext_dir)
    path_parts = rel_path.split(os.sep)
    
    if len(path_parts) < 2:
        return None
    
    # 模块目录 (如 sage_db, sage_queue)
    module_dir_name = path_parts[0]
    module_base_dir = os.path.join(sage_ext_dir, module_dir_name)
    
    # 从绑定文件中解析模块名
    module_name = extract_module_name_from_binding(binding_file)
    if not module_name:
        # 如果无法从文件中解析，使用文件名
        module_name = os.path.splitext(os.path.basename(binding_file))[0]
    
    # 构建完整的Python模块名
    python_module_name = f"sage_ext.{module_dir_name}.{module_name}"
    
    # 收集源文件
    sources = [binding_file]
    
    # 添加src目录下的cpp文件
    src_dir = os.path.join(module_base_dir, "src")
    if os.path.exists(src_dir):
        for cpp_file in glob.glob(os.path.join(src_dir, "*.cpp")):
            # 避免重复添加
            if cpp_file not in sources:
                sources.append(cpp_file)
    
    # 构建include目录列表
    include_dirs = [pybind11.get_include()]
    
    # 添加模块的include目录
    module_include = os.path.join(module_base_dir, "include")
    if os.path.exists(module_include):
        include_dirs.append(module_include)
    
    return {
        'module_name': python_module_name,
        'sources': sources,
        'include_dirs': include_dirs,
        'module_base_dir': module_base_dir,
        'module_dir_name': module_dir_name
    }


def extract_module_name_from_binding(binding_file):
    """从绑定文件中提取PYBIND11_MODULE定义的模块名"""
    try:
        with open(binding_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # 查找 PYBIND11_MODULE(module_name, m) 模式
        import re
        match = re.search(r'PYBIND11_MODULE\s*\(\s*([^,\s]+)\s*,', content)
        if match:
            return match.group(1)
    except Exception as e:
        print(f"Warning: Failed to parse module name from {binding_file}: {e}")
    
    return None


def create_pybind_extension(module_info):
    """根据模块信息创建Pybind11Extension"""
    try:
        # 基础库
        libraries = []
        
        # 根据模块类型添加特定的库
        module_dir_name = module_info['module_dir_name']
        
        if 'queue' in module_dir_name.lower():
            libraries.append('pthread')  # queue模块需要pthread
        
        ext = Pybind11Extension(
            module_info['module_name'],
            sources=module_info['sources'],
            include_dirs=module_info['include_dirs'],
            libraries=libraries,
            cxx_std=17,
            define_macros=[("VERSION_INFO", '"dev"')],
        )
        
        return ext
        
    except Exception as e:
        print(f"Error creating extension for {module_info['module_name']}: {e}")
        return None


def build_sage_ext_libraries():
    """预构建sage_ext目录下的所有库"""
    sage_ext_dir = "sage_ext"
    
    if not os.path.exists(sage_ext_dir):
        return
    
    # 自动发现所有包含build.sh的子目录
    for root, dirs, files in os.walk(sage_ext_dir):
        if 'build.sh' in files and root != sage_ext_dir:  # 排除根目录的build.sh
            module_name = os.path.basename(root)
            build_script = os.path.join(root, 'build.sh')
            
            print(f"Building {module_name}...")
            try:
                # 对于需要Python绑定的模块，我们需要确保启用Python绑定
                # 检查CMakeLists.txt或build.sh来判断是否支持Python绑定
                cmake_file = os.path.join(root, 'CMakeLists.txt')
                enable_python_bindings = False
                
                if os.path.exists(cmake_file):
                    with open(cmake_file, 'r') as f:
                        content = f.read()
                        if 'BUILD_PYTHON_BINDINGS' in content:
                            enable_python_bindings = True
                
                # 构建命令
                build_cmd = ["bash", "build.sh", "--clean"]
                
                # 如果模块支持Python绑定，我们可能需要设置环境变量
                env = os.environ.copy()
                if enable_python_bindings:
                    env['BUILD_PYTHON_BINDINGS'] = 'ON'
                    print(f"  → Enabling Python bindings for {module_name}")
                
                subprocess.run(
                    build_cmd, 
                    cwd=root, 
                    check=True,
                    capture_output=True,
                    text=True,
                    env=env
                )
                print(f"✓ {module_name} built successfully")
                
                # 检查生成的文件
                check_built_files(root, module_name)
                
            except subprocess.CalledProcessError as e:
                print(f"Warning: Failed to build {module_name}: {e}")
                if e.stdout:
                    print(f"stdout: {e.stdout}")
                if e.stderr:
                    print(f"stderr: {e.stderr}")


def check_built_files(module_dir, module_name):
    """检查模块构建后生成的文件"""
    print(f"  Checking built files for {module_name}:")
    
    # 查找.so文件
    so_files = []
    for root, dirs, files in os.walk(module_dir):
        for file in files:
            if file.endswith('.so'):
                so_path = os.path.join(root, file)
                so_files.append(so_path)
                print(f"    ✓ Found: {os.path.relpath(so_path, module_dir)}")
    
    if not so_files:
        print(f"    ⚠️  No .so files found for {module_name}")
    
    # 查找Python文件
    py_files = []
    for file in os.listdir(module_dir):
        if file.endswith('.py') and not file.startswith('test'):
            py_path = os.path.join(module_dir, file)
            py_files.append(py_path)
            print(f"    ✓ Found Python wrapper: {file}")
    
    return so_files, py_files

cythonized_files = get_py_files()
with open("cythonized_files.txt", "w") as f:
    for fn in cythonized_files:
        f.write(fn + "\n")

# 获取所有扩展模块
sage_ext_modules = build_sage_ext_modules()
cython_modules = cythonize(
    cythonized_files,
    build_dir="build",
    compiler_directives={'language_level': "3"},
)

setup(
    name='sage',
    version='0.1.2',
    author='IntelliStream',
    author_email="intellistream@outlook.com",
    description="SAGE - Stream Processing Framework for python-native distributed systems with JobManager",
    long_description=read_long_description(),
    long_description_content_type="text/markdown",
    packages=find_packages(
        include=['sage', 'sage.*', 'sage_ext', 'sage_ext.*'],
        exclude=[
            'tests', 'test',
            '*.tests', '*.tests.*',
            '*test*', '*tests*'
        ]
    ),
    url="https://github.com/intellistream/SAGE",
    install_requires=parse_requirements("installation/env_setup/requirements.txt") + [
        "pybind11>=2.6.0",
    ],
    python_requires=">=3.11",

    # 所有扩展模块
    ext_modules=sage_ext_modules + cython_modules,
    cmdclass={"build_ext": build_ext},

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
        # 动态包含sage_ext下的所有构建产物
        'sage_ext': ['**/*.so', '**/*.pyd', '**/*.py'],
        'sage_ext.sage_db': [
            '*.so', '*.pyd', '*.py', 'include/*.h', 'include/**/*.h',
            'build.sh', 'CMakeLists.txt'
        ],
        'sage_ext.sage_queue': [
            '*.so', '*.pyd', '*.py', 'include/*.h', 'include/**/*.h', 
            'build.sh', 'CMakeLists.txt'
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