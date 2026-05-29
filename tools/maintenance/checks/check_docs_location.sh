#!/bin/bash
set -e

# ============================================================================
# Check Docs Location Hook
# ============================================================================
# Purpose: Ensure markdown files are in proper locations.
#          User-facing project docs live in the sibling sage-docs repository.
#
# This hook prevents:
# 1. Any files under legacy docs-public/
# 2. Markdown files in random locations outside allowed patterns
#
# Rationale:
# - User-facing docs are centralized in the sibling 'sage-docs' repository
# - Legacy 'docs-public/' paths must not be reintroduced
# - Root 'docs/' in SAGE is reserved for machine-owned governance artifacts only
# - In-tree module docs live under src/.../docs/ when they are implementation-local
# - Optional adapter / tooling repos may keep their own docs in their owning repositories
# - Tools can have their own docs/ directories (e.g., tools/install/docs/)
# ============================================================================

# Get all markdown files (staged if in commit, or all files if --all-files)
if [ -n "$PRE_COMMIT_FROM_REF" ] && [ -n "$PRE_COMMIT_TO_REF" ]; then
    # Running with --all-files or during push
    all_md_files=$(git ls-files "*.md")
else
    # Running in normal commit mode
    all_md_files=$(git diff --cached --name-only --diff-filter=ACM | grep "\.md$" || true)
fi

if [ -z "$all_md_files" ]; then
    exit 0
fi

# Check for files in legacy docs-public/ - STRICTLY FORBIDDEN
legacy_docs_violations=""
other_violations=""

# Define allowed patterns (whitelist)
allowed_patterns=(
    "^README\.md$"
    "^CHANGELOG\.md$"
    "^CONTRIBUTING\.md$"
    "^LICENSE\.md$"
    "^DEVELOPER\.md$"
    "^docs/dependency-audit-gate\.md$"
    "^docs/layer-manifest\.json$"
    "^docker/.*\.md$"
    "^evaluation/README\.md$"
    "^src/.*/docs/"
    "^src/.*/README\.md$"
    "^src/.*/README_[^/]+\.md$"

    "^config/README\.md$"
    "^tools/.*/README\.md$"
    "^tools/.*/(docs|documentation)/"
    "^tools/docs/.*\.md$"  # Allow tools/docs/ directory
    "^\.sage/.*\.md$"

    # .github: Allow standard GitHub convention files in root + anything in subdirectories
    "^\.github/copilot-instructions\.md$"
    "^\.github/COPILOT_SETUP\.md$"
    "^\.github/[^/]+\.md$"    # Standard GitHub root-level markdown (PULL_REQUEST_TEMPLATE, ISSUE_TEMPLATE, etc.)
    "^\.github/[^/]+/"
)

# Define third-party library exclusions (always allowed)
third_party_patterns=(
    "^src/.*/implementations/SPTAG/"      # Microsoft SPTAG
    "^src/.*/implementations/faiss/"      # Facebook FAISS
    "^src/.*/implementations/diskann-ms/" # Microsoft DiskANN
    "^src/.*/implementations/pybind11/"   # pybind11 library
    "^src/.*/implementations/puck/"       # Puck library
    "^src/.*/implementations/zstd/"       # Zstandard library
    "^src/.*/implementations/candy/"      # Candy library family
    "^src/.*/third[-_]party/"             # Generic third-party directories
    "^src/.*/external/"                   # External dependencies
    "^src/.*/vendor/"                     # Vendored libraries
)

for file in $all_md_files; do
    if [[ "$file" == "docs-public/"* ]]; then
        legacy_docs_violations="$legacy_docs_violations$file\n"
        continue
    fi

    # Check if file is in third-party library (always allowed)
    is_third_party=false
    for pattern in "${third_party_patterns[@]}"; do
        if echo "$file" | grep -qE "$pattern"; then
            is_third_party=true
            break
        fi
    done

    if [ "$is_third_party" = true ]; then
        continue  # Skip third-party library documentation
    fi

    # Check against allowed patterns
    allowed=false
    for pattern in "${allowed_patterns[@]}"; do
        if echo "$file" | grep -qE "$pattern"; then
            allowed=true
            break
        fi
    done

    if [ "$allowed" = false ]; then
        other_violations="$other_violations$file\n"
    fi
