#!/bin/bash

# SAGE高性能环形队列编译脚本
# Compile script for SAGE high-performance ring buffer

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== SAGE Ring Buffer 编译脚本 ==="
echo "编译目录: $SCRIPT_DIR"

# 检查依赖
echo "检查编译依赖..."

if ! command -v gcc &> /dev/null; then
    echo "错误: 找不到gcc编译器"
    echo "Ubuntu/Debian: sudo apt-get install build-essential"
    echo "CentOS/RHEL: sudo yum install gcc"
    exit 1
fi

if ! command -v pkg-config &> /dev/null; then
    echo "警告: 找不到pkg-config，但可以继续编译"
fi

# 编译参数
CC=gcc
CFLAGS="-std=c11 -Wall -Wextra -O3 -fPIC -g"
LDFLAGS="-shared -lrt -lpthread"
SRC_FILE="ring_buffer.c"
HEADER_FILE="ring_buffer.h"
OUTPUT_LIB="ring_buffer.so"

echo "编译器: $CC"
echo "编译选项: $CFLAGS"
echo "链接选项: $LDFLAGS"
echo "源文件: $SRC_FILE"
echo "输出库: $OUTPUT_LIB"

# 检查源文件
if [[ ! -f "$SRC_FILE" ]]; then
    echo "错误: 找不到源文件 $SRC_FILE"
    exit 1
fi

if [[ ! -f "$HEADER_FILE" ]]; then
    echo "错误: 找不到头文件 $HEADER_FILE"
    exit 1
fi

# 清理旧文件
echo "清理旧的编译产物..."
rm -f "$OUTPUT_LIB"
rm -f *.o

# 编译
echo "开始编译..."
$CC $CFLAGS $LDFLAGS -o "$OUTPUT_LIB" "$SRC_FILE"

# 检查编译结果
if [[ -f "$OUTPUT_LIB" ]]; then
    echo "✓ 编译成功!"
    echo "生成的库文件: $OUTPUT_LIB"
    
    # 显示库信息
    echo "库文件信息:"
    ls -lh "$OUTPUT_LIB"
    
    # 检查符号
    if command -v nm &> /dev/null; then
        echo "导出的符号:"
        nm -D "$OUTPUT_LIB" 2>/dev/null | grep -E "ring_buffer_" | head -10
    fi
    
    # 设置权限
    chmod 755 "$OUTPUT_LIB"
    
    echo "编译完成! 现在可以使用Python接口了。"
    echo "测试命令: python3 -c \"from sage.queue import SageQueue; print('导入成功!')\""
else
    echo "✗ 编译失败!"
    exit 1
fi

# 可选: 创建软链接
if [[ ! -f "libring_buffer.so" ]]; then
    ln -s "$OUTPUT_LIB" "libring_buffer.so"
    echo "创建软链接: libring_buffer.so -> $OUTPUT_LIB"
fi

echo "=== 编译完成 ==="
