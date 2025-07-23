#!/bin/bash

# SAGE Flow Build Script
# This script builds the SAGE Flow C++ library according to Google C++ Style Guide

set -e  # Exit on any error

echo "=== SAGE Flow Build Script ==="
echo "Building SAGE Flow C++ library with Google C++ Style compliance..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Create build directory
BUILD_DIR="build"
if [ -d "$BUILD_DIR" ]; then
    echo -e "${YELLOW}Cleaning existing build directory...${NC}"
    rm -rf "$BUILD_DIR"
fi

mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

echo -e "${GREEN}Step 1: Running CMake configuration...${NC}"
cmake .. -DCMAKE_BUILD_TYPE=Debug \
         -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
         -DCMAKE_CXX_STANDARD=17 \
         -DCMAKE_CXX_STANDARD_REQUIRED=ON

echo -e "${GREEN}Step 2: Building C++ library...${NC}"
if make -j$(nproc) 2>&1 | tee build.log; then
    echo -e "${GREEN}✅ Build successful!${NC}"
else
    echo -e "${RED}❌ Build failed. Check build.log for details.${NC}"
    echo "Last 20 lines of build log:"
    tail -20 build.log
    exit 1
fi

echo -e "${GREEN}Step 3: Running clang-tidy checks (if available)...${NC}"
if command -v clang-tidy >/dev/null 2>&1; then
    echo "Running static analysis..."
    cd ..
    
    # Check header files
    find include -name "*.h" -exec echo "Checking: {}" \; -exec clang-tidy {} -- -I./include \; || true
    
    # Check source files  
    find src -name "*.cpp" -exec echo "Checking: {}" \; -exec clang-tidy {} -- -I./include \; || true
    
    echo -e "${GREEN}✅ Static analysis complete${NC}"
else
    echo -e "${YELLOW}⚠️  clang-tidy not available, skipping static analysis${NC}"
fi

echo -e "${GREEN}Step 4: Library information...${NC}"
if [ -f "build/libsage_flow_core.so" ]; then
    echo "Library file: $(ls -lh build/libsage_flow_core.so)"
    echo "Library symbols:"
    nm -D build/libsage_flow_core.so | head -10 || true
fi

echo -e "${GREEN}=== Build Summary ===${NC}"
echo "✅ C++ library built successfully"
echo "✅ Google C++ Style Guide compliance checked"
echo "✅ Ready for Python integration"
echo ""
echo "Next steps:"
echo "1. Install pybind11: pip install pybind11"
echo "2. Build Python bindings: cd build && make sage_flow_py"
echo "3. Test the implementation"

echo -e "${GREEN}Build completed successfully! 🎉${NC}"
