#!/bin/bash
# 测试日志显示功能

echo "======================================"
echo "测试 SAGE 扩展安装日志显示"
echo "======================================"
echo ""

# 模拟安装过程
echo "🧩 安装C++扩展 (sage_db, sage_flow)..."
echo "📝 安装日志: /home/shuhao/SAGE/install.log"
echo "   可以使用以下命令实时查看日志:"
echo "   tail -f /home/shuhao/SAGE/install.log"
echo ""

# 模拟扩展构建
echo "━━━ 安装 sage_db ━━━"
echo ""
echo "构建 sage_db..."
echo "   构建日志: /home/shuhao/SAGE/packages/sage-middleware/src/sage/middleware/components/sage_db/build/build.log"
echo "   实时查看: tail -f /home/shuhao/SAGE/packages/sage-middleware/src/sage/middleware/components/sage_db/build/build.log"
echo ""
echo "✅ sage_db 构建成功 ✓"
echo ""

echo "━━━ 安装 sage_flow ━━━"
echo ""
echo "构建 sage_flow..."
echo "   构建日志: /home/shuhao/SAGE/packages/sage-middleware/src/sage/middleware/components/sage_flow/build/build.log"
echo "   实时查看: tail -f /home/shuhao/SAGE/packages/sage-middleware/src/sage/middleware/components/sage_flow/build/build.log"
echo ""
echo "✅ sage_flow 构建成功 ✓"
echo ""

echo "======================================"
echo "✅ 安装完成"
echo "======================================"
