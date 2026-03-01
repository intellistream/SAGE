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
# - Submodules can have their own docs/ directories (e.g., sageLLM/docs/, sageFlow/docs/)
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
    "^packages/[^/]+/README\.md$"              # Only top-level README in packages
    "^packages/[^/]+/CHANGELOG\.md$"           # Only top-level CHANGELOG in packages
    "^packages/[^/]+/(docs|documentation)/"    # Package docs directory
    "^packages/[^/]+/examples/.*\.md$"         # Package examples documentation
    "^packages/[^/]+/src/.*/docs/"             # Submodule docs (sageLLM, sageFlow, etc.)

    # Allow module-level READMEs for apps, benchmarks, libs components
    "^packages/sage-apps/src/sage/apps/[^/]+/README\.md$"
    "^packages/sage-benchmark/src/sage/benchmark/benchmark_[^/]+/README\.md$"
    "^packages/sage-benchmark/src/sage/benchmark/benchmark_[^/]+/[^/]+/README\.md$"  # evaluation/, scripts/, etc.
    "^packages/sage-benchmark/src/sage/benchmark/benchmark_[^/]+/experiments/[^/]+/README\.md$"
    "^packages/sage-libs/src/sage/libs/anns/README\.md$"
    "^packages/sage-libs/src/sage/libs/anns/implementations/README\.md$"
    "^packages/sage-libs/src/sage/libs/anns/wrappers/.*/README\.md$"
    "^packages/sage-libs/src/sage/libs/amms/README\.md$"  # Main module README
    "^packages/sage-libs/src/sage/libs/agentic/[^/]+/[^/]+/README\.md$"
    "^packages/sage-llm-core/src/sage/llm/control_plane/[^/]+/README\.md$"
    "^packages/sage-cli/src/sage/cli/templates/README\.md$"
    "^packages/sage-tools/src/sage/tools/templates/.*\.md$"

    # Allow submodule markers
    "^packages/.*/SUBMODULE\.md$"

    # Allow experiment config docs (special case for benchmark)
    "^packages/sage-benchmark/src/sage/benchmark/benchmark_[^/]+/experiment/config/.*\.md$"

    # Allow benchmark special docs (DATA_PATHS, VISUALIZATION at benchmark root)
    "^packages/sage-benchmark/src/sage/benchmark/benchmark_[^/]+/DATA_PATHS\.md$"
    "^packages/sage-benchmark/src/sage/benchmark/benchmark_[^/]+/VISUALIZATION\.md$"

    # Allow deep subdirectory READMEs in benchmark evaluation/
    "^packages/sage-benchmark/src/sage/benchmark/benchmark_[^/]+/evaluation/.*/README\.md$"

    # Allow experiment design docs in benchmark experiments/
    "^packages/sage-benchmark/src/sage/benchmark/benchmark_[^/]+/experiments/.*/DESIGN\.md$"

    # Allow anns implementation technical docs
    "^packages/sage-libs/src/sage/libs/anns/implementations/README_[^/]+\.md$"
    "^packages/sage-libs/src/sage/libs/anns/wrappers/.*\.md$"

    "^examples/README\.md$"
    "^examples/.*/README\.md$"
    "^examples/tutorials/"
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
    "^packages/.*/implementations/SPTAG/"      # Microsoft SPTAG
    "^packages/.*/implementations/faiss/"      # Facebook FAISS
    "^packages/.*/implementations/diskann-ms/" # Microsoft DiskANN
    "^packages/.*/implementations/pybind11/"   # pybind11 library
    "^packages/.*/implementations/puck/"       # Puck library
    "^packages/.*/implementations/zstd/"       # Zstandard library
    "^packages/.*/implementations/candy/"      # Candy library family
    "^packages/.*/third[-_]party/"            # Generic third-party directories
    "^packages/.*/external/"                   # External dependencies
    "^packages/.*/vendor/"                     # Vendored libraries
)

for file in $all_md_files; do
    # CRITICAL CHECK: Reject any file in root docs/ directory ONLY
    # Allow packages/*/docs/ and submodule docs/ directories
    if [[ "$file" == "docs/"* ]] && [[ "$file" != "packages/"* ]]; then
        docs_violations="$docs_violations$file\n"
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

