# SAGE Extensions

SAGE Framework 的高性能 C++ 扩展包。

## 特性

- **高性能向量数据库**: 基于 FAISS 的高性能向量存储和搜索
- **C++ 加速**: 关键算法使用 C++ 实现，通过 pybind11 绑定到 Python
- **自动编译**: 安装时自动编译 C++ 源代码
- **自动依赖管理**: 一键安装脚本自动处理系统依赖

## 快速开始

### 一键安装（推荐）

```bash
# 克隆或进入项目目录
cd /path/to/sage-extensions

# 运行一键安装脚本（自动安装所有依赖并构建）
./scripts/install.sh
```

该脚本将自动：
1. 检测操作系统类型
2. 安装系统依赖（cmake, gcc, pkg-config, blas, lapack 等）
3. 安装 Python 依赖（numpy, pybind11, faiss 等）
4. 构建 C++ 扩展
5. 验证安装

## 构建过程

1. **依赖检查**: 检查 CMake 和其他系统依赖
2. **FAISS 安装**: 如果未找到 FAISS，会自动通过 conda 或 pip 安装
3. **CMake 配置**: 使用 CMake 配置 C++ 构建
4. **编译**: 编译 C++ 源代码并生成 Python 绑定
5. **安装**: 将编译好的扩展安装到包中

## 使用

```python
from sage.extensions.sage_db import SageDB, IndexType, DistanceMetric

# 创建向量数据库
db = SageDB(dimension=768, index_type=IndexType.FLAT)

# 添加向量
vectors = [[0.1, 0.2, ...], [0.3, 0.4, ...]]
ids = db.add_vectors(vectors)

# 搜索
query = [0.1, 0.2, ...]
results = db.search(query, k=5)
```

## 开发

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest

# 清理构建文件
python setup.py clean --all
```

## 故障排除

### CMake 未找到

```bash
# Ubuntu/Debian
sudo apt-get install cmake

# CentOS/RHEL
sudo yum install cmake

# macOS
brew install cmake
```

### FAISS 安装失败

```bash
# 手动安装 FAISS
conda install -c conda-forge faiss-cpu
# 或
pip install faiss-cpu
```

### 编译错误

确保您的编译器支持 C++17：

```bash
# 检查 GCC 版本
gcc --version

# 检查 Clang 版本
clang --version
```
