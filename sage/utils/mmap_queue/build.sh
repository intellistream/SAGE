#!/bin/bash
set -e

echo "Building SAGE mmap_queue with moodycamel/concurrentqueue..."

# 编译为共享库，注意改为 C++
g++ -std=c++11 -fPIC -shared -O3 \
    -I. \
    -o libring_buffer.so \
    ring_buffer.cpp

# 创建兼容链接
ln -sf libring_buffer.so ring_buffer.so

echo "✓ Build completed successfully"
echo "✓ Using moodycamel/concurrentqueue for high-performance MCMQ"