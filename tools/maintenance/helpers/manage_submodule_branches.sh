#!/bin/bash
# 🔄 SAGE Submodule 分支管理脚本
# 功能：根据当前 SAGE 分支自动切换 submodule 到对应分支并拉取最新代码
# - main 分支 → submodules 的 main 分支
# - 其他分支 → submodules 的 main-dev 分支
# - 自动 fetch 远程分支并 pull 最新代码
#
# 注意事项：
# - 支持浅克隆(shallow clone)的 submodules
# - 浅克隆时会自动 fetch 目标分支或 unshallow（如果需要）
# - 切换分支后自动拉取最新代码
# - 修复了 quickstart.sh 中 --depth 1 导致的分支切换问题

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
DIM='\033[0;2m'
NC='\033[0m' # No Color
CHECK='✅'
CROSS='❌'
INFO='ℹ️'
ROCKET='🚀'

# 获取当前分支
get_current_branch() {
    git rev-parse --abbrev-ref HEAD
}

# 获取 submodule 列表
get_submodules() {
    git config --file .gitmodules --get-regexp path | awk '{ print $2 }'
}

# 获取 submodule 的 remote URL
get_submodule_url() {
    local submodule_path="$1"
    git config --file .gitmodules --get "submodule.${submodule_path}.url"
}

# 获取 submodule 的当前配置分支
get_submodule_configured_branch() {
    local submodule_path="$1"
    git config --file .gitmodules --get "submodule.${submodule_path}.branch" || echo "stable"
}

# 检查 submodule 远程仓库是否存在某个分支
check_remote_branch_exists() {
    local submodule_path="$1"
    local branch_name="$2"

    cd "$submodule_path" 2>/dev/null || return 1

    # 检查是否是浅克隆（submodule 的 .git 是文件，需要用 git rev-parse）
    local git_dir=$(git rev-parse --git-dir 2>/dev/null)
    if [ -f "$git_dir/shallow" ]; then
        # 浅克隆情况下，尝试 fetch 该分支来检查是否存在
        git fetch origin "$branch_name" --depth 1 2>/dev/null
    else
        # 非浅克隆，正常 fetch
        git fetch origin "$branch_name" 2>/dev/null
    fi

    local exists=$?
    cd - > /dev/null
    return $exists
}

# 更新 .gitmodules 中的分支配置
update_gitmodules_branch() {
    local submodule_path="$1"
    local target_branch="$2"

    git config --file .gitmodules "submodule.${submodule_path}.branch" "$target_branch"
}

# 设置 submodule 的上游追踪分支
# 解决浅克隆导致的 VS Code "Publish Branch" 显示问题
# 注意：此函数假设当前已经在子模块目录内
setup_upstream_tracking() {
    local target_branch="$1"

    # 检查是否已有上游追踪
    if git rev-parse --abbrev-ref --symbolic-full-name @{u} >/dev/null 2>&1; then
        return 0
    fi

    # 添加 fetch refspec（如果尚未存在）
    if ! git config --get-all remote.origin.fetch 2>/dev/null | grep -q "refs/heads/$target_branch"; then
        git config --add remote.origin.fetch "+refs/heads/$target_branch:refs/remotes/origin/$target_branch" 2>/dev/null || true
        git fetch origin "$target_branch" >/dev/null 2>&1 || git fetch origin >/dev/null 2>&1 || true
    fi

    # 设置上游追踪
    if git show-ref --verify --quiet "refs/remotes/origin/$target_branch"; then
        git branch -u "origin/$target_branch" "$target_branch" >/dev/null 2>&1 || true
    fi

    return 0
}

