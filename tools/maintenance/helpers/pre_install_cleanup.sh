#!/bin/bash
# 🧹 SAGE 安装前清理脚本
# 在运行 quickstart.sh 前清理缓存和临时文件

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
DIM='\033[0;2m'
NC='\033[0m'

echo -e "${BLUE}🧹 安装前清理...${NC}"

# 统一 pip 命令（优先使用 quickstart 注入的 PIP_CMD）
PYTHON_CMD="${PYTHON_CMD:-python3}"
PIP_CMD="${PIP_CMD:-$PYTHON_CMD -m pip}"

# 计数器
removed_count=0

# 清理当前主仓直接产出的历史安装（避免误删 benchmark/docs/isagellm/zoo 等独立包）
echo -e "${DIM}清理当前 SAGE 主仓的直接安装包...${NC}"

collect_direct_sage_packages_to_remove() {
    local installed_lines="$1"
    local removable_packages=(
        "isage"
        "sage"
        "intsage"
    )

    local package_name
    for package_name in "${removable_packages[@]}"; do
        echo "$installed_lines" | awk -F'==' -v pkg="$package_name" '$1==pkg {print $1}'
    done | awk '!seen[$0]++'
}

installed_packages=$(eval "$PIP_CMD list --format=freeze" 2>/dev/null || true)
package_names=$(collect_direct_sage_packages_to_remove "$installed_packages" | tr '\n' ' ')

if [ -n "$package_names" ]; then
    echo -e "${DIM}将卸载: $package_names${NC}"
    eval "$PIP_CMD uninstall -y $package_names" >/dev/null 2>&1 || true
    pkg_count=$(echo "$package_names" | wc -w)
    echo -e "${GREEN}✅ 清理了 $pkg_count 个主仓历史安装包${NC}"
    removed_count=$((removed_count + pkg_count))
else
    echo -e "${DIM}未检测到需要清理的主仓安装包${NC}"
fi
echo -e "${DIM}保留独立包: isagellm / isage-benchmark / sage-docs / zoo packages${NC}"

# 清理 Python 缓存文件
echo -e "${DIM}清理 __pycache__ 目录...${NC}"
pycache_count=$(find . -name "__pycache__" -type d 2>/dev/null | wc -l)
if [ "$pycache_count" -gt 0 ]; then
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    echo -e "${GREEN}✅ 删除了 $pycache_count 个 __pycache__ 目录${NC}"
    removed_count=$((removed_count + pycache_count))
fi

# 清理 .pyc 和 .pyo 文件
echo -e "${DIM}清理 .pyc/.pyo 文件...${NC}"
pyc_count=$(find . -name "*.pyc" -o -name "*.pyo" 2>/dev/null | wc -l)
if [ "$pyc_count" -gt 0 ]; then
    find . -name "*.pyc" -o -name "*.pyo" -delete 2>/dev/null || true
    echo -e "${GREEN}✅ 删除了 $pyc_count 个 .pyc/.pyo 文件${NC}"
    removed_count=$((removed_count + pyc_count))
fi

# 清理 .egg-info 目录
echo -e "${DIM}清理 .egg-info 目录...${NC}"
egg_info_count=$(find . -name "*.egg-info" -type d 2>/dev/null | wc -l)
if [ "$egg_info_count" -gt 0 ]; then
    find . -name "*.egg-info" -type d -exec rm -rf {} + 2>/dev/null || true
    echo -e "${GREEN}✅ 删除了 $egg_info_count 个 .egg-info 目录${NC}"
    removed_count=$((removed_count + egg_info_count))
fi

# 清理旧的构建产物
echo -e "${DIM}清理旧的构建产物...${NC}"
if [ -d "build" ]; then
    rm -rf build/
    echo -e "${GREEN}✅ 删除了 build/ 目录${NC}"
    removed_count=$((removed_count + 1))
fi

if [ -d "dist" ]; then
    rm -rf dist/
    echo -e "${GREEN}✅ 删除了 dist/ 目录${NC}"
    removed_count=$((removed_count + 1))
fi

# 清理空目录 (排除.git目录)
echo -e "${DIM}清理空目录...${NC}"
empty_dirs=$(find . -type d -empty -not -path "./.git/*" -not -path "./.sage/*" 2>/dev/null | wc -l)
if [ "$empty_dirs" -gt 0 ]; then
    # 多次运行以处理嵌套的空目录
    for i in {1..5}; do
        find . -type d -empty -not -path "./.git/*" -not -path "./.sage/*" -delete 2>/dev/null || true
    done
    echo -e "${GREEN}✅ 删除了 $empty_dirs 个空目录${NC}"
    removed_count=$((removed_count + empty_dirs))
fi

# 清理 pip 缓存 (可选，占用较大空间)
if [ "${CLEAN_PIP_CACHE:-false}" = "true" ]; then
    echo -e "${DIM}清理 pip 缓存...${NC}"
    if eval "$PIP_CMD cache --help" >/dev/null 2>&1; then
        eval "$PIP_CMD cache purge" 2>/dev/null || true
        echo -e "${GREEN}✅ pip 缓存已清理${NC}"
    fi
fi

echo ""
if [ "$removed_count" -gt 0 ]; then
    echo -e "${GREEN}✅ 安装前清理完成！共清理 $removed_count 个文件/目录${NC}"
else
    echo -e "${DIM}ℹ️  没有需要清理的内容${NC}"
fi
echo ""
