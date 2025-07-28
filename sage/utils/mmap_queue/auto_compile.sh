#!/bin/bash
# Auto-compile script for SAGE mmap_queue library
# This script ensures the C++ library is compiled in CI environments

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "Compiling SAGE mmap_queue library in: $SCRIPT_DIR"

# Check if we have the necessary files
if [[ ! -f "ring_buffer.cpp" || ! -f "ring_buffer.h" ]]; then
    echo "ERROR: Required source files not found"
    echo "Looking for: ring_buffer.cpp, ring_buffer.h"
    echo "Available files:"
    ls -la
    exit 1
fi

# Install build dependencies if needed
if ! command -v g++ &> /dev/null; then
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