# 切换 submodule 到指定分支并拉取最新代码
switch_submodule_branch() {
    local submodule_path="$1"
    local target_branch="$2"
    local submodule_name=$(basename "$submodule_path")

    if [ ! -d "$submodule_path/.git" ] && [ ! -f "$submodule_path/.git" ]; then
        echo -e "${YELLOW}  ⚠️  Submodule ${submodule_name} 未初始化${NC}"
        return 1
    fi

    cd "$submodule_path"

    # 检查是否是浅克隆仓库
    # 注意：submodule 的 .git 是文件不是目录，需要用 git rev-parse --git-dir 获取实际路径
    local is_shallow=false
    local git_dir=$(git rev-parse --git-dir 2>/dev/null)
    if [ -f "$git_dir/shallow" ]; then
        is_shallow=true
        echo -e "${DIM}  检测到浅克隆，将 fetch 目标分支...${NC}"
    fi

    # 获取远程分支
    # 对于浅克隆，明确 fetch 目标分支
    if [ "$is_shallow" = true ]; then
        echo -e "${DIM}  正在 fetch ${target_branch} 分支...${NC}"
        # 浅克隆情况下，使用 refspec 明确指定要 fetch 的分支
        # 格式：refs/heads/branch:refs/remotes/origin/branch
        # 注意：即使命令返回非零，也可能成功 fetch，所以不检查返回码
        git fetch origin "refs/heads/$target_branch:refs/remotes/origin/$target_branch" --depth 1 >/dev/null 2>&1 || \
        git fetch origin "$target_branch" --depth 1 >/dev/null 2>&1 || \
        git fetch --unshallow >/dev/null 2>&1 || true
    else
        # 非浅克隆，正常 fetch 所有分支
        git fetch origin >/dev/null 2>&1 || true
    fi

    # 首先检查当前是否已经在目标分支上
    local current_branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")
    local already_on_branch=false
    if [ "$current_branch" = "$target_branch" ]; then
        already_on_branch=true
        echo -e "${GREEN}  ${CHECK} 已在 ${target_branch} 分支${NC}"
    fi

    # 确定目标引用（优先使用 origin/分支，其次使用本地分支）
    # 注意：如果已在目标分支上，不需要切换，只需要pull
    local target_ref=""
    if [ "$already_on_branch" = false ]; then
        if git show-ref --verify --quiet "refs/remotes/origin/$target_branch"; then
            target_ref="origin/$target_branch"
        elif git show-ref --verify --quiet "refs/heads/$target_branch"; then
            target_ref="$target_branch"
        else
            echo -e "${RED}  ${CROSS} 未找到 ${target_branch} 对应的远程或本地分支${NC}"
            echo -e "${DIM}  提示: 请确认远程仓库中存在 ${target_branch} 分支${NC}"
            cd - > /dev/null
            return 1
        fi
    fi

    # 切换分支（如果尚未在目标分支上）
    if [ "$already_on_branch" = false ]; then
        echo -e "${DIM}  切换到 ${target_branch} 分支...${NC}"
        if ! git checkout -B "$target_branch" "$target_ref" >/dev/null 2>&1; then
            echo -e "${RED}  ${CROSS} 无法切换到 ${target_branch}${NC}"
            cd - > /dev/null
            return 1
        fi
        echo -e "${GREEN}  ${CHECK} 已切换到 ${target_branch}${NC}"
    fi

    # 设置上游追踪分支（修复 VS Code "Publish Branch" 问题）
    # 注意：当前已在子模块目录内
    setup_upstream_tracking "$target_branch"

    # 拉取最新代码
    echo -e "${DIM}  正在拉取最新代码...${NC}"
    local old_commit=$(git rev-parse HEAD 2>/dev/null || echo "unknown")

    if git pull origin "$target_branch" >/dev/null 2>&1; then
        local new_commit=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
        if [ "$old_commit" != "$new_commit" ]; then
            local commit_short=$(echo "$new_commit" | cut -c1-7)
            echo -e "${GREEN}  ${CHECK} 已更新到最新 (${commit_short})${NC}"
        else
            echo -e "${GREEN}  ${CHECK} 已是最新${NC}"
        fi
    else
        echo -e "${YELLOW}  ⚠️  无法拉取最新代码，继续使用当前版本${NC}"
    fi

    cd - > /dev/null
    return 0
}

# 检查目录是否存在残留文件（非空且不是有效的 git 仓库）
check_dir_has_residual_files() {
    local dir_path="$1"

    # 目录不存在，无残留
    if [ ! -d "$dir_path" ]; then
        return 1
    fi

    # 目录存在但是有效的 git 仓库（有 .git 目录或文件）
    if [ -d "$dir_path/.git" ] || [ -f "$dir_path/.git" ]; then
        return 1
    fi

    # 目录为空，无残留
    if [ -z "$(ls -A "$dir_path" 2>/dev/null)" ]; then
        return 1
    fi

    # 目录存在且非空，且不是有效的 git 仓库 → 有残留文件
    return 0
}

