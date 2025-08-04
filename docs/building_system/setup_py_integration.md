# setup.py 与 pyproject.toml 联合构建

## 目录
- [概述](#概述)
- [为什么需要 setup.py](#为什么需要-setuppy)
- [构建系统架构](#构建系统架构)
- [setup.py 深度解析](#setuppy-深度解析)
- [联合构建机制](#联合构建机制)
- [SAGE 项目实例](#sage-项目实例)
- [构建流程详解](#构建流程详解)
- [故障排除](#故障排除)

## 概述

虽然 `pyproject.toml` 是现代 Python 项目的标准配置文件，但在以下场景中，`setup.py` 仍然是必需的：

1. **复杂的 C/C++ 扩展构建**
2. **自定义构建逻辑**
3. **动态配置生成**
4. **与遗留系统的兼容性**

在 SAGE 项目中，`pyproject.toml` 和 `setup.py` 协同工作，实现了现代化配置与灵活构建的完美结合。

## 为什么需要 setup.py

### 现代构建系统的限制

```toml
# pyproject.toml - 静态配置优秀，但动态能力有限
[build-system]
requires = ["setuptools>=64", "wheel"]
build-backend = "setuptools.build_meta"  # 最终还是调用 setuptools

[project]
# 静态元数据配置
name = "sage-extensions"
version = "1.0.0"
```

### setup.py 的独特优势

```python
# setup.py - 完整的 Python 编程能力
import os
import subprocess
from setuptools import setup
from setuptools.command.build_ext import build_ext

class CustomBuildExt(build_ext):
    """自定义构建逻辑"""
    def run(self):
        # 动态检测系统环境
        if not self._check_cpp_compiler():
            self._install_build_deps()
        
        # 运行自定义构建脚本
        self._run_cmake_build()
        
        # 调用标准构建流程
        super().run()
```

## 构建系统架构

### 现代 Python 构建系统层次结构

```
┌─────────────────────────────────────────┐
│              pip (安装器)                │
├─────────────────────────────────────────┤
│                                         │
│  ┌─────────────────────────────────┐    │
│  │        pyproject.toml           │    │
│  │      (配置文件)                  │    │
│  └─────────────────────────────────┘    │
│                   │                     │
│  ┌─────────────────────────────────┐    │
│  │      build backend              │    │
│  │   (setuptools.build_meta)       │    │
│  └─────────────────────────────────┘    │
│                   │                     │
│  ┌─────────────────────────────────┐    │
│  │        setup.py                 │    │
│  │    (构建实现)                    │    │
│  └─────────────────────────────────┘    │
│                   │                     │
│  ┌─────────────────────────────────┐    │
│  │      C++ 构建系统                │    │
│  │  (CMake, 编译器, linker)         │    │
│  └─────────────────────────────────┘    │
└─────────────────────────────────────────┘
```

### 配置传递机制

```toml
# pyproject.toml
[build-system]
requires = ["setuptools>=64", "pybind11"]
build-backend = "setuptools.build_meta"

[project]
name = "sage-extensions"  # 传递给 setup.py
version = "1.0.0"         # 传递给 setup.py
```

```python
# setup.py
from setuptools import setup

# setuptools 自动读取 pyproject.toml 中的 [project] 配置
setup(
    # 不需要重复指定 name, version 等
    # 但可以添加自定义构建逻辑
    cmdclass={
        'build_ext': CustomBuildExt,
    }
)
```

## setup.py 深度解析

### SAGE Extensions 的 setup.py 结构

```python
#!/usr/bin/env python3
"""
SAGE Extensions - Setup script for C++ extensions
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
from setuptools import setup, Extension
from setuptools.command.build_ext import build_ext as _build_ext
from setuptools.command.install import install as _install
```

### 自定义安装命令

```python
class CustomInstallCommand(_install):
    """自定义安装命令，确保 .so 文件被正确安装"""
    
    def run(self):
        # 1. 确保在安装前构建扩展
        self.run_command('build_ext')
        
        # 2. 运行标准安装流程
        _install.run(self)
        
        # 3. 后处理：确保 .so 文件在正确位置
        self._ensure_extension_files()
    
    def _ensure_extension_files(self):
        """确保扩展文件在安装位置"""
        import site
        
        # 查找已安装的包位置
        installed_paths = [
            os.path.join(self.install_lib, 'sage', 'extensions', 'sage_db'),
            os.path.join(site.getsitepackages()[0], 'sage', 'extensions', 'sage_db')
        ]
        
        # 复制编译好的 .so 文件
        source_dir = Path('src/sage/extensions/sage_db')
        so_files = list(source_dir.glob('*.so')) + list(source_dir.glob('*.pyd'))
        
        for install_path in installed_paths:
            if install_path and os.path.exists(install_path):
                for so_file in so_files:
                    dest = os.path.join(install_path, so_file.name)
                    if os.path.exists(str(so_file)):
                        shutil.copy2(str(so_file), dest)
                        print(f"Copied {so_file.name} to {dest}")
```

### 自定义构建命令

```python
class BuildExtCommand(_build_ext):
    """自定义构建命令"""
    
    def run(self):
        """运行构建过程"""
        # 1. 检查系统依赖
        if not self._check_system_deps():
            raise RuntimeError("System dependencies not satisfied")
        
        # 2. 运行自定义构建脚本
        build_script = Path(__file__).parent / "scripts" / "build.py"
        if build_script.exists():
            print("Running custom build script...")
            result = subprocess.run([sys.executable, str(build_script)], 
                                  capture_output=False)
            if result.returncode != 0:
                raise RuntimeError("Build failed")
    
    def _check_system_deps(self):
        """检查系统依赖"""
        print("Checking system dependencies...")
        
        # 检查关键工具
        required_tools = ["cmake", "gcc", "pkg-config"]
        missing_tools = []
        
        for tool in required_tools:
            if not self._which(tool):
                missing_tools.append(tool)
        
        if missing_tools:
            print(f"❌ Missing required tools: {', '.join(missing_tools)}")
            print("\n请安装缺失的系统依赖:")
            print("Ubuntu/Debian: sudo apt-get install build-essential cmake pkg-config")
            print("CentOS/RHEL: sudo yum install gcc-c++ cmake pkgconfig")
            print("macOS: brew install cmake gcc pkg-config")
            return False
        
        # 检查 Python 开发头文件
        try:
            import pybind11
            print("✅ pybind11 available")
        except ImportError:
            print("❌ pybind11 not found, installing...")
            subprocess.run([sys.executable, "-m", "pip", "install", "pybind11[global]"])
        
        return True
```

## 联合构建机制

### 构建流程时序图

```
用户执行: pip install .
       │
       ▼
   pip 读取 pyproject.toml
       │
       ├─ 安装 build-system.requires 中的依赖
       │  (setuptools, wheel, pybind11, cmake...)
       │
       ▼
   调用 build-backend
   (setuptools.build_meta)
       │
       ▼
   setuptools 读取 pyproject.toml [project] 配置
       │
       ├─ 项目名称: sage-extensions
       ├─ 版本: 1.0.0
       ├─ 依赖: numpy, pybind11
       │
       ▼
   setuptools 调用 setup.py
       │
       ├─ 执行 CustomInstallCommand
       │  ├─ 运行 build_ext 命令
       │  │  ├─ 检查系统依赖
       │  │  ├─ 运行 CMake 构建
       │  │  └─ 编译 C++ 扩展
       │  │
       │  ├─ 执行标准安装
       │  └─ 复制 .so 文件到正确位置
       │
       ▼
   生成 wheel 包
       │
       ▼
   安装到 Python 环境
```

### 配置合并机制

**pyproject.toml 提供静态配置：**
```toml
[project]
name = "sage-extensions"
version = "1.0.0"
dependencies = ["numpy>=1.21.0", "pybind11>=2.10.0"]
```

**setup.py 提供动态行为：**
```python
setup(
    # 静态配置从 pyproject.toml 自动读取
    # 这里只定义动态行为
    cmdclass={
        'build_ext': BuildExtCommand,      # 自定义构建
        'install': CustomInstallCommand,   # 自定义安装
    },
    # 不定义 ext_modules，使用自定义构建脚本
)
```

### 环境变量和构建选项

```python
# setup.py 中的环境感知构建
class BuildExtCommand(_build_ext):
    def run(self):
        # 检测构建环境
        build_type = os.environ.get('BUILD_TYPE', 'Release')
        parallel_jobs = os.environ.get('PARALLEL_JOBS', str(os.cpu_count()))
        
        # 根据环境调整构建参数
        cmake_args = [
            f'-DCMAKE_BUILD_TYPE={build_type}',
            f'-j{parallel_jobs}',
        ]
        
        # GPU 支持检测
        if self._has_cuda():
            cmake_args.append('-DWITH_GPU=ON')
        
        # 执行 CMake 构建
        self._run_cmake(cmake_args)
```

## SAGE 项目实例

### 工作空间级别配置传播

**根目录 pyproject.toml:**
```toml
# 定义全局开发工具配置
[tool.black]
line-length = 88
target-version = ["py311"]

[tool.mypy]
python_version = "3.11"
mypy_path = [
    "packages/sage-core/src",
    "packages/sage-extensions/src",
]
```

**扩展包的 pyproject.toml:**
```toml
# 继承全局配置，添加包特定配置
[build-system]
requires = [
    "setuptools>=64", "wheel",
    "pybind11>=2.10.0",    # C++ 绑定
    "cmake>=3.18",         # 构建系统
]

[project]
name = "sage-extensions"
dependencies = [
    "sage-core",           # 内部依赖
    "numpy>=1.21.0",       # C++ 扩展需要
]
```

**扩展包的 setup.py:**
```python
def main():
    """主安装函数"""
    setup(
        # pyproject.toml 中的配置自动应用
        cmdclass={
            'build_ext': BuildExtCommand,
            'install': CustomInstallCommand,
        },
        # 使用自定义构建而不是标准 ext_modules
    )
```

### 多包构建协调

```python
# 工作空间级别的构建脚本
def build_all_packages():
    """按依赖顺序构建所有包"""
    build_order = [
        'sage-utils',      # 基础工具，无依赖
        'sage-core',       # 核心功能，依赖 utils
        'sage-lib',        # 算法库，依赖 core
        'sage-extensions', # C++ 扩展，依赖 lib
        'sage-plugins',    # 插件系统，依赖 extensions
        'sage-service',    # 服务层，依赖 plugins
        'sage-cli',        # 命令行工具，依赖 service
    ]
    
    for package in build_order:
        package_dir = Path(f'packages/{package}')
        if package_dir.exists():
            print(f"Building {package}...")
            subprocess.run([
                sys.executable, '-m', 'pip', 'install', '-e', str(package_dir)
            ], check=True)
```

## 构建流程详解

### 开发模式安装 (pip install -e .)

```bash
# 1. 开发者执行
cd /home/flecther/SAGE/packages/sage-extensions
pip install -e .

# 2. pip 读取配置
pip 读取 pyproject.toml → 安装构建依赖 → 调用 setuptools

# 3. setuptools 执行
setuptools 读取项目配置 → 调用 setup.py → 执行自定义命令

# 4. 自定义构建
BuildExtCommand.run() → 检查依赖 → 运行构建脚本 → 编译 C++

# 5. 开发安装
创建 .egg-link 文件 → 添加到 sys.path → 可直接导入使用
```

### 生产模式安装 (pip install .)

```bash
# 1. 用户执行
pip install sage-extensions

# 2. 完整构建流程
构建依赖安装 → C++ 编译 → 创建 wheel → 安装到环境

# 3. 验证安装
python -c "import sage.extensions.sage_db; print('✅ C++ extension loaded')"
```

### 构建缓存机制

```python
# setup.py 中的缓存优化
class BuildExtCommand(_build_ext):
    def _should_rebuild(self, extension_name):
        """检查是否需要重新构建"""
        extension_dir = Path(f'src/sage/extensions/{extension_name}')
        build_dir = extension_dir / 'build'
        
        # 检查源文件修改时间
        source_files = list(extension_dir.glob('**/*.cpp')) + \
                      list(extension_dir.glob('**/*.hpp'))
        
        if not build_dir.exists():
            return True
        
        so_files = list(build_dir.glob('*.so'))
        if not so_files:
            return True
        
        # 比较时间戳
        latest_so = max(so_files, key=lambda f: f.stat().st_mtime)
        latest_source = max(source_files, key=lambda f: f.stat().st_mtime)
        
        return latest_source.stat().st_mtime > latest_so.stat().st_mtime
```

## 故障排除

### 常见问题和解决方案

#### 1. 构建依赖缺失

**问题现象：**
```
ERROR: Could not build wheels for sage-extensions
ModuleNotFoundError: No module named 'pybind11'
```

**解决方案：**
```toml
# pyproject.toml - 确保构建依赖完整
[build-system]
requires = [
    "setuptools>=64",
    "wheel",
    "pybind11>=2.10.0",  # 明确版本要求
    "numpy>=1.21.0",     # C++ 扩展需要
]
```

#### 2. 系统依赖缺失

**问题现象：**
```
cmake: command not found
gcc: command not found
```

**解决方案：**
```python
# setup.py - 智能依赖检查
def _check_system_deps(self):
    """检查并提示安装系统依赖"""
    missing_tools = []
    for tool in ["cmake", "gcc", "pkg-config"]:
        if not shutil.which(tool):
            missing_tools.append(tool)
    
    if missing_tools:
        print(f"Missing tools: {missing_tools}")
        print("Install with:")
        print("  Ubuntu: sudo apt install build-essential cmake")
        print("  macOS: brew install cmake gcc")
        return False
    return True
```

#### 3. 权限问题

**问题现象：**
```
PermissionError: [Errno 13] Permission denied: '/usr/local/lib/python3.11/site-packages/'
```

**解决方案：**
```bash
# 使用用户安装模式
pip install --user sage-extensions

# 或使用虚拟环境
python -m venv venv
source venv/bin/activate
pip install sage-extensions
```

#### 4. C++ 编译错误

**问题现象：**
```
error: 'class std::vector<double>' has no member named 'data'
```

**解决方案：**
```python
# setup.py - C++ 标准版本控制
class BuildExtCommand(_build_ext):
    def _get_cmake_args(self):
        return [
            '-DCMAKE_CXX_STANDARD=17',      # 确保 C++17 支持
            '-DCMAKE_CXX_STANDARD_REQUIRED=ON',
            '-DPYTHON_EXECUTABLE=' + sys.executable,
        ]
```

### 调试技巧

#### 1. 详细构建日志

```bash
# 启用详细输出
pip install -e . --verbose

# 保留构建文件进行调试
pip install -e . --no-clean
```

#### 2. 构建过程检查

```python
# setup.py - 添加调试输出
class BuildExtCommand(_build_ext):
    def run(self):
        print(f"Python executable: {sys.executable}")
        print(f"Python version: {sys.version}")
        print(f"Build directory: {self.build_temp}")
        print(f"Install directory: {self.build_lib}")
        
        # 检查环境变量
        for key, value in os.environ.items():
            if 'PYTHON' in key or 'CMAKE' in key:
                print(f"{key}={value}")
```

#### 3. 模块导入测试

```python
# 测试脚本
def test_extensions():
    """测试 C++ 扩展是否正确安装"""
    try:
        import sage.extensions.sage_db as db
        print("✅ sage_db extension loaded")
        
        # 测试基本功能
        result = db.test_function()
        print(f"✅ Extension function works: {result}")
        
    except ImportError as e:
        print(f"❌ Failed to import extension: {e}")
        
        # 诊断信息
        import sys
        print(f"Python path: {sys.path}")
        
        import site
        print(f"Site packages: {site.getsitepackages()}")

if __name__ == '__main__':
    test_extensions()
```

## 总结

setup.py 与 pyproject.toml 的联合构建机制实现了：

1. **配置标准化**: pyproject.toml 提供标准化的项目元数据
2. **构建灵活性**: setup.py 提供完整的构建控制能力
3. **依赖管理**: 统一的依赖声明和环境检查
4. **开发体验**: 简化的开发模式安装和调试

在 SAGE 项目中，这种机制特别适合：
- **混合语言项目**: Python + C++ 的复杂构建需求
- **多包协调**: monorepo 中多个相关包的构建依赖
- **环境适配**: 跨平台的系统依赖检查和处理

下一章：[Python C++ 项目规范](./python_cpp_project_standards.md) →
