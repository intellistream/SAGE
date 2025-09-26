#!/bin/bash
set -e

echo "Building SAGE DB - Vector Database Module..."

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Configuration
BUILD_TYPE="Release"
BUILD_DIR="build"
INSTALL_PREFIX="$SCRIPT_DIR/install"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --debug)
            BUILD_TYPE="Debug"
            shift
            ;;
        --clean)
            echo "Cleaning previous build..."
            rm -rf "$BUILD_DIR" "$INSTALL_PREFIX"
            shift
            ;;
        --install-deps)
            echo "Installing dependencies (system + Python packages)..."
            
            # Install system dependencies first
            echo "📦 Installing system dependencies..."
            set +e
            SYSTEM_DEPS_INSTALLED=false
            
            # 检查是否在 CI 环境中，CI 环境中依赖应该已经由专用脚本安装
            if [[ "${CI:-false}" == "true" ]]; then
                echo "🤖 CI 环境检测到，依赖应该已由 install_system_deps.sh 安装"
                # 验证系统依赖是否可用
                if pkg-config --exists openblas lapack 2>/dev/null || \
                   ldconfig -p | grep -q "libopenblas\|libblas" 2>/dev/null; then
                    echo "✅ 系统 BLAS/LAPACK 库已可用"
                    SYSTEM_DEPS_INSTALLED=true
                else
                    echo "⚠️  系统 BLAS/LAPACK 库未找到，但在 CI 环境中继续构建"
                    SYSTEM_DEPS_INSTALLED=true  # 在 CI 中强制继续，让 CMake 处理
                fi
            elif command -v apt-get &> /dev/null; then
                echo "🔧 Installing BLAS/LAPACK via apt..."
                if sudo apt-get update -qq && sudo apt-get install -y libopenblas-dev liblapack-dev; then
                    echo "✅ System dependencies installed via apt"
                    SYSTEM_DEPS_INSTALLED=true
                fi
            elif command -v yum &> /dev/null; then
                echo "🔧 Installing BLAS/LAPACK via yum..."
                if sudo yum install -y openblas-devel lapack-devel; then
                    echo "✅ System dependencies installed via yum"
                    SYSTEM_DEPS_INSTALLED=true
                fi
            elif command -v dnf &> /dev/null; then
                echo "🔧 Installing BLAS/LAPACK via dnf..."
                if sudo dnf install -y openblas-devel lapack-devel; then
                    echo "✅ System dependencies installed via dnf"
                    SYSTEM_DEPS_INSTALLED=true
                fi
            elif command -v pacman &> /dev/null; then
                echo "🔧 Installing BLAS/LAPACK via pacman..."
                if sudo pacman -S --noconfirm openblas lapack; then
                    echo "✅ System dependencies installed via pacman"
                    SYSTEM_DEPS_INSTALLED=true
                fi
            elif command -v brew &> /dev/null; then
                echo "🔧 Installing BLAS/LAPACK via homebrew..."
                if brew install openblas lapack; then
                    echo "✅ System dependencies installed via homebrew"
                    SYSTEM_DEPS_INSTALLED=true
                fi
            elif [[ -n "$CONDA_PREFIX" ]]; then
                echo "🔧 Installing BLAS/LAPACK via conda..."
                if conda install -c conda-forge openblas liblapack -y; then
                    echo "✅ System dependencies installed via conda"
                    SYSTEM_DEPS_INSTALLED=true
                fi
            else
                echo "⚠️  Could not detect package manager"
            fi
            
            if [ "$SYSTEM_DEPS_INSTALLED" != true ]; then
                echo "⚠️  System dependencies installation failed or not available"
                echo "   The build will continue but may fail if BLAS/LAPACK are required"
                echo "   Manual installation commands:"
                echo "   Ubuntu/Debian: sudo apt-get install libopenblas-dev liblapack-dev"
                echo "   CentOS/RHEL: sudo yum install openblas-devel lapack-devel"
                echo "   macOS: brew install openblas lapack"
                echo "   Conda: conda install -c conda-forge openblas liblapack"
            fi
            set -e
            
            # Install Python dependencies
            echo "📦 Installing Python dependencies..."
            # Avoid failing the entire build if dependency install has conflicts (e.g., conda solver pins)
            set +e
            INSTALLED=false
            if command -v pip &> /dev/null; then
                echo "📦 Trying: pip install faiss-cpu pybind11[global]"
                pip install --upgrade pip >/dev/null 2>&1
                if pip install "faiss-cpu>=1.7.3" "pybind11[global]"; then
                    INSTALLED=true
                    echo "✅ Dependencies installed via pip"
                else
                    echo "⚠️  pip installation failed, will try conda if available"
                fi
            fi

            if [ "$INSTALLED" != true ] && command -v conda &> /dev/null; then
                echo "📦 Trying: conda install -c conda-forge faiss-cpu pybind11"
                # Use conda-forge explicitly and allow failures (avoid libmamba pin issues on CI)
                if conda install -c conda-forge faiss-cpu pybind11 -y; then
                    INSTALLED=true
                    echo "✅ Dependencies installed via conda"
                else
                    echo "⚠️  conda installation failed; continuing without FAISS (fallback build)"
                fi
            fi

            if [ "$INSTALLED" != true ]; then
                echo "ℹ️ Proceeding without FAISS; the build will use a fallback implementation."
                echo "   For optimal performance, install FAISS manually later:"
                echo "   - pip install faiss-cpu"
                echo "   - or: conda install -c conda-forge faiss-cpu"
            fi
            set -e
            shift
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --debug        Build in debug mode"
            echo "  --clean        Clean previous build"
            echo "  --install-deps Install dependencies (FAISS, pybind11)"
            echo "  --help         Show this help"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Check for required tools
