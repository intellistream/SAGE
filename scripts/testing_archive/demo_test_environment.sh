#!/bin/bash
# SAGE 本地测试环境演示脚本
# 展示各种测试功能和GitHub Actions模拟

echo "🎯 SAGE 本地测试环境演示"
echo "=========================="

echo ""
echo "📦 当前Python环境信息："
echo "🐍 Python版本: $(python --version)"
echo "📍 虚拟环境: $VIRTUAL_ENV"
echo "📚 已安装包数量: $(pip list | wc -l)"

echo ""
echo "🏗️ 项目结构分析："
echo "📁 SAGE目录: $(find sage -type d -name 'test*' | wc -l) 个测试目录"
echo "📄 总测试文件: $(find . -name 'test_*.py' -o -name '*_test.py' | wc -l) 个"

echo ""
echo "🚀 测试运行器功能演示："
echo "1. 列出所有测试文件"
python scripts/test_runner.py --list

echo ""
echo "2. 智能差异测试（基于git diff）"
python scripts/test_runner.py --diff

echo ""
echo "3. 检查生成的测试日志"
if [ -d "test_logs" ]; then
    echo "📊 生成的日志文件数量: $(find test_logs -name '*.log' | wc -l)"
    echo "📝 最新的几个日志文件:"
    ls -lt test_logs/*.log | head -5
else
    echo "⏳ 测试日志目录还未创建（测试可能仍在运行）"
fi

echo ""
echo "🎭 GitHub Actions本地模拟 (使用act工具)："
echo "🐳 Docker状态:"
if command -v docker &> /dev/null; then
    if docker info &> /dev/null; then
        echo "✅ Docker 可用"
        docker --version
    else
        echo "⚠️  Docker已安装但无法连接到daemon"
    fi
else
    echo "❌ Docker 未安装"
fi

echo ""
echo "🔧 Act工具状态:"
if command -v act &> /dev/null; then
    echo "✅ Act工具已安装"
    act --version
    echo "📋 可用的工作流:"
    act --list 2>/dev/null || echo "⚠️  无法列出工作流（可能是Docker连接问题）"
else
    echo "❌ Act工具未安装"
fi

echo ""
echo "🧪 本地测试脚本演示:"
if [ -f "test_github_actions.sh" ]; then
    echo "✅ GitHub Actions本地测试脚本可用"
    echo "运行命令: ./test_github_actions.sh"
fi

if [ -f "test_act_local.sh" ]; then
    echo "✅ Act本地模拟脚本可用"  
    echo "运行命令: ./test_act_local.sh"
fi

if [ -f "test_menu.sh" ]; then
    echo "✅ 交互式测试菜单可用"
    echo "运行命令: ./test_menu.sh"
fi

echo ""
echo "📈 性能和环境信息："
echo "💾 内存使用: $(free -h | grep '^Mem:' | awk '{print $3 "/" $2}')"
echo "🖥️  CPU核心数: $(nproc)"
echo "💽 磁盘空间: $(df -h . | tail -1 | awk '{print $4}') 可用"

echo ""
echo "🎉 环境设置完成！可以开始运行各种测试了。"
echo ""
echo "💡 推荐的下一步操作："
echo "   • 运行小规模测试: python scripts/test_runner.py --all --workers 2"
echo "   • 查看测试日志: ls -la test_logs/"
echo "   • 运行特定模块测试: python scripts/test_runner.py --diff"
echo "   • GitHub Actions模拟: ./test_github_actions.sh"
