# SAGE Extensions 脚本目录

这个目录包含了用于构建、安装和测试 SAGE Extensions 的辅助脚本。

## 脚本说明

### `install.sh`
一键安装脚本，自动处理：
- 系统依赖安装（cmake, gcc, pkg-config, blas, lapack）
- Python 依赖安装（numpy, pybind11, faiss）
- C++ 扩展编译
- 安装验证

使用方法：
```bash
./scripts/install.sh
```

### `build.py`
构建脚本，用于编译 C++ 扩展：
- 检查系统依赖
- 安装 Python 依赖
- 使用 CMake 编译 C++ 扩展
- 复制库文件到正确位置

使用方法：
```bash
python scripts/build.py
```

### `test_install.py`
安装测试脚本，验证：
- 基本模块导入
- SageDB 类创建和使用
- 向量添加和搜索功能

使用方法：
```bash
python scripts/test_install.py
```

### `verify_install.py`
安装验证脚本，提供：
- 快速状态检查
- 调用详细测试
- 安装成功确认

使用方法：
```bash
python scripts/verify_install.py
```

## 典型工作流程

### 新安装
```bash
# 1. 一键安装（推荐）
./scripts/install.sh

# 或者分步安装
# 2a. 构建
python scripts/build.py

# 2b. 安装
pip install -e .

# 3. 验证
python scripts/verify_install.py
```

### 开发过程
```bash
# 重新构建
python scripts/build.py

# 测试
python scripts/test_install.py

# 清理重建
rm -rf src/sage/extensions/sage_db/build/
python scripts/build.py
```

### 故障排除
```bash
# 检查依赖
cmake --version
gcc --version
pkg-config --version

# 重新安装依赖
./scripts/install.sh

# 强制重装
pip install -e . --force-reinstall
```

## 脚本特性

- **跨平台支持**：支持 Ubuntu/Debian、CentOS/RHEL、macOS
- **自动依赖管理**：自动检测和安装缺失的依赖
- **错误处理**：提供详细的错误信息和修复建议
- **状态反馈**：显示每个步骤的执行状态
- **清理功能**：支持清理和重建
