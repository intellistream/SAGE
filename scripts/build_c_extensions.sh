#!/bin/bash
set -e

echo "Building SAGE C extensions for CI/CD..."

# 确保在正确的目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
MMAP_QUEUE_DIR="$PROJECT_ROOT/sage/utils/mmap_queue"

echo "Project root: $PROJECT_ROOT"
echo "mmap_queue directory: $MMAP_QUEUE_DIR"

# 检查目录是否存在
if [ ! -d "$MMAP_QUEUE_DIR" ]; then
    echo "Error: mmap_queue directory not found at $MMAP_QUEUE_DIR"
    exit 1
fi

# 进入mmap_queue目录
cd "$MMAP_QUEUE_DIR"

# 检查必要文件
if [ ! -f "ring_buffer.cpp" ]; then
    echo "Error: ring_buffer.cpp not found"
    exit 1
fi

if [ ! -f "ring_buffer.h" ]; then
    echo "Error: ring_buffer.h not found"
    exit 1
fi

# 安装必要的系统依赖
echo "Installing system dependencies..."
if command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update -y
    sudo apt-get install -y build-essential g++ gcc
elif command -v yum >/dev/null 2>&1; then
    sudo yum install -y gcc-c++ gcc make
fi

# 创建简化版本的构建脚本，避免复杂的条件编译
echo "Building ring_buffer C++ library..."

# 直接编译，使用简单的命令
g++ -shared -fPIC -O2 \
    -o ring_buffer.so \
    ring_buffer.cpp \
    -lpthread \
    -std=c++11

# 检查编译结果
if [ -f "ring_buffer.so" ]; then
    echo "✅ Successfully built ring_buffer.so"
    ls -la ring_buffer.so
else
    echo "❌ Failed to build ring_buffer.so"
    exit 1
fi

# 验证库可以加载
echo "Testing library loading..."
python3 -c "
import ctypes
try:
    lib = ctypes.CDLL('./ring_buffer.so')
    print('✅ Library loads successfully')
except Exception as e:
    print(f'❌ Library loading failed: {e}')
    exit(1)
"

echo "🎉 C extension build completed successfully!"
