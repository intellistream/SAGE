#!/bin/bash
set -e

echo "Building SAGE Queue - High-Performance Memory-Mapped Queue..."

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
        --debug|debug)
            BUILD_TYPE="Debug"
            echo "Debug build enabled"
            shift
            ;;
        --clean|clean)
            echo "Cleaning previous build..."
            rm -rf "$BUILD_DIR" "$INSTALL_PREFIX"
            shift
            ;;
        --install-deps)
            echo "Installing dependencies..."
            # Install build dependencies if needed
            # 检测是否在CI环境中
            if [[ "$CI" == "true" || "$GITHUB_ACTIONS" == "true" ]]; then
                echo "🔧 CI环境检测到，使用非交互式安装"
                export DEBIAN_FRONTEND=noninteractive
            fi
            
            if command -v apt-get &> /dev/null; then
                echo "📦 使用apt-get安装依赖..."
                if [[ "$CI" == "true" || "$GITHUB_ACTIONS" == "true" ]]; then
                    # CI环境：假设已有sudo权限且非交互式
                    apt-get update && apt-get install -y cmake g++ libboost-dev libboost-system-dev
                else
                    # 本地环境：需要sudo并可能需要交互
                    sudo apt-get update && sudo apt-get install -y cmake g++ libboost-dev libboost-system-dev
                fi
            elif command -v yum &> /dev/null; then
                echo "📦 使用yum安装依赖..."
                if [[ "$CI" == "true" || "$GITHUB_ACTIONS" == "true" ]]; then
                    yum install -y cmake gcc-c++ boost-devel
                else
                    sudo yum install -y cmake gcc-c++ boost-devel
                fi
            else
                echo "⚠️  未找到支持的包管理器 (apt-get/yum)"
                echo "请手动安装以下依赖："
                echo "  - cmake"
                echo "  - g++ 或 gcc-c++"
                echo "  - libboost-dev 或 boost-devel"
                echo "  - libboost-system-dev"
            fi
            shift
            ;;
        --help|-h)
            echo "SAGE Queue Build Script"
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --debug         Build in debug mode with AddressSanitizer"
            echo "  --clean         Clean previous build artifacts"
            echo "  --install-deps  Install build dependencies (cmake, g++, boost)"
            echo "  --help, -h      Show this help message"
            echo ""
            echo "Environment Variables:"
            echo "  CI=true         Enable CI mode (non-interactive)"
            echo "  GITHUB_ACTIONS=true  Enable GitHub Actions mode"
            echo ""
            echo "Examples:"
            echo "  $0                    # Normal build"
            echo "  $0 --clean --debug   # Clean and debug build"
            echo "  $0 --install-deps    # Install dependencies and build"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--debug|debug] [--clean|clean] [--install-deps] [--help|-h]"
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

# Create build directory
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

echo "Configuring with CMake..."
echo "  Build type: $BUILD_TYPE"
echo "  Source dir: $SCRIPT_DIR"
echo "  Build dir: $BUILD_DIR"

# Configure with CMake
cmake .. \
    -DCMAKE_BUILD_TYPE="$BUILD_TYPE" \
    -DCMAKE_INSTALL_PREFIX="$INSTALL_PREFIX" \
    -DBUILD_DEBUG=$([ "$BUILD_TYPE" == "Debug" ] && echo "ON" || echo "OFF") \
    -DBUILD_TESTS=ON \
    -DBUILD_PYTHON_BINDINGS=OFF \
    -DUSE_OPENMP=ON

# Build
echo "Building..."
make -j$(nproc)

# Create compatibility symlinks in the parent directory
cd "$SCRIPT_DIR"
ln -sf "$BUILD_DIR/libring_buffer.so" ring_buffer.so
ln -sf "$BUILD_DIR/libring_buffer.so" libring_buffer.so

echo "✅ Build completed successfully!"
echo "Library: $SCRIPT_DIR/$BUILD_DIR/libring_buffer.so"
echo "Symlinks: $SCRIPT_DIR/ring_buffer.so -> $BUILD_DIR/libring_buffer.so"

# Run tests if available
if [[ -f "$BUILD_DIR/test_sage_queue" ]]; then
    echo "Running tests..."
    cd "$BUILD_DIR"
    ctest --output-on-failure
    cd "$SCRIPT_DIR"
fi

echo "✅ SAGE Queue build completed successfully!"
