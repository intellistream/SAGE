#!/bin/bash

# SAGE 文档同步脚本
# 用于将内部文档同步到公开文档仓库

set -e

# 脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# 路径定义
SAGE_KERNEL_DOCS="$REPO_ROOT/packages/sage-kernel/docs"
SAGE_MIDDLEWARE_DOCS="$REPO_ROOT/packages/sage-middleware/docs"
SAGE_TOOLS_DOCS="$REPO_ROOT/packages/sage-tools/docs"
PUBLIC_DOCS="$REPO_ROOT/docs-public/docs_src"

echo "🔄 开始同步 SAGE 文档..."

# 检查目录是否存在
if [ ! -d "$SAGE_KERNEL_DOCS" ]; then
    echo "❌ 错误: sage-kernel 文档目录不存在: $SAGE_KERNEL_DOCS"
    exit 1
fi

if [ ! -d "$PUBLIC_DOCS" ]; then
    echo "❌ 错误: 公开文档目录不存在: $PUBLIC_DOCS"
    exit 1
fi

# 同步 Kernel 文档
echo "📘 同步 SAGE Kernel 文档..."
rsync -av --delete \
    --exclude=".git*" \
    --exclude="__pycache__" \
    --exclude="*.pyc" \
    "$SAGE_KERNEL_DOCS/" "$PUBLIC_DOCS/kernel/"

# 同步 Middleware 文档 (如果存在)
if [ -d "$SAGE_MIDDLEWARE_DOCS" ]; then
    echo "🔧 同步 SAGE Middleware 文档..."
    rsync -av --delete \
        --exclude=".git*" \
        --exclude="__pycache__" \
        --exclude="*.pyc" \
        "$SAGE_MIDDLEWARE_DOCS/" "$PUBLIC_DOCS/middleware/"
else
    echo "⚠️  Middleware 文档目录不存在，跳过同步"
fi

# 同步 Tools 文档 (如果存在)
if [ -d "$SAGE_TOOLS_DOCS" ]; then
    echo "🛠️  同步 SAGE Tools 文档..."
    rsync -av --delete \
        --exclude=".git*" \
        --exclude="__pycache__" \
        --exclude="*.pyc" \
        "$SAGE_TOOLS_DOCS/" "$PUBLIC_DOCS/tools/"
else
    echo "⚠️  Tools 文档目录不存在，跳过同步"
fi

# 进入公开文档目录
cd "$REPO_ROOT/docs-public"

# 检查是否有更改
if git diff --quiet && git diff --staged --quiet; then
    echo "✅ 没有检测到文档更改"
    exit 0
fi

echo "📝 检测到文档更改，准备提交..."

# 显示更改
git status --short

# 询问是否提交
read -p "🤔 是否要提交这些更改到公开文档仓库? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    # 添加所有更改
    git add -A
    
    # 生成提交信息
    TIMESTAMP=$(date "+%Y-%m-%d %H:%M:%S")
    COMMIT_MSG="docs: 同步内部文档更新 ($TIMESTAMP)

- 自动同步来自主仓库的文档更改
- 更新时间: $TIMESTAMP
- 同步脚本: tools/sync_docs.sh"

    # 提交更改
    git commit -m "$COMMIT_MSG"
    
    echo "✅ 文档更改已提交到本地仓库"
    
    # 询问是否推送
    read -p "🚀 是否要推送到远程仓库? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git push origin main
        echo "🎉 文档已成功推送到远程仓库！"
        echo "📖 查看更新后的文档: https://intellistream.github.io/SAGE-Pub/"
    else
        echo "📋 文档已提交到本地，使用 'git push origin main' 手动推送"
    fi
else
    echo "❌ 取消提交，文档更改保留在工作区"
fi

echo "🏁 文档同步完成！"
