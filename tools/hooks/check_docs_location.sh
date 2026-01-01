#!/bin/bash
set -e

# ============================================================================
# Check Docs Location Hook
# ============================================================================
# Purpose: Ensure markdown files are in proper locations.
#          CRITICAL: Root 'docs/' directory is FORBIDDEN. Use 'docs-public/' instead.
#
# This hook prevents:
# 1. Any files in root docs/ directory (which should not exist)
# 2. Markdown files in random locations outside allowed patterns
#
# Rationale:
# - Root 'docs/' is gitignored and should not be used for committed documentation
# - All documentation must go to 'docs-public/' for centralized management
# - Package-specific docs go in packages/<package>/docs/ or README.md
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

# Check for files in docs/ (root docs folder) - STRICTLY FORBIDDEN
docs_violations=""
other_violations=""

# Define allowed patterns (whitelist)
allowed_patterns=(
    "^README\.md$"
    "^CHANGELOG\.md$"
    "^CONTRIBUTING\.md$"
    "^LICENSE\.md$"
    "^DEVELOPER\.md$"
    "^docs-public/"
    "^docker/.*\.md$"
    "^packages/.*/README\.md$"
    "^packages/.*README.*\.md$"
    "^packages/.*/CHANGELOG\.md$"
    "^packages/.*/(docs|documentation)/"
    "^packages/.*\.md$"
    "^examples/README\.md$"
    "^examples/.*/README\.md$"
    "^examples/tutorials/"
    "^config/README\.md$"
    "^tools/.*/README\.md$"
    "^tools/.*\.md$"
    "^\.sage/.*\.md$"
    "^\.github/.*\.md$"
)

for file in $all_md_files; do
    # CRITICAL CHECK: Reject any file in root docs/ directory
    if [[ "$file" == docs/* ]]; then
        docs_violations="$docs_violations$file\n"
        continue
    fi

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

# Priority 1: Root docs/ violations (most critical)
if [ -n "$docs_violations" ]; then
    echo "================================================================================================"
    echo "❌ CRITICAL ERROR: Files detected in FORBIDDEN 'docs/' directory"
    echo "================================================================================================"
    echo ""
    echo "The root 'docs/' directory is gitignored and must NOT contain committed documentation."
    echo "All documentation must be placed in 'docs-public/' or other appropriate locations."
    echo ""
    echo "Violating files:"
    echo -e "$docs_violations" | sed "s/^/  - /"
    echo ""
    echo "📁 Correct locations for documentation:"
    echo "  ✅ User-facing docs:     docs-public/docs_src/..."
    echo "  ✅ Developer docs:       docs-public/docs_src/dev-notes/..."
    echo "  ✅ Package-specific:     packages/<package-name>/README.md or packages/<package-name>/docs/"
    echo "  ✅ Examples:             examples/<name>/README.md"
    echo ""
    echo "💡 Action required:"
    echo "   1. Move files from 'docs/' to 'docs-public/docs_src/...' (appropriate subdirectory)"
    echo "   2. Update any internal links/references"
    echo "   3. Remove the root 'docs/' directory entirely"
    echo ""
    echo "================================================================================================"
    failed=true
fi

# Priority 2: Other location violations
if [ -n "$other_violations" ]; then
    echo "❌ 错误: 以下 markdown 文件不在允许的位置:"
    echo -e "$other_violations" | sed "s/^/  - /"
    echo ""
    echo "✅ 允许的位置:"
    echo "  - 项目根目录: README.md, CHANGELOG.md, CONTRIBUTING.md, LICENSE.md, DEVELOPER.md"
    echo "  - 用户文档: docs-public/"
    echo "  - 包文档: packages/<package-name>/README.md, packages/<package-name>/CHANGELOG.md"
    echo "  - 包文档目录: packages/<package-name>/docs/, packages/<package-name>/documentation/"
    echo "  - 示例文档: examples/<example-name>/README.md, examples/tutorials/"
    echo "  - GitHub 模板: .github/ISSUE_TEMPLATE/, .github/PULL_REQUEST_TEMPLATE/"
    echo ""
    echo "💡 建议: 请将文档移动到合适的位置或更新允许列表"
    failed=true
fi

if [ "$failed" = true ]; then
    exit 1
fi

exit 0
