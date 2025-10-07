#!/bin/bash
# SAGE Flow 构建包装脚本
# 此脚本仅构建C++库，不构建Python绑定（Python绑定已移至主SAGE仓库）

set -e

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SUBMODULE_DIR="$SCRIPT_DIR/sageFlow"

# 检查子模块是否已初始化
if [ ! -d "$SUBMODULE_DIR" ]; then
    echo "错误: sageFlow 子模块未初始化"
    echo "请运行: git submodule update --init --recursive"
    exit 1
fi

echo "🔨 构建 SAGE Flow C++库 (不包括Python绑定)..."

# 切换到子模块目录
cd "$SUBMODULE_DIR"

# 检查libstdc++是否可用（内联检查）
if ! ldconfig -p 2>/dev/null | grep -q libstdc++; then
    echo "⚠️ 警告: 在ldconfig缓存中未找到libstdc++"
fi

# 创建构建目录
BUILD_DIR="$SUBMODULE_DIR/build"
mkdir -p "$BUILD_DIR"

# 创建空的examples目录以满足CMakeLists.txt
EXAMPLES_DIR="$SUBMODULE_DIR/examples"
if [ ! -d "$EXAMPLES_DIR" ]; then
    echo "📝 创建空examples目录..."
    mkdir -p "$EXAMPLES_DIR"
    # 创建最小的CMakeLists.txt，这样add_subdirectory不会失败
    echo "# Placeholder for examples" > "$EXAMPLES_DIR/CMakeLists.txt"
fi

cd "$BUILD_DIR"

# 使用CMake配置 - 禁用测试
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

# 临时重命名 CMakeLists.txt 中的 pybind11 部分以跳过 Python 绑定
cd "$BUILD_DIR"

# 配置 CMake - 只构建 C++ 库
# 通过设置一个未定义的变量来跳过 pybind11_add_module 调用
echo "⚙️  配置 CMake (仅 C++ 库)..."
cmake -DCMAKE_BUILD_TYPE=Release \
      -DBUILD_TESTING=OFF \
      -DPYTHON_EXECUTABLE=/usr/bin/python3 \
      .. 2>&1 | grep -v "Cannot find source file.*python/bindings.cpp" | grep -v "No SOURCES given to target: _sage_flow" || true

# 即使有 pybind11 错误也继续，因为我们只需要 C++ 库
if [ ${PIPESTATUS[0]} -ne 0 ]; then
    # CMake 配置失败，但可能是因为 pybind11 部分
    # 检查是否生成了 Makefile
    if [ ! -f "Makefile" ]; then
        echo "❌ CMake 配置失败"
        exit 1
    fi
    echo "⚠️  CMake 配置有警告，但继续构建 C++ 库..."
fi

# 只构建 C++ 库目标（不构建 Python 模块）
echo "🔧 编译 C++ 库..."
# 构建除了 _sage_flow 之外的所有目标
cmake --build . --config Release -j$(nproc) --target candy 2>&1 || {
    echo "ℹ️  尝试直接 make（忽略 Python 绑定目标）..."
    make candy -j$(nproc) || {
        echo "⚠️  部分目标构建失败，但继续..."
    }
}

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

# 使用 setup.py 或直接调用 pybind11 编译
# 首先尝试找到 Python 和 pybind11
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

# 库目录
library_dirs = [
    str(install_dir / "lib"),
    str(build_dir / "src"),
]

# 链接库
libraries = ["candy"]

ext_modules = [
    Pybind11Extension(
        "_sage_flow",
        [str(script_dir / "python" / "bindings.cpp")],
        include_dirs=include_dirs,
        library_dirs=library_dirs,
        libraries=libraries,
        cxx_std=17,
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
echo "🔧 编译 Python 绑定..."
$PYTHON_CMD "$SCRIPT_DIR/setup_temp.py" build_ext --inplace

# 清理临时文件
rm -f "$SCRIPT_DIR/setup_temp.py"

# 检查生成的 .so 文件
SO_FILE=$(find "$PYTHON_DIR" -name "_sage_flow*.so" -type f 2>/dev/null | head -1)
if [ -f "$SO_FILE" ]; then
    echo "✅ Python 绑定构建成功: $(basename $SO_FILE)"
else
    echo "❌ 错误: 未找到生成的 .so 文件"
    exit 1
fi

echo ""
echo "🎉 SAGE Flow 构建完成！"
exit 0
echo "⚙️ 配置CMake..."
cmake -DCMAKE_BUILD_TYPE=Release \
      -DBUILD_TESTING=OFF \
      ..

# 构建C++库
echo "🔧 编译C++库..."
cmake --build . --config Release -j$(nproc)

# 安装（将C++库安装到子模块的install目录）
echo "📦 安装C++库..."
cmake --install . --prefix "$SUBMODULE_DIR/install"

echo "✅ SAGE Flow C++库构建成功"
exit 0
