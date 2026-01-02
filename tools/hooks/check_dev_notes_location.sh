#!/bin/bash
# Pre-commit hook to enforce dev-notes categorization
# All dev-notes markdown files must be in categorized subdirectories

set -e

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

# Check for dev-notes files in wrong locations
violations=""
dev_notes_root="docs-public/docs_src/dev-notes"

# Valid dev-notes subdirectories
valid_subdirs=(
    "archive"
    "cross-layer/architecture"
    "cross-layer/ci-cd"
    "cross-layer"
    "l1-common"
    "l2-platform"
    "l3-kernel"
    "l3-libs"
    "l4-middleware"
    "l5-apps"
    "l5-benchmark"
    "l6-cli"
    "l6-gateway"
    "l6-studio"
    "l6-tools"
    "research_work"
    "testing"
)

# Special allowed files in dev-notes root
allowed_root_files=(
    "TEMPLATE.md"
    "README.md"
    "index.md"
    "dev_notes_catalog.csv"
    "package-architecture.md"
)

for file in $all_md_files; do
    # Only check files in dev-notes directory
    if [[ "$file" == ${dev_notes_root}/* ]]; then
        # Get relative path from dev-notes root
        relative_path="${file#${dev_notes_root}/}"

        # Check if it's directly in dev-notes root (not in a subdirectory)
        if [[ "$relative_path" != */* ]]; then
            # Check if it's an allowed root file
            is_allowed=false
            for allowed_file in "${allowed_root_files[@]}"; do
                if [[ "$relative_path" == "$allowed_file" ]]; then
                    is_allowed=true
                    break
                fi
            done

            if [ "$is_allowed" = false ]; then
                violations="$violations$file\n"
            fi
        else
            # File is in a subdirectory, check if it's a valid one
            subdir="${relative_path%%/*}"
            is_valid=false

            for valid_dir in "${valid_subdirs[@]}"; do
                if [[ "$subdir" == "$valid_dir" ]] || [[ "$relative_path" == "$valid_dir"/* ]]; then
                    is_valid=true
                    break
                fi
            done

            if [ "$is_valid" = false ]; then
                violations="$violations$file (无效子目录: $subdir)\n"
            fi
        fi
    fi
done

if [ -n "$violations" ]; then
    echo "❌ 错误: 以下 dev-notes 文档未放置在正确的分类目录中:"
    echo -e "$violations" | sed "s/^/  - /"
    echo ""
    echo "✅ 开发日志文档必须放置在以下分类目录之一:"
    echo ""
    echo "📦 按层级分类 (Package Layers):"
    echo "  - ${dev_notes_root}/l1-common/          # L1 Common 层"
    echo "  - ${dev_notes_root}/l2-platform/        # L2 Platform 层"
    echo "  - ${dev_notes_root}/l3-kernel/          # L3 Kernel 层"
    echo "  - ${dev_notes_root}/l3-libs/            # L3 Libs 层"
    echo "  - ${dev_notes_root}/l4-middleware/      # L4 Middleware 层"
    echo "  - ${dev_notes_root}/l5-apps/            # L5 Apps 层"
    echo "  - ${dev_notes_root}/l5-benchmark/       # L5 Benchmark 层"
    echo "  - ${dev_notes_root}/l6-cli/             # L6 CLI 层"
    echo "  - ${dev_notes_root}/l6-gateway/         # L6 Gateway 层"
    echo "  - ${dev_notes_root}/l6-studio/          # L6 Studio 层"
    echo "  - ${dev_notes_root}/l6-tools/           # L6 Tools 层"
    echo ""
    echo "🔀 跨层级分类 (Cross-Layer):"
    echo "  - ${dev_notes_root}/cross-layer/architecture/  # 架构设计"
    echo "  - ${dev_notes_root}/cross-layer/ci-cd/         # CI/CD 和构建"
    echo "  - ${dev_notes_root}/cross-layer/              # 其他跨层级"
    echo ""
    echo "📚 其他分类:"
    echo "  - ${dev_notes_root}/research_work/      # 研究工作"
    echo "  - ${dev_notes_root}/testing/            # 测试相关"
    echo "  - ${dev_notes_root}/archive/            # 历史归档"
    echo ""
    echo "💡 提示:"
    echo "  1. 使用 TEMPLATE.md 作为模板创建新文档"
    echo "  2. 根据内容选择合适的分类目录"
    echo "  3. 跨多个层级的内容应放在 cross-layer/ 下"
    echo "  4. 不确定时参考 dev_notes_catalog.csv"
    echo ""
    exit 1
fi

exit 0
