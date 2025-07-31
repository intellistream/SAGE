# SAGE 生产级打包指南

本文档说明如何将 SAGE 项目打包为不暴露源码的生产级 wheel 包。

## 🎯 目标

构建一个包含以下特性的 wheel 包：
- ✅ Python 源码编译为 `.so` 文件（不暴露源码）
- ✅ C++ 扩展模块（sage_db, sage_queue）
- ✅ 高性能 pybind11 绑定
- ✅ 保留包结构和 `__init__.py` 文件
- ✅ 生产级优化和错误处理

## 📦 提供的脚本

### 1. `build_production_wheel.sh` (完整版)
功能全面的生产级构建脚本，包含：
- 依赖检查
- 详细的构建步骤
- 错误处理和回退
- 构建验证
- 多种构建选项

```bash
# 标准构建（删除源码）
./build_production_wheel.sh

# 保留源码构建
./build_production_wheel.sh --keep-source

# 仅清理
./build_production_wheel.sh --clean-only

# 查看帮助
./build_production_wheel.sh --help
```

### 2. `quick_build.sh` (快速版)
简化的快速构建脚本：

```bash
./quick_build.sh
```

## 🛠️ 构建流程详解

### 步骤 1: 环境准备
```bash
# 清理之前的构建
rm -rf build dist *.egg-info

# 设置构建环境
export TMPDIR=$(pwd)/temp_build
export MAX_JOBS=1  # 避免资源冲突
```

### 步骤 2: C++ 扩展构建
```bash
# 构建 sage_queue
cd sage_ext/sage_queue && bash build.sh --clean

# 构建 sage_db (可能需要修复编译错误)
cd sage_ext/sage_db && bash build.sh --clean
```

### 步骤 3: Python 代码编译
```bash
# 编译 Python 源码为 .so 文件
python release_build.py build_ext --inplace
```

### 步骤 4: 源码清理
```bash
# 删除 Python 源文件，保留 __init__.py
if [ -f "cythonized_files.txt" ]; then
    grep -v "__init__.py" cythonized_files.txt | xargs rm -f
fi
```

### 步骤 5: Wheel 构建
```bash
# 构建最终的 wheel 包
python release_build.py bdist_wheel
```

## 🔍 验证和测试

### 检查 wheel 内容
```bash
# 查看 wheel 文件列表
unzip -l dist/*.whl

# 检查编译文件数量
unzip -l dist/*.whl | grep -c "\.so$"

# 检查 Python 文件数量（应该主要是 __init__.py）
unzip -l dist/*.whl | grep -c "\.py$"
```

### 测试安装
```bash
# 在干净环境中测试安装
pip install dist/*.whl

# 验证导入
python -c "import sage; print(sage.__version__)"
python -c "from sage_ext import sage_queue; print('C++ extensions OK')"
```

## 🚨 常见问题和解决方案

### 1. 磁盘空间不足
```bash
# 使用本地临时目录
mkdir -p ./temp_build
export TMPDIR=$(pwd)/temp_build
```

### 2. 编译器错误 (gcc 失败)
```bash
# 设置单线程编译
export MAX_JOBS=1
export MAKEFLAGS="-j1"

# 清理临时文件
rm -rf /tmp/cc* 2>/dev/null || true
```

### 3. C++ 扩展构建失败
```bash
# 跳过有问题的扩展
./build_production_wheel.sh  # 脚本会自动处理失败

# 或手动修复 sage_db 编译错误后重试
```

### 4. Python 源码清理问题
```bash
# 如果需要保留源码用于调试
./build_production_wheel.sh --keep-source
```

## 📋 构建结果检查清单

- [ ] wheel 文件成功生成在 `dist/` 目录
- [ ] wheel 文件大小合理（通常 5-15MB）
- [ ] 包含编译后的 `.so` 文件
- [ ] 保留必要的 `__init__.py` 文件
- [ ] C++ 扩展模块存在
- [ ] 可以正常安装和导入
- [ ] 核心功能正常工作

## 🎉 成功示例

```bash
$ ./build_production_wheel.sh
[STEP] 检查构建依赖
[SUCCESS] 所有依赖检查通过
[STEP] 清理之前的构建
[SUCCESS] 清理完成
[STEP] 构建 C++ 扩展
[SUCCESS] ✓ sage_queue 构建成功
[STEP] 构建 Cython 扩展和 Python 绑定
[SUCCESS] Cython 扩展构建成功
[STEP] 清理 Python 源码文件
[SUCCESS] 删除了 174 个 Python 源文件
[STEP] 构建生产级 wheel 包
[SUCCESS] Wheel 包构建成功
[STEP] 验证 wheel 包
[SUCCESS] 找到 wheel 文件: sage-0.1.2-cp311-cp311-linux_x86_64.whl

🎉 生产级 wheel 包构建成功！
文件位置: dist/sage-0.1.2-cp311-cp311-linux_x86_64.whl
安装命令: pip install dist/sage-0.1.2-cp311-cp311-linux_x86_64.whl
```

## 📚 相关文件说明

- `release_build.py`: 核心构建逻辑，处理 Cython 和 pybind11 编译
- `build_release.sh`: 原始构建脚本（参考用）
- `setup.py`: 传统 setuptools 配置（已被 release_build.py 替代）
- `cythonized_files.txt`: Cython 编译文件列表，用于源码清理

现在你拥有了完整的生产级打包解决方案！🚀
