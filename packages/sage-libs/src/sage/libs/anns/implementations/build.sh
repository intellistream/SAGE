#!/bin/bash
# ============================================================================
# 构建 PyCANDYAlgo 模块的脚本
# ============================================================================
#
# 本脚本只负责构建 PyCANDYAlgo Python 扩展模块。
# 第三方库 (GTI, IP-DiskANN, PLSH) 由 build_all.sh 统一管理。
#
# 使用方法:
#   ./build.sh [--clean] [--jobs N]
#
# 选项:
#   --clean    清理旧构建目录后重新构建
#   --jobs N   指定并行编译数 (默认自动计算)
#   --help     显示帮助信息
# ============================================================================

set -e  # 遇到错误立即退出

# ============================================================================
# 颜色定义
# ============================================================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_success() { echo -e "${GREEN}✓ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠ $1${NC}"; }
print_error() { echo -e "${RED}✗ $1${NC}"; }
print_info() { echo -e "${BLUE}→ $1${NC}"; }

# ============================================================================
# 解析命令行参数
# ============================================================================
CLEAN_BUILD=false
CUSTOM_JOBS=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --clean)
            CLEAN_BUILD=true
            shift
            ;;
        --jobs)
            CUSTOM_JOBS="$2"
            shift 2
            ;;
        --help)
            head -n 18 "$0" | tail -n +2 | sed 's/^# //'
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# ============================================================================
# 获取脚本所在目录的绝对路径
# ============================================================================
ALGORITHMS_IMPL_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$ALGORITHMS_IMPL_DIR"

echo "========================================="
echo "Building PyCANDYAlgo Module"
echo "========================================="
echo ""

# ============================================================================
# 检查基本依赖
# ============================================================================
echo "Checking dependencies..."

python3 -c "import torch" 2>/dev/null || { print_error "PyTorch not installed. Run: pip install torch"; exit 1; }
print_success "PyTorch found"

which cmake >/dev/null 2>&1 || { print_error "CMake not installed"; exit 1; }
print_success "CMake found: $(cmake --version | head -n1)"

pkg-config --exists gflags 2>/dev/null || print_warning "gflags not found (may cause build errors)"

echo ""

# ============================================================================
# 计算并行编译数
# ============================================================================
if [ -n "$CUSTOM_JOBS" ]; then
    JOBS=$CUSTOM_JOBS
else
    NPROC=$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 4)
    # 根据可用内存计算 (每个编译进程约需 1-2GB)
    AVAILABLE_MEM=$(free -g 2>/dev/null | awk '/^Mem:/{print $7}' || echo 8)
    MAX_JOBS=$((AVAILABLE_MEM / 2))
    JOBS=$((MAX_JOBS < NPROC ? MAX_JOBS : NPROC))
    JOBS=$((JOBS < 1 ? 1 : JOBS))
    JOBS=$((JOBS > 8 ? 8 : JOBS))  # 最多 8 个
fi
print_info "Using -j${JOBS} for parallel compilation"

# ============================================================================
# 设置 MKL 环境变量（Puck 需要）
# ============================================================================
echo ""
echo "Setting up build environment..."
echo "----------------------------------------"

if [ -f "/opt/intel/oneapi/setvars.sh" ]; then
    print_info "Loading Intel oneAPI environment..."
    source /opt/intel/oneapi/setvars.sh --force 2>/dev/null || true
fi

if [ -d "/opt/intel/oneapi/mkl/latest" ]; then
    export MKLROOT="/opt/intel/oneapi/mkl/latest"
    export LD_LIBRARY_PATH="$MKLROOT/lib/intel64:$LD_LIBRARY_PATH"
    export CPATH="$MKLROOT/include:$CPATH"
    export CMAKE_PREFIX_PATH="$MKLROOT:$CMAKE_PREFIX_PATH"
    export LIBRARY_PATH="$MKLROOT/lib/intel64:$LIBRARY_PATH"
    print_success "MKL found: $MKLROOT"
elif [ -d "/opt/intel/mkl" ]; then
    export MKLROOT="/opt/intel/mkl"
    export LD_LIBRARY_PATH="$MKLROOT/lib/intel64:$LD_LIBRARY_PATH"
    export CPATH="$MKLROOT/include:$CPATH"
    export CMAKE_PREFIX_PATH="$MKLROOT:$CMAKE_PREFIX_PATH"
    export LIBRARY_PATH="$MKLROOT/lib/intel64:$LIBRARY_PATH"
    print_success "MKL found: $MKLROOT"
