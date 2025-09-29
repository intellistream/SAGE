#!/bin/bash
# 多模态融合演示运行脚本
# Multimodal Fusion Demo Runner

set -e  # 遇到错误立即退出

echo "🎯 SAGE 多模态数据融合演示"
echo "=================================================="

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误：未找到python3，请确保Python 3.8+已安装"
    exit 1
fi

# 检查SAGE路径
SAGE_ROOT="/home/shuhao/SAGE"
if [ ! -d "$SAGE_ROOT" ]; then
    echo "❌ 错误：未找到SAGE根目录: $SAGE_ROOT"
    exit 1
fi

cd "$SAGE_ROOT"

# 设置Python路径
export PYTHONPATH="$SAGE_ROOT:$PYTHONPATH"

echo "📍 当前工作目录: $(pwd)"
echo "🐍 Python版本: $(python3 --version)"
echo "📚 PYTHONPATH: $PYTHONPATH"
echo ""

# 检查演示文件是否存在
DEMO_FILE="examples/rag/qa_multimodal_fusion.py"
if [ ! -f "$DEMO_FILE" ]; then
    echo "❌ 错误：未找到演示文件: $DEMO_FILE"
    exit 1
fi

echo "🚀 启动多模态融合QA演示..."
echo "=================================================="

# 运行演示
if [ "$1" = "test" ] || [ "$SAGE_EXAMPLES_MODE" = "test" ]; then
    echo "🧪 运行测试模式..."
    SAGE_EXAMPLES_MODE=test python3 "$DEMO_FILE"
else
    echo "🎯 运行完整演示..."
    python3 "$DEMO_FILE"
fi

echo ""
echo "✅ 演示完成！"
echo "📖 更多信息请查看: examples/rag/README_multimodal_fusion.md"