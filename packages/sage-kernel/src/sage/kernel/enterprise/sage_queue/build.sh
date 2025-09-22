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
            if command -v apt-get &> /dev/null; then
                sudo apt-get update && sudo apt-get install -y cmake g++
            elif command -v yum &> /dev/null; then
                sudo yum install -y cmake gcc-c++
            fi
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--debug|debug] [--clean|clean] [--install-deps]"
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
