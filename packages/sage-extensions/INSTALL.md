# SAGE Extensions 安装指南

## 快速安装

```bash
cd /home/flecther/SAGE/packages/sage-extensions
pip install -e .
```

## 详细步骤

### 1. 检查系统依赖

确保您的系统有以下依赖：

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install build-essential cmake g++ gcc

# CentOS/RHEL  
sudo yum install gcc-c++ gcc make cmake

# macOS
brew install cmake
xcode-select --install
```

### 2. 安装Python依赖

```bash
pip install numpy pybind11 cmake ninja
```

### 3. 安装FAISS (可选，构建时会自动安装)

```bash
# 使用conda (推荐)
conda install -c conda-forge faiss-cpu

# 或使用pip
pip install faiss-cpu
```

### 4. 构建和安装

```bash
# 开发安装
pip install -e .

# 或运行构建脚本
python scripts/build.py

# 验证安装
python scripts/verify_install.py
```

## 构建选项

### 环境变量

- `CMAKE_ARGS`: 传递给CMake的额外参数
- `CMAKE_BUILD_PARALLEL_LEVEL`: 并行构建级别
- `CMAKE_GENERATOR`: CMake生成器 (默认: Ninja)

示例：
```bash
CMAKE_ARGS="-DCMAKE_BUILD_TYPE=Debug" pip install -e .
```

### 清理构建

```bash
# 清理构建文件
rm -rf src/sage/extensions/sage_db/build/
rm -rf build/
rm -rf *.egg-info/

# 重新构建
pip install -e . --force-reinstall
```

## 故障排除

### CMake 未找到

```bash
pip install cmake
# 或系统安装
sudo apt-get install cmake  # Ubuntu
brew install cmake          # macOS
```

### 编译错误

1. 确保C++编译器支持C++17
2. 检查CMake版本 >= 3.18
3. 更新pybind11版本

### FAISS 相关错误

```bash
# 手动安装FAISS
conda install -c conda-forge faiss-cpu

# 或降级到兼容版本
pip install faiss-cpu==1.7.4
```

### Python版本兼容性

- 支持 Python 3.10+
- 推荐使用 Python 3.11

## 验证安装

```python
import sage.extensions

# 检查扩展状态
status = sage.extensions.get_extension_status()
print(status)

# 测试SAGE DB
from sage.extensions.sage_db import SageDB
db = SageDB(dimension=128)
print("✅ Installation successful!")
```
