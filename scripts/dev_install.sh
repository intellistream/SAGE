#!/usr/bin/env bash

# SAGE 开发环境快速安装脚本
# 使用 editable 模式进行开发安装

set -e

echo "🛠️  SAGE 开发环境安装 (Editable Mode)"
echo "============================================"

# 安装顺序：按依赖关系从底层到上层
packages=(
    "packages/sage-kernel"
    "packages/sage-middleware" 
    "packages/sage-userspace"
    "packages/sage-tools/sage-dev-toolkit"
    "packages/sage-tools/sage-cli"
    "packages/sage"  # meta package最后安装
)

echo "📦 开始editable安装..."

for package in "${packages[@]}"; do
    if [ -d "$package" ]; then
        echo "📍 安装 $package (editable模式)..."
        pip install -e "$package"
    else
        echo "⚠️  警告: $package 目录不存在，跳过"
    fi
done

echo ""
echo "✅ 开发环境安装完成！"
echo ""
echo "💡 开发提示:"
echo "   - 代码修改会立即生效，无需重新安装"
echo "   - Python文件修改后直接import即可看到变化"
echo "   - C++扩展修改后仍需重新编译"
echo ""
echo "🔍 验证安装:"
echo "   python -c 'import sage; print(sage.__file__)'"
