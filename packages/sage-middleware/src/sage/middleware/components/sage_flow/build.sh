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
# 注意: sageFlow没有BUILD_PYTHON_BINDINGS选项，
# 但如果pybind11不可用或python/bindings.cpp缺失，CMake会自动跳过Python绑定
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
