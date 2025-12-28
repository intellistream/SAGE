#!/bin/bash
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

# Check for files in docs/ (root docs folder)
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
    # Check if file is in docs/
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

if [ -n "$docs_violations" ]; then
    echo "❌ 错误: 检测到在 'docs/' 目录下提交了文档。"
    echo "   我们不再推送根目录的 'docs/'，它已被 gitignore。"
    echo "   请将文档移动到 'docs-public/' 下的合适位置。"
    echo -e "$docs_violations" | sed "s/^/  - /"
    echo ""
    failed=true
fi

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
