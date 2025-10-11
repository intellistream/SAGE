#!/bin/bash
# 🔄 SAGE Submodule 分支管理脚本
# 功能：根据当前 SAGE 分支自动切换 submodule 到对应分支
# - main 分支 → submodules 的 main 分支
# - 其他分支 → submodules 的 main-dev 分支

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
    git fetch origin "$branch_name" 2>/dev/null
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

# 切换 submodule 到指定分支
switch_submodule_branch() {
    local submodule_path="$1"
    local target_branch="$2"
    local submodule_name=$(basename "$submodule_path")
    
    if [ ! -d "$submodule_path/.git" ] && [ ! -f "$submodule_path/.git" ]; then
        echo -e "${YELLOW}  ⚠️  Submodule ${submodule_name} 未初始化${NC}"
        return 1
    fi
    
    cd "$submodule_path"

    # 获取远程分支，若失败则继续使用本地引用
    if ! git fetch origin >/dev/null 2>&1; then
        echo -e "${YELLOW}  ⚠️ 无法访问远程 origin，使用本地引用尝试切换${NC}"
    fi

    local target_ref="origin/$target_branch"
    if ! git show-ref --verify --quiet "refs/remotes/$target_ref"; then
        if git show-ref --verify --quiet "refs/heads/$target_branch"; then
            target_ref="$target_branch"
        else
            echo -e "${RED}  ${CROSS} 未找到 ${target_branch} 对应的远程或本地分支${NC}"
            cd - > /dev/null
            return 1
        fi
    fi

    # 切换分支
    echo -e "${DIM}  切换到 ${target_branch} 分支...${NC}"
    if ! git checkout -B "$target_branch" "$target_ref" >/dev/null 2>&1; then
        echo -e "${RED}  ${CROSS} 无法切换到 ${target_branch}${NC}"
        cd - > /dev/null
        return 1
    fi

    echo -e "${GREEN}  ${CHECK} 已切换到 ${target_branch}${NC}"
    cd - > /dev/null
    return 0
}

# 初始化 submodules（如果需要）
init_submodules() {
    echo -e "${BLUE}🔍 检查 submodule 初始化状态...${NC}"
    
    local need_init=false
    while IFS= read -r submodule_path; do
        if [ ! -d "$submodule_path/.git" ]; then
            need_init=true
            break
        fi
    done < <(get_submodules)
    
    if [ "$need_init" = true ]; then
        echo -e "${DIM}初始化 submodules...${NC}"
        git submodule sync --recursive >/dev/null 2>&1 || true
        git config --file .git/config --remove-section "submodule.packages/sage-middleware/src/sage/middleware/components/sage_vllm/sageLLM" >/dev/null 2>&1 || true
        if git submodule update --init --recursive; then
            echo -e "${CHECK} Submodules 初始化完成${NC}"
        else
            echo -e "${YELLOW}  ⚠️ 检测到旧的 submodule 路径（可能正在重定位），跳过自动初始化${NC}"
        fi
    else
        echo -e "${CHECK} 所有 submodules 已初始化${NC}"
    fi
}

# 主函数：切换 submodule 分支
switch_submodules() {
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
    
    # 确保 submodules 已初始化
    init_submodules
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
    echo -e "  ${GREEN}switch${NC}            根据当前 SAGE 分支切换 submodules 到对应分支"
    echo -e "                    - main 分支 → submodules 的 main 分支"
    echo -e "                    - 其他分支 → submodules 的 main-dev 分支"
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
