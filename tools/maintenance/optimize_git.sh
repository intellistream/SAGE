#!/bin/bash
# Git 克隆优化配置脚本
# 为 SAGE 项目优化 Git submodule 克隆速度

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SAGE_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "🚀 优化 Git 配置以提升 submodule 克隆速度"
echo ""

# 1. 配置并行克隆数量
echo "📦 配置并行克隆..."
git config --local submodule.fetchJobs 4
echo "   ✅ 设置并行克隆数: 4"

# 2. 配置 HTTP 缓冲区（解决大文件克隆问题）
echo "📦 配置 HTTP 缓冲区..."
git config --local http.postBuffer 524288000  # 500MB
echo "   ✅ HTTP 缓冲区: 500MB"

# 3. 配置克隆深度（默认浅克隆）
echo "📦 配置默认克隆深度..."
git config --local submodule.recurse true
echo "   ✅ 启用递归 submodule"

# 4. 显示当前配置
echo ""
echo "📋 当前 Git 配置："
echo "   并行克隆数: $(git config --local submodule.fetchJobs)"
echo "   HTTP 缓冲区: $(git config --local http.postBuffer) bytes"
echo "   递归 submodule: $(git config --local submodule.recurse)"

echo ""
echo "✅ Git 优化配置完成！"
echo ""
echo "提示："
echo "  - 使用 './manage.sh' 克隆 submodules 将自动使用并行模式"
echo "  - 首次克隆 8 个仓库预计需要 2-5 分钟"
echo "  - 如需更快速度，可考虑使用 Git 镜像或代理"
