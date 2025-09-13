#!/bin/bash
#
# SAGE Studio 快速启动演示脚本
# 展示如何使用新的 SAGE CLI 命令启动和管理 Studio
#

echo "🎨 SAGE Studio 快速启动演示"
echo "================================"

echo ""
echo "📋 1. 显示 Studio 信息"
python -m sage.tools.cli.main studio info

echo ""
echo "📋 2. 检查当前状态"
python -m sage.tools.cli.main studio status

echo ""
echo "📋 3. 安装依赖 (如果需要)"
echo "如需安装依赖，运行: sage studio install"

echo ""
echo "📋 4. 启动服务"
echo "运行以下命令启动 Studio："
echo "  sage studio start"

echo ""
echo "📋 5. 访问 Studio"
echo "服务启动后，访问: http://localhost:4200"

echo ""
echo "📋 6. 管理命令"
echo "可用的管理命令："
echo "  sage studio status    # 检查状态"
echo "  sage studio logs      # 查看日志"
echo "  sage studio restart   # 重启服务"
echo "  sage studio stop      # 停止服务"
echo "  sage studio open      # 在浏览器中打开"

echo ""
echo "🎯 完成! 现在你可以使用 'sage studio start' 启动 Studio 了！"
