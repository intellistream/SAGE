#!/bin/bash
# MemoryService 示例运行脚本
# 运行这个脚本来演示MemoryService的使用

echo "🚀 运行 MemoryService 使用示例"
echo "=================================="

# 检查Python是否可用
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未找到，请确保Python3已安装"
    exit 1
fi

# 检查是否在正确的目录
if [ ! -f "memory_service_demo.py" ]; then
    echo "❌ memory_service_demo.py 文件未找到"
    echo "请确保在 examples/memory 目录下运行此脚本"
    exit 1
fi

# 运行示例
echo "📋 正在运行示例..."
python3 memory_service_demo.py

echo ""
echo "✅ 示例运行完成"
echo "📖 查看 README_memory_service_demo.md 了解更多详情"