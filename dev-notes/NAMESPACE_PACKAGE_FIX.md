# 命名空间包问题修复

## 问题描述

在 PyPI 发布准备验证测试中，出现以下错误：

```
ModuleNotFoundError: No module named 'sage.kernel.api'
```

影响的导入：
- `LocalEnvironment`
- `BatchFunction`
- `SinkFunction`

## 根本原因

1. **setuptools 版本依赖问题**：`setuptools>=77.0.0` 需要 `packaging>=24.2`，但构建系统中未声明此依赖
2. **命名空间包配置不当**：最初使用 `pkg_resources.declare_namespace()` 方式，但这需要特殊的 setuptools 配置且已被弃用
3. **sage/__init__.py 未被打包**：使用过时的 namespace_packages 配置导致 `sage/__init__.py` 文件没有被包含在 wheel 包中

## 最终解决方案

### 1. 添加 packaging 依赖

在所有包的 `pyproject.toml` 中的 `[build-system]` 部分添加 `packaging>=24.2`：

```toml
[build-system]
requires = ["setuptools>=64", "wheel", "packaging>=24.2"]
build-backend = "setuptools.build_meta"
```

### 2. 使用 pkgutil.extend_path() 声明命名空间

在所有子包的 `src/sage/__init__.py` 中使用**标准库方式**：

```python
# This is a namespace package
__path__ = __import__("pkgutil").extend_path(__path__, __name__)
```

**关键优势**：
- ✅ Python 标准库内置，无需额外依赖
- ✅ 不需要特殊的 setuptools 配置
- ✅ `sage/__init__.py` 文件会自动被打包
- ✅ 兼容性好，适用于所有 Python 3.x 版本

### 3. 移除过时的配置

**不要使用**以下过时配置：
- ❌ `setup.cfg` 中的 `[options] namespace_packages = sage`
- ❌ `setup.py` 中的 `namespace_packages=['sage']`
- ❌ `pkg_resources.declare_namespace(__name__)`

这些方式已被 setuptools 标记为弃用，会导致构建错误。

## 技术细节

### 命名空间包的三种实现方式对比

| 方式 | 状态 | 优缺点 |
|------|------|--------|
| **pkgutil.extend_path()** | ✅ 推荐 | Python 标准库，简单可靠，自动打包 __init__.py |
| **pkg_resources.declare_namespace()** | ⚠️ 弃用 | 需要特殊配置，setuptools 已标记为弃用 |
| **PEP 420 隐式命名空间** | ⚠️ 限制 | 无 __init__.py，某些工具不兼容 |

### 为什么不使用 PEP 420？

PEP 420 隐式命名空间包（完全删除 `__init__.py`）虽然是 Python 3.3+ 的特性，但存在以下问题：

1. **Pylance/PyLance 无法识别**：导致 IDE 自动补全失效
2. **某些打包工具不兼容**：如 setuptools 的某些旧版本
3. **调试困难**：没有明确的标记文件

## 验证方法

### 检查 wheel 包内容

```bash
python -c "
import zipfile
wheel_file = 'packages/sage-kernel/dist/isage_kernel-*.whl'
with zipfile.ZipFile(wheel_file, 'r') as zf:
    if 'sage/__init__.py' in zf.namelist():
        print('✅ sage/__init__.py 已打包')
        print(zf.read('sage/__init__.py').decode('utf-8'))
"
```

### 本地完整测试

```bash
# 创建测试环境
python -m venv /tmp/test_env
source /tmp/test_env/bin/activate

# 构建并安装
pip install wheel setuptools>=77.0.0 packaging>=24.2
cd packages/sage-common && python -m build --wheel && cd ../..
cd packages/sage-kernel && python -m build --wheel && cd ../..
pip install packages/sage-common/dist/*.whl
pip install packages/sage-kernel/dist/*.whl

# 测试导入
python -c "from sage.kernel.api.local_environment import LocalEnvironment; print('✅ Success')"
python -c "from sage.kernel.api.function.batch_function import BatchFunction; print('✅ Success')"
python -c "from sage.kernel.api.function.sink_function import SinkFunction; print('✅ Success')"
```

## 影响范围

**修改的包（共5个）：**
- isage-common
- isage-kernel  
- isage-libs
- isage-middleware
- isage-tools

**修改的文件类型：**
- `pyproject.toml`：添加 packaging>=24.2 依赖
- `src/sage/__init__.py`：使用 pkgutil.extend_path()
- `setup.cfg`：移除 namespace_packages 配置
- `setup.py`：为缺少的包添加基础配置

## 测试结果

✅ **所有测试通过**：
```
✅ sage-common wheel 构建成功
✅ sage-kernel wheel 构建成功
✅ sage/__init__.py 正确打包到 wheel 中
✅ import sage
✅ import sage.common
✅ import sage.kernel
✅ from sage.kernel.api.local_environment import LocalEnvironment
✅ from sage.kernel.api.function.batch_function import BatchFunction
✅ from sage.kernel.api.function.sink_function import SinkFunction
```

## 相关文档

- [Python Packaging Guide - Namespace Packages](https://packaging.python.org/guides/packaging-namespace-packages/)
- [pkgutil documentation](https://docs.python.org/3/library/pkgutil.html#pkgutil.extend_path)
- [PEP 420 - Implicit Namespace Packages](https://www.python.org/dev/peps/pep-0420/)

## 更新历史

- **2025-10-10 初版**：使用 pkg_resources.declare_namespace()
- **2025-10-10 最终版**：改用 pkgutil.extend_path()（推荐方案）
