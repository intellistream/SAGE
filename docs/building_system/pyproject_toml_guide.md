# pyproject.toml 详解

## 目录
- [概述](#概述)
- [文件结构](#文件结构)
- [核心配置详解](#核心配置详解)
- [依赖管理](#依赖管理)
- [工具配置](#工具配置)
- [SAGE 项目实例分析](#sage-项目实例分析)
- [最佳实践](#最佳实践)

## 概述

`pyproject.toml` 是 Python 项目的现代化配置文件，基于 [PEP 518](https://peps.python.org/pep-0518/)、[PEP 621](https://peps.python.org/pep-0621/) 等标准制定。它统一了项目元数据、构建配置、依赖管理和开发工具配置。

### 为什么使用 pyproject.toml？

**传统方式的问题：**
```python
# setup.py - 复杂且容易出错
from setuptools import setup, find_packages

setup(
    name="my-package",
    version="1.0.0",
    # 大量重复的样板代码
    # 与其他配置文件分离（requirements.txt, setup.cfg, tox.ini...）
)
```

**现代方式的优势：**
```toml
# pyproject.toml - 简洁且标准化
[project]
name = "my-package"
version = "1.0.0"
# 统一配置，工具链标准化
```

## 文件结构

pyproject.toml 文件主要由以下几个部分组成：

```toml
[build-system]      # 构建系统配置
[project]           # 项目元数据
[project.scripts]   # 命令行脚本
[project.gui-scripts] # GUI 脚本
[project.optional-dependencies] # 可选依赖组
[project.urls]      # 项目相关链接
[tool.*]           # 各种开发工具的配置
```

## 核心配置详解

### 1. 构建系统配置 (build-system)

```toml
[build-system]
requires = ["setuptools>=64", "wheel"]  # 构建时需要的依赖
build-backend = "setuptools.build_meta" # 构建后端
```

**详细说明：**
- `requires`: 构建过程中需要安装的依赖包
- `build-backend`: 指定使用哪个构建后端（setuptools, flit, poetry 等）

**SAGE 项目示例：**
```toml
[build-system]
requires = [
    "setuptools>=64", 
    "wheel",
    "pybind11>=2.10.0",  # C++ 绑定
    "cmake>=3.18",       # C++ 构建系统
    "numpy>=1.21.0",     # NumPy C API
]
build-backend = "setuptools.build_meta"
```

### 2. 项目元数据 (project)

```toml
[project]
name = "sage-workspace"                    # 项目名称
version = "1.0.0"                         # 版本号
description = "SAGE Framework"            # 简短描述
readme = "README.md"                      # README 文件
requires-python = ">=3.10"               # Python 版本要求
license = "Apache-2.0"                   # 许可证
authors = [                              # 作者信息
    {name = "IntelliStream Team", email = "sage@intellistream.cc"},
]
keywords = ["rag", "llm", "framework"]   # 关键词
classifiers = [                          # PyPI 分类器
    "Development Status :: 4 - Beta",
    "Programming Language :: Python :: 3",
]
dependencies = []                        # 运行时依赖
```

**版本管理策略：**
- **静态版本**: 直接在 toml 中指定 `version = "1.0.0"`
- **动态版本**: 使用 `dynamic = ["version"]` 从代码中读取
- **版本文件**: 从单独的版本文件中读取

### 3. 依赖管理系统

#### 运行时依赖
```toml
[project]
dependencies = [
    "numpy>=1.21.0",
    "requests>=2.28.0",
    "pydantic>=1.10.0",
]
```

#### 可选依赖组
```toml
[project.optional-dependencies]
# 基础安装
basic = [
    "sage-utils",
    "sage-kernel",
]

# 扩展功能
extended = [
    "sage-utils",
    "sage-kernel", 
    "sage-extensions",  # C++ 扩展
]

# 开发环境
dev = [
    "pytest>=7.0.0",
    "black>=23.0.0",
    "mypy>=1.0.0",
]

# 测试环境
test = [
    "pytest",
    "pytest-asyncio",
    "coverage",
]
```

**安装方式：**
```bash
# 基础安装
pip install sage-workspace

# 安装扩展功能
pip install sage-workspace[extended]

# 安装开发依赖
pip install sage-workspace[dev]

# 安装多个依赖组
pip install sage-workspace[dev,test]
```

## 工具配置

### 1. 代码格式化 (Black)

```toml
[tool.black]
line-length = 88                    # 行长度限制
target-version = ["py311"]          # 目标 Python 版本
extend-exclude = '''                # 排除文件/目录
/(
    \.git
    | \.venv
    | build
    | dist
)/
'''
```

### 2. 导入排序 (isort)

```toml
[tool.isort]
profile = "black"                   # 与 black 兼容
multi_line_output = 3               # 多行输出格式
line_length = 88                    # 与 black 保持一致
known_first_party = ["sage"]        # 第一方包
src_paths = [                       # 源代码路径
    "packages/sage-kernel/src",
    "packages/sage-utils/src",
]
```

### 3. 类型检查 (mypy)

```toml
[tool.mypy]
python_version = "3.11"             # Python 版本
warn_return_any = true              # 警告返回 Any
warn_unused_configs = true          # 警告未使用的配置
namespace_packages = true           # 命名空间包支持
mypy_path = [                       # 类型检查路径
    "packages/sage-kernel/src",
    "packages/sage-utils/src",
]

[[tool.mypy.overrides]]            # 特定模块配置
module = "sage.*"
ignore_missing_imports = false
```

### 4. 测试配置 (pytest)

```toml
[tool.pytest.ini_options]
testpaths = [                       # 测试路径
    "packages/sage-kernel/tests",
    "packages/sage-utils/tests",
    "tests",
]
python_files = ["test_*.py", "*_test.py"]  # 测试文件模式
addopts = [                         # 默认选项
    "-v",                           # 详细输出
    "--tb=short",                   # 简短回溯
]
markers = [                         # 自定义标记
    "slow: marks tests as slow",
    "integration: marks tests as integration tests",
]
```

## SAGE 项目实例分析

### 工作空间级别配置 (根目录)

```toml
# /home/flecther/SAGE/pyproject.toml
[build-system]
requires = ["setuptools>=64", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "sage-workspace"              # 虚拟工作空间包
version = "1.0.0"
description = "SAGE Framework - 智能化Monorepo工作空间"
dependencies = []                    # 虚拟包，无直接依赖

[project.optional-dependencies]
# 分层安装策略
basic = ["sage-utils", "sage-kernel", "sage-lib"]
extended = ["sage-utils", "sage-kernel", "sage-lib", "sage-extensions"]
full = ["sage-utils", "sage-kernel", "sage-lib", "sage-extensions", 
        "sage-plugins", "sage-service", "sage-cli"]

# 统一的开发工具链
dev = [
    "pytest", "pytest-asyncio>=0.21.0",
    "black>=23.0.0", "isort>=5.12.0", 
    "mypy>=1.0.0", "ruff>=0.1.0",
]
```

### 扩展包配置 (C++ 扩展)

```toml
# /home/flecther/SAGE/packages/sage-extensions/pyproject.toml
[build-system]
requires = [
    "setuptools>=64", "wheel",
    "pybind11>=2.10.0",              # Python-C++ 绑定
    "cmake>=3.18",                   # C++ 构建系统
    "numpy>=1.21.0",                 # NumPy C API
]
build-backend = "setuptools.build_meta"

[project]
name = "sage-extensions"
dependencies = [
    "sage-kernel",                     # 内部依赖
    "numpy>=1.21.0",                 # C++ 扩展需要
    "pybind11>=2.10.0",             # 运行时绑定
]
```

### 配置继承和覆盖

**特点：**
1. **工作空间级别**: 定义通用的开发工具配置
2. **包级别**: 定义特定的构建需求和依赖
3. **配置继承**: 子包可以继承工作空间的配置
4. **选择性覆盖**: 子包可以覆盖特定的配置项

## 最佳实践

### 1. 版本管理

```toml
# 推荐：使用语义化版本
version = "1.2.3"  # MAJOR.MINOR.PATCH

# 动态版本（高级用法）
dynamic = ["version"]
```

配合 `setuptools_scm` 自动生成版本：
```toml
[build-system]
requires = ["setuptools>=64", "setuptools-scm>=8"]

[tool.setuptools_scm]
write_to = "src/_version.py"
```

### 2. 依赖管理策略

```toml
[project]
# 核心依赖：保守的版本约束
dependencies = [
    "numpy>=1.21.0,<2.0.0",     # 明确上界
    "requests>=2.28.0",          # 只指定下界
]

[project.optional-dependencies]
# 开发依赖：更新的版本要求
dev = [
    "pytest>=7.0.0",
    "black>=23.0.0",
]

# 性能依赖：可选的高性能组件
performance = [
    "numba>=0.56.0",
    "sage-extensions",  # 自定义 C++ 扩展
]
```

### 3. 多环境配置

```toml
[project.optional-dependencies]
# 生产环境：最小依赖
prod = [
    "sage-kernel",
    "numpy>=1.21.0",
]

# 开发环境：完整工具链
dev = [
    "sage-kernel[prod]",
    "pytest", "black", "mypy",
    "pre-commit",
]

# 测试环境：测试相关工具
test = [
    "sage-kernel[prod]",
    "pytest", "pytest-cov", "pytest-asyncio",
]

# CI 环境：自动化工具
ci = [
    "sage-kernel[test]",
    "tox", "coverage", "codecov",
]
```

### 4. 工具配置最佳实践

```toml
# 统一的代码风格
[tool.black]
line-length = 88
target-version = ["py311"]
skip-string-normalization = false

[tool.isort]
profile = "black"  # 与 black 兼容
known_first_party = ["sage"]

# 严格的类型检查
[tool.mypy]
python_version = "3.11"
strict = true  # 启用所有严格检查
warn_unreachable = true
warn_no_return = true

# 全面的测试配置
[tool.pytest.ini_options]
minversion = "7.0"
addopts = [
    "-ra",           # 显示所有测试结果摘要
    "--strict-markers",  # 严格标记模式
    "--strict-config",   # 严格配置模式
]
testpaths = ["tests"]
```

### 5. 性能优化配置

```toml
# 针对大型项目的优化
[tool.setuptools.packages.find]
exclude = [
    "tests*", "docs*", "build*", "dist*",
    "*.egg-info", "__pycache__*",
]

# 缓存配置
[tool.mypy]
cache_dir = ".mypy_cache"
sqlite_cache = true

[tool.pytest.ini_options]
cache_dir = ".pytest_cache"
```

## 总结

pyproject.toml 作为现代 Python 项目的标准配置文件，提供了：

1. **统一配置**: 将项目元数据、构建配置、工具配置集中管理
2. **标准化**: 基于 PEP 标准，具有良好的互操作性
3. **可扩展性**: 支持复杂的多包项目和自定义构建流程
4. **工具集成**: 与现代 Python 开发工具深度集成

在 SAGE 项目中，pyproject.toml 实现了：
- **分层依赖管理**: 基础→扩展→完整的安装选项
- **开发工具统一**: 所有代码质量工具的一致配置
- **构建系统标准化**: Python 和 C++ 的统一构建流程

下一章：[setup.py 与 pyproject.toml 联合构建](./setup_py_integration.md) →
