#!/bin/bash
set -e

echo "Building SAGE Queue with CMake..."

# Parse command line arguments
DEBUG_BUILD=OFF
CLEAN_BUILD=false

while [[ $# -gt 0 ]]; do
    case $1 in
        debug)
            DEBUG_BUILD=ON
            echo "Debug build enabled"
            shift
            ;;
        clean)
            CLEAN_BUILD=true
            echo "Clean build enabled"
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [debug] [clean]"
            exit 1
            ;;
    esac
done

# Clean previous build if requested
if [[ "$CLEAN_BUILD" == "true" ]]; then
    echo "Cleaning previous build..."
    rm -rf build
fi

# Create build directory
mkdir -p build
cd build

# Configure with CMake
echo "Configuring with CMake..."
cmake .. \
    -DCMAKE_BUILD_TYPE=$([ "$DEBUG_BUILD" == "ON" ] && echo "Debug" || echo "Release") \
    -DBUILD_DEBUG=$DEBUG_BUILD \
    -DBUILD_TESTS=ON \
    -DBUILD_PYTHON_BINDINGS=OFF \
    -DUSE_OPENMP=ON

# Build
echo "Building..."
make -j$(nproc)

# Create compatibility symlink in the original location
cd ..
ln -sf build/libring_buffer.so ring_buffer.so
ln -sf build/libring_buffer.so libring_buffer.so

echo "✓ Build completed successfully!"
echo "Library: $(pwd)/build/libring_buffer.so"
echo "Symlink: $(pwd)/ring_buffer.so -> build/libring_buffer.so"

# Run tests if available
if [[ -f "build/test_sage_queue" ]]; then
    echo "Running tests..."
    cd build
    ctest --output-on-failure
    cd ..
fi
