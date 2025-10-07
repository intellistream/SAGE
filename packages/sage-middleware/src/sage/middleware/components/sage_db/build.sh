#!/bin/bash
# SAGE DB 构建包装脚本
# 分两步构建：1) C++库（子模块） 2) Python绑定（主仓库）
#
# 注意: Python绑定已从子模块移至主SAGE仓库

set -e

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SUBMODULE_DIR="$SCRIPT_DIR/sageDB"
PYTHON_DIR="$SCRIPT_DIR/python"

echo "🔨 构建 SAGE DB..."

# ==================== 步骤1: 构建C++库 ====================
echo ""
echo "📦 步骤 1/2: 构建 C++ 库（sageDB 子模块）"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 检查子模块是否已初始化
if [ ! -d "$SUBMODULE_DIR" ]; then
    echo "❌ 错误: sageDB 子模块未初始化"
    echo "请运行: git submodule update --init --recursive"
    exit 1
fi

cd "$SUBMODULE_DIR"

# libstdc++ 兼容性检查
check_libstdcxx() {
    if [[ -z "${CONDA_PREFIX}" ]]; then
        return 0
    fi
    local conda_libstdcxx="${CONDA_PREFIX}/lib/libstdc++.so.6"
    if [[ ! -f "${conda_libstdcxx}" ]]; then
        return 0
    fi
    local gcc_version=$(gcc -dumpversion | cut -d. -f1)
    if [[ ${gcc_version} -ge 11 ]]; then
        if ! strings "${conda_libstdcxx}" | grep -q "GLIBCXX_3.4.30"; then
            echo "⚠️  检测到conda环境中的libstdc++版本过低，正在更新..."
            if command -v conda &> /dev/null; then
                conda install -c conda-forge libstdcxx-ng -y || {
                    if [[ -f "/usr/lib/x86_64-linux-gnu/libstdc++.so.6" ]]; then
                        export LD_LIBRARY_PATH="/usr/lib/x86_64-linux-gnu:${LD_LIBRARY_PATH}"
                    fi
                }
            fi
        fi
    fi
}

check_libstdcxx

# 创建build目录
BUILD_DIR="$SUBMODULE_DIR/build"
mkdir -p "$BUILD_DIR"

# 配置CMake - 禁用Python绑定和测试
BUILD_TYPE=${BUILD_TYPE:-Release}

cmake_args=(
    -DCMAKE_BUILD_TYPE="${BUILD_TYPE}"
    -DCMAKE_INSTALL_PREFIX="$SUBMODULE_DIR/install"
    -DBUILD_TESTS=OFF
    -DBUILD_PYTHON_BINDINGS=OFF
    -DUSE_OPENMP=ON
)

# 传递可选环境变量
if [[ -n "${SAGE_COMMON_DEPS_FILE:-}" ]]; then
    cmake_args+=(-DSAGE_COMMON_DEPS_FILE="${SAGE_COMMON_DEPS_FILE}")
fi
if [[ -n "${SAGE_ENABLE_GPERFTOOLS:-}" ]]; then
    cmake_args+=(-DSAGE_ENABLE_GPERFTOOLS="${SAGE_ENABLE_GPERFTOOLS}")
fi

echo "⚙️  CMake配置: ${cmake_args[@]}"
cmake -B "$BUILD_DIR" "${cmake_args[@]}"

# 构建C++库
echo "🔧 编译 C++ 库..."
cmake --build "$BUILD_DIR" -j "$(nproc)"

# 安装C++库
echo "📦 安装 C++ 库..."
cmake --install "$BUILD_DIR"

echo "✅ C++ 库构建完成"

# ==================== 步骤2: 构建Python绑定 ====================
echo ""
echo "🐍 步骤 2/2: 构建 Python 绑定（主仓库）"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

cd "$SCRIPT_DIR"

# 检查 Python 绑定源文件
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

# 检查 pybind11
if ! $PYTHON_CMD -c "import pybind11" 2>/dev/null; then
    echo "❌ 错误: pybind11 未安装"
    echo "请运行: pip install pybind11"
    exit 1
fi

# 创建临时 setup.py
cat > "$SCRIPT_DIR/setup_temp.py" << 'SETUP_EOF'
import os
import sys
from pathlib import Path
from pybind11.setup_helpers import Pybind11Extension, build_ext
from setuptools import setup

# 获取路径
script_dir = Path(__file__).parent
submodule_dir = script_dir / "sageDB"
install_dir = submodule_dir / "install"
build_dir = submodule_dir / "build"

# 包含目录
include_dirs = [
    str(submodule_dir / "include"),
    str(build_dir / "_deps" / "fmt-src" / "include"),
    str(build_dir / "_deps" / "spdlog-src" / "include"),
]

# 库目录
library_dirs = [
    str(install_dir / "lib"),
    str(build_dir),
]

# 链接库 - 注意：库文件名是 libsage_db.so，链接时用 sage_db
libraries = ["sage_db"]

# 添加运行时库路径，确保运行时能找到 .so
runtime_library_dirs = [
    str(install_dir / "lib"),
    str(build_dir),
]

ext_modules = [
    Pybind11Extension(
        "_sage_db",
        [str(script_dir / "python" / "bindings.cpp")],
        include_dirs=include_dirs,
        library_dirs=library_dirs,
        libraries=libraries,
        runtime_library_dirs=runtime_library_dirs,
        cxx_std=17,
        extra_compile_args=["-O3"],
    ),
]

setup(
    name="_sage_db",
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
SO_FILE=$(find "$PYTHON_DIR" -name "_sage_db*.so" -type f 2>/dev/null | head -1)
if [ -f "$SO_FILE" ]; then
    echo "✅ Python 绑定构建成功: $(basename $SO_FILE)"
else
    echo "❌ 错误: 未找到生成的 .so 文件"
    exit 1
fi

echo ""
echo "🎉 SAGE DB 构建完成！"
exit 0
