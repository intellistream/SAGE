#!/bin/bash
# 测试扩展日志路径

echo "======================================"
echo "测试扩展日志路径设置"
echo "======================================"
echo ""

# 检查.sage目录结构
echo "📁 检查 .sage 目录结构..."
mkdir -p .sage/logs/extensions
ls -la .sage/logs/extensions/ 2>/dev/null || echo "  目录为空"

echo ""
echo "📝 预期日志路径："
echo "  - .sage/logs/extensions/sage_db_build.log"
echo "  - .sage/logs/extensions/sage_flow_build.log"

echo ""
echo "🧪 测试扩展安装命令（dry-run）..."
echo ""

# 显示帮助信息看是否有错误
sage extensions install --help

echo ""
echo "======================================"
echo "✅ 命令检查完成"
echo "======================================"
