#!/bin/bash
# SAGE DB 构建包装脚本
# 此脚本调用子模块中的实际构建脚本
#
# 注意: Python绑定已从子模块移至主SAGE仓库
# 因此我们禁用子模块的Python绑定构建，只构建C++库

set -e

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SUBMODULE_DIR="$SCRIPT_DIR/sageDB"

# 检查子模块是否已初始化
if [ ! -d "$SUBMODULE_DIR" ] || [ ! -f "$SUBMODULE_DIR/build.sh" ]; then
    echo "错误: sageDB 子模块未初始化"
    echo "请运行: git submodule update --init --recursive"
    exit 1
fi

# 切换到子模块目录
cd "$SUBMODULE_DIR"

echo "🔨 构建 SAGE DB C++库 (Python绑定在主仓库中构建)..."

# 创建临时的build.sh包装，禁用Python绑定
# 因为Python绑定已移至主SAGE仓库
BUILD_TYPE=${BUILD_TYPE:-Debug}

# 检查libstdc++（从原build.sh复制）
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
mkdir -p build

# 配置CMake - 关键：禁用Python绑定
cmake_args=(
    -DCMAKE_BUILD_TYPE="${BUILD_TYPE}"
    -DCMAKE_INSTALL_PREFIX="$(pwd)/install"
    -DBUILD_TESTS=OFF
    -DBUILD_PYTHON_BINDINGS=OFF
    -DUSE_OPENMP=ON
)

# 传递环境变量
if [[ -n "${SAGE_COMMON_DEPS_FILE:-}" ]]; then
    cmake_args+=(-DSAGE_COMMON_DEPS_FILE="${SAGE_COMMON_DEPS_FILE}")
fi
if [[ -n "${SAGE_ENABLE_GPERFTOOLS:-}" ]]; then
    cmake_args+=(-DSAGE_ENABLE_GPERFTOOLS="${SAGE_ENABLE_GPERFTOOLS}")
fi

echo "� CMake配置: ${cmake_args[@]}"
cmake -B build "${cmake_args[@]}"

# 构建
echo "🔧 开始编译..."
cmake --build build -j "$(nproc)"

echo "✅ SAGE DB C++库构建完成"

BUILD_STATUS=$?

if [ $BUILD_STATUS -eq 0 ]; then
    echo "✅ SAGE DB 构建成功"
    
    # 将构建产物复制到父目录的python目录
    if [ -d "build" ]; then
        PARENT_PYTHON_DIR="$SCRIPT_DIR/python"
        mkdir -p "$PARENT_PYTHON_DIR"
        
        # 查找并复制.so文件
        find build -name "_sage_db*.so" -type f -exec cp {} "$PARENT_PYTHON_DIR/" \;
        
        if [ -f "$PARENT_PYTHON_DIR/_sage_db"*.so ]; then
            echo "✅ 已复制扩展模块到 $PARENT_PYTHON_DIR"
        fi
    fi
else
    echo "❌ SAGE DB 构建失败"
    exit $BUILD_STATUS
fi

exit 0