done

failed=false

# Priority 1: Legacy docs-public violations (most critical)
if [ -n "$legacy_docs_violations" ]; then
    echo "================================================================================================"
    echo "❌ CRITICAL ERROR: Files detected in forbidden legacy 'docs-public/' directory"
    echo "================================================================================================"
    echo ""
    echo "The legacy 'docs-public/' path has been removed from the SAGE meta repository."
    echo "User-facing project documentation must be managed in the sibling 'sage-docs' repository."
    echo ""
    echo "⚠️  Note: package/tool docs and machine-owned governance docs ARE ALLOWED:"
    echo "   ✅ ../sage-docs/                    - Centralized project documentation"
    echo "   ✅ docs/dependency-audit-gate.md    - Meta governance audit evidence"
    echo "   ✅ src/.../docs/                    - In-tree implementation-local documentation"
    echo "   ✅ tools/<tool>/docs/               - Tool-specific documentation"
    echo ""
    echo "❌ Violating files (under docs-public/):"
    echo -e "$legacy_docs_violations" | sed "s/^/  - /"
    echo ""
    echo "📁 Correct locations for documentation:"
    echo "  ✅ Project docs:         ../sage-docs/..."
    echo "  ✅ In-tree implementation docs: src/.../README.md or src/.../docs/"
    echo "  ✅ Tool-specific:        tools/<tool-name>/docs/"
    echo "  ✅ Examples:             ../sage-examples/ (independent repository)"
    echo ""
    echo "💡 Action required:"
    echo "   1. Move user-facing docs into the sibling 'sage-docs' repository"
    echo "   2. Update any internal links/references"
    echo "   3. Remove the legacy docs-public path entirely"
    echo ""
    echo "================================================================================================"
    failed=true
fi

# Priority 2: Other location violations
if [ -n "$other_violations" ]; then
    echo "================================================================================================"
    echo "❌ 错误: 以下 markdown 文件不在允许的位置"
    echo "================================================================================================"
    echo ""
    echo "散落的文档文件（需要整理到标准位置）:"
    echo -e "$other_violations" | sed "s/^/  - /"
    echo ""
    echo "✅ 允许的标准位置:"
    echo "  📦 项目根目录:"
    echo "     - README.md, CHANGELOG.md, CONTRIBUTING.md, LICENSE.md, DEVELOPER.md"
    echo ""
    echo "  📚 项目文档:"
    echo "     - ../sage-docs/                       (集中管理的项目文档仓库)"
    echo "     - docs/dependency-audit-gate.md       (元仓库治理证据文档)"
    echo ""
    echo "  📦 主仓内实现文档:"
    echo "     - src/<module>/README.md              (模块主文档)"
    echo "     - src/<module>/docs/                  (实现细节文档目录)"
    echo ""
    echo "  🔧 工具文档:"
    echo "     - tools/<tool>/README.md"
    echo "     - tools/<tool>/docs/"
    echo ""
    echo "  🚫 第三方库文档 (自动排除):"
    echo "     - src/.*/implementations/SPTAG/        (Microsoft SPTAG)"
    echo "     - src/.*/implementations/faiss/        (Facebook FAISS)"
    echo "     - src/.*/implementations/diskann-ms/   (Microsoft DiskANN)"
    echo "     - src/.*/implementations/pybind11/, puck/, zstd/, candy/ (其他第三方库)"
    echo ""
    echo "💡 整理建议:"
    echo "   1. 用户文档 → ../sage-docs 仓库"
    echo "   2. 模块实现文档 → src/.../docs/"
    echo "   3. 工具说明 → tools/.../docs/"
    echo "   4. 元仓库治理证据/报告 → docs/ 中的机器专用文件"
    echo ""
    echo "🔍 常见违规案例:"
    echo "   ❌ src/.../BUILD.md                       → 应移至 src/.../docs/"
    echo "   ❌ src/.../MIGRATION.md                   → 应移至 src/.../docs/"
    echo "   ❌ 根目录散落的用户文档                     → 应移至 ../sage-docs/"
    echo ""
    echo "================================================================================================"
    failed=true
fi

if [ "$failed" = true ]; then
    exit 1
fi

exit 0
