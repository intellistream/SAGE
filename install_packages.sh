#!/bin/bash
# SAGE Framework Monorepo 安装脚本
# 用于安装工作空间中的所有子包

echo "=== SAGE Framework Monorepo 安装 ==="

# 获取脚本所在目录（项目根目录）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 安装计数器
SUCCESS_COUNT=0
FAILED_COUNT=0

# 安装单个包的函数
install_package() {
    local package_path="$1"
    local package_name=$(basename "$package_path")
    
    if [ ! -d "$package_path" ]; then
        echo "跳过 $package_name: 目录不存在"
        return 0
    fi
    
    if [ ! -f "$package_path/pyproject.toml" ]; then
        echo "跳过 $package_name: 没有 pyproject.toml"
        return 0
    fi
    
    echo "安装包: $package_name"
    if pip install -e "$package_path"; then
        echo "✓ 成功安装: $package_name"
        ((SUCCESS_COUNT++))
        return 0
    else
        echo "✗ 安装失败: $package_name"
        ((FAILED_COUNT++))
        return 1
    fi
}

echo ""
echo "开始安装 SAGE 子包..."

# 1. 安装内核
echo ""
echo "1. 安装内核层..."
install_package "packages/sage-kernel"

# 2. 安装中间件
echo ""
echo "2. 安装中间件层..."
install_package "packages/sage-middleware"

# 3. 安装用户空间
echo ""
echo "3. 安装用户空间层..."
install_package "packages/sage-userspace"

# 4. 安装工具包
echo ""
echo "4. 安装工具包..."
install_package "packages/tools/sage-cli"
install_package "packages/tools/sage-frontend"

# 5. 安装开发工具包
echo ""
echo "5. 安装开发工具包..."
install_package "dev-toolkit"

# 6. 安装商业包（如果存在）
echo ""
echo "6. 安装商业包（如果存在）..."
if [ -d "packages/commercial" ]; then
    install_package "packages/commercial/sage-kernel"
    install_package "packages/commercial/sage-middleware"
    install_package "packages/commercial/sage-userspace"
else
    echo "跳过商业包: 目录不存在"
fi

# 显示安装结果
echo ""
echo "=== 安装完成 ==="
echo "成功安装: $SUCCESS_COUNT 个包"
echo "安装失败: $FAILED_COUNT 个包"

if [ $FAILED_COUNT -gt 0 ]; then
    echo ""
    echo "警告: 部分包安装失败，请检查上面的错误信息"
    exit 1
else
    echo ""
    echo "🎉 所有包安装成功！"
    echo ""
    echo "现在您可以使用以下命令验证安装："
    echo "  python -c \"import sage; print('SAGE 安装成功!')\"" 
    echo "  sage --version"
fi