else
    print_warning "MKL not found - Puck may fail to build"
fi

# 获取 PyTorch CMake 路径
TORCH_CMAKE_PATH=""
if python3 -c "import torch; print(torch.utils.cmake_prefix_path)" 2>/dev/null; then
    TORCH_CMAKE_PATH=$(python3 -c "import torch; print(torch.utils.cmake_prefix_path)")
    print_success "PyTorch CMake path: $TORCH_CMAKE_PATH"
else
    print_warning "Could not get torch.utils.cmake_prefix_path"
fi

# ============================================================================
# 清理旧构建（如果指定）
# ============================================================================
if [ "$CLEAN_BUILD" = true ]; then
    echo ""
    print_info "Cleaning old build directory..."
    rm -rf build
    rm -f PyCANDYAlgo*.so
fi

# ============================================================================
# 创建构建目录并配置 CMake
# ============================================================================
mkdir -p build
cd build

# 检查是否需要重新配置 CMake
NEED_CMAKE_CONFIG=false
if [ ! -f "Makefile" ] || [ ! -f "CMakeCache.txt" ]; then
    NEED_CMAKE_CONFIG=true
fi

if [ "$NEED_CMAKE_CONFIG" = true ]; then
    echo ""
    echo "Configuring with CMake..."
    echo "----------------------------------------"

    # 构建 CMake 参数
    CMAKE_ARGS=(
        -DCMAKE_BUILD_TYPE=Release
        -DPYTHON_EXECUTABLE=$(which python3)
        -DFAISS_ENABLE_GPU=OFF
        -DFAISS_ENABLE_PYTHON=OFF
        -DBUILD_TESTING=OFF
    )

    # 添加 torch 路径
    if [ -n "$TORCH_CMAKE_PATH" ]; then
        CMAKE_ARGS+=(-DCMAKE_PREFIX_PATH="$TORCH_CMAKE_PATH")
    fi

    # 运行 CMake 配置
    print_info "Running: cmake ${CMAKE_ARGS[*]} .."
    cmake "${CMAKE_ARGS[@]}" .. \
        2>&1 | tee cmake_config.log \
        || { echo ""; print_error "CMake configuration failed"; cat cmake_config.log | tail -50; exit 1; }

    print_success "CMake configuration complete"
else
    print_info "Using existing CMake configuration (use --clean to reconfigure)"
fi

# ============================================================================
# 编译 PyCANDYAlgo
# ============================================================================
echo ""
echo "========================================="
echo "Compiling PyCANDYAlgo"
echo "========================================="
echo ""

make -j${JOBS} PyCANDYAlgo || { print_error "Build failed"; exit 1; }

# 返回上级目录
cd ..

# ============================================================================
# 检查和复制生成的 .so 文件
# ============================================================================
echo ""
echo "========================================="
echo "Build Complete"
echo "========================================="
echo ""

# 检查生成的文件
SO_FILE=$(ls PyCANDYAlgo*.so 2>/dev/null | head -1)

if [ -n "$SO_FILE" ]; then
    print_success "PyCANDYAlgo module generated:"
    ls -lh "$SO_FILE"
    echo ""

    # 测试本地导入
    print_info "Testing local import..."
    if python3 -c "import sys; sys.path.insert(0, '.'); import PyCANDYAlgo; print('  Version:', PyCANDYAlgo.__version__)" 2>&1; then
        print_success "Import test passed"
    else
        print_warning "Local import test failed (may need to activate venv)"
        echo "  This is not critical - the .so file was built successfully"
    fi
else
    # 可能在 build 目录中
    SO_FILE=$(find build -name "PyCANDYAlgo*.so" 2>/dev/null | head -1)
    if [ -n "$SO_FILE" ]; then
        print_info "Found .so file in build directory, copying..."
        cp "$SO_FILE" .
        print_success "PyCANDYAlgo module copied to: $(pwd)/$(basename "$SO_FILE")"
    else
        print_error "PyCANDYAlgo.so not found"
        exit 1
    fi
fi

echo ""
print_info "To use PyCANDYAlgo:"
echo "  python3 -c 'import PyCANDYAlgo'"
echo ""

exit 0
