#!/bin/bash

# SAGE Frontend 构建和安装脚本

set -e

echo "🚀 开始构建 SAGE Frontend 包..."

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "📁 当前目录: $(pwd)"

# 检查必要文件
echo "🔍 检查项目文件..."
if [[ ! -f "pyproject.toml" ]]; then
    echo "❌ 错误: 未找到 pyproject.toml 文件"
    exit 1
fi

if [[ ! -f "README.md" ]]; then
    echo "❌ 错误: 未找到 README.md 文件"
    exit 1
fi

if [[ ! -d "src/sage_frontend" ]]; then
    echo "❌ 错误: 未找到源代码目录 src/sage_frontend"
    exit 1
fi

echo "✅ 项目文件检查完成"

# 清理旧的构建文件
echo "🧹 清理旧的构建文件..."
rm -rf build/
rm -rf dist/
rm -rf *.egg-info/
rm -rf src/*.egg-info/

echo "✅ 清理完成"

# 检查是否需要构建前端
if [[ -d "dashboard" && -f "dashboard/package.json" ]]; then
    echo "🔨 检查前端构建..."
    
    if [[ ! -d "dashboard/dist" ]]; then
        echo "📦 构建 Angular 前端..."
        
        # 检查 Node.js 和 npm
        if ! command -v node &> /dev/null; then
            echo "⚠️  警告: 未找到 Node.js，跳过前端构建"
        elif ! command -v npm &> /dev/null; then
            echo "⚠️  警告: 未找到 npm，跳过前端构建"
        else
            cd dashboard
            
            # 安装依赖
            if [[ ! -d "node_modules" ]]; then
                echo "📦 安装前端依赖..."
                npm install
            fi
            
            # 构建
            echo "🔨 构建前端..."
            npm run build
            
            cd ..
            echo "✅ 前端构建完成"
        fi
    else
        echo "✅ 前端已构建"
    fi
fi

# 构建 Python 包
echo "🔨 构建 Python 包..."

# 确保有构建工具
python -m pip install --upgrade pip setuptools wheel build

# 构建包
python -m build

echo "✅ Python 包构建完成"

# 检查构建结果
echo "📋 构建结果:"
if [[ -d "dist" ]]; then
    ls -la dist/
    
    # 验证包内容
    echo "🔍 验证包内容..."
    WHEEL_FILE=$(ls dist/*.whl | head -n 1)
    if [[ -n "$WHEEL_FILE" ]]; then
        echo "📦 轮子文件: $WHEEL_FILE"
        python -m zipfile -l "$WHEEL_FILE" | head -n 20
    fi
else
    echo "❌ 错误: 构建失败，未找到 dist 目录"
    exit 1
fi

echo ""
echo "🎉 SAGE Frontend 包构建完成!"
echo ""
echo "📦 安装命令:"
echo "   pip install dist/sage_frontend-1.0.0-py3-none-any.whl"
echo ""
echo "🚀 运行命令:"
echo "   sage-frontend --help"
echo "   sage-server --help"
echo ""
echo "📚 更多信息请查看 README.md"