# 显示目录内容摘要
show_dir_contents_summary() {
    local dir_path="$1"
    local max_items=5

    echo -e "${DIM}  目录内容:${NC}"
    local count=0
    for item in "$dir_path"/*; do
        if [ -e "$item" ]; then
            local item_name=$(basename "$item")
            if [ -d "$item" ]; then
                echo -e "${DIM}    📁 ${item_name}/${NC}"
            else
                echo -e "${DIM}    📄 ${item_name}${NC}"
            fi
            ((count++))
            if [ $count -ge $max_items ]; then
                local total=$(ls -A "$dir_path" 2>/dev/null | wc -l)
                local remaining=$((total - max_items))
                if [ $remaining -gt 0 ]; then
                    echo -e "${DIM}    ... 还有 ${remaining} 个文件/目录${NC}"
                fi
                break
            fi
        fi
    done
}

# 询问用户是否删除残留目录
# 返回: 0 = 用户同意删除, 1 = 用户拒绝或非交互模式
ask_delete_residual_dir() {
    local dir_path="$1"
    local submodule_name="$2"

    # 检查是否在非交互模式（CI 环境或 --yes 参数）
    if [[ -n "$CI" || -n "$GITHUB_ACTIONS" || "$SAGE_AUTO_YES" == "true" ]]; then
        echo -e "${YELLOW}  ⚠️  非交互模式，自动删除残留目录${NC}"
        return 0
    fi

    # 检查 stdin 是否是终端
    if [ ! -t 0 ]; then
        echo -e "${YELLOW}  ⚠️  非交互式环境，跳过删除确认${NC}"
        return 1
    fi

    echo ""
    echo -e "${YELLOW}  ❓ 是否删除残留目录并重新初始化 ${submodule_name}? [y/N]${NC}"
    read -r -n 1 response </dev/tty
    echo ""

    case "$response" in
        [yY])
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

# 尝试初始化单个 submodule，处理残留目录的情况
try_init_submodule() {
    local submodule_path="$1"
    local submodule_name=$(basename "$submodule_path")

    # 检查是否有残留文件
    if check_dir_has_residual_files "$submodule_path"; then
        echo -e "${YELLOW}  ⚠️  检测到 ${submodule_name} 目录存在残留文件${NC}"
        show_dir_contents_summary "$submodule_path"

        if ask_delete_residual_dir "$submodule_path" "$submodule_name"; then
            echo -e "${DIM}  正在删除残留目录...${NC}"
            if rm -rf "$submodule_path"; then
                echo -e "${GREEN}  ${CHECK} 残留目录已删除${NC}"
            else
                echo -e "${RED}  ${CROSS} 无法删除残留目录${NC}"
                return 1
            fi
        else
            echo -e "${YELLOW}  ⚠️  跳过 ${submodule_name}，请手动处理残留目录${NC}"
            echo -e "${DIM}  手动命令: rm -rf ${submodule_path} && git submodule update --init ${submodule_path}${NC}"
            return 1
        fi
    fi

    # 尝试初始化 submodule
    echo -e "${DIM}  初始化 ${submodule_name}...${NC}"
    local init_output
    if init_output=$(git submodule update --init "$submodule_path" 2>&1); then
        echo -e "${GREEN}  ${CHECK} ${submodule_name} 初始化成功${NC}"
        return 0
    else
        # 初始化失败，检查是否是 "already exists and is not an empty directory" 错误
        if echo "$init_output" | grep -q "already exists and is not an empty directory"; then
            echo -e "${YELLOW}  ⚠️  检测到 ${submodule_name} 目录存在但不为空${NC}"
            show_dir_contents_summary "$submodule_path"

            if ask_delete_residual_dir "$submodule_path" "$submodule_name"; then
                echo -e "${DIM}  正在删除残留目录...${NC}"
                if rm -rf "$submodule_path"; then
                    echo -e "${GREEN}  ${CHECK} 残留目录已删除${NC}"
                    # 重新尝试初始化
                    echo -e "${DIM}  重新初始化 ${submodule_name}...${NC}"
                    if git submodule update --init "$submodule_path" >/dev/null 2>&1; then
                        echo -e "${GREEN}  ${CHECK} ${submodule_name} 初始化成功${NC}"
                        return 0
                    fi
                fi
            else
                echo -e "${YELLOW}  ⚠️  跳过 ${submodule_name}，请手动处理残留目录${NC}"
                echo -e "${DIM}  手动命令: rm -rf ${submodule_path} && git submodule update --init ${submodule_path}${NC}"
            fi
        fi

        echo -e "${RED}  ${CROSS} ${submodule_name} 初始化失败${NC}"
        echo -e "${DIM}  错误信息: ${init_output}${NC}"
        return 1
    fi
}

# 检查 submodules 是否已初始化，如果未初始化则自动初始化
check_submodules_initialized() {
    echo -e "${BLUE}🔍 检查 submodule 初始化状态...${NC}"

    local uninit_submodules=()
    while IFS= read -r submodule_path; do
        if [ ! -d "$submodule_path/.git" ] && [ ! -f "$submodule_path/.git" ]; then
            uninit_submodules+=("$submodule_path")
        fi
    done < <(get_submodules)

    if [ ${#uninit_submodules[@]} -gt 0 ]; then
        echo -e "${YELLOW}  ⚠️  发现 ${#uninit_submodules[@]} 个未初始化的 submodules，正在自动初始化...${NC}"

        local failed_count=0
        for submodule_path in "${uninit_submodules[@]}"; do
            if ! try_init_submodule "$submodule_path"; then
                ((failed_count++))
            fi
        done

        if [ $failed_count -gt 0 ]; then
            echo -e "${RED}${CROSS} ${failed_count} 个 submodules 初始化失败${NC}"
            return 1
        fi

        echo -e "${GREEN}${CHECK} 所有 submodules 已自动初始化${NC}"
        return 0
    else
        echo -e "${CHECK} 所有 submodules 已初始化${NC}"
        return 0
    fi
}

# 主函数：切换 submodule 分支
switch_submodules() {
    # 在 CI 环境中跳过分支切换，因为 checkout@v4 已经将 submodules checkout 到正确的 commit
    if [[ -n "$CI" || -n "$GITHUB_ACTIONS" ]]; then
        echo -e "${INFO} ${YELLOW}检测到 CI 环境，跳过 submodule 分支切换${NC}"
        echo -e "${DIM}CI 环境中 submodules 已由 checkout action 设置到正确的 commit${NC}"
        return 0
    fi

    local current_branch=$(get_current_branch)
    local target_branch

    echo -e "${ROCKET} ${BLUE}SAGE Submodule 分支管理${NC}"
    echo -e "${DIM}当前 SAGE 分支: ${current_branch}${NC}"
    echo ""

    # 确定目标分支
    if [ "$current_branch" = "main" ]; then
        target_branch="main"
        echo -e "${INFO} 在 main 分支，submodules 将切换到 ${GREEN}main${NC} 分支"
    else
        target_branch="main-dev"
        echo -e "${INFO} 在 ${current_branch} 分支，submodules 将切换到 ${GREEN}main-dev${NC} 分支"
    fi
    echo ""

    # 检查 submodules 是否已初始化（不执行初始化，只检查）
    if ! check_submodules_initialized; then
        echo ""
        return 1
    fi
    echo ""

    local success_count=0
    local fail_count=0

    mapfile -t submodules < <(get_submodules)
    for submodule_path in "${submodules[@]}"; do
        local submodule_name=$(basename "$submodule_path")
        local current_config_branch=$(get_submodule_configured_branch "$submodule_path")

        echo -e "${BLUE}📦 处理 submodule: ${submodule_name}${NC}"
        echo -e "${DIM}  当前配置分支: ${current_config_branch}${NC}"
        echo -e "${DIM}  目标分支: ${target_branch}${NC}"

        # 更新 .gitmodules
        update_gitmodules_branch "$submodule_path" "$target_branch"

        # 切换分支
        if switch_submodule_branch "$submodule_path" "$target_branch"; then
            success_count=$((success_count + 1))
        else
            fail_count=$((fail_count + 1))
        fi
        echo ""
    done

    # 更新 submodule 注册信息
    echo -e "${DIM}更新 submodule 注册信息...${NC}"
    git submodule sync

    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}${CHECK} 成功: $success_count${NC}"
    if [ $fail_count -gt 0 ]; then
        echo -e "${RED}${CROSS} 失败: $fail_count${NC}"
    fi
    echo ""

    # 提示用户提交更改
    if git diff --quiet .gitmodules; then
        echo -e "${INFO} .gitmodules 无需更新"
    else
        echo -e "${YELLOW}${INFO} .gitmodules 已更新，需要提交更改：${NC}"
        echo -e "${DIM}  git add .gitmodules${NC}"
        echo -e "${DIM}  git commit -m \"chore: update submodules to ${target_branch} branch\"${NC}"
    fi
}

# 显示当前状态
show_status() {
    local current_branch=$(get_current_branch)

    echo -e "${ROCKET} ${BLUE}SAGE Submodule 状态${NC}"
    echo -e "${DIM}SAGE 分支: ${current_branch}${NC}"
    echo ""

    echo -e "${BLUE}Submodule 配置：${NC}"
    printf "%-50s %-15s %-15s\n" "Submodule" "配置分支" "当前分支"
    echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    while IFS= read -r submodule_path; do
        local submodule_name=$(basename "$submodule_path")
        local config_branch=$(get_submodule_configured_branch "$submodule_path")
        local actual_branch="N/A"

        # 检查 submodule 是否已初始化（.git 可能是文件或目录）
        if [ -e "$submodule_path/.git" ]; then
            actual_branch=$(cd "$submodule_path" && git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "detached")
        fi

        # 颜色标记
        if [ "$config_branch" = "$actual_branch" ]; then
            printf "%-50s ${GREEN}%-15s${NC} ${GREEN}%-15s${NC}\n" "$submodule_name" "$config_branch" "$actual_branch"
        else
            printf "%-50s ${YELLOW}%-15s${NC} ${RED}%-15s${NC}\n" "$submodule_name" "$config_branch" "$actual_branch"
        fi
    done < <(get_submodules)

    echo ""
}

# 显示帮助
show_help() {
    echo -e "${ROCKET} ${BOLD}SAGE Submodule 分支管理工具${NC}"
    echo ""
    echo -e "${BOLD}用法:${NC}"
    echo -e "  $0 [命令] [选项]"
    echo ""
    echo -e "${BOLD}命令:${NC}"
    echo -e "  ${GREEN}switch${NC}            根据当前 SAGE 分支切换 submodules 到对应分支并拉取最新代码"
    echo -e "                    - main 分支 → submodules 的 main 分支"
    echo -e "                    - 其他分支 → submodules 的 main-dev 分支"
    echo -e "                    - 自动 fetch 远程并 pull 最新代码"
    echo -e "  ${GREEN}status${NC}            显示当前 submodule 分支状态"
    echo -e "  ${GREEN}help${NC}              显示此帮助信息"
    echo ""
    echo -e "${BOLD}示例:${NC}"
    echo -e "  # 切换 submodule 分支（根据当前 SAGE 分支）"
    echo -e "  $0 switch"
    echo ""
    echo -e "  # 查看当前状态"
    echo -e "  $0 status"
    echo ""
    echo -e "${BOLD}工作流程:${NC}"
    echo -e "  1. 切换 SAGE 分支后运行 'switch' 自动同步 submodule 分支"
    echo -e "  2. 运行 'status' 查看当前配置"
    echo ""
    echo -e "${BOLD}前置条件:${NC}"
    echo -e "  - 所有 submodules 的远程仓库已有 main 和 main-dev 分支"
    echo -e "  - 你有相应的访问权限"
}

# 主程序
main() {
    # 检查是否在 git 仓库中
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        echo -e "${RED}${CROSS} 错误：当前目录不是 git 仓库${NC}"
        exit 1
    fi

    # 检查是否在 SAGE 根目录
    if [ ! -f ".gitmodules" ]; then
        echo -e "${RED}${CROSS} 错误：未找到 .gitmodules 文件${NC}"
        echo -e "${DIM}请在 SAGE 项目根目录运行此脚本${NC}"
        exit 1
    fi

    case "${1:-switch}" in
        switch)
            switch_submodules
            ;;
        status)
            show_status
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            echo -e "${RED}${CROSS} 未知命令: $1${NC}"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

main "$@"
