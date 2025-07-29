#!/bin/bash
set -e

echo "Building SAGE mmap_queue..."

# 检查是否需要调试版本
if [[ "$1" == "debug" ]]; then
    echo "Building with debug symbols and AddressSanitizer..."
    g++ -std=c++11 -fPIC -shared -g -O0 \
        -fsanitize=address \
        -fno-omit-frame-pointer \
        -I. \
        -o libring_buffer.so \
        ring_buffer.cpp
    echo "✓ Debug build completed with AddressSanitizer"
else
    echo "Building optimized release version..."
    g++ -std=c++11 -fPIC -shared -O2 \
        -I. \
        -o libring_buffer.so \
        ring_buffer.cpp
    echo "✓ Release build completed"
fi

# 创建兼容链接
ln -sf libring_buffer.so ring_buffer.so

echo "✓ Library ready: ring_buffer.so -> libring_buffer.so"
