#!/bin/bash
# SAGE CodeServer 快速启动脚本

set -e

echo "🚀 SAGE CodeServer 启动脚本"
echo "=============================="

# 检查Python版本
python_version=$(python3 --version 2>&1 | cut -d' ' -f2)
echo "📍 Python版本: $python_version"

# 检查是否在SAGE根目录
if [ ! -d "packages" ] || [ ! -f "README.md" ]; then
    echo "❌ 错误: 请在SAGE项目根目录中运行此脚本"
    exit 1
fi

echo "📁 当前目录: $(pwd)"

# 安装依赖（如果需要）
if [ "$1" == "--install-deps" ]; then
    echo "📦 安装CodeServer依赖..."
    pip install -r scripts/codeserver_requirements.txt
    echo "✅ 依赖安装完成"
fi

# 检查必需的脚本是否存在
required_scripts=(
    "scripts/test_runner.py"
    "scripts/advanced_dependency_analyzer_with_sage_mapping.py"
    "scripts/sage-package-manager.py"
    "scripts/check_package_dependencies.py"
)

for script in "${required_scripts[@]}"; do
    if [ ! -f "$script" ]; then
        echo "⚠️  警告: 缺少脚本 $script"
    else
        echo "✅ 找到脚本: $script"
    fi
done

# 检查端口是否被占用
if lsof -Pi :8888 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "⚠️  警告: 端口8888已被占用"
    echo "   如需强制启动，请先结束占用进程："
    echo "   lsof -ti:8888 | xargs kill -9"
    read -p "   是否继续启动? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo ""
echo "🌟 启动信息:"
echo "   - Web界面: http://localhost:8888"
echo "   - API文档: http://localhost:8888/docs"
echo "   - ReDoc文档: http://localhost:8888/redoc"
echo ""
echo "🔄 启动服务器..."
echo ""

# 启动CodeServer
python3 scripts/sage_codeserver.py
