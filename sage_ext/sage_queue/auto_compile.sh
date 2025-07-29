#!/bin/bash
# Auto-compile script for SAGE queue library
# This script ensures the C++ library is compiled in CI environments
# Now uses CMake for consistent build system

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "Compiling SAGE queue library in: $SCRIPT_DIR"

# Check if we have the necessary files
if [[ ! -f "src/ring_buffer.cpp" || ! -f "include/ring_buffer.h" ]]; then
    echo "ERROR: Required source files not found"
    echo "Looking for: src/ring_buffer.cpp, include/ring_buffer.h"
    echo "Available files:"
    ls -la
    exit 1
fi

# Install build dependencies if needed
if ! command -v cmake &> /dev/null; then
    echo "Installing cmake..."
    if command -v apt-get &> /dev/null; then
        sudo apt-get update && sudo apt-get install -y cmake
    elif command -v yum &> /dev/null; then
        sudo yum install -y cmake
    else
        echo "ERROR: Cannot install cmake automatically"
        exit 1
    fi
fi

if ! command -v g++ &> /dev/null; then
    echo "Installing g++..."
    if command -v apt-get &> /dev/null; then
        sudo apt-get update && sudo apt-get install -y g++
    elif command -v yum &> /dev/null; then
        sudo yum install -y gcc-c++
    else
        echo "ERROR: Cannot install g++ automatically"
        exit 1
    fi
fi

# Build using CMake
echo "Building with CMake..."
./build_cmake.sh

echo "✓ Auto-compilation completed successfully"
    echo "Installing build dependencies..."
    if command -v apt-get &> /dev/null; then
        sudo apt-get update -y
        sudo apt-get install -y build-essential g++
    elif command -v yum &> /dev/null; then
        sudo yum install -y gcc-c++
    else
        echo "ERROR: Cannot install build dependencies. Please install g++ manually."
        exit 1
    fi
fi

# Compile the library
echo "Compiling C++ library..."
g++ -std=c++11 -fPIC -shared -O2 -I. -o libring_buffer.so ring_buffer.cpp

# Create compatibility symlink
ln -sf libring_buffer.so ring_buffer.so

echo "✅ Successfully compiled mmap_queue library"
echo "Generated files:"
ls -la *.so
