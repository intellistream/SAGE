#!/bin/bash

# SAGE项目快速清理脚本
# 清理Python缓存文件和构建文件

set -e

echo "🧹 清理 SAGE 项目缓存和临时文件..."

# 计数器
removed_count=0

# 清理 Python 缓存文件
echo "清理 __pycache__ 目录..."
pycache_count=$(find . -name "__pycache__" -type d 2>/dev/null | wc -l)
if [ $pycache_count -gt 0 ]; then
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    echo "✅ 删除了 $pycache_count 个 __pycache__ 目录"
    removed_count=$((removed_count + pycache_count))
fi

# 清理 .pyc 和 .pyo 文件
echo "清理 .pyc/.pyo 文件..."
pyc_count=$(find . -name "*.pyc" -o -name "*.pyo" 2>/dev/null | wc -l)
if [ $pyc_count -gt 0 ]; then
    find . -name "*.pyc" -o -name "*.pyo" -delete 2>/dev/null || true
    echo "✅ 删除了 $pyc_count 个 .pyc/.pyo 文件"
    removed_count=$((removed_count + pyc_count))
fi

# 清理构建文件
echo "清理构建文件..."
if [ -d "build" ]; then
    rm -rf build/
    echo "✅ 删除了 build/ 目录"
    removed_count=$((removed_count + 1))
fi

if [ -d "dist" ]; then
    rm -rf dist/
    echo "✅ 删除了 dist/ 目录"
    removed_count=$((removed_count + 1))
fi

# 清理 .egg-info 目录
egg_info_count=$(find . -name "*.egg-info" -type d 2>/dev/null | wc -l)
if [ $egg_info_count -gt 0 ]; then
    find . -name "*.egg-info" -type d -exec rm -rf {} + 2>/dev/null || true
    echo "✅ 删除了 $egg_info_count 个 .egg-info 目录"
    removed_count=$((removed_count + egg_info_count))
fi

# 清理子模块中的构建文件
if [ -d "sage_ext" ]; then
    find sage_ext/ -name "build" -type d -exec rm -rf {} + 2>/dev/null || true
    echo "✅ 清理了 sage_ext 子模块的构建文件"
fi

# 清理空目录 (排除.git目录和docs-public子模块)
echo "清理空目录..."
empty_dirs=$(find . -type d -empty -not -path "./.git/*" -not -path "./docs-public" 2>/dev/null | wc -l)
if [ $empty_dirs -gt 0 ]; then
    # 多次运行以处理嵌套的空目录
    for i in {1..5}; do
        find . -type d -empty -not -path "./.git/*" -not -path "./docs-public" -delete 2>/dev/null || true
    done
    echo "✅ 删除了 $empty_dirs 个空目录"
    removed_count=$((removed_count + empty_dirs))
fi

echo ""
echo "🎉 清理完成！总共清理了 $removed_count 个文件/目录"

# 显示项目大小
echo ""
echo "当前项目大小:"
du -sh . 2>/dev/null | head -1
