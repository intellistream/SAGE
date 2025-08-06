#!/bin/bash

# SAGE 微服务架构演示启动脚本

echo "🚀 SAGE 微服务架构演示"
echo "=" * 50

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未安装"
    exit 1
fi

# 进入项目目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "📁 项目目录: $PROJECT_DIR"
cd "$PROJECT_DIR"

# 设置Python路径
export PYTHONPATH="$PROJECT_DIR/src:$PYTHONPATH"

echo "🔧 检查依赖..."

# 检查核心依赖
python3 -c "import numpy" 2>/dev/null || {
    echo "⚠️  numpy 未安装，尝试安装..."
    pip install numpy
}

# 可选依赖检查
echo "📋 可选依赖状态:"

python3 -c "import redis" 2>/dev/null && echo "✅ redis 可用" || echo "⚠️  redis 不可用 (KV Service将使用内存后端)"

python3 -c "import chromadb" 2>/dev/null && echo "✅ chromadb 可用" || echo "⚠️  chromadb 不可用 (需要安装: pip install chromadb)"

python3 -c "import ray" 2>/dev/null && echo "✅ ray 可用 (支持分布式)" || echo "⚠️  ray 不可用 (仅支持本地模式)"

echo ""
echo "🎬 启动演示..."

# 运行演示
python3 examples/dag_microservices_demo.py

echo ""
echo "✅ 演示完成!"
echo ""
echo "📖 了解更多:"
echo "  - 微服务代码: src/sage/service/"
echo "  - 使用指南: MICROSERVICES_GUIDE.md"
echo "  - SAGE文档: https://github.com/intellistream/SAGE"
