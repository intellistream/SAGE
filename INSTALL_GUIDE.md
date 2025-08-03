# SAGE Framework - 快速安装指南

## 🚀 一键安装（推荐）

### 方法 1: 使用一键安装脚本

```bash
# 下载并运行一键安装脚本
python quick_install.py

# 或直接选择安装模式
python quick_install.py --python-only    # 纯 Python 安装（推荐）
python quick_install.py --full          # 完整安装（需要编译环境）
```

### 方法 2: 使用 pip 直接安装

```bash
# 从源码安装（推荐）
pip install -e .

# 或安装预构建的 wheel
pip install dist/sage_stream-*.whl
```

## 📦 构建自定义 Wheel 包

### 现代化构建（推荐）

```bash
# 构建纯 Python wheel（快速，适合大多数用户）
./build_modern_wheel.sh

# 构建包含 C++ 扩展的 wheel（需要编译环境）
./build_modern_wheel.sh --with-cpp
```

### 传统构建（向后兼容）

```bash
# 使用原有的构建脚本
./build_production_wheel.sh
./quick_build.sh
```

## ✅ 验证安装

```bash
# 检查安装状态
python quick_install.py --check

# 手动验证
python -c "import sage; print(f'SAGE version: {sage.__version__}')"
sage --help
```

## 🛠️ 开发者指南

### 本地开发环境

```bash
# 克隆项目
git clone https://github.com/intellistream/SAGE.git
cd SAGE

# 安装开发依赖
pip install -e .[dev]

# 运行测试
pytest
```

### 构建发布包

```bash
# 清理并构建
./build_modern_wheel.sh --clean-only
./build_modern_wheel.sh --with-cpp

# 上传到 PyPI
twine upload dist/*
```

## 📋 系统要求

- **Python**: 3.11 或更高版本
- **操作系统**: Linux, macOS, Windows
- **内存**: 最少 4GB RAM
- **磁盘**: 最少 2GB 可用空间

### 可选依赖（用于 C++ 扩展）

- GCC/G++ 编译器
- CMake 3.16+
- Make

## 🆘 故障排除

### 常见问题

1. **Python 版本不兼容**
   ```bash
   # 检查 Python 版本
   python --version
   # 需要 Python 3.11+
   ```

2. **缺少编译工具**
   ```bash
   # Ubuntu/Debian
   sudo apt-get install build-essential cmake
   
   # CentOS/RHEL
   sudo yum groupinstall "Development Tools"
   sudo yum install cmake
   
   # macOS
   xcode-select --install
   brew install cmake
   ```

3. **权限问题**
   ```bash
   # 使用虚拟环境（推荐）
   python -m venv sage_env
   source sage_env/bin/activate  # Linux/macOS
   # 或 sage_env\Scripts\activate  # Windows
   ```

### 获取帮助

- 📚 [文档](https://github.com/intellistream/SAGE/docs)
- 🐛 [问题反馈](https://github.com/intellistream/SAGE/issues)
- 💬 [讨论](https://github.com/intellistream/SAGE/discussions)

## 📈 性能优化

- 使用 `--with-cpp` 选项构建以获得最佳性能
- 在生产环境中使用预构建的 wheel 包
- 考虑使用 Docker 容器进行部署

---

**快速开始**: 运行 `python quick_install.py` 并按照向导进行安装！