echo "Checking build dependencies..."

if ! command -v cmake &> /dev/null; then
    echo "❌ CMake not found. Please install CMake."
    exit 1
fi

if ! command -v g++ &> /dev/null && ! command -v clang++ &> /dev/null; then
    echo "❌ No C++ compiler found. Please install g++ or clang++."
    exit 1
fi

echo "✅ Build tools found"

# Try to find FAISS
echo "Checking for FAISS..."
FAISS_FOUND=false

# Check in conda environment
if [[ -n "$CONDA_PREFIX" ]] && [[ -f "$CONDA_PREFIX/include/faiss/IndexFlat.h" ]]; then
    echo "✅ Found FAISS in conda environment: $CONDA_PREFIX"
    FAISS_FOUND=true
    export CMAKE_PREFIX_PATH="$CONDA_PREFIX:$CMAKE_PREFIX_PATH"
elif [[ -f "/usr/local/include/faiss/IndexFlat.h" ]]; then
    echo "✅ Found FAISS in system path"
    FAISS_FOUND=true
elif [[ -f "/usr/include/faiss/IndexFlat.h" ]]; then
    echo "✅ Found FAISS in system path"
    FAISS_FOUND=true
else
    echo "⚠️  FAISS not found. Building with fallback implementation."
    echo "   For optimal performance, install FAISS:"
    echo "   conda install -c conda-forge faiss-cpu"
    echo "   or: pip install faiss-cpu"
fi

# Create build directory
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

# Configure with CMake
echo "Configuring build..."
CMAKE_ARGS=(
    "-DCMAKE_BUILD_TYPE=$BUILD_TYPE"
    "-DCMAKE_INSTALL_PREFIX=$INSTALL_PREFIX"
    "-DBUILD_TESTS=ON"
    "-DBUILD_PYTHON_BINDINGS=ON"
    "-DUSE_OPENMP=ON"
)

# Add conda prefix if available
if [[ -n "$CONDA_PREFIX" ]]; then
    CMAKE_ARGS+=("-DCMAKE_PREFIX_PATH=$CONDA_PREFIX")
    CMAKE_ARGS+=("-DPython3_ROOT_DIR=$CONDA_PREFIX")
fi

# Add system library paths for CI environments
CMAKE_ARGS+=("-DCMAKE_PREFIX_PATH=/usr/lib/x86_64-linux-gnu:/usr/include:/usr/local:${CMAKE_PREFIX_PATH}")

# Set specific BLAS vendor for consistent behavior
CMAKE_ARGS+=("-DBLA_VENDOR=OpenBLAS")

# Debug information
echo "CMAKE_ARGS: ${CMAKE_ARGS[@]}"
echo "Environment:"
echo "  CONDA_PREFIX: $CONDA_PREFIX"
echo "  CMAKE_PREFIX_PATH: $CMAKE_PREFIX_PATH"

cmake "${CMAKE_ARGS[@]}" ..

# Build
echo "Building..."
echo "🔨 开始编译 (使用 $(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 4) 个并行任务)..."

if ! make -j$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 4); then
    echo "❌ 编译失败，显示详细错误信息："
    echo ""
    echo "=== CMake 配置信息 ==="
    if [ -f "CMakeCache.txt" ]; then
        echo "CMAKE_BUILD_TYPE: $(grep CMAKE_BUILD_TYPE CMakeCache.txt || echo '未设置')"
        echo "CMAKE_PREFIX_PATH: $(grep CMAKE_PREFIX_PATH CMakeCache.txt || echo '未设置')"
        echo "BLAS_FOUND: $(grep BLAS_FOUND CMakeCache.txt || echo '未找到')"
        echo "LAPACK_FOUND: $(grep LAPACK_FOUND CMakeCache.txt || echo '未找到')"
        echo "BLAS_LIBRARIES: $(grep BLAS_LIBRARIES CMakeCache.txt || echo '未设置')"
        echo "LAPACK_LIBRARIES: $(grep LAPACK_LIBRARIES CMakeCache.txt || echo '未设置')"
    fi
    echo ""
    echo "=== 系统库检查 ==="
    echo "BLAS 库搜索路径:"
    find /usr -name "*blas*" -type f 2>/dev/null | head -5 || echo "未找到"
    echo "LAPACK 库搜索路径:"
    find /usr -name "*lapack*" -type f 2>/dev/null | head -5 || echo "未找到"
    echo ""
    echo "请检查上述错误信息并安装缺失的依赖"
    exit 1
fi

# Run tests if available
if [[ -f "test_sage_db" ]]; then
    echo "Running tests..."
    ./test_sage_db
fi

# Install
echo "Installing..."
make install

# Copy Python extension next to canonical python/ for import stability
cd "$SCRIPT_DIR"
if ls "$BUILD_DIR"/_sage_db* 1> /dev/null 2>&1; then
    echo "Copying Python extension into python/ ..."
    mkdir -p python
    cp "$BUILD_DIR"/_sage_db* python/
fi

echo "✅ SAGE DB build completed!"
echo ""
echo "📁 Files prepared:"
echo "   - libsage_db.* (C++ library in build)"
echo "   - python/_sage_db.* (Python C++ extension)"
echo "   - python/sage_db.py (Python API wrapper in repo)"
echo ""
