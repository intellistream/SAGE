#!/bin/bash
# Build script for SAGE TSDB C++ extension

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TSDB_DIR="$SCRIPT_DIR/sageTSDB"
BUILD_DIR="$TSDB_DIR/build"
PYTHON_DIR="$SCRIPT_DIR/python"

echo "🔨 Building SAGE TSDB C++ Extension"
echo "===================================="

# Check if sageTSDB submodule is initialized
if [ ! -f "$TSDB_DIR/CMakeLists.txt" ]; then
    echo "❌ Error: sageTSDB submodule not initialized"
    echo "   Run: git submodule update --init --recursive"
    exit 1
fi

# Create build directory if it doesn't exist
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

# Configure with CMake
echo "📋 Configuring CMake..."
cmake .. -DBUILD_PYTHON_BINDINGS=ON

# Build
echo "🔧 Building..."
make -j$(nproc)

# Find the generated .so file
SO_FILE=$(find "$BUILD_DIR/python" -name "_sage_tsdb*.so" -type f | head -n 1)

if [ -z "$SO_FILE" ]; then
    echo "❌ Error: Failed to build _sage_tsdb.so"
    exit 1
fi

# Copy to Python package directory
echo "📦 Installing Python extension..."
cp "$SO_FILE" "$PYTHON_DIR/"

echo "✅ SAGE TSDB C++ extension built successfully!"
echo "   Location: $PYTHON_DIR/$(basename $SO_FILE)"
