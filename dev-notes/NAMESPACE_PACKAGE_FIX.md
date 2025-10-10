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
2. **命名空间包配置**：SAGE 使用多个子包（sage-common, sage-kernel, sage-libs 等）共享 `sage` 命名空间，需要正确配置

## 解决方案

### 1. 添加 packaging 依赖

在所有包的 `pyproject.toml` 中的 `[build-system]` 部分添加 `packaging>=24.2`：

**修改的文件：**
- `/home/shuhao/SAGE/packages/sage/pyproject.toml`
- `/home/shuhao/SAGE/packages/sage-common/pyproject.toml`
- `/home/shuhao/SAGE/packages/sage-kernel/pyproject.toml`
- `/home/shuhao/SAGE/packages/sage-libs/pyproject.toml`
- `/home/shuhao/SAGE/packages/sage-middleware/pyproject.toml`
- `/home/shuhao/SAGE/packages/sage-tools/pyproject.toml`

**修改内容：**
```toml
[build-system]
requires = ["setuptools>=64", "wheel", "packaging>=24.2"]
build-backend = "setuptools.build_meta"
```

### 2. 使用 pkg_resources 声明命名空间

在所有子包的 `src/sage/__init__.py` 中使用 `pkg_resources.declare_namespace()`：

**修改的文件：**
- `/home/shuhao/SAGE/packages/sage-common/src/sage/__init__.py`
- `/home/shuhao/SAGE/packages/sage-kernel/src/sage/__init__.py`
- `/home/shuhao/SAGE/packages/sage-libs/src/sage/__init__.py`
- `/home/shuhao/SAGE/packages/sage-middleware/src/sage/__init__.py`
- `/home/shuhao/SAGE/packages/sage-tools/src/sage/__init__.py`

**代码内容：**
```python
"""SAGE 命名空间包 - 使用 setuptools 命名空间包机制"""
# 声明为setuptools命名空间包
__import__('pkg_resources').declare_namespace(__name__)
```

### 3. 添加 setup.cfg 配置

为所有子包添加 `setup.cfg` 文件来声明命名空间：

**创建的文件：**
- `/home/shuhao/SAGE/packages/sage-common/setup.cfg`
- `/home/shuhao/SAGE/packages/sage-kernel/setup.cfg`
- `/home/shuhao/SAGE/packages/sage-libs/setup.cfg`
- `/home/shuhao/SAGE/packages/sage-middleware/setup.cfg`
- `/home/shuhao/SAGE/packages/sage-tools/setup.cfg`

**配置内容：**
```ini
[options]
namespace_packages = sage
zip_safe = False
```

## 技术细节

### 命名空间包机制

SAGE 采用 **setuptools 命名空间包** 方式：

1. **`pkg_resources.declare_namespace()`**：在运行时声明命名空间
2. **`setup.cfg` 中的 `namespace_packages`**：在打包时声明命名空间
3. **`pyproject.toml` 中的 `namespaces = true`**：告诉 setuptools 查找命名空间包

### 为什么不使用 PEP 420 隐式命名空间？

PEP 420 隐式命名空间包（完全删除 `__init__.py`）虽然是 Python 3.3+ 的推荐方式，但在以下场景可能有问题：

1. **开发模式安装**：`pip install -e .` 可能无法正确处理
2. **工具兼容性**：某些旧工具可能不支持
3. **调试困难**：问题排查更复杂

setuptools 命名空间包提供了更好的兼容性和可靠性。

## 验证方法

### 本地验证

```bash
# 构建包
cd /home/shuhao/SAGE/packages/sage-common
python -m build --wheel

cd /home/shuhao/SAGE/packages/sage-kernel
python -m build --wheel

# 在虚拟环境中测试
python -m venv /tmp/test_env
source /tmp/test_env/bin/activate
pip install packages/sage-common/dist/isage_common-*.whl
pip install packages/sage-kernel/dist/isage_kernel-*.whl

# 测试导入
python -c "from sage.kernel.api.local_environment import LocalEnvironment; print('✅ Success')"
```

### CI/CD 验证

在 `.github/workflows/dev-ci.yml` 中的 "Validate PyPI Release Readiness" 步骤会自动验证。

## 影响范围

**受影响的包：**
- isage-common
- isage-kernel
- isage-libs
- isage-middleware
- isage-tools

**不受影响的包：**
- isage (元包，无需命名空间)

## 注意事项

1. **开发安装**：使用 `pip install -e .` 时，所有依赖的命名空间包都必须已安装
2. **包安装顺序**：建议按以下顺序安装：
   - isage-common
   - isage-kernel
   - isage-middleware
   - isage-libs
   - isage-tools
   - isage (元包会自动处理依赖)

3. **PyPI 发布**：构建前确保环境中有 `packaging>=24.2`

## 相关文档

- [Python Packaging Guide - Namespace Packages](https://packaging.python.org/guides/packaging-namespace-packages/)
- [setuptools documentation - Namespace Packages](https://setuptools.pypa.io/en/latest/userguide/package_discovery.html#namespace-packages)
- [PEP 420 - Implicit Namespace Packages](https://www.python.org/dev/peps/pep-0420/)

## 更新时间

2025-10-10
