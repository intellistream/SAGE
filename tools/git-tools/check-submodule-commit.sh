#!/bin/bash
# 检查文件是否在子模块中，如果是则给出正确的提交指导

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# 如果没有提供文件路径，检查所有暂存的文件
if [ $# -eq 0 ]; then
    files=$(cd "$REPO_ROOT" && git diff --cached --name-only)
else
    files="$@"
fi

cd "$REPO_ROOT"

# 存储是否在子模块中的文件
in_submodule=()
submodule_info=()

for file in $files; do
    # 检查文件是否在子模块中
    submodule_path=$(git submodule foreach --quiet 'echo $sm_path' | while read sm_path; do
        if [[ "$file" == "$sm_path"* ]]; then
            echo "$sm_path"
            break
        fi
    done)

    if [ -n "$submodule_path" ]; then
        in_submodule+=("$file")

        # 获取子模块信息
        url=$(git config --file .gitmodules --get "submodule.$submodule_path.url")
        branch=$(git config --file .gitmodules --get "submodule.$submodule_path.branch" || echo "main-dev")
        repo_name=$(basename "$url" .git)

        submodule_info+=("$submodule_path|$repo_name|$branch")
    fi
done

# 如果有文件在子模块中，给出警告和指导
if [ ${#in_submodule[@]} -gt 0 ]; then
    echo "⚠️  警告: 以下文件在 Git 子模块中"
    echo "=========================================="
    echo ""

    # 按子模块分组
    declare -A submodule_files
    for i in "${!in_submodule[@]}"; do
        file="${in_submodule[$i]}"
        info="${submodule_info[$i]}"
        sm_path=$(echo "$info" | cut -d'|' -f1)

        if [ -z "${submodule_files[$sm_path]}" ]; then
            submodule_files[$sm_path]="$file"
        else
            submodule_files[$sm_path]="${submodule_files[$sm_path]}"$'\n'"$file"
        fi
    done

    # 显示每个子模块的指导
    for sm_path in "${!submodule_files[@]}"; do
        # 查找对应的 info
        for info in "${submodule_info[@]}"; do
            if [[ "$info" == "$sm_path|"* ]]; then
                repo_name=$(echo "$info" | cut -d'|' -f2)
                branch=$(echo "$info" | cut -d'|' -f3)
                break
            fi
        done

        echo "📦 子模块: $repo_name"
        echo "   路径: $sm_path"
        echo "   分支: $branch"
        echo ""
        echo "   文件:"
        echo "${submodule_files[$sm_path]}" | while read f; do
            echo "   - $f"
        done
        echo ""
        echo "   ✅ 正确的提交步骤:"
        echo ""
        echo "   # 1. 在子模块中提交"
        echo "   cd $sm_path"
        echo "   git add ."
        echo "   git commit -m \"your message\""
        echo "   git push origin $branch"
        echo ""
        echo "   # 2. 在主仓库中更新引用"
        echo "   cd $REPO_ROOT"
        echo "   git add $sm_path"
        echo "   git commit -m \"chore: update $repo_name submodule\""
        echo ""
        echo "=========================================="
        echo ""
    done

    echo "💡 提示: 查看 $sm_path/SUBMODULE.md 了解更多"
    echo ""

    exit 1
else
    # 没有子模块文件，正常提交
    exit 0
fi
