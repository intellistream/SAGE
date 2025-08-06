# SAGE 字节码编译器使用指南

SAGE开发工具包现在集成了字节码编译功能，可以将Python源码编译为.pyc文件，隐藏企业版源代码。

## 功能特性

- 🔧 **字节码编译**: 将Python源码编译为.pyc文件
- 🗑️ **源码清理**: 自动删除.py源文件，只保留.pyc
- 📦 **Wheel构建**: 支持直接构建wheel包
- 🚀 **PyPI上传**: 支持上传到PyPI
- 🎯 **批量处理**: 支持批量编译多个包
- 📊 **进度显示**: Rich界面显示编译进度
- 🔍 **预演模式**: 默认预演模式，安全测试

## 安装和配置

确保sage-dev-toolkit已正确安装：

```bash
cd /home/flecther/SAGE/packages/sage-tools/sage-dev-toolkit
pip install -e .
```

## 基本使用

### 1. 编译单个包

```bash
# 基本编译
sage-dev compile packages/sage-apps

# 编译并构建wheel
sage-dev compile packages/sage-apps --build

# 编译、构建并上传到PyPI（预演模式）
sage-dev compile packages/sage-apps --build --upload

# 实际执行（非预演模式）
sage-dev compile packages/sage-apps --build --upload --no-dry-run
```

### 2. 批量编译多个包

```bash
# 编译多个包
sage-dev compile packages/sage-apps,packages/sage-kernel,packages/sage-middleware

# 或者使用批量模式
sage-dev compile packages/sage-apps --batch
```

### 3. 指定输出目录

```bash
# 指定编译输出目录
sage-dev compile packages/sage-apps --output /tmp/compiled_packages
```

## 高级选项

### 命令行参数详解

- `package_path`: 要编译的包路径（必需）
  - 单个路径: `packages/sage-apps`
  - 多个路径: `packages/sage-apps,packages/sage-kernel`

- `--output, -o`: 输出目录
  - 如果不指定，使用临时目录

- `--build, -b`: 构建wheel包
  - 编译完成后自动构建wheel

- `--upload, -u`: 上传到PyPI
  - 需要配合 `--build` 使用
  - 需要配置twine凭据

- `--dry-run`: 预演模式（默认开启）
  - 使用 `--no-dry-run` 关闭预演模式

- `--force-cleanup`: 强制清理临时目录
  - 默认保留临时目录供检查

- `--batch`: 批量模式
  - 多包处理时自动启用

- `--verbose, -v`: 详细输出
  - 显示详细的错误信息

## 使用示例

### 示例1: 开发测试
```bash
# 快速测试编译，不构建wheel
sage-dev compile packages/sage-apps --verbose
```

### 示例2: 准备发布
```bash
# 编译并构建wheel，预演模式
sage-dev compile packages/sage-apps --build --verbose
```

### 示例3: 正式发布
```bash
# 编译、构建并上传到PyPI
sage-dev compile packages/sage-apps --build --upload --no-dry-run
```

### 示例4: 批量发布多个包
```bash
# 批量编译核心包
sage-dev compile packages/sage-kernel,packages/sage-middleware,packages/sage-apps --build --upload --no-dry-run
```

## 编译过程

1. **包验证**: 检查包路径是否存在和有效
2. **结构复制**: 复制整个包结构到临时目录
3. **Python编译**: 编译所有.py文件为.pyc文件
4. **源码清理**: 删除.py源文件（保留必要文件如setup.py）
5. **配置更新**: 更新pyproject.toml包含.pyc文件
6. **Wheel构建**: （可选）构建wheel包
7. **PyPI上传**: （可选）上传到PyPI

## 注意事项

### 文件处理规则

**跳过编译的文件**:
- `setup.py`: 构建脚本
- `conftest.py`: pytest配置
- 测试文件: 包含`test_`或`_test.py`的文件
- 测试目录: `tests/`目录下的文件

**保留的源文件**:
- `setup.py`: 构建时需要

### 安全建议

1. **总是先使用预演模式**: 默认启用，验证无误后再使用`--no-dry-run`
2. **检查输出**: 编译后检查临时目录中的结果
3. **备份源码**: 确保源码有备份
4. **测试功能**: 编译后测试包的功能是否正常

### 故障排除

**常见问题**:

1. **编译失败**: 检查Python语法错误
2. **包路径错误**: 确保路径正确且包含pyproject.toml
3. **权限问题**: 确保有写入输出目录的权限
4. **依赖缺失**: 确保安装了build和twine工具

**调试方法**:
```bash
# 使用详细输出查看错误信息
sage-dev compile packages/sage-apps --verbose

# 保留临时目录检查结果
sage-dev compile packages/sage-apps --no-force-cleanup
```

## 集成到CI/CD

可以将字节码编译集成到CI/CD流程中：

```yaml
# GitHub Actions示例
- name: Compile packages to bytecode
  run: |
    sage-dev compile packages/sage-apps --build --upload --no-dry-run
  env:
    TWINE_USERNAME: ${{ secrets.PYPI_USERNAME }}
    TWINE_PASSWORD: ${{ secrets.PYPI_PASSWORD }}
```

## 开发说明

字节码编译器位于 `/packages/sage-tools/sage-dev-toolkit/src/sage_dev_toolkit/core/bytecode_compiler.py`

主要类：
- `BytecodeCompiler`: 单包编译器
- `compile_multiple_packages`: 批量编译函数

CLI命令位于 `/packages/sage-tools/sage-dev-toolkit/src/sage_dev_toolkit/cli/main.py` 中的 `compile_command` 函数。
