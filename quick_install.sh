#!/bin/bash
# SAGE Framework 一键安装脚本
# 适用于已经克隆了 SAGE 仓库的用户

set -e

echo "🚀 SAGE Framework 一键安装脚本"
echo "=================================="

# 检查是否在 SAGE 目录中
if [ ! -f "pyproject.toml" ] || [ ! -d "packages" ]; then
    echo "❌ 错误: 当前目录不是 SAGE 项目根目录"
    echo "请先克隆仓库："
    echo "  git clone https://github.com/intellistream/SAGE.git"
    echo "  cd SAGE"
    echo "  ./quick_install.sh"
    exit 1
fi

# 检查 Python 版本
python_version=$(python3 -c "import sys; print('.'.join(map(str, sys.version_info[:2])))")
required_version="3.10"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ 错误: 需要 Python 3.10+ (当前: $python_version)"
    exit 1
fi

echo "✓ Python 版本检查通过: $python_version"

echo ""
echo "📦 第一步: 安装工作空间根包..."
pip install .

echo ""
echo "🔧 第二步: 安装所有子包..."

# 检查 requirements-subpackages.txt 是否存在
if [ -f "requirements-subpackages.txt" ]; then
    echo "使用 requirements-subpackages.txt 安装子包..."
    pip install -r requirements-subpackages.txt
    INSTALL_SUCCESS=true
else
    echo "⚠️  requirements-subpackages.txt 未找到，使用备用安装方法..."
    if [ -f "install_packages.sh" ]; then
        ./install_packages.sh
        INSTALL_SUCCESS=true
    else
        echo "❌ 未找到安装脚本，使用手动安装方法..."
        INSTALL_SUCCESS=false
    fi
fi

echo ""
echo "✅ 验证安装..."

# 运行验证脚本
if [ -f "verify_installation.py" ]; then
    echo "运行安装验证脚本..."
    python verify_installation.py
else
    # 简单验证
    if command -v sage &> /dev/null; then
        echo "🎉 安装成功! SAGE CLI 已可用"
        sage --version 2>/dev/null || echo "CLI 工具已安装"
    else
        echo "⚠️  CLI 命令未找到，但核心包可能已安装"
        echo "   尝试运行: python -c \"import sage; print('SAGE 核心包已安装')\""
    fi
fi

echo ""
echo "🎯 安装完成!"
echo "现在您可以："
echo "  - 运行 'sage --help' 查看可用命令"
echo "  - 运行 'python verify_installation.py' 验证安装"
echo "  - 查看 'app/' 目录中的示例应用"
echo ""
echo "如果遇到问题，请查看 README.md 中的故障排除部分"
}

echo ""
echo "开始安装 SAGE 子包..."

# 按依赖顺序安装
install_package "packages/sage-middleware" "中间件层"
install_package "packages/sage-kernel" "内核层"
install_package "packages/sage-userspace" "用户空间层"
install_package "packages/tools/sage-cli" "CLI工具"
install_package "packages/tools/sage-frontend" "前端工具"
install_package "dev-toolkit" "开发工具包"

# 商业包（如果存在）
if [ -d "packages/commercial" ]; then
    echo ""
    echo "检测到商业包，正在安装..."
    install_package "packages/commercial/sage-middleware" "商业中间件"
    install_package "packages/commercial/sage-kernel" "商业内核"
    install_package "packages/commercial/sage-userspace" "商业用户空间"
fi

echo ""
echo "==============================================="
echo "安装完成！"
echo "==============================================="
echo "成功安装: $SUCCESS_COUNT/$TOTAL_COUNT 个包"

if [ $SUCCESS_COUNT -eq $TOTAL_COUNT ]; then
    echo ""
    echo "🎉 所有包安装成功！"
    echo ""
    echo "验证安装："
    echo "  python verify_installation.py"
    echo ""
    echo "开始使用："
    echo "  sage --help"
    echo "  python app/qa_dense_retrieval.py"
else
    echo ""
    echo "⚠️ 部分包安装失败，但核心功能应该可用"
    echo "检查详细错误信息并手动安装失败的包"
fi

echo ""
echo "如需帮助，请查看："
echo "  README.md 的故障排除部分"
echo "  https://github.com/intellistream/SAGE/issues"
