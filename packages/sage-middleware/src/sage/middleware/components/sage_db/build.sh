#!/bin/bash
# SAGE DB 构建包装脚本
# 此脚本调用子模块中的实际构建脚本

set -e

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SUBMODULE_DIR="$SCRIPT_DIR/sageDB"

# 检查子模块是否已初始化
if [ ! -d "$SUBMODULE_DIR" ] || [ ! -f "$SUBMODULE_DIR/build.sh" ]; then
    echo "错误: sageDB 子模块未初始化"
    echo "请运行: git submodule update --init --recursive"
    exit 1
fi

# 切换到子模块目录并执行构建
cd "$SUBMODULE_DIR"

echo "🔨 构建 SAGE DB (在 sageDB 子模块中)..."
bash build.sh "$@"

BUILD_STATUS=$?

if [ $BUILD_STATUS -eq 0 ]; then
    echo "✅ SAGE DB 构建成功"
    
    # 将构建产物复制到父目录的python目录
    if [ -d "build" ]; then
        PARENT_PYTHON_DIR="$SCRIPT_DIR/python"
        mkdir -p "$PARENT_PYTHON_DIR"
        
        # 查找并复制.so文件
        find build -name "_sage_db*.so" -type f -exec cp {} "$PARENT_PYTHON_DIR/" \;
        
        if [ -f "$PARENT_PYTHON_DIR/_sage_db"*.so ]; then
            echo "✅ 已复制扩展模块到 $PARENT_PYTHON_DIR"
        fi
    fi
else
    echo "❌ SAGE DB 构建失败"
    exit $BUILD_STATUS
fi

exit 0
