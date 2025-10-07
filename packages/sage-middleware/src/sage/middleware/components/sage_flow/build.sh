#!/bin/bash
# SAGE Flow 构建包装脚本
# 分两步构建：1) C++库（子模块） 2) Python绑定（主仓库）

set -e

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SUBMODULE_DIR="$SCRIPT_DIR/sageFlow"
PYTHON_DIR="$SCRIPT_DIR/python"

echo "🔨 构建 SAGE Flow..."

# ==================== 步骤1: 构建C++库 ====================
echo ""
echo "📦 步骤 1/2: 构建 C++ 库（sageFlow 子模块）"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 检查子模块是否已初始化
if [ ! -d "$SUBMODULE_DIR" ]; then
    echo "❌ 错误: sageFlow 子模块未初始化"
    echo "请运行: git submodule update --init --recursive"
    exit 1
fi

cd "$SUBMODULE_DIR"

# 检查libstdc++
if ! ldconfig -p 2>/dev/null | grep -q libstdc++; then
    echo "⚠️ 警告: libstdc++ 未在 ldconfig 缓存中找到"
fi

# 创建构建目录
BUILD_DIR="$SUBMODULE_DIR/build"
mkdir -p "$BUILD_DIR"

# 创建空的examples目录
EXAMPLES_DIR="$SUBMODULE_DIR/examples"
if [ ! -d "$EXAMPLES_DIR" ]; then
    mkdir -p "$EXAMPLES_DIR"
    echo "# Placeholder for examples" > "$EXAMPLES_DIR/CMakeLists.txt"
fi

cd "$BUILD_DIR"

# 配置 CMake - 只构建 C++ 库
echo "⚙️  配置 CMake (仅 C++ 库)..."
cmake -DCMAKE_BUILD_TYPE=Release \
      -DBUILD_TESTING=OFF \
      .. 2>&1 | grep -v "Cannot find source file.*python/bindings.cpp" | grep -v "No SOURCES given to target: _sage_flow" || true

# 检查 CMake 配置是否成功
if [ ! -f "Makefile" ] && [ ! -f "build.ninja" ]; then
    echo "❌ CMake 配置失败"
    exit 1
fi

# 只构建 C++ 库目标（不构建 Python 模块）
echo "🔧 编译 C++ 库..."
# 尝试构建 sageflow 目标（sageFlow 的主库）
if cmake --build . --config Release -j$(nproc) --target sageflow 2>&1 | tee /tmp/build.log; then
    echo "✅ sageflow 目标构建成功"
elif grep -q "No rule to make target" /tmp/build.log; then
    # 如果 sageflow 目标不存在，尝试构建所有目标但忽略 Python 绑定错误
    echo "ℹ️  尝试构建所有C++目标..."
    cmake --build . --config Release -j$(nproc) 2>&1 | grep -v "_sage_flow" || true
fi

# 安装 C++ 库
echo "📦 安装 C++ 库..."
cmake --install . --prefix "$SUBMODULE_DIR/install" 2>&1 || echo "⚠️  部分安装步骤跳过"

echo "✅ C++ 库构建完成"

# ==================== 步骤2: 构建Python绑定 ====================
echo ""
echo "🐍 步骤 2/2: 构建 Python 绑定（主仓库）"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

cd "$SCRIPT_DIR"

# 检查 Python 绑定源文件是否存在
BINDINGS_SRC="$PYTHON_DIR/bindings.cpp"
if [ ! -f "$BINDINGS_SRC" ]; then
    echo "❌ 错误: Python 绑定源文件不存在: $BINDINGS_SRC"
    exit 1
fi

# 查找 Python
PYTHON_CMD=$(which python3 || which python)
if [ -z "$PYTHON_CMD" ]; then
    echo "❌ 错误: 未找到 Python"
    exit 1
fi

echo "ℹ️  使用 Python: $PYTHON_CMD"

# 检查 pybind11 是否可用
if ! $PYTHON_CMD -c "import pybind11" 2>/dev/null; then
    echo "❌ 错误: pybind11 未安装"
    echo "请运行: pip install pybind11"
    exit 1
fi

# 创建临时的 setup.py 用于构建 Python 扩展
cat > "$SCRIPT_DIR/setup_temp.py" << 'SETUP_EOF'
import os
import sys
from pathlib import Path
from pybind11.setup_helpers import Pybind11Extension, build_ext
from setuptools import setup

# 获取路径
script_dir = Path(__file__).parent
submodule_dir = script_dir / "sageFlow"
install_dir = submodule_dir / "install"
build_dir = submodule_dir / "build"

# 包含目录
include_dirs = [
    str(submodule_dir / "include"),
    str(build_dir / "_deps" / "fmt-src" / "include"),
    str(build_dir / "_deps" / "spdlog-src" / "include"),
    str(build_dir / "_deps" / "tomlplusplus-src" / "include"),
]

# 库目录 - sageFlow的静态库
library_dirs = [str(build_dir / "lib")]

# 链接sageFlow的所有组件静态库
libraries = [
    "execution",
    "stream", 
    "query",
    "operator",
    "function",
    "common",
    "utils",
    "concurrency",
    "storage",
    "compute_engine",
    "index"
]

# Python bindings source (只需要bindings.cpp)
sources = [str(script_dir / "python" / "bindings.cpp")]

ext_modules = [
    Pybind11Extension(
        "_sage_flow",
        sources,
        include_dirs=include_dirs,
        library_dirs=library_dirs,
        libraries=libraries,
        cxx_std=20,
        extra_compile_args=["-O3"],
    ),
]

setup(
    name="_sage_flow",
    ext_modules=ext_modules,
    cmdclass={"build_ext": build_ext},
)
SETUP_EOF

# 构建 Python 扩展
echo "�� 编译 Python 绑定..."
$PYTHON_CMD "$SCRIPT_DIR/setup_temp.py" build_ext --inplace 2>&1

# 清理临时文件
rm -f "$SCRIPT_DIR/setup_temp.py"

# 检查生成的 .so 文件（可能在 python/ 目录或 build/ 目录）
SO_FILE=$(find "$PYTHON_DIR" -name "_sage_flow*.so" -type f 2>/dev/null | head -1)
if [ -z "$SO_FILE" ]; then
    # 如果 python/ 目录没有，检查 build/ 目录
    SO_FILE=$(find "$SCRIPT_DIR/build" -name "_sage_flow*.so" -type f 2>/dev/null | head -1)
    if [ -n "$SO_FILE" ]; then
        echo "ℹ️  在 build/ 目录找到 .so 文件，复制到 python/ 目录..."
        cp "$SO_FILE" "$PYTHON_DIR/"
    fi
fi

# 最终检查
SO_FILE=$(find "$PYTHON_DIR" -name "_sage_flow*.so" -type f 2>/dev/null | head -1)
if [ -f "$SO_FILE" ]; then
    echo "✅ Python 绑定构建成功: $(basename $SO_FILE)"
else
    echo "❌ 错误: 未找到生成的 .so 文件"
    echo "🔍 搜索路径:"
    echo "   - $PYTHON_DIR"
    echo "   - $SCRIPT_DIR/build"
    exit 1
fi

echo ""
echo "🎉 SAGE Flow 构建完成！"
exit 0