# Priority 1: Root docs/ violations (most critical)
if [ -n "$docs_violations" ]; then
    echo "================================================================================================"
    echo "❌ CRITICAL ERROR: Files detected in FORBIDDEN root 'docs/' directory"
    echo "================================================================================================"
    echo ""
    echo "The root 'docs/' directory is gitignored and must NOT contain committed documentation."
    echo "All documentation must be placed in 'docs-public/' or other appropriate locations."
    echo ""
    echo "⚠️  Note: Package and submodule docs/ directories ARE ALLOWED:"
    echo "   ✅ packages/<package>/docs/          - Package-specific documentation"
    echo "   ✅ packages/.../submodule/docs/      - Submodule documentation (sageLLM, sageFlow, etc.)"
    echo "   ✅ tools/<tool>/docs/                - Tool-specific documentation"
    echo ""
    echo "❌ Violating files (in ROOT docs/ directory):"
    echo -e "$docs_violations" | sed "s/^/  - /"
    echo ""
    echo "📁 Correct locations for documentation:"
    echo "  ✅ User-facing docs:     docs-public/docs_src/..."
    echo "  ✅ Developer docs:       docs-public/docs_src/dev-notes/..."
    echo "  ✅ Package-specific:     packages/<package-name>/README.md or packages/<package-name>/docs/"
    echo "  ✅ Submodule docs:       packages/<package>/src/.../submodule/docs/ (e.g., sageLLM/docs/)"
    echo "  ✅ Tool-specific:        tools/<tool-name>/docs/"
    echo "  ✅ Examples:             examples/<name>/README.md"
    echo ""
    echo "💡 Action required:"
    echo "   1. Move files from ROOT 'docs/' to 'docs-public/docs_src/...' (appropriate subdirectory)"
    echo "   2. Update any internal links/references"
    echo "   3. Remove the root 'docs/' directory entirely"
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
    echo "  📚 用户和开发者文档:"
    echo "     - docs-public/docs_src/               (用户指南、教程)"
    echo "     - docs-public/docs_src/dev-notes/     (开发者文档)"
    echo ""
    echo "  📦 包级文档:"
    echo "     - packages/<package>/README.md        (包的主文档)"
    echo "     - packages/<package>/CHANGELOG.md     (包的变更日志)"
    echo "     - packages/<package>/docs/            (包的详细文档目录)"
    echo ""
    echo "  🔧 子模块文档 (必须在 docs/ 子目录):"
    echo "     - packages/<package>/src/.../submodule/docs/  (sageLLM, sageVDB, sageFlow, etc.)"
    echo "     - 子模块内散落的 MD 文件也是违规的，必须放在 submodule/docs/ 下"
    echo ""
    echo "  📂 示例和工具:"
    echo "     - examples/<example>/README.md"
    echo "     - examples/tutorials/"
    echo "     - tools/<tool>/README.md"
    echo "     - tools/<tool>/docs/"
    echo ""
    echo "  🚫 第三方库文档 (自动排除):"
    echo "     - packages/.*/implementations/SPTAG/   (Microsoft SPTAG)"
    echo "     - packages/.*/implementations/faiss/   (Facebook FAISS)"
    echo "     - packages/.*/implementations/diskann-ms/ (Microsoft DiskANN)"
    echo "     - packages/.*/implementations/pybind11/, puck/, zstd/, candy/ (其他第三方库)"
    echo ""
    echo "💡 整理建议:"
    echo "   1. 包内文档 → packages/<package>/docs/"
    echo "   2. 子模块文档 → 子模块的 docs/ 子目录"
    echo "   3. 通用开发者笔记 → docs-public/docs_src/dev-notes/"
    echo "   4. 用户指南 → docs-public/docs_src/guides/"
    echo ""
    echo "🔍 常见违规案例:"
    echo "   ❌ packages/.../src/.../BUILD.md          → 应移至 packages/<pkg>/docs/"
    echo "   ❌ packages/.../src/.../MIGRATION.md      → 应移至 packages/<pkg>/docs/"
    echo "   ❌ packages/.../submodule/dev-notes/*.md  → 应移至 submodule/docs/dev-notes/"
    echo ""
    echo "================================================================================================"
    failed=true
fi

if [ "$failed" = true ]; then
    exit 1
fi

exit 0
