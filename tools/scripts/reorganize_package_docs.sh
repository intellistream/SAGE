#!/bin/bash
# ============================================================================
# Reorganize Package Documentation (All Packages)
# ============================================================================
# Purpose: Move misplaced markdown files to proper locations
# Author: SAGE Team
# Date: 2026-01-02
#
# Violations found:
#   - packages/sage-libs/ (3 files)
#   - packages/sage-middleware/ (1 file)
# ============================================================================

set -e

SAGE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$SAGE_ROOT"

echo "🔄 开始整理所有包的文档..."
echo ""
echo "发现的违规文件："
echo "  ❌ packages/sage-libs/AMMS_PYPI_PUBLISH_GUIDE.md"
echo "  ❌ packages/sage-libs/LIBAMM_INSTALLATION.md"
echo "  ❌ packages/sage-libs/README_LIBAMM.md"
echo "  ❌ packages/sage-middleware/MIGRATION_SCIKIT_BUILD.md"
echo ""

# ============================================================================
# 1. sage-libs 文档整理
# ============================================================================
echo "📦 处理 sage-libs..."

# 包级文档 → packages/sage-libs/docs/
if [ -f "packages/sage-libs/LIBAMM_INSTALLATION.md" ]; then
    echo "  📝 移动 LIBAMM_INSTALLATION.md → packages/sage-libs/docs/"
    git mv packages/sage-libs/LIBAMM_INSTALLATION.md \
           packages/sage-libs/docs/
    echo "     ✓ 已移动"
fi

if [ -f "packages/sage-libs/README_LIBAMM.md" ]; then
    echo "  📝 移动 README_LIBAMM.md → packages/sage-libs/docs/LIBAMM.md"
    git mv packages/sage-libs/README_LIBAMM.md \
           packages/sage-libs/docs/LIBAMM.md
    echo "     ✓ 已重命名并移动"
fi

# 项目级开发者文档 → docs-public/
if [ -f "packages/sage-libs/AMMS_PYPI_PUBLISH_GUIDE.md" ]; then
    echo "  📝 移动 AMMS_PYPI_PUBLISH_GUIDE.md → docs-public/docs_src/dev-notes/l3-libs/"
    mkdir -p docs-public/docs_src/dev-notes/l3-libs
    git mv packages/sage-libs/AMMS_PYPI_PUBLISH_GUIDE.md \
           docs-public/docs_src/dev-notes/l3-libs/pypi-publish-guide.md
    echo "     ✓ 已移动到项目级开发者文档"
fi

echo ""

# ============================================================================
# 2. sage-middleware 文档整理
# ============================================================================
echo "📦 处理 sage-middleware..."

if [ -f "packages/sage-middleware/MIGRATION_SCIKIT_BUILD.md" ]; then
    echo "  📝 移动 MIGRATION_SCIKIT_BUILD.md → packages/sage-middleware/docs/"
    mkdir -p packages/sage-middleware/docs
    git mv packages/sage-middleware/MIGRATION_SCIKIT_BUILD.md \
           packages/sage-middleware/docs/
    echo "     ✓ 已移动到包级文档目录"
fi

echo ""
echo "✅ 所有文档整理完成！"
echo ""
echo "� 整理统计："
echo "  • 处理的包: 2 (sage-libs, sage-middleware)"
echo "  • 移动的文件: 4"
echo "  • 包级文档: 3"
echo "  • 项目级文档: 1"
echo ""
echo "📋 下一步操作："
echo ""
echo "  1️⃣  检查并更新文档链接："
echo "     grep -r 'AMMS_PYPI_PUBLISH_GUIDE' --include='*.md' --include='*.py' ."
echo "     grep -r 'LIBAMM_INSTALLATION' --include='*.md' --include='*.py' ."
echo "     grep -r 'README_LIBAMM' --include='*.md' --include='*.py' ."
echo "     grep -r 'MIGRATION_SCIKIT_BUILD' --include='*.md' --include='*.py' ."
echo ""
echo "  2️⃣  更新 packages/sage-libs/README.md 中的链接"
echo ""
echo "  3️⃣  验证 pre-commit hook："
echo "     pre-commit run markdown-files-location-check --all-files"
echo ""
echo "  4️⃣  提交变更："
echo "     git status"
echo "     git add -A"
echo "     git commit -m 'docs: reorganize package documentation to follow location policy"
echo ""
echo "     - Move sage-libs docs to proper locations"
echo "     - Move sage-middleware migration doc to docs/"
echo "     - Fix pre-commit hook to enforce stricter patterns"
echo "     - Ref: Documentation Location Policy (.github/copilot-instructions.md)'"
echo ""
